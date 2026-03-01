import * as PIXI from "pixi.js";
import type { SimSimEvent, SimSimPrompt, SimSimRoom, SimSimViewerState } from "./simSimStore";
import { deriveEventRailCards, deriveForecastBandsPerRoom, deriveSecurityDirective } from "./viewModel";
import type { EventRailCard, ForecastBand, ForecastRoomBands, SecurityDirective } from "./viewModel";

type Vec2 = { x: number; y: number };
type Bounds = { min_x: number; min_y: number; max_x: number; max_y: number };
type SubmitPromptChoice = {
    tickTarget: number;
    promptId: string;
    choice: string;
};
type AdvanceDayPayload = {
    tickTarget: number;
};
type ApplySupervisorPlacementsPayload = {
    tickTarget: number;
    setSupervisors: Record<string, string | null>;
};
type SimSimSceneOpts = {
    onSubmitPromptChoice?: (payload: SubmitPromptChoice) => void;
    onAdvanceDay?: (payload: AdvanceDayPayload) => void;
    onApplySupervisorPlacements?: (payload: ApplySupervisorPlacementsPayload) => void;
};
type PlacementDraft = Record<number, string | null>;

const FALLBACK_LAYOUT: Record<number, Bounds> = {
    1: { min_x: 0, min_y: 0, max_x: 12, max_y: 8 },
    2: { min_x: 12, min_y: 0, max_x: 24, max_y: 8 },
    3: { min_x: 24, min_y: 0, max_x: 36, max_y: 8 },
    4: { min_x: 0, min_y: 8, max_x: 12, max_y: 16 },
    5: { min_x: 12, min_y: 8, max_x: 24, max_y: 16 },
    6: { min_x: 24, min_y: 8, max_x: 36, max_y: 16 },
};

export class SimSimScene {
    public readonly app: PIXI.Application;
    private readonly showDevUi = isSimSimDevUiEnabled();

    private mountEl?: HTMLElement;
    private ready = false;
    private visible = true;
    private pendingState?: SimSimViewerState;
    private readonly root = new PIXI.Container();
    private readonly roomLayer = new PIXI.Container();
    private readonly supervisorLayer = new PIXI.Container();
    private readonly uiLayer = new PIXI.Container();
    private overlayRoot?: HTMLDivElement;
    private hudEl?: HTMLDivElement;
    private roomCardsEl?: HTMLDivElement;
    private eventsEl?: HTMLDivElement;
    private promptsEl?: HTMLDivElement;
    private debugPanelEl?: HTMLDivElement;
    private advanceDayButtonEl?: HTMLButtonElement;
    private advanceStatusEl?: HTMLDivElement;
    private securityDirectivePanelEl?: HTMLDivElement;
    private supervisorPanelEl?: HTMLDivElement;
    private placementControlsEl?: HTMLDivElement;
    private debugVisible = false;
    private lastState?: SimSimViewerState;
    private placementsBaseline: PlacementDraft = {};
    private placementsDraft: PlacementDraft = {};
    private placementsHistory: PlacementDraft[] = [];
    private selectedSupId: string | null = null;
    private selectedRoomId: number | null = null;
    private placementInteractionStatus: { text: string; color: string } | null = null;
    private lastPlacementSyncTick: number | null = null;
    private lastPlacementSyncSignature = "";
    private advanceInFlight = false;
    private advanceInFlightStateKey: string | null = null;
    private advanceStatusOverride: { text: string; color: string; untilMs: number } | null = null;
    private promptsFlashTimer: number | null = null;
    private eventRailExpandedCardId: string | null = null;
    private liveFeedCollapsed = true;
    private debugFeedVisible = false;
    private readonly onSubmitPromptChoice?: (payload: SubmitPromptChoice) => void;
    private readonly onAdvanceDay?: (payload: AdvanceDayPayload) => void;
    private readonly onApplySupervisorPlacements?: (payload: ApplySupervisorPlacementsPayload) => void;

    constructor(mountEl: HTMLElement, opts?: SimSimSceneOpts) {
        this.onSubmitPromptChoice = opts?.onSubmitPromptChoice;
        this.onAdvanceDay = opts?.onAdvanceDay;
        this.onApplySupervisorPlacements = opts?.onApplySupervisorPlacements;
        this.app = new PIXI.Application();
        void this.init(mountEl);
    }

    private async init(mountEl: HTMLElement): Promise<void> {
        this.mountEl = mountEl;
        await this.app.init({
            resizeTo: mountEl,
            antialias: true,
            backgroundAlpha: 0,
        });

        mountEl.appendChild(this.app.canvas);
        this.root.addChild(this.roomLayer, this.supervisorLayer, this.uiLayer);
        this.app.stage.addChild(this.root);
        this.installOverlay(mountEl);
        this.ready = true;
        this.setVisible(this.visible);

        if (this.pendingState) {
            const s = this.pendingState;
            this.pendingState = undefined;
            this.renderFromState(s);
        }
    }

    setVisible(visible: boolean): void {
        this.visible = visible;
        if (!this.ready) return;
        this.app.canvas.style.display = visible ? "block" : "none";
        if (this.overlayRoot) this.overlayRoot.style.display = visible ? "block" : "none";
    }

    refreshLayout(opts?: { forceAutoFit?: boolean }): void {
        if (!this.ready || !this.mountEl) return;
        const rect = this.mountEl.getBoundingClientRect();
        const width = Math.max(1, Math.floor(rect.width));
        const height = Math.max(1, Math.floor(rect.height));
        this.app.renderer.resize(width, height);
        if (opts?.forceAutoFit && this.lastState) this.renderFromState(this.lastState);
    }

    renderFromState(state: SimSimViewerState): void {
        if (!this.ready) {
            this.pendingState = state;
            return;
        }
        const previousState = this.lastState;
        this.lastState = state;

        const updateKey = this.stateUpdateKey(state);
        if (this.advanceInFlight && this.advanceInFlightStateKey !== updateKey) {
            this.advanceInFlight = false;
            this.advanceInFlightStateKey = null;
        }

        this.roomLayer.removeChildren();
        this.supervisorLayer.removeChildren();
        this.uiLayer.removeChildren();

        const rooms = Array.from(state.rooms.values()).sort((a, b) => a.room_id - b.room_id);
        this.syncPlacementEditorState(state, rooms);
        const stageBounds = this.computeStageBounds(rooms);
        const toScreen = this.makeProjector(stageBounds);
        const events = sortedEvents(state.events);
        const securityDirective = deriveSecurityDirective(this.resolveSecurityLeadCode(state, rooms), events);
        const forecastByRoom = new Map<number, ForecastRoomBands>(
            deriveForecastBandsPerRoom(rooms, securityDirective).map((forecast) => [forecast.roomId, forecast])
        );

        for (const room of rooms) {
            const draftSupervisorCode = this.placementsDraft[room.room_id] ?? room.supervisor ?? null;
            const supervisorName = draftSupervisorCode ? (state.supervisors.get(draftSupervisorCode)?.name ?? draftSupervisorCode) : "Unassigned";
            this.drawRoom(room, toScreen, {
                draftSupervisorCode,
                supervisorName,
                forecast: forecastByRoom.get(room.room_id),
                tick: state.tick,
            });
        }

        const eventLines = events.slice(-3).map((ev) => `t${ev.tick} #${ev.event_id} ${ev.kind}`);
        const caption = new PIXI.Text({
            text: `sim_sim   tick=${state.tick}\n${eventLines.join("\n")}`,
            style: {
                fontFamily: "Bricolage Grotesque, sans-serif",
                fontSize: 14,
                fill: 0xf3efe3,
                stroke: { color: 0x161b20, width: 3 },
            },
        });
        caption.x = 18;
        caption.y = 16;
        this.uiLayer.addChild(caption);

        if (state.desynced) {
            const banner = new PIXI.Text({
                text: `DESYNC: ${state.desyncReason ?? "unknown"}`,
                style: {
                    fontFamily: "Bricolage Grotesque, sans-serif",
                    fontSize: 16,
                    fill: 0xffd8cf,
                    stroke: { color: 0x2a0f0f, width: 4 },
                },
            });
            banner.x = 18;
            banner.y = this.app.renderer.height - 38;
            this.uiLayer.addChild(banner);
        }

        const prompts = sortedPrompts(state.prompts);
        this.renderOverlay(state, events, prompts, {
            previousState,
            securityDirective,
            forecastByRoom,
        });
    }

    private computeStageBounds(rooms: SimSimRoom[]): Bounds {
        if (rooms.length === 0) return { min_x: 0, min_y: 0, max_x: 36, max_y: 16 };
        let minX = Number.POSITIVE_INFINITY;
        let minY = Number.POSITIVE_INFINITY;
        let maxX = Number.NEGATIVE_INFINITY;
        let maxY = Number.NEGATIVE_INFINITY;
        for (const room of rooms) {
            const b = this.roomBounds(room);
            minX = Math.min(minX, b.min_x);
            minY = Math.min(minY, b.min_y);
            maxX = Math.max(maxX, b.max_x);
            maxY = Math.max(maxY, b.max_y);
        }
        return { min_x: minX, min_y: minY, max_x: maxX, max_y: maxY };
    }

    private makeProjector(stage: Bounds): (x: number, y: number) => Vec2 {
        const padX = 48;
        const padY = 76;
        const width = Math.max(1, this.app.renderer.width);
        const height = Math.max(1, this.app.renderer.height);
        const spanX = Math.max(1e-6, stage.max_x - stage.min_x);
        const spanY = Math.max(1e-6, stage.max_y - stage.min_y);
        const scale = Math.min((width - padX * 2) / spanX, (height - padY * 2) / spanY);
        const baseX = (width - spanX * scale) * 0.5;
        const baseY = (height - spanY * scale) * 0.5;
        return (x: number, y: number) => ({
            x: baseX + (x - stage.min_x) * scale,
            y: baseY + (y - stage.min_y) * scale,
        });
    }

    private drawRoom(
        room: SimSimRoom,
        toScreen: (x: number, y: number) => Vec2,
        data: {
            draftSupervisorCode: string | null;
            supervisorName: string;
            forecast: ForecastRoomBands | undefined;
            tick: number;
        }
    ): void {
        const { draftSupervisorCode, supervisorName, forecast, tick } = data;
        const b = this.roomBounds(room);
        const topLeft = toScreen(b.min_x, b.min_y);
        const bottomRight = toScreen(b.max_x, b.max_y);
        const width = Math.max(8, bottomRight.x - topLeft.x);
        const height = Math.max(8, bottomRight.y - topLeft.y);
        const locked = room.locked;
        const fill = locked ? 0x402d2d : 0x223644;
        const line = locked ? 0xe89f8f : 0x8cd6c8;
        const rect = new PIXI.Graphics();
        rect.roundRect(topLeft.x, topLeft.y, width, height, 10);
        rect.fill({ color: fill, alpha: locked ? 0.92 : 0.82 });
        rect.stroke({ width: locked ? 3 : 2, color: line, alpha: 0.95 });
        this.roomLayer.addChild(rect);
        const hazardCritical = isHazardCriticalForecast(forecast);
        const equipmentLow = isEquipmentLow(room.equipment_condition);
        if (!locked && hazardCritical) {
            this.drawHazardStripes(topLeft, width, height, tick);
        }
        if (!locked && equipmentLow) {
            this.drawEquipmentWear(topLeft, width, height, room.room_id);
        }

        const label = new PIXI.Text({
            text: room.name ?? `Room ${room.room_id}`,
            style: {
                fontFamily: "Bricolage Grotesque, sans-serif",
                fontSize: 13,
                fill: 0xf4efe2,
                stroke: { color: 0x161b20, width: 3 },
            },
        });
        label.x = topLeft.x + 8;
        label.y = topLeft.y + 7;
        this.roomLayer.addChild(label);
        const microStats = roomMicroStatsLabel(room);
        if (microStats) {
            const stats = new PIXI.Text({
                text: microStats,
                style: {
                    fontFamily: "Chivo Mono, monospace",
                    fontSize: 10,
                    fill: 0xd6dde2,
                    stroke: { color: 0x12161a, width: 2 },
                    letterSpacing: 0.3,
                },
            });
            stats.x = topLeft.x + 8;
            stats.y = topLeft.y + Math.max(24, height - stats.height - 7);
            this.roomLayer.addChild(stats);
        }
        if (!locked) {
            this.drawRoomSupervisorAnchor(topLeft, width, height, draftSupervisorCode, supervisorName);
        }
    }

