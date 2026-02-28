import * as PIXI from "pixi.js";
import type { SimSimEvent, SimSimPrompt, SimSimRoom, SimSimViewerState } from "./simSimStore";

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
    private supervisorPanelEl?: HTMLDivElement;
    private debugVisible = true;
    private lastState?: SimSimViewerState;
    private placementsBaseline: PlacementDraft = {};
    private placementsDraft: PlacementDraft = {};
    private placementsHistory: PlacementDraft[] = [];
    private selectedSupId: string | null = null;
    private selectedRoomId: number | null = null;
    private lastPlacementSyncTick: number | null = null;
    private lastPlacementSyncSignature = "";
    private advanceInFlight = false;
    private advanceInFlightStateKey: string | null = null;
    private advanceStatusOverride: { text: string; color: string; untilMs: number } | null = null;
    private promptsFlashTimer: number | null = null;
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

        for (const room of rooms) {
            const draftSupervisorCode = this.placementsDraft[room.room_id] ?? room.supervisor ?? null;
            this.drawRoom(room, toScreen, draftSupervisorCode);
        }

        const events = sortedEvents(state.events);
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
        this.renderOverlay(state, events, prompts, previousState);
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

    private drawRoom(room: SimSimRoom, toScreen: (x: number, y: number) => Vec2, draftSupervisorCode: string | null): void {
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
        if (!locked) {
            this.drawRoomSupervisorAnchor(topLeft, width, height, draftSupervisorCode);
        }
    }

    private drawRoomSupervisorAnchor(topLeft: Vec2, width: number, height: number, code: string | null): void {
        const radius = Math.max(10, Math.min(16, Math.min(width, height) * 0.14));
        const x = topLeft.x + width - radius - 8;
        const y = topLeft.y + radius + 8;
        const assigned = Boolean(code);

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
        hud.style.padding = "10px 12px";
        hud.style.borderRadius = "10px";
        hud.style.background = "rgba(10, 13, 18, 0.76)";
        hud.style.border = "1px solid rgba(140, 214, 200, 0.36)";
        hud.style.fontSize = "12px";
        hud.style.lineHeight = "1.45";
        hud.style.pointerEvents = "auto";
        root.appendChild(hud);

        const advanceControls = document.createElement("div");
        advanceControls.style.position = "absolute";
        advanceControls.style.left = "14px";
        advanceControls.style.top = "150px";
        advanceControls.style.padding = "10px 12px";
        advanceControls.style.borderRadius = "10px";
        advanceControls.style.border = "1px solid rgba(243, 199, 106, 0.45)";
        advanceControls.style.background = "rgba(24, 17, 9, 0.82)";
        advanceControls.style.pointerEvents = "auto";
        advanceControls.style.minWidth = "240px";

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
        supervisorPanel.style.top = "250px";
        supervisorPanel.style.padding = "10px 12px";
        supervisorPanel.style.borderRadius = "10px";
        supervisorPanel.style.border = "1px solid rgba(140, 214, 200, 0.42)";
        supervisorPanel.style.background = "rgba(13, 20, 28, 0.86)";
        supervisorPanel.style.pointerEvents = "auto";
        supervisorPanel.style.minWidth = "320px";
        supervisorPanel.style.maxWidth = "min(420px, 38vw)";
        supervisorPanel.style.maxHeight = "40vh";
        supervisorPanel.style.overflowY = "auto";
        root.appendChild(supervisorPanel);

        const roomCards = document.createElement("div");
        roomCards.style.position = "absolute";
        roomCards.style.right = "14px";
        roomCards.style.top = "12px";
        roomCards.style.width = "min(460px, 34vw)";
        roomCards.style.maxHeight = "66vh";
        roomCards.style.overflowY = "auto";
        roomCards.style.display = "grid";
        roomCards.style.gap = "8px";
        roomCards.style.padding = "2px";
        root.appendChild(roomCards);

        const events = document.createElement("div");
        events.style.position = "absolute";
        events.style.left = "14px";
        events.style.bottom = "14px";
        events.style.width = "min(540px, 46vw)";
        events.style.maxHeight = "28vh";
        events.style.overflow = "hidden";
        events.style.padding = "10px 12px";
        events.style.borderRadius = "10px";
        events.style.background = "rgba(10, 13, 18, 0.78)";
        events.style.border = "1px solid rgba(243, 199, 106, 0.34)";
        events.style.fontSize = "12px";
        events.style.lineHeight = "1.35";
        root.appendChild(events);

        const prompts = document.createElement("div");
        prompts.style.position = "absolute";
        prompts.style.right = "14px";
        prompts.style.bottom = "84px";
        prompts.style.width = "min(460px, 34vw)";
        prompts.style.maxHeight = "30vh";
        prompts.style.overflowY = "auto";
        prompts.style.padding = "10px 12px";
        prompts.style.borderRadius = "10px";
        prompts.style.border = "1px solid rgba(243, 199, 106, 0.45)";
        prompts.style.background = "rgba(24, 17, 9, 0.86)";
        prompts.style.fontSize = "12px";
        prompts.style.lineHeight = "1.35";
        prompts.style.display = "none";
        prompts.style.pointerEvents = "auto";
        root.appendChild(prompts);

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

        const debugPanel = document.createElement("div");
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
        root.appendChild(debugPanel);

        this.overlayRoot = root;
        this.hudEl = hud;
        this.roomCardsEl = roomCards;
        this.eventsEl = events;
        this.promptsEl = prompts;
        this.debugPanelEl = debugPanel;
        this.advanceDayButtonEl = advanceButton;
        this.advanceStatusEl = advanceStatus;
        this.supervisorPanelEl = supervisorPanel;

        mountEl.appendChild(root);
    }

    private renderOverlay(
        state: SimSimViewerState,
        events: SimSimEvent[],
        prompts: SimSimPrompt[],
        previousState?: SimSimViewerState
    ): void {
        if (!this.hudEl || !this.roomCardsEl || !this.eventsEl || !this.promptsEl || !this.debugPanelEl || !this.supervisorPanelEl) return;
        const wm = state.worldMeta;
        const inv = state.inventory;
        const regime = state.regime;
        const previousPhase = (previousState?.worldMeta?.phase ?? "").toLowerCase();
        const awaitingPrompts = (wm?.phase ?? "").toLowerCase() === "awaiting_prompts";
        const planningPhase = (wm?.phase ?? "").toLowerCase() === "planning";
        const enteredAwaitingPrompts = previousPhase === "planning" && awaitingPrompts;
        if (enteredAwaitingPrompts) {
            this.advanceStatusOverride = {
                text: "Day requires a decision - resolve prompts to continue.",
                color: "#f3c76a",
                untilMs: Date.now() + 4000,
            };
        }
        const tickTarget = state.tick + 1;
        this.roomCardsEl.style.pointerEvents = awaitingPrompts ? "none" : "auto";

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
            `<div style="font-size:13px;font-weight:700;letter-spacing:0.03em;margin-bottom:4px;">sim_sim LIVE</div>`,
            `<div>day <strong>${wm?.day ?? "-"}</strong> • tick <strong>${wm?.tick ?? state.tick}</strong> • ${wm?.phase ?? "-"} @ ${wm?.time ?? "-"}</div>`,
            `<div>cash <strong>${inv?.cash ?? "-"}</strong> • raw ${inv?.inventories.raw_brains_dumb ?? 0}/${inv?.inventories.raw_brains_smart ?? 0} • washed ${inv?.inventories.washed_dumb ?? 0}/${inv?.inventories.washed_smart ?? 0}</div>`,
            `<div>substrate ${inv?.inventories.substrate_gallons ?? 0} • ribbon ${inv?.inventories.ribbon_yards ?? 0}</div>`,
            `<div>workers ${inv?.worker_pools?.dumb_total ?? "-"}d / ${inv?.worker_pools?.smart_total ?? "-"}s</div>`,
            `<div>security lead <strong>${wm?.security_lead ?? "-"}</strong></div>`,
            `<div>supervisors: ${supervisorSummary || "none unlocked"}</div>`,
            `<div>regime: ${activeFlags.length ? activeFlags.join(", ") : "none"}</div>`,
            awaitingPrompts
                ? `<div style="color:#f3c76a;">phase awaiting_prompts: placements and advance disabled until prompt resolution</div>`
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
            } else if (latestRejection) {
                this.advanceStatusEl.style.color = "#ffd8cf";
                this.advanceStatusEl.textContent = `Last rejection: ${latestRejection.reasonCode} — ${latestRejection.reason}`;
            } else {
                this.advanceStatusEl.style.color = "#f3efe3";
                this.advanceStatusEl.textContent = "Ready: submit no-op SIM_INPUT to advance one day.";
            }
        }

        const rooms = Array.from(state.rooms.values()).sort((a, b) => a.room_id - b.room_id);
        this.roomCardsEl.innerHTML = rooms
            .map((room) => {
                const acc = room.accidents_today ?? { count: 0, casualties: 0 };
                const draftCode = this.placementsDraft[room.room_id] ?? room.supervisor ?? null;
                const supervisor = draftCode ? supervisorByCode.get(draftCode) : undefined;
                const supervisorLabel = supervisor ? supervisor.name : draftCode ?? "Unassigned";
                const supervisorToken = room.locked
                    ? roomCardSupervisorTokenHtml("LK", "")
                    : roomCardSupervisorTokenHtml(draftCode ?? "—", supervisorLabel);
                return [
                    `<div style="pointer-events:none;border:1px solid ${room.locked ? "rgba(232,159,143,0.45)" : "rgba(140,214,200,0.34)"};`,
                    `background:${room.locked ? "rgba(44,23,23,0.80)" : "rgba(13,20,28,0.82)"};border-radius:10px;padding:8px 10px;">`,
                    `<div style="display:flex;justify-content:space-between;gap:8px;font-size:12px;font-weight:700;">`,
                    `<span>${room.name} (unlock day ${room.unlocked_day >= 0 ? room.unlocked_day : "never"})</span>`,
                    `<span style="display:inline-flex;align-items:center;gap:6px;">${supervisorToken}<span>${room.locked ? "LOCKED" : supervisorLabel}</span></span></div>`,
                    `<div style="font-size:11px;opacity:0.95;">assigned ${fmtPair(room.workers_assigned.dumb, room.workers_assigned.smart)} • present ${fmtPair(room.workers_present.dumb, room.workers_present.smart)}</div>`,
                    `<div style="font-size:11px;opacity:0.95;">equip ${pct(room.equipment_condition)} • S ${pct(room.stress)} • D ${pct(room.discipline)} • A ${pct(room.alignment)}</div>`,
                    `<div style="font-size:11px;opacity:0.95;">out rb ${room.output_today.raw_brains_dumb}/${room.output_today.raw_brains_smart} • w ${room.output_today.washed_dumb}/${room.output_today.washed_smart} • sub ${room.output_today.substrate_gallons} • rib ${room.output_today.ribbon_yards}</div>`,
                    `<div style="font-size:11px;opacity:0.95;">accidents ${acc.count} • casualties ${acc.casualties}</div>`,
                    `</div>`,
                ].join("");
            })
            .join("");

        this.renderSupervisorPlacementsPanel(state, rooms, awaitingPrompts);
        this.renderPromptsPanel(state, prompts, awaitingPrompts, events);
        if (enteredAwaitingPrompts && prompts.length > 0) {
            this.focusPromptsPanel();
        }

        const eventRows = events.slice(-10).map((event) => {
            const room = event.room_id ? ` room=${event.room_id}` : "";
            const sup = event.supervisor ? ` ${event.supervisor}` : "";
            const details = event.details ? ` ${JSON.stringify(event.details)}` : "";
            return `<div>t${event.tick} #${event.event_id} <strong>${event.kind}</strong>${room}${sup}${details}</div>`;
        });
        this.eventsEl.innerHTML = `<div style="font-size:12px;font-weight:700;margin-bottom:4px;">Live Feed</div>${eventRows.join("")}`;

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

    private focusPromptsPanel(): void {
        if (!this.promptsEl) return;
        this.promptsEl.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
        this.promptsEl.style.transition = "box-shadow 120ms ease, border-color 120ms ease";
        this.promptsEl.style.borderColor = "rgba(243, 199, 106, 0.95)";
        this.promptsEl.style.boxShadow = "0 0 0 2px rgba(243, 199, 106, 0.32)";
        if (this.promptsFlashTimer !== null) {
            window.clearTimeout(this.promptsFlashTimer);
        }
        this.promptsFlashTimer = window.setTimeout(() => {
            if (!this.promptsEl) return;
            this.promptsEl.style.borderColor = "rgba(243, 199, 106, 0.45)";
            this.promptsEl.style.boxShadow = "none";
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
        if (this.isPlacementMapEqual(this.placementsDraft, this.placementsBaseline)) return;
        this.pushHistory();
        this.placementsDraft = this.clonePlacementMap(this.placementsBaseline);
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

    private candidateDraftForPlacement(roomId: number, nextCode: string | null, unlockedRooms: SimSimRoom[]): PlacementDraft {
        const candidate = this.clonePlacementMap(this.placementsDraft);
        if (nextCode) {
            for (const room of unlockedRooms) {
                if (room.room_id !== roomId && candidate[room.room_id] === nextCode) {
                    candidate[room.room_id] = null;
                }
            }
        }
        candidate[roomId] = nextCode;
        return candidate;
    }

    private isPlacementTokenDisabled(args: {
        roomId: number;
        nextCode: string | null;
        swapBudget: number;
        controlsDisabled: boolean;
        unlockedRooms: SimSimRoom[];
    }): boolean {
        const { roomId, nextCode, swapBudget, controlsDisabled, unlockedRooms } = args;
        if (controlsDisabled) return true;
        if ((this.placementsDraft[roomId] ?? null) === nextCode) return true;
        const candidate = this.candidateDraftForPlacement(roomId, nextCode, unlockedRooms);
        const swapsUsed = this.computeSwapsUsed(candidate, this.placementsBaseline);
        return swapsUsed > swapBudget;
    }

    private applyPlacementFromToken(args: {
        roomId: number;
        nextCode: string | null;
        state: SimSimViewerState;
        rooms: SimSimRoom[];
        awaitingPrompts: boolean;
        unlockedRooms: SimSimRoom[];
    }): void {
        const { roomId, nextCode, state, rooms, awaitingPrompts, unlockedRooms } = args;
        const currentCode = this.placementsDraft[roomId] ?? null;
        if (currentCode === nextCode) return;
        this.pushHistory();
        this.placementsDraft = this.candidateDraftForPlacement(roomId, nextCode, unlockedRooms);
        this.selectedRoomId = roomId;
        this.selectedSupId = nextCode;
        this.renderSupervisorPlacementsPanel(state, rooms, awaitingPrompts);
    }

    private renderSupervisorPlacementsPanel(state: SimSimViewerState, rooms: SimSimRoom[], awaitingPrompts: boolean): void {
        if (!this.supervisorPanelEl) return;
        const panel = this.supervisorPanelEl;
        panel.innerHTML = "";

        const wm = state.worldMeta;
        const planningPhase = (wm?.phase ?? "").toLowerCase() === "planning";
        const controlsDisabled = !planningPhase || awaitingPrompts || state.desynced;
        const tickTarget = state.tick + 1;
        const unlockedRooms = rooms.filter((room) => !room.locked).sort((a, b) => a.room_id - b.room_id);
        const unlockedSupervisors = Array.from(state.supervisors.values())
            .filter((supervisor) => supervisor.unlocked_day <= tickTarget)
            .sort((a, b) => a.code.localeCompare(b.code));
        this.syncPlacementEditorState(state, rooms);

        const title = document.createElement("div");
        title.style.fontSize = "12px";
        title.style.fontWeight = "700";
        title.style.marginBottom = "6px";
        title.textContent = "Supervisor Placements";
        panel.appendChild(title);

        const hint = document.createElement("div");
        hint.style.fontSize = "11px";
        hint.style.opacity = "0.92";
        hint.style.marginBottom = "8px";
        hint.textContent = "Optional: set room supervisors before advancing. Security (room 1) sets dispatch behavior.";
        panel.appendChild(hint);

        if (unlockedRooms.length === 0) {
            const empty = document.createElement("div");
            empty.style.fontSize = "11px";
            empty.style.opacity = "0.82";
            empty.textContent = "No unlocked rooms yet.";
            panel.appendChild(empty);
            return;
        }

        const swapsUsed = this.computeSwapsUsed(this.placementsDraft, this.placementsBaseline);
        const swapBudget = wm?.supervisor_swaps?.swap_budget ?? ((wm?.day ?? state.tick) < 4 ? 1 : 2);
        const swapsRemaining = Math.max(0, swapBudget - swapsUsed);
        const overBudget = swapsUsed > swapBudget;
        const changed = !this.isPlacementMapEqual(this.placementsDraft, this.placementsBaseline);

        const summary = document.createElement("div");
        summary.style.fontSize = "11px";
        summary.style.marginBottom = "8px";
        summary.innerHTML = [
            `<div>Swap budget: <strong>${swapBudget}</strong> • used: <strong>${swapsUsed}</strong> • remaining: <strong>${swapsRemaining}</strong></div>`,
            `<div>Selected: ${this.selectedRoomId !== null ? `room ${this.selectedRoomId}` : "none"}${this.selectedSupId ? ` -> ${this.selectedSupId}` : ""}</div>`,
            overBudget ? `<div style="color:#ffd8cf;">Placement draft exceeds daily swap budget.</div>` : "",
            controlsDisabled ? `<div style="color:#f3c76a;">Placements locked while phase is ${wm?.phase ?? "unknown"}.</div>` : "",
        ].join("");
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
            const token = createSupervisorToken({
                label: supervisor.code,
                name: supervisor.name,
                selected: this.selectedSupId === supervisor.code && this.selectedRoomId === null,
                disabled: controlsDisabled,
                sizePx: 56,
                onClick: controlsDisabled
                    ? undefined
                    : () => {
                          this.selectedSupId = supervisor.code;
                          this.selectedRoomId = null;
                          this.renderSupervisorPlacementsPanel(state, rooms, awaitingPrompts);
                      },
            });
            supervisorBar.appendChild(token);
        }
        panel.appendChild(supervisorBar);

        for (const room of unlockedRooms) {
            const row = document.createElement("div");
            row.style.display = "block";
            row.style.fontSize = "11px";
            row.style.marginBottom = "8px";
            if (this.selectedRoomId === room.room_id) {
                row.style.background = "rgba(243, 199, 106, 0.16)";
                row.style.borderRadius = "6px";
                row.style.padding = "4px 6px";
            }

            const label = document.createElement("label");
            label.textContent = `Room ${room.room_id} • ${room.name}`;
            label.style.display = "block";
            label.style.marginBottom = "6px";
            row.appendChild(label);

            const selectedCode = this.placementsDraft[room.room_id] ?? null;
            const currentWrap = document.createElement("div");
            currentWrap.style.display = "flex";
            currentWrap.style.alignItems = "center";
            currentWrap.style.gap = "8px";
            currentWrap.style.marginBottom = "6px";
            const currentLabel = document.createElement("span");
            currentLabel.textContent = "Current:";
            currentLabel.style.opacity = "0.84";
            currentWrap.appendChild(currentLabel);
            const currentToken = createSupervisorToken({
                label: selectedCode ?? "—",
                name: selectedCode ? (unlockedSupervisors.find((sup) => sup.code === selectedCode)?.name ?? selectedCode) : "Unassigned",
                selected: false,
                disabled: true,
                sizePx: 48,
            });
            currentWrap.appendChild(currentToken);
            row.appendChild(currentWrap);

            const tokenRail = document.createElement("div");
            tokenRail.style.display = "flex";
            tokenRail.style.flexWrap = "wrap";
            tokenRail.style.gap = "6px";

            const clearDisabled = this.isPlacementTokenDisabled({
                roomId: room.room_id,
                nextCode: null,
                swapBudget,
                controlsDisabled,
                unlockedRooms,
            });
            tokenRail.appendChild(
                createSupervisorToken({
                    label: "×",
                    name: "Unassign",
                    selected: selectedCode === null,
                    disabled: clearDisabled,
                    sizePx: 50,
                    onClick: clearDisabled
                        ? undefined
                        : () =>
                              this.applyPlacementFromToken({
                                  roomId: room.room_id,
                                  nextCode: null,
                                  state,
                                  rooms,
                                  awaitingPrompts,
                                  unlockedRooms,
                              }),
                })
            );

            for (const supervisor of unlockedSupervisors) {
                const tokenDisabled = this.isPlacementTokenDisabled({
                    roomId: room.room_id,
                    nextCode: supervisor.code,
                    swapBudget,
                    controlsDisabled,
                    unlockedRooms,
                });
                tokenRail.appendChild(
                    createSupervisorToken({
                        label: supervisor.code,
                        name: supervisor.name,
                        selected: selectedCode === supervisor.code,
                        disabled: tokenDisabled,
                        sizePx: 50,
                        onClick: tokenDisabled
                            ? undefined
                            : () =>
                                  this.applyPlacementFromToken({
                                      roomId: room.room_id,
                                      nextCode: supervisor.code,
                                      state,
                                      rooms,
                                      awaitingPrompts,
                                      unlockedRooms,
                                  }),
                    })
                );
            }
            row.appendChild(tokenRail);

            panel.appendChild(row);
        }

        const editorActions = document.createElement("div");
        editorActions.style.display = "flex";
        editorActions.style.alignItems = "center";
        editorActions.style.gap = "6px";
        editorActions.style.marginTop = "8px";
        editorActions.style.marginBottom = "4px";

        const undoButton = document.createElement("button");
        undoButton.type = "button";
        undoButton.textContent = "Undo";
        undoButton.disabled = controlsDisabled || this.placementsHistory.length === 0;
        styleSecondaryButton(undoButton, undoButton.disabled);
        if (!undoButton.disabled) {
            undoButton.addEventListener("click", () => {
                this.undo();
                this.renderSupervisorPlacementsPanel(state, rooms, awaitingPrompts);
            });
        }
        editorActions.appendChild(undoButton);

        const resetButton = document.createElement("button");
        resetButton.type = "button";
        resetButton.textContent = "Reset";
        resetButton.disabled = controlsDisabled || !changed;
        styleSecondaryButton(resetButton, resetButton.disabled);
        if (!resetButton.disabled) {
            resetButton.addEventListener("click", () => {
                this.resetDraftToBaseline();
                this.renderSupervisorPlacementsPanel(state, rooms, awaitingPrompts);
            });
        }
        editorActions.appendChild(resetButton);

        const unselectButton = document.createElement("button");
        unselectButton.type = "button";
        unselectButton.textContent = "Unselect";
        unselectButton.disabled = controlsDisabled || (this.selectedRoomId === null && this.selectedSupId === null);
        styleSecondaryButton(unselectButton, unselectButton.disabled);
        if (!unselectButton.disabled) {
            unselectButton.addEventListener("click", () => {
                this.unselect();
                this.renderSupervisorPlacementsPanel(state, rooms, awaitingPrompts);
            });
        }
        editorActions.appendChild(unselectButton);

        panel.appendChild(editorActions);

        const actions = document.createElement("div");
        actions.style.display = "flex";
        actions.style.alignItems = "center";
        actions.style.gap = "8px";
        actions.style.marginTop = "8px";

        const applyButton = document.createElement("button");
        applyButton.type = "button";
        applyButton.textContent = "Apply Placements";
        applyButton.style.border = "1px solid rgba(140, 214, 200, 0.65)";
        applyButton.style.background = "rgba(12, 25, 31, 0.95)";
        applyButton.style.color = "#f3efe3";
        applyButton.style.borderRadius = "8px";
        applyButton.style.padding = "5px 10px";
        applyButton.style.fontSize = "11px";
        applyButton.style.fontWeight = "700";
        applyButton.style.cursor = "pointer";

        const applyDisabled = controlsDisabled || overBudget || !changed;
        applyButton.disabled = applyDisabled;
        applyButton.style.opacity = applyDisabled ? "0.55" : "1";
        applyButton.style.cursor = applyDisabled ? "not-allowed" : "pointer";
        if (!applyDisabled) {
            applyButton.addEventListener("click", () => {
                const setSupervisors: Record<string, string | null> = {};
                for (const room of unlockedRooms) {
                    setSupervisors[String(room.room_id)] = this.placementsDraft[room.room_id] ?? null;
                }
                this.onApplySupervisorPlacements?.({
                    tickTarget,
                    setSupervisors,
                });
            });
        }
        actions.appendChild(applyButton);

        const applyHint = document.createElement("div");
        applyHint.style.fontSize = "11px";
        applyHint.style.opacity = "0.88";
        applyHint.textContent = !changed
            ? "No placement changes."
            : overBudget
              ? "Reduce changes to fit swap budget."
              : `Ready for tick ${tickTarget}.`;
        actions.appendChild(applyHint);

        panel.appendChild(actions);
    }

    private renderPromptsPanel(
        state: SimSimViewerState,
        prompts: SimSimPrompt[],
        awaitingPrompts: boolean,
        events: SimSimEvent[]
    ): void {
        if (!this.promptsEl) return;
        if (prompts.length === 0) {
            this.promptsEl.style.display = "none";
            this.promptsEl.innerHTML = "";
            return;
        }

        this.promptsEl.style.display = "block";
        this.promptsEl.innerHTML = "";

        const title = document.createElement("div");
        title.style.fontSize = "12px";
        title.style.fontWeight = "700";
        title.style.marginBottom = "6px";
        title.textContent = "Prompts";
        this.promptsEl.appendChild(title);

        const hint = document.createElement("div");
        hint.style.fontSize = "11px";
        hint.style.opacity = "0.9";
        hint.style.marginBottom = "8px";
        hint.textContent = awaitingPrompts
            ? "Choose a response to continue day advancement."
            : "Prompt history (resolved prompts are read-only).";
        this.promptsEl.appendChild(hint);

        const latestRejection = findLatestInputRejection(events);
        if (latestRejection) {
            const warning = document.createElement("div");
            warning.style.fontSize = "11px";
            warning.style.marginBottom = "8px";
            warning.style.padding = "6px 7px";
            warning.style.borderRadius = "7px";
            warning.style.border = "1px solid rgba(232, 159, 143, 0.45)";
            warning.style.background = "rgba(58, 22, 22, 0.75)";
            warning.style.color = "#ffd8cf";
            warning.textContent = `Last rejection: ${latestRejection.reasonCode} — ${latestRejection.reason}`;
            this.promptsEl.appendChild(warning);
        }

        const tickTarget = state.tick + 1;

        for (const prompt of prompts) {
            const row = document.createElement("div");
            row.style.border = "1px solid rgba(243, 199, 106, 0.32)";
            row.style.borderRadius = "8px";
            row.style.padding = "8px";
            row.style.marginBottom = "7px";
            row.style.background = "rgba(11, 10, 10, 0.42)";

            const header = document.createElement("div");
            header.style.fontSize = "11px";
            header.style.marginBottom = "6px";
            header.innerHTML = `<strong>${prompt.kind}</strong> • ${prompt.prompt_id}<br/>created t${prompt.tick_created} • status=${prompt.status}`;
            row.appendChild(header);

            const choices = prompt.choices ?? [];
            if (choices.length === 0) {
                const none = document.createElement("div");
                none.style.fontSize = "11px";
                none.style.opacity = "0.75";
                none.textContent = "No valid choices declared.";
                row.appendChild(none);
            } else {
                const buttons = document.createElement("div");
                buttons.style.display = "flex";
                buttons.style.flexWrap = "wrap";
                buttons.style.gap = "6px";
                for (const choice of choices) {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.textContent = choice;
                    btn.style.border = "1px solid rgba(243, 199, 106, 0.55)";
                    btn.style.background = "rgba(28, 24, 16, 0.9)";
                    btn.style.color = "#f3efe3";
                    btn.style.borderRadius = "7px";
                    btn.style.padding = "4px 8px";
                    btn.style.fontSize = "11px";
                    btn.style.pointerEvents = "auto";
                    const disabled = !awaitingPrompts || prompt.status === "resolved" || state.desynced;
                    btn.disabled = disabled;
                    btn.style.opacity = disabled ? "0.55" : "1";
                    if (!disabled) {
                        btn.addEventListener("click", () => {
                            this.onSubmitPromptChoice?.({
                                tickTarget,
                                promptId: prompt.prompt_id,
                                choice,
                            });
                        });
                    }
                    buttons.appendChild(btn);
                }
                row.appendChild(buttons);
            }

            this.promptsEl.appendChild(row);
        }
    }
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

function fmtPair(a: number | null | undefined, b: number | null | undefined): string {
    const left = a === null || a === undefined ? "--" : String(a);
    const right = b === null || b === undefined ? "--" : String(b);
    return `${left}/${right}`;
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
    btn.style.cursor = opts.disabled ? "not-allowed" : "pointer";
    btn.style.opacity = opts.disabled ? "0.45" : "1";
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
    circle.style.border = opts.selected ? "2px solid rgba(243, 199, 106, 0.95)" : "1px solid rgba(140, 214, 200, 0.48)";
    circle.style.background = opts.selected ? "radial-gradient(circle at 35% 30%, rgba(243,199,106,0.28), rgba(20,29,37,0.94) 70%)" : "radial-gradient(circle at 35% 30%, rgba(140,214,200,0.24), rgba(18,24,30,0.94) 72%)";
    circle.style.boxShadow = opts.selected
        ? "0 0 0 2px rgba(243,199,106,0.26), 0 0 18px rgba(243,199,106,0.35)"
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
            if (opts.selected) return;
            circle.style.borderColor = "rgba(243, 199, 106, 0.66)";
            circle.style.boxShadow = "0 0 0 1px rgba(243,199,106,0.2), 0 0 14px rgba(243,199,106,0.30)";
            circle.style.transform = "translateY(-1px)";
        });
        btn.addEventListener("mouseleave", () => {
            if (opts.selected) return;
            circle.style.borderColor = "rgba(140, 214, 200, 0.48)";
            circle.style.boxShadow = "0 0 10px rgba(140,214,200,0.18)";
            circle.style.transform = "translateY(0)";
        });
    }

    return btn;
}