    private drawRoomSupervisorAnchor(topLeft: Vec2, width: number, height: number, code: string | null, supervisorName: string): void {
        const radius = Math.max(10, Math.min(16, Math.min(width, height) * 0.14));
        const x = topLeft.x + width - radius - 8;
        const y = topLeft.y + radius + 8;
        const assigned = Boolean(code);

        const socket = new PIXI.Graphics();
        socket.circle(x, y, radius + 3);
        socket.stroke({
            width: 1.5,
            color: assigned ? 0xf3c76a : 0x8b98a4,
            alpha: assigned ? 0.55 : 0.4,
        });
        this.supervisorLayer.addChild(socket);

        const token = new PIXI.Graphics();
        token.circle(x, y, radius);
        token.fill({ color: assigned ? 0x2a3944 : 0x22252a, alpha: 0.96 });
        token.stroke({
            width: assigned ? 2.2 : 1.4,
            color: assigned ? 0xf3c76a : 0x8b98a4,
            alpha: assigned ? 0.98 : 0.76,
        });
        this.supervisorLayer.addChild(token);

        const label = new PIXI.Text({
            text: code ?? "—",
            style: {
                fontFamily: "Chivo Mono, monospace",
                fontSize: Math.max(10, Math.floor(radius * 0.95)),
                fill: assigned ? 0xf3efe3 : 0xb4bec8,
                fontWeight: "700",
                stroke: { color: 0x151a1f, width: 2 },
            },
        });
        label.x = x - label.width * 0.5;
        label.y = y - label.height * 0.52;
        this.supervisorLayer.addChild(label);

        const nameplate = new PIXI.Text({
            text: assigned ? `${code ?? "—"} • ${supervisorName}` : "UNASSIGNED",
            style: {
                fontFamily: "Bricolage Grotesque, sans-serif",
                fontSize: 9,
                fill: assigned ? 0xe8edf2 : 0xc2c8cf,
                stroke: { color: 0x0f151a, width: 2 },
                letterSpacing: 0.2,
            },
        });
        const platePadX = 6;
        const platePadY = 2;
        const plateHeight = nameplate.height + platePadY * 2;
        const maxPlateWidth = Math.max(36, width - 12);
        const plateWidth = Math.min(maxPlateWidth, Math.max(56, nameplate.width + platePadX * 2));
        const plateX = clamp(topLeft.x + 6, x - plateWidth * 0.5, topLeft.x + width - plateWidth - 6);
        const plateY = y + radius + 4;

        const plate = new PIXI.Graphics();
        plate.roundRect(plateX, plateY, plateWidth, plateHeight, 6);
        plate.fill({ color: 0x141f27, alpha: 0.86 });
        plate.stroke({
            width: 1,
            color: assigned ? 0xf3c76a : 0x9ba7b2,
            alpha: assigned ? 0.46 : 0.34,
        });
        this.supervisorLayer.addChild(plate);

        nameplate.x = plateX + (plateWidth - nameplate.width) * 0.5;
        nameplate.y = plateY + platePadY;
        this.supervisorLayer.addChild(nameplate);
    }

    private drawHazardStripes(topLeft: Vec2, width: number, height: number, tick: number): void {
        const pulse = 0.15 + ((((Math.sin((tick + 1) * 0.9) + 1) * 0.5) * 0.16));
        const stripes = new PIXI.Graphics();
        const spacing = 12;
        for (let offset = -height; offset < width + height; offset += spacing) {
            stripes.moveTo(topLeft.x + offset, topLeft.y);
            stripes.lineTo(topLeft.x + offset + height, topLeft.y + height);
        }
        stripes.stroke({
            width: 3,
            color: 0xe77b4b,
            alpha: pulse,
        });
        this.roomLayer.addChild(stripes);
    }

    private drawEquipmentWear(topLeft: Vec2, width: number, height: number, roomId: number): void {
        const wear = new PIXI.Graphics();
        const seed = (roomId % 7) + 1;
        const crackAStartX = topLeft.x + width * (0.12 + (seed * 0.03));
        const crackAStartY = topLeft.y + height * 0.28;
        const crackAEndX = topLeft.x + width * 0.62;
        const crackAEndY = topLeft.y + height * 0.76;
        const crackBStartX = topLeft.x + width * (0.55 + (seed * 0.01));
        const crackBStartY = topLeft.y + height * 0.22;
        const crackBEndX = topLeft.x + width * 0.86;
        const crackBEndY = topLeft.y + height * 0.54;

        wear.moveTo(crackAStartX, crackAStartY);
        wear.lineTo(crackAEndX, crackAEndY);
        wear.moveTo(crackAStartX + 10, crackAStartY + 8);
        wear.lineTo(crackAEndX - 8, crackAEndY - 10);
        wear.moveTo(crackBStartX, crackBStartY);
        wear.lineTo(crackBEndX, crackBEndY);
        wear.stroke({ width: 1.6, color: 0x8d5b40, alpha: 0.36 });
        wear.circle(topLeft.x + width * 0.18, topLeft.y + height * 0.74, 4.2);
        wear.circle(topLeft.x + width * 0.76, topLeft.y + height * 0.19, 3.1);
        wear.fill({ color: 0x8f4f2f, alpha: 0.2 });
        this.roomLayer.addChild(wear);
    }

    private roomBounds(room: SimSimRoom): Bounds {
        if (room.bounds) return room.bounds;
        return FALLBACK_LAYOUT[room.room_id] ?? { min_x: 0, min_y: 0, max_x: 10, max_y: 6 };
    }

    private installOverlay(mountEl: HTMLElement): void {
        const root = document.createElement("div");
        root.style.position = "absolute";
        root.style.inset = "0";
        root.style.pointerEvents = "none";
        root.style.zIndex = "22";
        root.style.fontFamily = "\"Bricolage Grotesque\", sans-serif";
        root.style.color = "#f3efe3";

        const hud = document.createElement("div");
        hud.style.position = "absolute";
        hud.style.left = "14px";
        hud.style.top = "12px";
        hud.style.padding = "9px 11px";
        hud.style.borderRadius = "10px";
        hud.style.background = "rgba(10, 13, 18, 0.82)";
        hud.style.border = "1px solid rgba(140, 214, 200, 0.36)";
        hud.style.fontSize = "11px";
        hud.style.lineHeight = "1.4";
        hud.style.pointerEvents = "auto";
        hud.style.width = "min(350px, 26vw)";
        hud.style.maxHeight = "20vh";
        hud.style.overflow = "hidden auto";
        root.appendChild(hud);

        const advanceControls = document.createElement("div");
        advanceControls.style.position = "absolute";
        advanceControls.style.left = "14px";
        advanceControls.style.top = "188px";
        advanceControls.style.padding = "10px 12px";
        advanceControls.style.borderRadius = "10px";
        advanceControls.style.border = "1px solid rgba(243, 199, 106, 0.45)";
        advanceControls.style.background = "rgba(24, 17, 9, 0.82)";
        advanceControls.style.pointerEvents = "auto";
        advanceControls.style.width = "min(350px, 26vw)";

        const advanceButton = document.createElement("button");
        advanceButton.type = "button";
        advanceButton.textContent = "Advance Day";
        advanceButton.style.border = "1px solid rgba(243, 199, 106, 0.75)";
        advanceButton.style.background = "rgba(38, 29, 12, 0.95)";
        advanceButton.style.color = "#f3efe3";
        advanceButton.style.borderRadius = "8px";
        advanceButton.style.padding = "6px 10px";
        advanceButton.style.fontSize = "12px";
        advanceButton.style.fontWeight = "700";
        advanceButton.style.letterSpacing = "0.03em";
        advanceButton.style.cursor = "pointer";
        advanceControls.appendChild(advanceButton);

        const advanceStatus = document.createElement("div");
        advanceStatus.style.marginTop = "7px";
        advanceStatus.style.fontSize = "11px";
        advanceStatus.style.lineHeight = "1.35";
        advanceStatus.style.opacity = "0.95";
        advanceControls.appendChild(advanceStatus);
        root.appendChild(advanceControls);

        const supervisorPanel = document.createElement("div");
        supervisorPanel.style.position = "absolute";
        supervisorPanel.style.left = "14px";
        supervisorPanel.style.top = "500px";
        supervisorPanel.style.padding = "10px 12px";
        supervisorPanel.style.borderRadius = "10px";
        supervisorPanel.style.border = "1px solid rgba(140, 214, 200, 0.42)";
        supervisorPanel.style.background = "rgba(13, 20, 28, 0.86)";
        supervisorPanel.style.pointerEvents = "auto";
        supervisorPanel.style.width = "min(350px, 26vw)";
        supervisorPanel.style.maxHeight = "30vh";
        supervisorPanel.style.overflowY = "auto";
        root.appendChild(supervisorPanel);

        const placementControls = document.createElement("div");
        placementControls.style.position = "absolute";
        placementControls.style.left = "14px";
        placementControls.style.top = "320px";
        placementControls.style.padding = "10px 12px";
        placementControls.style.borderRadius = "10px";
        placementControls.style.border = "1px solid rgba(243, 199, 106, 0.45)";
        placementControls.style.background = "rgba(24, 17, 9, 0.86)";
        placementControls.style.pointerEvents = "auto";
        placementControls.style.width = "min(350px, 26vw)";
        root.appendChild(placementControls);

        const roomCards = document.createElement("div");
        roomCards.style.position = "absolute";
        roomCards.style.right = "14px";
        roomCards.style.top = "172px";
        roomCards.style.width = "min(400px, 28vw)";
        roomCards.style.maxHeight = "58vh";
        roomCards.style.overflowY = "auto";
        roomCards.style.display = "grid";
        roomCards.style.gap = "7px";
        roomCards.style.padding = "2px 0";
        root.appendChild(roomCards);

        const securityDirectivePanel = document.createElement("div");
        securityDirectivePanel.style.position = "absolute";
        securityDirectivePanel.style.right = "14px";
        securityDirectivePanel.style.top = "14px";
        securityDirectivePanel.style.width = "min(400px, 28vw)";
        securityDirectivePanel.style.padding = "10px 12px";
        securityDirectivePanel.style.borderRadius = "10px";
        securityDirectivePanel.style.pointerEvents = "auto";
        securityDirectivePanel.style.border = "1px solid rgba(140, 214, 200, 0.42)";
        securityDirectivePanel.style.background = "rgba(13, 20, 28, 0.86)";
        securityDirectivePanel.style.overflow = "hidden";
        root.appendChild(securityDirectivePanel);

        const events = document.createElement("div");
        if (this.showDevUi) {
            events.style.position = "absolute";
            events.style.left = "14px";
            events.style.bottom = "14px";
            events.style.width = "min(460px, 34vw)";
            events.style.maxHeight = "24vh";
            events.style.overflow = "hidden auto";
            events.style.padding = "8px 10px";
            events.style.borderRadius = "10px";
            events.style.background = "rgba(10, 13, 18, 0.7)";
            events.style.border = "1px solid rgba(243, 199, 106, 0.34)";
            events.style.fontSize = "11px";
            events.style.lineHeight = "1.3";
            events.style.pointerEvents = "auto";
            events.style.display = "none";
            root.appendChild(events);
        }

        const prompts = document.createElement("div");
        prompts.style.position = "absolute";
        prompts.style.inset = "0";
        prompts.style.display = "none";
        prompts.style.pointerEvents = "none";
        prompts.style.zIndex = "60";
        root.appendChild(prompts);

        if (this.showDevUi) {
            const feedToggle = document.createElement("button");
            feedToggle.type = "button";
            feedToggle.textContent = "Debug Feed";
            feedToggle.style.position = "absolute";
            feedToggle.style.left = "14px";
            feedToggle.style.bottom = "14px";
            feedToggle.style.pointerEvents = "auto";
            feedToggle.style.border = "1px solid rgba(243, 199, 106, 0.5)";
            feedToggle.style.background = "rgba(10, 13, 18, 0.84)";
            feedToggle.style.color = "#e9e2cf";
            feedToggle.style.borderRadius = "8px";
            feedToggle.style.padding = "6px 10px";
            feedToggle.style.fontSize = "11px";
            feedToggle.style.letterSpacing = "0.06em";
            feedToggle.style.textTransform = "uppercase";
            feedToggle.addEventListener("click", () => {
                this.debugFeedVisible = !this.debugFeedVisible;
                if (this.eventsEl) this.eventsEl.style.display = this.debugFeedVisible ? "block" : "none";
                feedToggle.textContent = this.debugFeedVisible ? "Hide Debug Feed" : "Debug Feed";
            });
            root.appendChild(feedToggle);

            const debugToggle = document.createElement("button");
            debugToggle.type = "button";
            debugToggle.textContent = "Schema Debug";
            debugToggle.style.position = "absolute";
            debugToggle.style.right = "14px";
            debugToggle.style.bottom = "14px";
            debugToggle.style.pointerEvents = "auto";
            debugToggle.style.border = "1px solid rgba(140, 214, 200, 0.5)";
            debugToggle.style.background = "rgba(10, 13, 18, 0.84)";
            debugToggle.style.color = "#e9e2cf";
            debugToggle.style.borderRadius = "8px";
            debugToggle.style.padding = "6px 10px";
            debugToggle.style.fontSize = "11px";
            debugToggle.style.letterSpacing = "0.06em";
            debugToggle.style.textTransform = "uppercase";
            debugToggle.addEventListener("click", () => {
                this.debugVisible = !this.debugVisible;
                if (this.debugPanelEl) this.debugPanelEl.style.display = this.debugVisible ? "block" : "none";
            });
            root.appendChild(debugToggle);
        }

        const debugPanel = document.createElement("div");
        if (this.showDevUi) {
            debugPanel.style.position = "absolute";
            debugPanel.style.right = "14px";
            debugPanel.style.bottom = "46px";
            debugPanel.style.pointerEvents = "none";
            debugPanel.style.padding = "8px 10px";
            debugPanel.style.borderRadius = "9px";
            debugPanel.style.border = "1px solid rgba(232, 159, 143, 0.45)";
            debugPanel.style.background = "rgba(34, 16, 16, 0.88)";
            debugPanel.style.fontFamily = "\"Chivo Mono\", monospace";
            debugPanel.style.fontSize = "11px";
            debugPanel.style.lineHeight = "1.4";
            debugPanel.style.display = "none";
            root.appendChild(debugPanel);
        }

        this.overlayRoot = root;
        this.hudEl = hud;
        this.roomCardsEl = roomCards;
        this.securityDirectivePanelEl = securityDirectivePanel;
        this.eventsEl = events;
        this.promptsEl = prompts;
        this.debugPanelEl = debugPanel;
        this.advanceDayButtonEl = advanceButton;
        this.advanceStatusEl = advanceStatus;
        this.supervisorPanelEl = supervisorPanel;
        this.placementControlsEl = placementControls;

        mountEl.appendChild(root);
    }

    private renderOverlay(
        state: SimSimViewerState,
        events: SimSimEvent[],
        prompts: SimSimPrompt[],
        overlayData: {
            previousState?: SimSimViewerState;
            securityDirective: SecurityDirective;
            forecastByRoom: Map<number, ForecastRoomBands>;
        }
    ): void {
        if (
            !this.hudEl ||
            !this.roomCardsEl ||
            !this.promptsEl ||
            !this.securityDirectivePanelEl ||
            !this.supervisorPanelEl ||
            !this.placementControlsEl
        )
            return;
        const previousState = overlayData.previousState;
        const wm = state.worldMeta;
        const inv = state.inventory;
        const regime = state.regime;
        const currentPhase = normalizePhaseToken(wm?.phase);
        const previousPhase = normalizePhaseToken(previousState?.worldMeta?.phase);
        const awaitingPrompts = currentPhase === "awaiting_prompts";
        const planningPhase = currentPhase === "planning";
        const endOfDayPhase = currentPhase === "end_of_day";
        const controlsDisabled = !planningPhase || state.desynced;
        const enteredDecisionGate =
            (previousPhase === "planning" && (awaitingPrompts || endOfDayPhase)) ||
            (previousPhase === "awaiting_prompts" && endOfDayPhase);
        const enteredAwaitingPrompts = previousPhase === "planning" && awaitingPrompts;
        if (enteredDecisionGate) {
            this.advanceStatusOverride = {
                text: awaitingPrompts
                    ? "Day requires a decision - resolve prompts to continue."
                    : "Planning closed - submit end-of-day actions to continue.",
                color: "#f3c76a",
                untilMs: Date.now() + 4000,
            };
        }
        const tickTarget = state.tick + 1;
        this.roomCardsEl.style.pointerEvents = "auto";

        const activeFlags: string[] = [];
        if (regime) {
            if (regime.refactor_days > 0) activeFlags.push(`refactor(${regime.refactor_days})`);
            if (regime.inversion_days > 0) activeFlags.push(`inversion(${regime.inversion_days})`);
            if (regime.shutdown_except_brewery_today) activeFlags.push("shutdown_except_brewery");
            if (regime.weaving_boost_next_day) activeFlags.push("weaving_boost_next_day");
            if (regime.global_accident_bonus > 0) activeFlags.push(`accident_bonus=${pct(regime.global_accident_bonus)}`);
        }
        const supervisorByCode = state.supervisors;
        const supervisorSummary = Array.from(supervisorByCode.values())
            .sort((a, b) => a.code.localeCompare(b.code))
            .map((supervisor) => `${supervisor.code} ${supervisor.name} @ ${supervisor.assigned_room ?? "-"}`)
            .join(" • ");

        this.hudEl.innerHTML = [
            `<div style="font-size:12px;font-weight:700;letter-spacing:0.04em;margin-bottom:4px;">sim_sim LIVE</div>`,
            `<div>day <strong>${wm?.day ?? "-"}</strong> • tick <strong>${wm?.tick ?? state.tick}</strong> • ${wm?.phase ?? "-"} @ ${wm?.time ?? "-"}</div>`,
            `<div>cash <strong>${inv?.cash ?? "-"}</strong> • workers ${inv?.worker_pools?.dumb_total ?? "-"}d / ${inv?.worker_pools?.smart_total ?? "-"}s</div>`,
            `<div>security lead <strong>${wm?.security_lead ?? "-"}</strong></div>`,
            `<div style="opacity:0.84;">raw ${inv?.inventories.raw_brains_dumb ?? 0}/${inv?.inventories.raw_brains_smart ?? 0} • washed ${inv?.inventories.washed_dumb ?? 0}/${inv?.inventories.washed_smart ?? 0} • sub ${inv?.inventories.substrate_gallons ?? 0} • rib ${inv?.inventories.ribbon_yards ?? 0}</div>`,
            `<div style="opacity:0.84;">${supervisorSummary || "none unlocked"}</div>`,
            `<div style="opacity:0.78;">regime: ${activeFlags.length ? activeFlags.join(", ") : "none"}</div>`,
            planningPhase
                ? `<div style="color:#c4d6e1;opacity:0.86;">Flow: swap on map → Apply Draft → Advance Day</div>`
                : "",
            awaitingPrompts
                ? `<div style="color:#f3c76a;">phase awaiting_prompts: placements and advance disabled until prompt resolution</div>`
                : "",
            endOfDayPhase
                ? `<div style="color:#f3c76a;">phase end_of_day: planning controls disabled until end-of-day actions are submitted</div>`
                : "",
        ].join("");

        const latestRejection = findLatestInputRejection(events);
        if (this.advanceDayButtonEl) {
            const disabled = !planningPhase || state.desynced || this.advanceInFlight;
            this.advanceDayButtonEl.disabled = disabled;
            this.advanceDayButtonEl.style.opacity = disabled ? "0.55" : "1";
            this.advanceDayButtonEl.style.cursor = disabled ? "not-allowed" : "pointer";
            this.advanceDayButtonEl.onclick = disabled
                ? null
                : () => {
                      if (this.advanceInFlight) return;
                      this.advanceInFlight = true;
                      this.advanceInFlightStateKey = this.stateUpdateKey(state);
                      this.advanceStatusOverride = {
                          text: "Submitting day advance...",
                          color: "#f3efe3",
                          untilMs: Date.now() + 3000,
                      };
                      if (this.advanceDayButtonEl) {
                          this.advanceDayButtonEl.disabled = true;
                          this.advanceDayButtonEl.style.opacity = "0.55";
                          this.advanceDayButtonEl.style.cursor = "not-allowed";
                      }
                      if (this.advanceStatusEl) {
                          this.advanceStatusEl.style.color = "#f3efe3";
                          this.advanceStatusEl.textContent = "Submitting day advance...";
                      }
                      this.onAdvanceDay?.({ tickTarget });
                  };
        }
        if (this.advanceStatusEl) {
            const overrideActive =
                this.advanceStatusOverride !== null && this.advanceStatusOverride.untilMs >= Date.now();
            if (overrideActive && this.advanceStatusOverride) {
                this.advanceStatusEl.style.color = this.advanceStatusOverride.color;
                this.advanceStatusEl.textContent = this.advanceStatusOverride.text;
            } else if (state.desynced) {
                this.advanceStatusEl.style.color = "#ffd8cf";
                this.advanceStatusEl.textContent = "Advance disabled while desynced.";
            } else if (this.advanceInFlight) {
                this.advanceStatusEl.style.color = "#f3efe3";
                this.advanceStatusEl.textContent = "Submitting day advance...";
            } else if (awaitingPrompts) {
                this.advanceStatusEl.style.color = "#f3c76a";
                this.advanceStatusEl.textContent = "Resolve pending prompts before advancing.";
            } else if (endOfDayPhase) {
                this.advanceStatusEl.style.color = "#f3c76a";
                this.advanceStatusEl.textContent = "End-of-day phase: submit EOD actions to continue.";
            } else if (latestRejection) {
                this.advanceStatusEl.style.color = "#ffd8cf";
                this.advanceStatusEl.textContent = `Last rejection: ${latestRejection.reasonCode} — ${latestRejection.reason}`;
            } else {
                this.advanceStatusEl.style.color = "#f3efe3";
                this.advanceStatusEl.textContent = "Ready: submit no-op SIM_INPUT to advance one day.";
            }
        }

        const rooms = Array.from(state.rooms.values()).sort((a, b) => a.room_id - b.room_id);
        const railCards = deriveEventRailCards(events, rooms, prompts)
            .filter((card) => card.source === "event")
            .filter((card) => !isPromptLifecycleCard(card))
            .slice(-10);
        if (this.eventRailExpandedCardId && !railCards.some((card) => card.id === this.eventRailExpandedCardId)) {
            this.eventRailExpandedCardId = null;
        }
        this.renderSecurityDirectivePanel(overlayData.securityDirective);
        const swapsUsed = this.computeSwapsUsed(this.placementsDraft, this.placementsBaseline);
        const swapBudget = wm?.supervisor_swaps?.swap_budget ?? ((wm?.day ?? state.tick) <= 2 ? 1 : 2);
        const swapsRemaining = Math.max(0, swapBudget - swapsUsed);
        const changed = !this.isPlacementMapEqual(this.placementsDraft, this.placementsBaseline);
        this.renderPlacementControlsCluster(state, currentPhase, {
            controlsDisabled,
            swapsUsed,
            swapBudget,
            swapsRemaining,
            changed,
            latestRejection,
        });
        const inspectionCards = rooms
            .map((room) => {
                const acc = room.accidents_today ?? { count: 0, casualties: 0 };
                const draftCode = this.placementsDraft[room.room_id] ?? room.supervisor ?? null;
                const supervisor = draftCode ? supervisorByCode.get(draftCode) : undefined;
                const supervisorLabel = supervisor ? supervisor.name : draftCode ?? "Unassigned";
                const supervisorToken = room.locked
                    ? roomCardSupervisorTokenHtml("LK", "")
                    : roomCardSupervisorTokenHtml(draftCode ?? "—", supervisorLabel);
                return renderInspectionRoomCardHtml({
                    room,
                    phase: currentPhase,
                    tick: state.tick,
                    supervisorLabel,
                    supervisorToken,
                    accidents: acc,
                    forecast: overlayData.forecastByRoom.get(room.room_id),
                });
            })
            .join("");
        this.roomCardsEl.innerHTML = [
            renderEventRailHtml(railCards, this.eventRailExpandedCardId),
            `<div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;opacity:0.75;margin:8px 0 4px 2px;">Inspection</div>`,
            inspectionCards,
        ].join("");
        const railButtons = this.roomCardsEl.querySelectorAll<HTMLButtonElement>("[data-event-rail-card-id]");
        for (const button of railButtons) {
            button.onclick = () => {
                const cardId = button.dataset.eventRailCardId ?? "";
                this.eventRailExpandedCardId = this.eventRailExpandedCardId === cardId ? null : cardId;
                this.renderFromState(state);
            };
        }

        this.renderSupervisorPlacementsPanel(state, rooms, {
            controlsDisabled,
            swapBudget,
            swapsUsed,
            swapsRemaining,
            changed,
        });
        this.renderPromptsPanel(state, prompts, awaitingPrompts, events);
        if (enteredAwaitingPrompts && firstUnresolvedPrompt(prompts)) {
            this.focusPromptsPanel();
        }

        if (this.eventsEl && this.showDevUi) {
            const eventRows = events.slice(-14).map((event) => {
                const room = event.room_id ? ` room=${event.room_id}` : "";
                const sup = event.supervisor ? ` ${event.supervisor}` : "";
                const details = event.details ? ` ${JSON.stringify(event.details)}` : "";
                return `<div>t${event.tick} #${event.event_id} <strong>${event.kind}</strong>${room}${sup}${details}</div>`;
            });
            const visibleRows = this.liveFeedCollapsed ? eventRows.slice(-3) : eventRows;
            this.eventsEl.innerHTML = [
                `<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:4px;">`,
                `<div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;opacity:0.8;">Live Feed (Dev)</div>`,
                `<button data-live-feed-toggle="1" type="button" style="pointer-events:auto;border:1px solid rgba(243,199,106,0.55);background:rgba(24,17,9,0.9);color:#f3efe3;border-radius:7px;padding:3px 8px;font-size:10px;cursor:pointer;">${this.liveFeedCollapsed ? "Expand" : "Collapse"}</button>`,
                `</div>`,
                `<div style="max-height:${this.liveFeedCollapsed ? "68px" : "22vh"};overflow:hidden auto;display:grid;gap:2px;">${visibleRows.join("")}</div>`,
            ].join("");
            const liveFeedToggle = this.eventsEl.querySelector<HTMLButtonElement>("[data-live-feed-toggle='1']");
            if (liveFeedToggle) {
                liveFeedToggle.onclick = () => {
                    this.liveFeedCollapsed = !this.liveFeedCollapsed;
                    this.renderFromState(state);
                };
            }
        }

        if (this.debugPanelEl && this.showDevUi) {
            this.debugPanelEl.style.display = this.debugVisible ? "block" : "none";
            this.debugPanelEl.innerHTML = [
                `<div>schema_version: ${state.schemaVersion ?? state.kernelHello?.schema_version ?? "-"}</div>`,
                `<div>last_msg_type: ${state.lastMsgType ?? "-"}</div>`,
                `<div>last_applied_diff_count: ${state.lastAppliedDiffCount}</div>`,
                `<div>diffs_applied_total: ${state.diffsAppliedTotal}</div>`,
                `<div>prompts: ${state.prompts.size}</div>`,
                `<div>config: ${wm?.config_id ?? "-"}</div>`,
            ].join("");
        }
    }

    private renderSecurityDirectivePanel(directive: SecurityDirective): void {
        if (!this.securityDirectivePanelEl) return;
        const panel = this.securityDirectivePanelEl;
        panel.innerHTML = "";
        const crisp = directive.display.clarityTreatment === "crisp";

        panel.style.border = crisp ? "1px solid rgba(140, 214, 200, 0.56)" : "1px solid rgba(232, 159, 143, 0.62)";
        panel.style.boxShadow = crisp
            ? "0 10px 26px rgba(8, 15, 23, 0.42)"
            : "0 10px 24px rgba(34, 11, 11, 0.44), inset 0 0 0 1px rgba(255, 214, 207, 0.06)";
        panel.style.background = crisp
            ? "linear-gradient(160deg, rgba(9, 17, 24, 0.93), rgba(11, 18, 26, 0.87))"
            : "repeating-linear-gradient(135deg, rgba(255, 214, 207, 0.08), rgba(255, 214, 207, 0.08) 2px, rgba(17, 12, 12, 0) 2px, rgba(17, 12, 12, 0) 6px), linear-gradient(160deg, rgba(33, 16, 16, 0.9), rgba(16, 12, 14, 0.85))";

        const header = document.createElement("div");
        header.style.display = "flex";
        header.style.alignItems = "center";
        header.style.justifyContent = "space-between";
        header.style.gap = "10px";
        header.style.marginBottom = "7px";

        const title = document.createElement("div");
        title.style.fontSize = "10px";
        title.style.fontWeight = "700";
        title.style.letterSpacing = "0.08em";
        title.style.textTransform = "uppercase";
        title.style.opacity = "0.78";
        title.textContent = "Security Directive";
        header.appendChild(title);

        const stamp = document.createElement("div");
        stamp.style.fontSize = "10px";
        stamp.style.opacity = "0.72";
        stamp.textContent = `${directive.stamp} • lead ${directive.lead}`;
        header.appendChild(stamp);
        panel.appendChild(header);

        const label = document.createElement("div");
        label.style.display = "inline-flex";
        label.style.alignItems = "center";
        label.style.padding = "4px 8px";
        label.style.borderRadius = "999px";
        label.style.marginBottom = "8px";
        label.style.fontSize = "11px";
        label.style.fontWeight = "700";
        label.style.letterSpacing = "0.06em";
        label.style.textTransform = "uppercase";
        label.style.border = crisp ? "1px solid rgba(140, 214, 200, 0.58)" : "1px solid rgba(243, 199, 106, 0.62)";
        label.style.background = crisp ? "rgba(11, 32, 36, 0.52)" : "rgba(43, 26, 14, 0.44)";
        label.textContent = directive.display.label;
        panel.appendChild(label);

        const blurb = document.createElement("div");
        blurb.style.display = "grid";
        blurb.style.gap = "3px";
        blurb.style.marginBottom = "8px";
        for (const line of directive.display.blurbLines.slice(0, 2)) {
            const row = document.createElement("div");
            row.style.fontSize = "11px";
            row.style.lineHeight = "1.34";
            row.style.opacity = "0.95";
            row.textContent = line;
            blurb.appendChild(row);
        }
        panel.appendChild(blurb);

        const effects = document.createElement("div");
        effects.style.display = "flex";
        effects.style.flexWrap = "wrap";
        effects.style.gap = "6px";
        effects.style.marginBottom = "8px";
        for (const fx of directive.display.effects.slice(0, 4)) {
            const chip = document.createElement("div");
            chip.style.display = "inline-flex";
            chip.style.alignItems = "center";
            chip.style.gap = "4px";
            chip.style.fontSize = "10px";
            chip.style.padding = "3px 6px";
            chip.style.borderRadius = "7px";
            chip.style.border = crisp ? "1px solid rgba(140, 214, 200, 0.26)" : "1px solid rgba(232, 159, 143, 0.4)";
            chip.style.background = crisp ? "rgba(8, 18, 22, 0.58)" : "rgba(31, 14, 16, 0.62)";

            const icon = document.createElement("span");
            icon.style.fontFamily = "\"Chivo Mono\", monospace";
            icon.style.opacity = "0.9";
            icon.textContent = fx.icon;
            chip.appendChild(icon);

            const text = document.createElement("span");
            text.style.opacity = "0.88";
            text.textContent = fx.text;
            chip.appendChild(text);
            effects.appendChild(chip);
        }
        panel.appendChild(effects);

        const clarity = document.createElement("div");
        clarity.style.display = "flex";
        clarity.style.alignItems = "center";
        clarity.style.justifyContent = "space-between";
        clarity.style.fontSize = "10px";
        clarity.style.letterSpacing = "0.06em";
        clarity.style.textTransform = "uppercase";
        clarity.style.opacity = "0.88";
        clarity.innerHTML = `<span>${directive.display.clarityHint}</span><span>clarity ${pct(directive.clarity)}</span>`;
        panel.appendChild(clarity);
    }

    private resolveSecurityLeadCode(state: SimSimViewerState, rooms: SimSimRoom[]): string {
        const securityRoom =
            rooms.find((room) => room.name.trim().toLowerCase() === "security") ??
            rooms.find((room) => room.room_id === 1);
        const draftLead =
            securityRoom !== undefined ? (this.placementsDraft[securityRoom.room_id] ?? securityRoom.supervisor ?? null) : null;
        return (draftLead ?? state.worldMeta?.security_lead ?? "L").trim();
    }

    private focusPromptsPanel(): void {
        if (!this.promptsEl) return;
        const popup = this.promptsEl.querySelector<HTMLElement>("[data-spotlight-popup='1']");
        if (!popup) return;
        popup.style.transition = "transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease";
        popup.style.transform = "scale(1.01)";
        popup.style.borderColor = "rgba(243, 199, 106, 0.95)";
        popup.style.boxShadow = "0 0 0 2px rgba(243, 199, 106, 0.28), 0 26px 56px rgba(5, 8, 12, 0.72)";
        if (this.promptsFlashTimer !== null) {
            window.clearTimeout(this.promptsFlashTimer);
        }
        this.promptsFlashTimer = window.setTimeout(() => {
            if (!this.promptsEl) return;
            const activePopup = this.promptsEl.querySelector<HTMLElement>("[data-spotlight-popup='1']");
            if (!activePopup) return;
            activePopup.style.transform = "scale(1)";
            activePopup.style.borderColor = "rgba(243, 199, 106, 0.52)";
            activePopup.style.boxShadow = "0 24px 52px rgba(4, 8, 13, 0.72)";
            this.promptsFlashTimer = null;
        }, 800);
    }

    private stateUpdateKey(state: SimSimViewerState): string {
        return `${state.lastMsgType ?? "-"}|${state.tick}|${state.stepHash ?? "-"}|${state.diffsAppliedTotal}|${state.lastAppliedDiffCount}`;
    }

    private syncPlacementEditorState(state: SimSimViewerState, rooms: SimSimRoom[]): void {
        const baseline = this.extractBaselinePlacements(state, rooms);
        const signature = this.placementSignature(baseline);
        if (this.lastPlacementSyncTick !== state.tick || this.lastPlacementSyncSignature !== signature) {
            this.placementsBaseline = this.clonePlacementMap(baseline);
            this.placementsDraft = this.clonePlacementMap(baseline);
            this.placementsHistory = [];
            this.placementInteractionStatus = null;
            this.unselect();
            this.lastPlacementSyncTick = state.tick;
            this.lastPlacementSyncSignature = signature;
        }
    }

    private extractBaselinePlacements(state: SimSimViewerState, rooms: SimSimRoom[]): PlacementDraft {
        const baseline: PlacementDraft = {};
        const unlockedRooms = rooms.filter((room) => !room.locked);
        for (const room of unlockedRooms) {
            baseline[room.room_id] = null;
        }

        const bySupervisor = state.worldMeta?.supervisor_swaps?.placements_current;
        if (bySupervisor && typeof bySupervisor === "object") {
            for (const [supCode, rawRoomId] of Object.entries(bySupervisor)) {
                const parsedRoomId =
                    typeof rawRoomId === "number"
                        ? rawRoomId
                        : typeof rawRoomId === "string"
                          ? Number(rawRoomId)
                          : NaN;
                if (!Number.isFinite(parsedRoomId)) continue;
                const roomId = Number(parsedRoomId);
                if (!Object.prototype.hasOwnProperty.call(baseline, roomId)) continue;
                baseline[roomId] = supCode;
            }
            return baseline;
        }

        for (const room of unlockedRooms) {
            baseline[room.room_id] = room.supervisor ?? null;
        }
        return baseline;
    }

    private placementSignature(placements: PlacementDraft): string {
        const ordered = Object.keys(placements)
            .map((roomId) => Number(roomId))
            .filter((roomId) => Number.isFinite(roomId))
            .sort((a, b) => a - b)
            .map((roomId) => [roomId, placements[roomId] ?? null]);
        return JSON.stringify(ordered);
    }

    private clonePlacementMap(placements: PlacementDraft): PlacementDraft {
        const clone: PlacementDraft = {};
        for (const [roomId, supId] of Object.entries(placements)) {
            clone[Number(roomId)] = supId ?? null;
        }
        return clone;
    }

    private isPlacementMapEqual(left: PlacementDraft, right: PlacementDraft): boolean {
        const keys = new Set<string>([...Object.keys(left), ...Object.keys(right)]);
        for (const key of keys) {
            const roomId = Number(key);
            if ((left[roomId] ?? null) !== (right[roomId] ?? null)) return false;
        }
        return true;
    }

    private resetDraftToBaseline(): void {
        this.placementsDraft = this.clonePlacementMap(this.placementsBaseline);
        this.placementsHistory = [];
        this.placementInteractionStatus = null;
        this.unselect();
    }

    private pushHistory(): void {
        this.placementsHistory.push(this.clonePlacementMap(this.placementsDraft));
        if (this.placementsHistory.length > 50) {
            this.placementsHistory.shift();
        }
    }

    private undo(): void {
        const previous = this.placementsHistory.pop();
        if (!previous) return;
        this.placementsDraft = this.clonePlacementMap(previous);
        this.unselect();
    }

    private unselect(): void {
        this.selectedSupId = null;
        this.selectedRoomId = null;
    }

    private computeSwapsUsed(draft: PlacementDraft, baseline: PlacementDraft): number {
        const keys = new Set<string>([...Object.keys(baseline), ...Object.keys(draft)]);
        let changed = 0;
        for (const key of keys) {
            const roomId = Number(key);
            if ((baseline[roomId] ?? null) !== (draft[roomId] ?? null)) {
                changed += 1;
            }
        }
        return Math.floor((changed + 1) / 2);
    }

    private swapDraftBetweenRooms(args: {
        roomId: number;
        otherRoomId: number;
    }): PlacementDraft {
        const { roomId, otherRoomId } = args;
        const nextDraft = this.clonePlacementMap(this.placementsDraft);
        const supA = nextDraft[roomId] ?? null;
        const supB = nextDraft[otherRoomId] ?? null;
        nextDraft[roomId] = supB;
        nextDraft[otherRoomId] = supA;
        return nextDraft;
    }

    private onRoomSupervisorTokenClick(args: {
        roomId: number;
        supervisorCode: string | null;
        swapBudget: number;
        controlsDisabled: boolean;
        state: SimSimViewerState;
    }): void {
        const { roomId, supervisorCode, swapBudget, controlsDisabled, state } = args;
        if (controlsDisabled || !supervisorCode) return;

        if (this.selectedRoomId === null) {
            this.selectedRoomId = roomId;
            this.selectedSupId = supervisorCode;
            this.placementInteractionStatus = null;
            this.renderFromState(state);
            return;
        }

        if (this.selectedRoomId === roomId) {
            this.unselect();
            this.placementInteractionStatus = null;
            this.renderFromState(state);
            return;
        }

        if (swapBudget - this.computeSwapsUsed(this.placementsDraft, this.placementsBaseline) <= 0) {
            this.placementInteractionStatus = { text: "No swaps remaining.", color: "#ffd8cf" };
            this.renderFromState(state);
            return;
        }

        const nextDraft = this.swapDraftBetweenRooms({
            roomId: this.selectedRoomId,
            otherRoomId: roomId,
        });
        const swapsUsedIfApplied = this.computeSwapsUsed(nextDraft, this.placementsBaseline);
        if (swapsUsedIfApplied > swapBudget) {
            this.placementInteractionStatus = { text: "No swaps remaining.", color: "#ffd8cf" };
            this.renderFromState(state);
            return;
        }

        this.pushHistory();
        this.placementsDraft = nextDraft;
        this.placementInteractionStatus = {
            text: `Swapped room ${this.selectedRoomId} with room ${roomId}.`,
            color: "#f3efe3",
        };
        this.unselect();
        this.renderFromState(state);
    }

    private renderPlacementControlsCluster(
        state: SimSimViewerState,
        phase: string,
        data: {
            controlsDisabled: boolean;
            swapsUsed: number;
            swapBudget: number;
            swapsRemaining: number;
            changed: boolean;
            latestRejection: { reasonCode: string; reason: string } | null;
        }
    ): void {
        if (!this.placementControlsEl) return;
        const cluster = this.placementControlsEl;
        cluster.innerHTML = "";

        const title = document.createElement("div");
        title.style.fontSize = "12px";
        title.style.fontWeight = "700";
        title.style.marginBottom = "6px";
        title.textContent = "Placement Controls";
        cluster.appendChild(title);

        const budget = document.createElement("div");
        budget.style.fontSize = "11px";
        budget.style.opacity = "0.95";
        budget.style.marginBottom = "8px";
        budget.textContent = `Swaps: used ${data.swapsUsed} / budget ${data.swapBudget} (remaining ${data.swapsRemaining})`;
        cluster.appendChild(budget);

        if (this.placementInteractionStatus) {
            const status = document.createElement("div");
            status.style.fontSize = "11px";
            status.style.marginBottom = "8px";
            status.style.color = this.placementInteractionStatus.color;
            status.textContent = this.placementInteractionStatus.text;
            cluster.appendChild(status);
        }

        const controls = document.createElement("div");
        controls.style.display = "flex";
        controls.style.alignItems = "center";
        controls.style.gap = "6px";
        controls.style.marginBottom = "2px";

        const undoButton = document.createElement("button");
        undoButton.type = "button";
        undoButton.textContent = "Undo";
        undoButton.disabled = data.controlsDisabled || this.placementsHistory.length === 0;
        styleSecondaryButton(undoButton, undoButton.disabled);
        if (!undoButton.disabled) {
            undoButton.addEventListener("click", () => {
                this.undo();
                this.placementInteractionStatus = null;
                this.renderFromState(state);
            });
        }
        controls.appendChild(undoButton);

        const canReset =
            !data.controlsDisabled &&
            (data.changed || this.placementsHistory.length > 0 || this.selectedRoomId !== null || this.selectedSupId !== null);
        const resetButton = document.createElement("button");
        resetButton.type = "button";
        resetButton.textContent = "Reset";
        resetButton.disabled = !canReset;
        styleSecondaryButton(resetButton, resetButton.disabled);
        if (!resetButton.disabled) {
            resetButton.addEventListener("click", () => {
                this.resetDraftToBaseline();
                this.renderFromState(state);
            });
        }
        controls.appendChild(resetButton);

        const canUnselect = this.selectedRoomId !== null || this.selectedSupId !== null;
        const unselectButton = document.createElement("button");
        unselectButton.type = "button";
        unselectButton.textContent = "Unselect";
        unselectButton.disabled = !canUnselect;
        styleSecondaryButton(unselectButton, unselectButton.disabled);
        if (!unselectButton.disabled) {
            unselectButton.addEventListener("click", () => {
                this.unselect();
                this.placementInteractionStatus = null;
                this.renderFromState(state);
            });
        }
        controls.appendChild(unselectButton);

        cluster.appendChild(controls);

        const applyDraftButton = document.createElement("button");
        applyDraftButton.type = "button";
        applyDraftButton.textContent = "Apply Draft";
        const applyDisabled = data.controlsDisabled || data.swapsUsed > data.swapBudget || !data.changed;
        applyDraftButton.disabled = applyDisabled;
        applyDraftButton.style.marginTop = "8px";
        applyDraftButton.style.border = "1px solid rgba(243, 199, 106, 0.75)";
        applyDraftButton.style.background = "rgba(38, 29, 12, 0.95)";
        applyDraftButton.style.color = "#f3efe3";
        applyDraftButton.style.borderRadius = "8px";
        applyDraftButton.style.padding = "6px 10px";
        applyDraftButton.style.fontSize = "12px";
        applyDraftButton.style.fontWeight = "700";
        applyDraftButton.style.letterSpacing = "0.03em";
        applyDraftButton.style.cursor = applyDisabled ? "not-allowed" : "pointer";
        applyDraftButton.style.opacity = applyDisabled ? "0.55" : "1";
        if (!applyDisabled) {
            applyDraftButton.addEventListener("click", () => {
                const setSupervisors: Record<string, string | null> = {};
                for (const [roomId, supervisorCode] of Object.entries(this.placementsDraft)) {
                    setSupervisors[String(roomId)] = supervisorCode ?? null;
                }
                this.onApplySupervisorPlacements?.({
                    tickTarget: state.tick + 1,
                    setSupervisors,
                });
            });
        }
        cluster.appendChild(applyDraftButton);

        const applyValidation = document.createElement("div");
        applyValidation.style.marginTop = "6px";
        applyValidation.style.fontSize = "11px";
        applyValidation.style.opacity = "0.95";
        if (data.latestRejection?.reasonCode === "SUPERVISOR_SWAP_BUDGET_EXCEEDED") {
            applyValidation.style.color = "#ffd8cf";
            applyValidation.textContent = "Too many swaps for today. Undo or Reset.";
        } else if (!data.changed) {
            applyValidation.style.color = "#d3d6da";
            applyValidation.textContent = "No draft changes to apply.";
        } else if (data.swapsUsed > data.swapBudget) {
            applyValidation.style.color = "#ffd8cf";
            applyValidation.textContent = "Too many swaps for today. Undo or Reset.";
        } else if (data.controlsDisabled) {
            applyValidation.style.color = "#f3c76a";
            applyValidation.textContent =
                phase === "awaiting_prompts"
                    ? "Placements locked while awaiting prompt resolution."
                    : phase === "end_of_day"
                      ? "Placements locked during end_of_day."
                      : "Placements unavailable in current phase.";
        } else {
            applyValidation.style.color = "#d3d6da";
            applyValidation.textContent = `Draft ready for tick ${state.tick + 1}.`;
        }
        cluster.appendChild(applyValidation);

        if (phase === "awaiting_prompts") {
            const promptLock = document.createElement("div");
            promptLock.style.marginTop = "6px";
            promptLock.style.fontSize = "11px";
            promptLock.style.color = "#f3c76a";
            promptLock.textContent = "Placements locked while awaiting prompt resolution.";
            cluster.appendChild(promptLock);
        }
    }

    private renderSupervisorPlacementsPanel(
        state: SimSimViewerState,
        rooms: SimSimRoom[],
        data: {
            controlsDisabled: boolean;
            swapBudget: number;
            swapsUsed: number;
            swapsRemaining: number;
            changed: boolean;
        }
    ): void {
        if (!this.supervisorPanelEl) return;
        const panel = this.supervisorPanelEl;
        panel.innerHTML = "";

        const tickTarget = state.tick + 1;
        const unlockedRooms = rooms.filter((room) => !room.locked).sort((a, b) => a.room_id - b.room_id);
        const unlockedSupervisors = Array.from(state.supervisors.values())
            .filter((supervisor) => supervisor.unlocked_day <= tickTarget)
            .sort((a, b) => a.code.localeCompare(b.code));
        this.syncPlacementEditorState(state, rooms);

        const title = document.createElement("div");
        title.style.fontSize = "11px";
        title.style.fontWeight = "700";
        title.style.marginBottom = "6px";
        title.style.letterSpacing = "0.08em";
        title.style.textTransform = "uppercase";
        title.style.opacity = "0.82";
        title.textContent = "Placement Board";
        panel.appendChild(title);

        const hint = document.createElement("div");
        hint.style.fontSize = "11px";
        hint.style.opacity = "0.9";
        hint.style.marginBottom = "8px";
        hint.textContent = "Select a room token on the map, then click another room token to swap.";
        panel.appendChild(hint);

        if (unlockedRooms.length === 0) {
            const empty = document.createElement("div");
            empty.style.fontSize = "11px";
            empty.style.opacity = "0.82";
            empty.textContent = "No unlocked rooms yet.";
            panel.appendChild(empty);
            return;
        }

        const summary = document.createElement("div");
        summary.style.fontSize = "11px";
        summary.style.marginBottom = "8px";
        summary.style.opacity = "0.9";
        summary.innerHTML = `<div>Selected: ${this.selectedRoomId !== null ? `room ${this.selectedRoomId}` : "none"}${this.selectedSupId ? ` -> ${this.selectedSupId}` : ""}</div>`;
        panel.appendChild(summary);

        const supervisorBar = document.createElement("div");
        supervisorBar.style.display = "flex";
        supervisorBar.style.flexWrap = "wrap";
        supervisorBar.style.gap = "8px";
        supervisorBar.style.marginBottom = "10px";
        supervisorBar.style.padding = "8px";
        supervisorBar.style.borderRadius = "8px";
        supervisorBar.style.border = "1px solid rgba(140, 214, 200, 0.25)";
        supervisorBar.style.background = "rgba(8, 12, 18, 0.45)";

        for (const supervisor of unlockedSupervisors) {
            const assignedRoom = Object.keys(this.placementsDraft)
                .map((roomId) => Number(roomId))
                .find((roomId) => this.placementsDraft[roomId] === supervisor.code);
            let highlighted = false;
            let ineligible = false;
            if (this.selectedRoomId !== null && assignedRoom !== undefined && this.selectedRoomId !== assignedRoom) {
                if (data.swapsRemaining <= 0) {
                    ineligible = true;
                } else {
                    const nextDraft = this.swapDraftBetweenRooms({
                        roomId: this.selectedRoomId,
                        otherRoomId: assignedRoom,
                    });
                    const swapsUsedIfApplied = this.computeSwapsUsed(nextDraft, this.placementsBaseline);
                    highlighted = swapsUsedIfApplied <= data.swapBudget;
                    ineligible = !highlighted;
                }
            }
            const hardDisabled = data.controlsDisabled || assignedRoom === undefined;
            const token = createSupervisorToken({
                label: supervisor.code,
                name: supervisor.name,
                selected: this.selectedSupId === supervisor.code,
                disabled: hardDisabled,
                highlighted: this.selectedSupId === supervisor.code || highlighted,
                ineligible,
                sizePx: 56,
                onClick:
                    hardDisabled || assignedRoom === undefined
                        ? undefined
                        : () =>
                              this.onRoomSupervisorTokenClick({
                                  roomId: assignedRoom,
                                  supervisorCode: supervisor.code,
                                  swapBudget: data.swapBudget,
                                  controlsDisabled: data.controlsDisabled,
                                  state,
                              }),
            });
            token.title = assignedRoom ? `Room ${assignedRoom}` : "Unassigned";
            supervisorBar.appendChild(token);
        }
        panel.appendChild(supervisorBar);

        if (this.debugVisible) {
            const debugHeader = document.createElement("div");
            debugHeader.style.fontSize = "10px";
            debugHeader.style.letterSpacing = "0.06em";
            debugHeader.style.textTransform = "uppercase";
            debugHeader.style.opacity = "0.6";
            debugHeader.style.marginTop = "2px";
            debugHeader.style.marginBottom = "6px";
            debugHeader.textContent = "Debug placement rows";
            panel.appendChild(debugHeader);

            for (const room of unlockedRooms) {
                const row = document.createElement("div");
                row.style.display = "flex";
                row.style.alignItems = "center";
                row.style.justifyContent = "space-between";
                row.style.gap = "8px";
                row.style.fontSize = "11px";
                row.style.marginBottom = "6px";
                row.style.padding = "5px 6px";
                row.style.borderRadius = "6px";
                row.style.background = this.selectedRoomId === room.room_id ? "rgba(243, 199, 106, 0.14)" : "rgba(10, 13, 18, 0.25)";

                const label = document.createElement("span");
                label.textContent = `Room ${room.room_id} • ${room.name}`;
                label.style.opacity = "0.88";
                row.appendChild(label);

                const selectedCode = this.placementsDraft[room.room_id] ?? null;
                const hardDisabled = data.controlsDisabled || !selectedCode;
                const currentToken = createSupervisorToken({
                    label: selectedCode ?? "—",
                    name: selectedCode ? (unlockedSupervisors.find((sup) => sup.code === selectedCode)?.name ?? selectedCode) : "Unassigned",
                    selected: this.selectedRoomId === room.room_id,
                    disabled: hardDisabled,
                    highlighted: false,
                    ineligible: false,
                    sizePx: 40,
                    onClick: hardDisabled
                        ? undefined
                        : () =>
                              this.onRoomSupervisorTokenClick({
                                  roomId: room.room_id,
                                  supervisorCode: selectedCode,
                                  swapBudget: data.swapBudget,
                                  controlsDisabled: data.controlsDisabled,
                                  state,
                              }),
                });
                row.appendChild(currentToken);
                panel.appendChild(row);
            }
        }
    }

    private renderPromptsPanel(
        state: SimSimViewerState,
        prompts: SimSimPrompt[],
        awaitingPrompts: boolean,
        events: SimSimEvent[]
    ): void {
        if (!this.promptsEl) return;
        const prompt = firstUnresolvedPrompt(prompts);
        if (!awaitingPrompts || !prompt) {
            this.promptsEl.style.display = "none";
            this.promptsEl.style.pointerEvents = "none";
            this.promptsEl.innerHTML = "";
            return;
        }
        this.promptsEl.style.display = "block";
        this.promptsEl.style.pointerEvents = "auto";
        this.promptsEl.innerHTML = "";
        const inFlight = this.advanceInFlight || state.desynced;
        const tickTarget = state.tick + 1;
        const latestRejection = findLatestInputRejection(events);
        const backdrop = document.createElement("div");
        backdrop.style.position = "absolute";
        backdrop.style.inset = "0";
        backdrop.style.display = "flex";
        backdrop.style.alignItems = "center";
        backdrop.style.justifyContent = "center";
        backdrop.style.padding = "26px";
        backdrop.style.background = "radial-gradient(circle at 50% 22%, rgba(243, 199, 106, 0.08), rgba(4, 8, 13, 0.72) 35%, rgba(3, 5, 8, 0.88) 100%)";
        backdrop.style.backdropFilter = "blur(1.6px)";
        backdrop.style.pointerEvents = "auto";

        const card = document.createElement("div");
        card.dataset.spotlightPopup = "1";
        card.style.position = "relative";
        card.style.width = "min(680px, 94vw)";
        card.style.borderRadius = "16px";
        card.style.border = "1px solid rgba(243, 199, 106, 0.52)";
        card.style.background = "linear-gradient(160deg, rgba(8, 15, 24, 0.96) 0%, rgba(20, 16, 9, 0.94) 100%)";
        card.style.boxShadow = "0 24px 52px rgba(4, 8, 13, 0.72)";
        card.style.overflow = "hidden";

        const frameGlow = document.createElement("div");
        frameGlow.style.position = "absolute";
        frameGlow.style.inset = "0";
        frameGlow.style.pointerEvents = "none";
        frameGlow.style.background =
            "linear-gradient(120deg, rgba(243, 199, 106, 0.12), rgba(243, 199, 106, 0) 18%), radial-gradient(circle at 80% 12%, rgba(140, 214, 200, 0.12), rgba(140, 214, 200, 0) 32%)";
        card.appendChild(frameGlow);

        const body = document.createElement("div");
        body.style.position = "relative";
        body.style.zIndex = "1";
        body.style.display = "grid";
        body.style.gap = "12px";
        body.style.padding = "16px 16px 15px";
        card.appendChild(body);

        const titleRow = document.createElement("div");
        titleRow.style.display = "flex";
        titleRow.style.alignItems = "flex-start";
        titleRow.style.justifyContent = "space-between";
        titleRow.style.gap = "12px";

        const titleWrap = document.createElement("div");
        const title = document.createElement("div");
        title.style.fontSize = "13px";
        title.style.fontWeight = "800";
        title.style.letterSpacing = "0.08em";
        title.style.textTransform = "uppercase";
        title.style.color = "#f5dfae";
        title.textContent = spotlightTitleForPrompt(prompt);
        titleWrap.appendChild(title);

        const subtitle = document.createElement("div");
        subtitle.style.marginTop = "4px";
        subtitle.style.fontSize = "11px";
        subtitle.style.opacity = "0.9";
        subtitle.textContent = `${prompt.kind} • ${prompt.prompt_id} • created t${prompt.tick_created}`;
        titleWrap.appendChild(subtitle);
        titleRow.appendChild(titleWrap);

        const gateTag = document.createElement("div");
        gateTag.style.border = "1px solid rgba(243, 199, 106, 0.52)";
        gateTag.style.background = "rgba(38, 28, 12, 0.64)";
        gateTag.style.borderRadius = "999px";
        gateTag.style.padding = "4px 8px";
        gateTag.style.fontSize = "10px";
        gateTag.style.fontWeight = "700";
        gateTag.style.letterSpacing = "0.07em";
        gateTag.style.textTransform = "uppercase";
        gateTag.textContent = "Decision Gate";
        titleRow.appendChild(gateTag);
        body.appendChild(titleRow);

        const art = document.createElement("div");
        art.style.borderRadius = "12px";
        art.style.border = "1px solid rgba(140, 214, 200, 0.36)";
        art.style.background =
            "linear-gradient(128deg, rgba(12, 20, 31, 0.94), rgba(30, 21, 12, 0.9)), repeating-linear-gradient(145deg, rgba(243, 199, 106, 0.09), rgba(243, 199, 106, 0.09) 2px, rgba(0, 0, 0, 0) 2px, rgba(0, 0, 0, 0) 10px)";
        art.style.height = "160px";
        art.style.display = "flex";
        art.style.alignItems = "center";
        art.style.justifyContent = "center";
        art.style.textAlign = "center";
        art.style.padding = "12px";
        art.innerHTML = `<div style="font-size:11px;letter-spacing:0.08em;text-transform:uppercase;opacity:0.84;">Spotlight Art Placeholder<br/><span style="font-size:10px;opacity:0.72;">${escapeHtml(spotlightArtLabelForPrompt(prompt))}</span></div>`;
        body.appendChild(art);

        const deltas = document.createElement("div");
        deltas.style.display = "grid";
        deltas.style.gridTemplateColumns = "repeat(auto-fit, minmax(120px, 1fr))";
        deltas.style.gap = "7px";
        for (const item of spotlightDeltaChips(prompt)) {
            const chip = document.createElement("div");
            chip.style.display = "grid";
            chip.style.gap = "2px";
            chip.style.padding = "7px 8px";
            chip.style.borderRadius = "8px";
            chip.style.border = deltaToneBorder(item.tone);
            chip.style.background = deltaToneBackground(item.tone);

            const top = document.createElement("div");
            top.style.fontSize = "10px";
            top.style.letterSpacing = "0.05em";
            top.style.textTransform = "uppercase";
            top.style.opacity = "0.86";
            top.textContent = `${item.icon} ${item.label}`;
            chip.appendChild(top);

            const value = document.createElement("div");
            value.style.fontFamily = "\"Chivo Mono\", monospace";
            value.style.fontSize = "12px";
            value.style.fontWeight = "700";
            value.textContent = item.delta;
            chip.appendChild(value);
            deltas.appendChild(chip);
        }
        body.appendChild(deltas);

        if (latestRejection) {
            const warning = document.createElement("div");
            warning.style.fontSize = "11px";
            warning.style.padding = "7px 8px";
            warning.style.borderRadius = "8px";
            warning.style.border = "1px solid rgba(232, 159, 143, 0.45)";
            warning.style.background = "rgba(58, 22, 22, 0.74)";
            warning.style.color = "#ffd8cf";
            warning.textContent = `Last rejection: ${latestRejection.reasonCode} - ${latestRejection.reason}`;
            body.appendChild(warning);
        }

        const choicesRow = document.createElement("div");
        choicesRow.style.display = "grid";
        choicesRow.style.gridTemplateColumns = "repeat(auto-fit, minmax(150px, 1fr))";
        choicesRow.style.gap = "8px";
        const choices = (prompt.choices ?? []).slice(0, 3);
        for (const [index, choice] of choices.entries()) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.textContent = choice;
            btn.style.border = "1px solid rgba(243, 199, 106, 0.72)";
            btn.style.borderRadius = "8px";
            btn.style.padding = "8px 10px";
            btn.style.fontSize = "12px";
            btn.style.fontWeight = "700";
            btn.style.letterSpacing = "0.03em";
            btn.style.cursor = inFlight ? "not-allowed" : "pointer";
            btn.style.pointerEvents = "auto";
            if (index === 0) {
                btn.style.background = "linear-gradient(160deg, rgba(48, 34, 12, 0.94), rgba(66, 45, 14, 0.9))";
            } else if (index === 1) {
                btn.style.background = "linear-gradient(160deg, rgba(16, 28, 33, 0.95), rgba(19, 37, 45, 0.9))";
            } else {
                btn.style.background = "linear-gradient(160deg, rgba(31, 24, 16, 0.95), rgba(37, 30, 19, 0.9))";
            }
            btn.style.color = "#f3efe3";
            btn.disabled = inFlight;
            btn.style.opacity = inFlight ? "0.62" : "1";
            if (!inFlight) {
                btn.addEventListener("click", () => {
                    if (this.advanceInFlight) return;
                    this.advanceInFlight = true;
                    this.advanceInFlightStateKey = this.stateUpdateKey(state);
                    this.advanceStatusOverride = {
                        text: "Submitting prompt response...",
                        color: "#f3efe3",
                        untilMs: Date.now() + 3000,
                    };
                    const allButtons = choicesRow.querySelectorAll<HTMLButtonElement>("button");
                    for (const button of allButtons) {
                        button.disabled = true;
                        button.style.opacity = "0.62";
                        button.style.cursor = "not-allowed";
                    }
                    this.onSubmitPromptChoice?.({
                        tickTarget,
                        promptId: prompt.prompt_id,
                        choice,
                    });
                });
            }
            choicesRow.appendChild(btn);
        }
        body.appendChild(choicesRow);

        const gateHint = document.createElement("div");
        gateHint.style.fontSize = "11px";
        gateHint.style.opacity = "0.88";
        gateHint.style.color = inFlight ? "#f3efe3" : "#f5ddaa";
        gateHint.textContent = inFlight
            ? "Submitting response..."
            : "Progression paused. Select one response to resolve this prompt.";
        body.appendChild(gateHint);

        backdrop.appendChild(card);
        this.promptsEl.appendChild(backdrop);
    }
}

type InspectionRoomCardArgs = {
    room: SimSimRoom;
    phase: string;
    tick: number;
    supervisorLabel: string;
    supervisorToken: string;
    accidents: { count: number; casualties: number };
    forecast: ForecastRoomBands | undefined;
};

type ForecastTone = "good" | "watch" | "bad" | "neutral";

type ForecastBandDisplay = {
    label: string;
    tone: ForecastTone;
};

function renderInspectionRoomCardHtml(args: InspectionRoomCardArgs): string {
    const { room, phase, tick, supervisorLabel, supervisorToken, accidents, forecast } = args;
    const staffing = staffingForPhase(phase, room);
    const hazard = describeHazardBand(forecast);
    const throughput = describeThroughputBand(forecast);
    const staffingBand = describeStaffingBand(forecast);
    const crewState = describeCrewStateBand(forecast);
    const whyLine = extractForecastWhyLine(room, forecast);
    const hazardCritical = isHazardCriticalForecast(forecast);
    const equipmentLow = isEquipmentLow(room.equipment_condition);
    const pulse = 0.18 + ((((Math.sin((tick + room.room_id + 1) * 0.85) + 1) * 0.5) * 0.24));

    const borderColor = room.locked
        ? "rgba(232,159,143,0.42)"
        : hazardCritical
          ? `rgba(231,123,75,${(0.56 + pulse).toFixed(2)})`
          : "rgba(140,214,200,0.28)";
    const background = room.locked
        ? "rgba(44,23,23,0.72)"
        : hazardCritical
          ? "linear-gradient(165deg, rgba(35,17,17,0.84), rgba(24,20,18,0.86))"
          : "rgba(13,20,28,0.72)";

    const hazardOverlay = hazardCritical
        ? `<div aria-hidden="true" style="position:absolute;inset:0;pointer-events:none;opacity:${(0.14 + pulse).toFixed(2)};background:repeating-linear-gradient(135deg, rgba(231,123,75,0.45), rgba(231,123,75,0.45) 6px, rgba(0,0,0,0) 6px, rgba(0,0,0,0) 13px);"></div>`
        : "";
    const wearOverlay = equipmentLow
        ? `<div aria-hidden="true" style="position:absolute;inset:0;pointer-events:none;background:linear-gradient(108deg, rgba(144,89,58,0) 14%, rgba(144,89,58,0.26) 15%, rgba(144,89,58,0) 17%),linear-gradient(46deg, rgba(130,80,52,0) 56%, rgba(130,80,52,0.24) 57%, rgba(130,80,52,0) 59%),radial-gradient(circle at 18% 76%, rgba(148,88,56,0.24), rgba(0,0,0,0) 38%),radial-gradient(circle at 78% 22%, rgba(148,88,56,0.22), rgba(0,0,0,0) 34%);"></div>`
        : "";
    // success/fiasco/accident stamp overlays are scheduled for a follow-up ticket.

    const title = escapeHtml(room.name ?? `Room ${room.room_id}`);
    const supervisorText = escapeHtml(room.locked ? "LOCKED" : supervisorLabel);
    const infoLine = `inspection • unlock day ${room.unlocked_day >= 0 ? room.unlocked_day : "never"}`;
    return [
        `<article style="position:relative;overflow:hidden;border:1px solid ${borderColor};background:${background};border-radius:10px;padding:8px 10px;box-shadow:${hazardCritical ? `0 0 0 1px rgba(231,123,75,${(0.16 + pulse).toFixed(2)}),0 6px 18px rgba(53,16,12,0.32)` : "none"};">`,
        hazardOverlay,
        wearOverlay,
        `<div style="position:relative;z-index:1;display:grid;gap:6px;">`,
        `<div style="display:flex;justify-content:space-between;gap:8px;font-size:12px;font-weight:700;">`,
        `<span>${title}</span>`,
        `<span style="display:inline-flex;align-items:center;gap:6px;">${supervisorToken}<span>${supervisorText}</span></span>`,
        `</div>`,
        `<div style="font-size:10px;opacity:0.78;">${infoLine}</div>`,
        `<div style="display:flex;align-items:center;flex-wrap:wrap;gap:6px;">`,
        `<span style="font-size:10px;text-transform:uppercase;letter-spacing:0.06em;border:1px solid rgba(243,199,106,0.6);border-radius:999px;padding:2px 6px;background:rgba(41,30,14,0.46);">${staffing.label}</span>`,
        `<span style="font-size:10px;border:1px solid rgba(140,214,200,0.4);border-radius:999px;padding:2px 6px;background:rgba(8,18,24,0.4);">D ${fmtCount(staffing.dumb)}</span>`,
        `<span style="font-size:10px;border:1px solid rgba(140,214,200,0.4);border-radius:999px;padding:2px 6px;background:rgba(8,18,24,0.4);">S ${fmtCount(staffing.smart)}</span>`,
        `</div>`,
        `<div style="font-size:11px;opacity:0.94;">equip ${pct(room.equipment_condition)} • S ${pct(room.stress)} • D ${pct(room.discipline)}${room.alignment !== null && room.alignment !== undefined ? ` • A ${pct(room.alignment)}` : ""}</div>`,
        `<div style="font-size:11px;opacity:0.92;">out rb ${room.output_today.raw_brains_dumb}/${room.output_today.raw_brains_smart} • w ${room.output_today.washed_dumb}/${room.output_today.washed_smart} • sub ${room.output_today.substrate_gallons} • rib ${room.output_today.ribbon_yards}</div>`,
        `<div style="font-size:11px;opacity:0.92;">accidents ${accidents.count} • casualties ${accidents.casualties}</div>`,
        `<details style="margin-top:2px;border:1px solid rgba(140,214,200,0.24);border-radius:8px;background:rgba(8,14,20,0.38);padding:6px 7px;">`,
        `<summary style="cursor:pointer;user-select:none;font-size:10px;letter-spacing:0.06em;text-transform:uppercase;opacity:0.9;">Forecast Bands</summary>`,
        `<div style="margin-top:6px;display:grid;gap:4px;">`,
        renderForecastBandRowHtml("hazard", hazard),
        renderForecastBandRowHtml("throughput", throughput),
        renderForecastBandRowHtml("staffing", staffingBand),
        renderForecastBandRowHtml("crew_state", crewState),
        whyLine ? `<div style="font-size:10px;line-height:1.35;opacity:0.88;">why: ${escapeHtml(whyLine)}</div>` : "",
        `</div>`,
        `</details>`,
        `</div>`,
        `</article>`,
    ].join("");
}

function renderForecastBandRowHtml(label: string, band: ForecastBandDisplay): string {
    return [
        `<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">`,
        `<span style="font-size:10px;opacity:0.78;letter-spacing:0.03em;text-transform:uppercase;">${label}</span>`,
        `<span style="font-size:10px;padding:2px 6px;border-radius:999px;${forecastBandStyle(band.tone)}">${band.label}</span>`,
        `</div>`,
    ].join("");
}

function staffingForPhase(phase: string, room: SimSimRoom): { label: "DISPATCHED" | "PRESENT"; dumb: number | null; smart: number | null } {
    if (phase === "planning" || phase === "awaiting_prompts" || phase === "resolving") {
        return {
            label: "DISPATCHED",
            dumb: room.workers_assigned.dumb,
            smart: room.workers_assigned.smart,
        };
    }
    return {
        label: "PRESENT",
        dumb: room.workers_present.dumb,
        smart: room.workers_present.smart,
    };
}

function describeHazardBand(forecast: ForecastRoomBands | undefined): ForecastBandDisplay {
    if (!forecast) return { label: "UNKNOWN", tone: "neutral" };
    switch (forecast.incidentRisk.band) {
        case "high":
            return { label: "CRITICAL", tone: "bad" };
        case "mid":
            return { label: "WATCH", tone: "watch" };
        case "low":
            return { label: "LOW", tone: "good" };
        default:
            return { label: "UNKNOWN", tone: "neutral" };
    }
}

function describeThroughputBand(forecast: ForecastRoomBands | undefined): ForecastBandDisplay {
    return describePositiveBand(forecast?.throughput.band);
}

function describeStaffingBand(forecast: ForecastRoomBands | undefined): ForecastBandDisplay {
    if (!forecast) return { label: "UNKNOWN", tone: "neutral" };
    switch (forecast.absenteeismRisk.band) {
        case "high":
            return { label: "THIN", tone: "bad" };
        case "mid":
            return { label: "TIGHT", tone: "watch" };
        case "low":
            return { label: "READY", tone: "good" };
        default:
            return { label: "UNKNOWN", tone: "neutral" };
    }
}

function describeCrewStateBand(forecast: ForecastRoomBands | undefined): ForecastBandDisplay {
    if (!forecast) return { label: "UNKNOWN", tone: "neutral" };
    switch (forecast.orderIndex.band) {
        case "high":
            return { label: "COHESIVE", tone: "good" };
        case "mid":
            return { label: "MIXED", tone: "watch" };
        case "low":
            return { label: "FRACTURED", tone: "bad" };
        default:
            return { label: "UNKNOWN", tone: "neutral" };
    }
}

function describePositiveBand(band: ForecastBand | undefined): ForecastBandDisplay {
    switch (band) {
        case "high":
            return { label: "HIGH", tone: "good" };
        case "mid":
            return { label: "MID", tone: "watch" };
        case "low":
            return { label: "LOW", tone: "bad" };
        default:
            return { label: "UNKNOWN", tone: "neutral" };
    }
}

function forecastBandStyle(tone: ForecastTone): string {
    if (tone === "good")
        return "border:1px solid rgba(140,214,200,0.5);background:rgba(10,31,29,0.58);color:#ccf0e8;";
    if (tone === "watch")
        return "border:1px solid rgba(243,199,106,0.52);background:rgba(42,31,11,0.58);color:#f5ddaa;";
    if (tone === "bad")
        return "border:1px solid rgba(231,123,75,0.58);background:rgba(44,19,15,0.62);color:#ffd9ca;";
    return "border:1px solid rgba(159,176,191,0.46);background:rgba(21,28,36,0.58);color:#d5dee8;";
}

function extractForecastWhyLine(room: SimSimRoom, forecast: ForecastRoomBands | undefined): string | null {
    const roomAny = room as SimSimRoom & {
        why?: unknown;
        why_line?: unknown;
        forecastWhy?: unknown;
        forecast_why?: unknown;
    };
    const forecastAny = forecast as (ForecastRoomBands & { why?: unknown; reason?: unknown }) | undefined;
    const candidates: unknown[] = [
        roomAny.forecast_why,
        roomAny.forecastWhy,
        roomAny.why_line,
        roomAny.why,
        forecastAny?.why,
        forecastAny?.reason,
    ];
    for (const candidate of candidates) {
        if (typeof candidate !== "string") continue;
        const line = candidate.trim();
        if (line.length > 0) return line;
    }
    return null;
}

function isHazardCriticalForecast(forecast: ForecastRoomBands | undefined): boolean {
    return forecast?.incidentRisk.band === "high";
}

function isEquipmentLow(value: number | null | undefined): boolean {
    return value !== null && value !== undefined && Number.isFinite(value) && value < 0.45;
}

function roomMicroStatsLabel(room: SimSimRoom): string {
    const parts = [`E ${pct(room.equipment_condition)}`, `S ${pct(room.stress)}`, `D ${pct(room.discipline)}`];
    if (room.alignment !== null && room.alignment !== undefined) {
        parts.push(`A ${pct(room.alignment)}`);
    }
    return parts.join(" · ");
}

function fmtCount(value: number | null | undefined): string {
    return value === null || value === undefined ? "--" : String(value);
}

function sortedEvents(events: Map<string, SimSimEvent>): SimSimEvent[] {
    return Array.from(events.values()).sort((a, b) => (a.tick - b.tick) || (a.event_id - b.event_id));
}

function sortedPrompts(prompts: Map<string, SimSimPrompt>): SimSimPrompt[] {
    return Array.from(prompts.values()).sort((a, b) => (a.tick_created - b.tick_created) || a.prompt_id.localeCompare(b.prompt_id));
}

function findLatestInputRejection(events: SimSimEvent[]): { reasonCode: string; reason: string } | null {
    for (let idx = events.length - 1; idx >= 0; idx -= 1) {
        const event = events[idx];
        if (event.kind !== "input_rejected") continue;
        const details = event.details;
        if (!details || typeof details !== "object") continue;
        const dict = details as Record<string, unknown>;
        const reasonCode = typeof dict["reason_code"] === "string" ? dict["reason_code"] : "";
        const reason = typeof dict["reason"] === "string" ? dict["reason"] : "";
        if (!reasonCode && !reason) continue;
        return {
            reasonCode: reasonCode || "UNKNOWN",
            reason: reason || "(no reason provided)",
        };
    }
    return null;
}

function pct(value: number | null | undefined): string {
    if (value === null || value === undefined || !Number.isFinite(value)) return "--";
    return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

function clamp(min: number, value: number, max: number): number {
    return Math.max(min, Math.min(max, value));
}

function normalizePhaseToken(phase: string | undefined | null): string {
    return (phase ?? "").trim().toLowerCase();
}

function styleSecondaryButton(btn: HTMLButtonElement, disabled: boolean): void {
    btn.style.border = "1px solid rgba(140, 214, 200, 0.46)";
    btn.style.background = "rgba(12, 25, 31, 0.78)";
    btn.style.color = "#f3efe3";
    btn.style.borderRadius = "7px";
    btn.style.padding = "4px 9px";
    btn.style.fontSize = "11px";
    btn.style.cursor = disabled ? "not-allowed" : "pointer";
    btn.style.opacity = disabled ? "0.5" : "1";
}

function roomCardSupervisorTokenHtml(code: string, name: string): string {
    const safeCode = escapeHtml(code);
    const safeName = escapeHtml(name);
    return [
        `<span title="${safeName}" style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:999px;`,
        `border:1px solid rgba(243, 199, 106, 0.78);background:radial-gradient(circle at 35% 30%, rgba(243,199,106,0.28), rgba(20,29,37,0.95) 72%);`,
        `font-size:11px;font-weight:700;line-height:1;color:#f3efe3;box-shadow:0 0 10px rgba(243,199,106,0.22);">${safeCode}</span>`,
    ].join("");
}

type SpotlightDeltaTone = "good" | "bad" | "neutral";

type SpotlightDeltaChip = {
    icon: string;
    label: string;
    delta: string;
    tone: SpotlightDeltaTone;
};

function firstUnresolvedPrompt(prompts: SimSimPrompt[]): SimSimPrompt | null {
    for (const prompt of prompts) {
        if (prompt.status !== "resolved") return prompt;
    }
    return null;
}

function spotlightTitleForPrompt(prompt: SimSimPrompt): string {
    if (prompt.kind === "conflict") return "Conflict Spotlight";
    if (prompt.kind === "critical") return "Critical Spotlight";
    return "Directive Spotlight";
}

function spotlightArtLabelForPrompt(prompt: SimSimPrompt): string {
    if (prompt.kind === "conflict") return "Supervisor feud at sector edge";
    if (prompt.kind === "critical") return "High-confidence supervisor incident";
    return "Decision branch requires command";
}

function spotlightDeltaChips(prompt: SimSimPrompt): SpotlightDeltaChip[] {
    if (prompt.kind === "conflict") {
        return [
            { icon: "⚖", label: "Influence", delta: "±0.10", tone: "neutral" },
            { icon: "⚠", label: "Stress", delta: "+0.00..+0.05", tone: "bad" },
            { icon: "◈", label: "Discipline", delta: "-0.03..+0.03", tone: "neutral" },
        ];
    }
    if (prompt.kind === "critical") {
        return [
            { icon: "☢", label: "Regime", delta: "event shift", tone: "bad" },
            { icon: "⚙", label: "Output", delta: "multiplier", tone: "neutral" },
            { icon: "◈", label: "Factory", delta: "metric delta", tone: "neutral" },
        ];
    }
    return [
        { icon: "⚑", label: "Directive", delta: "branch", tone: "neutral" },
        { icon: "⚙", label: "Systems", delta: "pending", tone: "neutral" },
        { icon: "◈", label: "State", delta: "unknown", tone: "neutral" },
    ];
}

function deltaToneBorder(tone: SpotlightDeltaTone): string {
    if (tone === "good") return "1px solid rgba(140, 214, 200, 0.48)";
    if (tone === "bad") return "1px solid rgba(232, 159, 143, 0.52)";
    return "1px solid rgba(243, 199, 106, 0.5)";
}

function deltaToneBackground(tone: SpotlightDeltaTone): string {
    if (tone === "good") return "rgba(9, 26, 29, 0.64)";
    if (tone === "bad") return "rgba(44, 17, 18, 0.62)";
    return "rgba(37, 28, 14, 0.52)";
}

type EventRailStampTone = "info" | "warning" | "danger" | "success";

function renderEventRailHtml(cards: EventRailCard[], expandedCardId: string | null): string {
    const rows = cards.length === 0
        ? `<div style="font-size:11px;opacity:0.78;padding:8px 2px;">No events yet. Advance day to populate rail.</div>`
        : cards
              .map((card) => {
                  const stamp = eventRailStampForCard(card);
                  const expanded = expandedCardId === card.id;
                  const chips = eventRailDeltaChips(card.details);
                  return [
                      `<button data-event-rail-card-id="${escapeHtml(card.id)}" type="button" aria-expanded="${expanded ? "true" : "false"}" style="border:1px solid ${stamp.border};background:${stamp.background};color:#f3efe3;border-radius:9px;padding:8px 9px;width:100%;text-align:left;display:grid;gap:6px;cursor:pointer;pointer-events:auto;">`,
                      `<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">`,
                      `<span style="font-size:10px;text-transform:uppercase;letter-spacing:0.06em;padding:2px 6px;border-radius:999px;border:1px solid ${stamp.badgeBorder};background:${stamp.badgeBg};">${stamp.label}</span>`,
                      `<span style="font-size:10px;opacity:0.74;">${escapeHtml(card.stamp)}</span>`,
                      `</div>`,
                      `<div style="font-size:12px;font-weight:700;line-height:1.3;">${escapeHtml(card.title)}</div>`,
                      `<div style="font-size:10px;opacity:0.86;">${escapeHtml(card.subtitle)}</div>`,
                      chips.length > 0
                          ? `<div style="display:flex;flex-wrap:wrap;gap:6px;">${chips
                                .map(
                                    (chip) =>
                                        `<span style="font-size:10px;padding:1px 6px;border-radius:999px;border:1px solid rgba(140,214,200,0.35);background:rgba(9,18,25,0.5);opacity:0.94;">${escapeHtml(chip)}</span>`
                                )
                                .join("")}</div>`
                          : "",
                      expanded
                          ? `<div style="font-size:11px;line-height:1.35;opacity:0.92;border-top:1px solid rgba(159,176,191,0.28);padding-top:6px;">${escapeHtml(shortCaption(card))}</div>`
                          : "",
                      `</button>`,
                  ].join("");
              })
              .join("");

    return [
        `<section style="border:1px solid rgba(243,199,106,0.36);background:rgba(12,18,24,0.74);border-radius:10px;padding:8px 8px 9px;display:grid;gap:7px;">`,
        `<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">`,
        `<div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;opacity:0.86;">EventRail</div>`,
        `<div style="font-size:10px;opacity:0.68;">minor/notable</div>`,
        `</div>`,
        `<div style="display:grid;gap:6px;">${rows}</div>`,
        `</section>`,
    ].join("");
}

function isPromptLifecycleCard(card: EventRailCard): boolean {
    const kind = card.kind.toLowerCase();
    return kind.startsWith("prompt_") || kind.startsWith("pending_");
}

function shortCaption(card: EventRailCard): string {
    if (card.details && card.details !== "no details") return card.details;
    if (card.subtitle) return card.subtitle;
    return "No additional details.";
}

function eventRailDeltaChips(details: string): string[] {
    if (!details || details === "no details") return [];
    return details
        .split(",")
        .map((token) => token.trim())
        .filter((token) => token.includes("=") && !token.endsWith("{...}"))
        .slice(0, 3);
}

function eventRailStampForCard(card: EventRailCard): {
    label: Uppercase<EventRailStampTone>;
    border: string;
    background: string;
    badgeBorder: string;
    badgeBg: string;
} {
    const tone = eventRailStampTone(card);
    if (tone === "danger") {
        return {
            label: "DANGER",
            border: "rgba(231,123,75,0.6)",
            background: "linear-gradient(165deg, rgba(38,16,16,0.9), rgba(24,12,12,0.9))",
            badgeBorder: "rgba(231,123,75,0.9)",
            badgeBg: "rgba(54,18,16,0.84)",
        };
    }
    if (tone === "success") {
        return {
            label: "SUCCESS",
            border: "rgba(118,214,161,0.58)",
            background: "linear-gradient(165deg, rgba(10,31,28,0.86), rgba(10,20,22,0.88))",
            badgeBorder: "rgba(118,214,161,0.86)",
            badgeBg: "rgba(11,44,38,0.72)",
        };
    }
    if (tone === "warning") {
        return {
            label: "WARNING",
            border: "rgba(243,199,106,0.56)",
            background: "linear-gradient(165deg, rgba(36,25,11,0.87), rgba(20,14,9,0.9))",
            badgeBorder: "rgba(243,199,106,0.85)",
            badgeBg: "rgba(51,34,12,0.72)",
        };
    }
    return {
        label: "INFO",
        border: "rgba(140,214,200,0.5)",
        background: "linear-gradient(165deg, rgba(12,22,28,0.86), rgba(11,16,22,0.88))",
        badgeBorder: "rgba(140,214,200,0.78)",
        badgeBg: "rgba(12,34,38,0.66)",
    };
}

function eventRailStampTone(card: EventRailCard): EventRailStampTone {
    const kind = card.kind.toLowerCase();
    if (kind === "critical_suppressed" || kind === "assignment_resolved" || kind === "security_redistribution") return "success";
    if (kind === "critical_triggered" || kind === "conflict_event" || kind === "input_rejected") return "danger";
    if (kind.includes("casualt") || kind.includes("critical") || kind.includes("conflict")) return "danger";
    if (card.severity === "notable") return "warning";
    return "info";
}

function isSimSimDevUiEnabled(): boolean {
    const env = (import.meta as unknown as { env?: Record<string, unknown> }).env ?? {};
    if (env["DEV"] === true) return true;
    if (String(env["VITE_SIM_SIM_DEV_UI"] ?? "").trim() === "1") return true;
    if (typeof window === "undefined") return false;
    const query = new URLSearchParams(window.location.search);
    return query.get("sim_sim_dev_ui") === "1";
}

function escapeHtml(value: string): string {
    return value
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

type SupervisorTokenOpts = {
    label: string;
    name?: string;
    selected: boolean;
    disabled: boolean;
    highlighted?: boolean;
    ineligible?: boolean;
    sizePx: number;
    onClick?: () => void;
};

function createSupervisorToken(opts: SupervisorTokenOpts): HTMLButtonElement {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.disabled = opts.disabled;
    btn.style.display = "inline-flex";
    btn.style.flexDirection = "column";
    btn.style.alignItems = "center";
    btn.style.justifyContent = "flex-start";
    btn.style.gap = "4px";
    btn.style.minWidth = `${opts.sizePx + 8}px`;
    btn.style.padding = "2px 3px";
    btn.style.border = "0";
    btn.style.background = "transparent";
    btn.style.color = "#f3efe3";
    btn.style.cursor = opts.disabled || opts.ineligible ? "not-allowed" : "pointer";
    btn.style.opacity = opts.disabled ? "0.45" : opts.ineligible ? "0.65" : "1";
    btn.style.pointerEvents = "auto";

    const circle = document.createElement("div");
    circle.textContent = opts.label;
    circle.style.width = `${opts.sizePx}px`;
    circle.style.height = `${opts.sizePx}px`;
    circle.style.borderRadius = "999px";
    circle.style.display = "flex";
    circle.style.alignItems = "center";
    circle.style.justifyContent = "center";
    circle.style.fontSize = `${Math.max(18, Math.floor(opts.sizePx * 0.42))}px`;
    circle.style.fontWeight = "700";
    circle.style.letterSpacing = "0.02em";
    circle.style.border = opts.selected
        ? "2px solid rgba(243, 199, 106, 0.98)"
        : opts.ineligible
          ? "1px solid rgba(232, 159, 143, 0.58)"
          : opts.highlighted
            ? "1px solid rgba(243, 199, 106, 0.74)"
            : "1px solid rgba(140, 214, 200, 0.48)";
    circle.style.background = opts.selected
        ? "radial-gradient(circle at 35% 30%, rgba(243,199,106,0.28), rgba(20,29,37,0.94) 70%)"
        : opts.ineligible
          ? "radial-gradient(circle at 35% 30%, rgba(232,159,143,0.20), rgba(26,20,22,0.95) 72%)"
          : "radial-gradient(circle at 35% 30%, rgba(140,214,200,0.24), rgba(18,24,30,0.94) 72%)";
    circle.style.boxShadow = opts.selected
        ? "0 0 0 2px rgba(243,199,106,0.26), 0 0 18px rgba(243,199,106,0.35)"
        : opts.highlighted
          ? "0 0 0 1px rgba(243,199,106,0.24), 0 0 14px rgba(243,199,106,0.30)"
          : opts.ineligible
            ? "0 0 8px rgba(232,159,143,0.20)"
            : "0 0 10px rgba(140,214,200,0.18)";
    circle.style.transition = "box-shadow 120ms ease, border-color 120ms ease, transform 120ms ease";
    btn.appendChild(circle);

    if (opts.name) {
        const name = document.createElement("div");
        name.textContent = opts.name;
        name.style.fontSize = "10px";
        name.style.lineHeight = "1.1";
        name.style.maxWidth = `${opts.sizePx + 16}px`;
        name.style.textAlign = "center";
        name.style.opacity = opts.selected ? "1" : "0.88";
        name.style.wordBreak = "break-word";
        btn.appendChild(name);
    }

    if (!opts.disabled && opts.onClick) {
        btn.addEventListener("click", opts.onClick);
        btn.addEventListener("mouseenter", () => {
            if (opts.selected || opts.ineligible) return;
            circle.style.borderColor = "rgba(243, 199, 106, 0.66)";
            circle.style.boxShadow = "0 0 0 1px rgba(243,199,106,0.2), 0 0 14px rgba(243,199,106,0.30)";
            circle.style.transform = "translateY(-1px)";
        });
        btn.addEventListener("mouseleave", () => {
            if (opts.selected || opts.ineligible) return;
            circle.style.borderColor = opts.highlighted ? "rgba(243, 199, 106, 0.74)" : "rgba(140, 214, 200, 0.48)";
            circle.style.boxShadow = opts.highlighted
                ? "0 0 0 1px rgba(243,199,106,0.24), 0 0 14px rgba(243,199,106,0.30)"
                : "0 0 10px rgba(140,214,200,0.18)";
            circle.style.transform = "translateY(0)";
        });
    }

    return btn;
}
