import * as PIXI from "pixi.js";
import type { SimSimEvent, SimSimPrompt, SimSimRoom, SimSimViewerState } from "./simSimStore";
import { deriveEventRailCards, deriveForecastBandsPerRoom, deriveRecapPanels, deriveSecurityDirective, deriveSpotlightPrompt } from "./viewModel";
import type { EventRailCard, ForecastBand, ForecastRoomBands, RecapDeltas, RecapPanel, SecurityDirective, SpotlightPrompt, SupervisorChange } from "./viewModel";
import {
    CANONICAL_VIEWPORT,
    CCTV_FEED_RECTS,
    TOP_STRIP_LEFT_CLUSTER_RECT,
    anchorBottomLeft,
    anchorBottomRight,
    anchorTopLeft,
    buildDirectorConsoleLayout,
    inset,
    listScaledDirectorRegions,
} from "./ui/layout";
import type { DirectorConsoleLayout, Rect } from "./ui/layout";

type Vec2 = { x: number; y: number };
type SubmitPromptChoice = {
    tickTarget: number;
    promptId: string;
    choice: string;
};
type EndOfDayActionsPayload = {
    sell_washed_dumb: number;
    sell_washed_smart: number;
    convert_workers_dumb: number;
    convert_workers_smart: number;
    upgrade_brains: number;
};
type AdvanceDayPayload = {
    tickTarget: number;
    endOfDay?: EndOfDayActionsPayload;
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
type EndOfDayDraft = EndOfDayActionsPayload;
type EndOfDayPlan = {
    max: EndOfDayDraft;
    effective: EndOfDayDraft;
    preview: {
        cashDelta: number;
        workersDumbDelta: number;
        workersSmartDelta: number;
    };
};
type SimSimClientUiPhase = "planning" | "resolving" | "recap";
type ResolvingBeatTone = "info" | "warning" | "danger" | "success";
type ResolvingBeatKind = "security" | "conflict" | "room" | "accident" | "stinger";
type ResolvingBeat = {
    id: string;
    kind: ResolvingBeatKind;
    title: string;
    detail: string;
    stamp: string;
    tone: ResolvingBeatTone;
};
type ResolvingSession = {
    tickTarget: number;
    submittedStateKey: string;
    baselineState: SimSimViewerState;
    awaitingResolution: boolean;
    beats: ResolvingBeat[];
    beatIndex: number;
    timerId: number | null;
};
type RecapStripModel = {
    day: number;
    spotlight: {
        title: string;
        lead: string;
        body: string;
    };
    topRailCards: EventRailCard[];
    escalations: string[];
    vibeTagline: string;
    netResultLines: string[];
    recapPanels: RecapPanel[];
};
type UiAudioCue = "pickup" | "magnet" | "drop" | "illegal" | "undo" | "rivet";

const EOD_CONVERT_COST = 5;
const EOD_SELL_WASHED_DUMB_PRICE = 10;
const EOD_SELL_WASHED_SMART_PRICE = 25;
const RESOLVING_BEAT_CADENCE_MS = 420;
const RESOLVING_REPLAY_START_DELAY_MS = 180;
const RESOLVING_FINAL_HOLD_MS = 900;
const FX_PICKUP_MS = 280;
const FX_MAGNET_MS = 360;
const FX_IMPACT_MS = 560;
const FX_ILLEGAL_MS = 520;
const FX_STEAM_REWIND_MS = 760;
const FX_RIVET_POP_MS = 420;
const DEV_UI_QUERY_PARAM = "sim_sim_dev_ui";
const DEV_UI_STORAGE_KEY = "loopforge.sim_sim.dev_ui";

export class SimSimScene {
    public readonly app: PIXI.Application;
    private devMode = isSimSimDevUiEnabled();

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
    private devModeMasterToggleEl?: HTMLButtonElement;
    private devFeedToggleEl?: HTMLButtonElement;
    private devSchemaToggleEl?: HTMLButtonElement;
    private promptsEl?: HTMLDivElement;
    private resolvingLayerEl?: HTMLDivElement;
    private recapLayerEl?: HTMLDivElement;
    private debugPanelEl?: HTMLDivElement;
    private layoutDebugOverlayEl?: HTMLDivElement;
    private advanceDayButtonEl?: HTMLButtonElement;
    private advanceControlsEl?: HTMLDivElement;
    private advanceStatusEl?: HTMLDivElement;
    private eodLayerEl?: HTMLDivElement;
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
    private eodDraft: EndOfDayDraft = makeZeroEndOfDayDraft();
    private lastEodDraftTick: number | null = null;
    private uiPhase: SimSimClientUiPhase = "planning";
    private resolvingSession: ResolvingSession | null = null;
    private recapStripModel: RecapStripModel | null = null;
    private lastRecapTriggerKey: string | null = null;
    private previewTargetRoomId: number | null = null;
    private pickupFxKey: string | null = null;
    private pickupFxUntilMs = 0;
    private magnetFxRoomId: number | null = null;
    private magnetFxUntilMs = 0;
    private impactFxRoomIds = new Set<number>();
    private impactFxUntilMs = 0;
    private illegalFxRoomId: number | null = null;
    private illegalFxUntilMs = 0;
    private steamRewindFxUntilMs = 0;
    private rivetPopIndices: number[] = [];
    private rivetPopUntilMs = 0;
    private audioCtx: AudioContext | null = null;
    private devModeHotkeyInstalled = false;
    private directorLayout: DirectorConsoleLayout = buildDirectorConsoleLayout(CANONICAL_VIEWPORT.w, CANONICAL_VIEWPORT.h);
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
        this.updateLayoutModel();
        this.installDevModeHotkey();
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
        this.updateLayoutModel();
        if (opts?.forceAutoFit && this.lastState) this.renderFromState(this.lastState);
    }

    private updateLayoutModel(): void {
        const width = Math.max(1, this.app.renderer.width);
        const height = Math.max(1, this.app.renderer.height);
        this.directorLayout = buildDirectorConsoleLayout(width, height);
        this.root.position.set(this.directorLayout.safeFrame.x, this.directorLayout.safeFrame.y);
        this.root.scale.set(this.directorLayout.safeFrame.scale, this.directorLayout.safeFrame.scale);
        this.applyOverlayRegionLayout();
    }

    private applyOverlayRegionLayout(): void {
        if (!this.overlayRoot) return;
        const scaled = this.directorLayout.scaled;
        if (this.hudEl) {
            applyAbsoluteRect(this.hudEl, scaled.topStripClusters.left);
            this.hudEl.style.maxHeight = `${Math.max(64, scaled.topStripClusters.left.h)}px`;
        }
        if (this.advanceControlsEl) applyAbsoluteRect(this.advanceControlsEl, scaled.commandDeckZones.centerPrimary);
        if (this.placementControlsEl) {
            applyAbsoluteRect(this.placementControlsEl, scaled.commandDeckZones.rightSecondary);
            this.placementControlsEl.style.maxHeight = `${Math.max(64, scaled.commandDeckZones.rightSecondary.h)}px`;
        }
        if (this.supervisorPanelEl) {
            applyAbsoluteRect(this.supervisorPanelEl, scaled.commandDeckZones.leftRoster);
            this.supervisorPanelEl.style.maxHeight = `${Math.max(64, scaled.commandDeckZones.leftRoster.h)}px`;
        }
        if (this.securityDirectivePanelEl) applyAbsoluteRect(this.securityDirectivePanelEl, scaled.rightColumnSplits.directive);
        if (this.roomCardsEl) {
            applyAbsoluteRect(this.roomCardsEl, scaled.rightColumnSplits.docket);
            this.roomCardsEl.style.maxHeight = `${Math.max(64, scaled.rightColumnSplits.docket.h)}px`;
        }
        if (this.eodLayerEl) {
            applyAbsoluteRect(this.eodLayerEl, scaled.overlays.eodBay);
            this.eodLayerEl.style.maxHeight = `${Math.max(64, scaled.overlays.eodBay.h)}px`;
        }

        const safeInset = inset(this.directorLayout.safeFrame, 14);
        const buttonHeight = Math.max(28, Math.round(30 * this.directorLayout.safeFrame.scale));
        const devButtonsArea = anchorBottomLeft(safeInset, {
            w: Math.round(420 * this.directorLayout.safeFrame.scale),
            h: buttonHeight,
        });
        if (this.devModeMasterToggleEl) {
            applyAbsoluteRect(this.devModeMasterToggleEl, anchorTopLeft(devButtonsArea, { w: Math.round(136 * this.directorLayout.safeFrame.scale), h: buttonHeight }));
        }
        if (this.devFeedToggleEl) {
            applyAbsoluteRect(this.devFeedToggleEl, anchorTopLeft(devButtonsArea, { w: Math.round(120 * this.directorLayout.safeFrame.scale), h: buttonHeight }, { x: Math.round(146 * this.directorLayout.safeFrame.scale) }));
        }
        if (this.devSchemaToggleEl) {
            applyAbsoluteRect(this.devSchemaToggleEl, anchorTopLeft(devButtonsArea, { w: Math.round(128 * this.directorLayout.safeFrame.scale), h: buttonHeight }, { x: Math.round(276 * this.directorLayout.safeFrame.scale) }));
        }
        if (this.eventsEl) {
            applyAbsoluteRect(
                this.eventsEl,
                anchorBottomLeft(safeInset, { w: Math.round(460 * this.directorLayout.safeFrame.scale), h: Math.round(220 * this.directorLayout.safeFrame.scale) }, { y: buttonHeight + 8 })
            );
        }
        if (this.debugPanelEl) {
            applyAbsoluteRect(
                this.debugPanelEl,
                anchorBottomRight(safeInset, { w: Math.round(340 * this.directorLayout.safeFrame.scale), h: Math.round(120 * this.directorLayout.safeFrame.scale) }, { y: buttonHeight + 8 })
            );
        }
        this.renderLayoutDebugOverlay();
    }

    private renderLayoutDebugOverlay(): void {
        if (!this.layoutDebugOverlayEl) return;
        const regions = listScaledDirectorRegions(this.directorLayout);
        const html = regions
            .map((region) => {
                const color =
                    region.group === "primary"
                        ? "rgba(140,214,200,0.5)"
                        : region.group === "overlay"
                          ? "rgba(243,199,106,0.5)"
                          : region.group === "feed"
                            ? "rgba(232,159,143,0.42)"
                            : "rgba(199,223,241,0.38)";
                return [
                    `<div style=\"position:absolute;left:${region.rect.x}px;top:${region.rect.y}px;width:${region.rect.w}px;height:${region.rect.h}px;border:1px solid ${color};border-radius:1px;box-sizing:border-box;\">`,
                    `<div style=\"position:absolute;left:2px;top:2px;padding:1px 3px;border-radius:3px;background:rgba(5,8,13,0.62);color:#dce7ef;font-size:9px;line-height:1.2;letter-spacing:0.03em;white-space:nowrap;\">${escapeHtml(region.name)}</div>`,
                    `</div>`,
                ].join("");
            })
            .join("");
        this.layoutDebugOverlayEl.innerHTML = html;
    }

    private nowMs(): number {
        return Date.now();
    }

    private scheduleFxRefresh(delayMs: number): void {
        if (typeof window === "undefined") return;
        window.setTimeout(() => {
            if (!this.lastState) return;
            this.renderFromState(this.lastState);
        }, Math.max(0, Math.floor(delayMs)));
    }

    private ensureAudioContext(): AudioContext | null {
        if (typeof globalThis === "undefined") return null;
        if (this.audioCtx) return this.audioCtx;
        const audioGlobal = globalThis as unknown as {
            AudioContext?: new () => AudioContext;
            webkitAudioContext?: new () => AudioContext;
        };
        const Ctor = audioGlobal.AudioContext ?? audioGlobal.webkitAudioContext;
        if (!Ctor) return null;
        try {
            this.audioCtx = new Ctor();
        } catch {
            this.audioCtx = null;
        }
        return this.audioCtx;
    }

    private playTone(args: {
        type: "sine" | "square" | "sawtooth" | "triangle";
        fromHz: number;
        toHz: number;
        durationMs: number;
        gain: number;
    }): void {
        const ctx = this.ensureAudioContext();
        if (!ctx) return;
        if (ctx.state === "suspended") {
            void ctx.resume().catch(() => undefined);
        }
        const start = ctx.currentTime + 0.002;
        const end = start + (Math.max(40, args.durationMs) / 1000);
        const osc = ctx.createOscillator();
        const amp = ctx.createGain();
        osc.type = args.type;
        osc.frequency.setValueAtTime(Math.max(40, args.fromHz), start);
        osc.frequency.exponentialRampToValueAtTime(Math.max(30, args.toHz), end);
        amp.gain.setValueAtTime(0.0001, start);
        amp.gain.exponentialRampToValueAtTime(Math.max(0.0002, args.gain), start + 0.02);
        amp.gain.exponentialRampToValueAtTime(0.0001, end);
        osc.connect(amp);
        amp.connect(ctx.destination);
        osc.start(start);
        osc.stop(end + 0.02);
    }

    private playUiCue(cue: UiAudioCue): void {
        if (typeof window === "undefined") return;
        switch (cue) {
            case "pickup":
                this.playTone({ type: "triangle", fromHz: 420, toHz: 620, durationMs: 110, gain: 0.045 });
                break;
            case "magnet":
                this.playTone({ type: "sine", fromHz: 560, toHz: 760, durationMs: 90, gain: 0.032 });
                break;
            case "drop":
                this.playTone({ type: "square", fromHz: 980, toHz: 260, durationMs: 190, gain: 0.03 });
                this.playTone({ type: "triangle", fromHz: 360, toHz: 180, durationMs: 220, gain: 0.04 });
                break;
            case "illegal":
                this.playTone({ type: "sawtooth", fromHz: 320, toHz: 90, durationMs: 220, gain: 0.05 });
                break;
            case "undo":
                this.playTone({ type: "triangle", fromHz: 320, toHz: 120, durationMs: 260, gain: 0.036 });
                break;
            case "rivet":
                this.playTone({ type: "square", fromHz: 880, toHz: 520, durationMs: 80, gain: 0.026 });
                break;
            default:
                break;
        }
    }

    private isPickupFxActive(roomId: number, supervisorCode: string): boolean {
        if (this.nowMs() > this.pickupFxUntilMs) return false;
        return this.pickupFxKey === `${roomId}:${supervisorCode}`;
    }

    private isMagnetFxActive(roomId: number): boolean {
        return this.magnetFxRoomId === roomId && this.nowMs() <= this.magnetFxUntilMs;
    }

    private isImpactFxActive(roomId: number): boolean {
        if (this.nowMs() > this.impactFxUntilMs) return false;
        return this.impactFxRoomIds.has(roomId);
    }

    private isIllegalFxActive(roomId: number): boolean {
        return this.illegalFxRoomId === roomId && this.nowMs() <= this.illegalFxUntilMs;
    }

    private isSteamRewindActive(): boolean {
        return this.nowMs() <= this.steamRewindFxUntilMs;
    }

    private triggerPickupFx(roomId: number, supervisorCode: string): void {
        this.pickupFxKey = `${roomId}:${supervisorCode}`;
        this.pickupFxUntilMs = this.nowMs() + FX_PICKUP_MS;
        this.playUiCue("pickup");
        this.scheduleFxRefresh(FX_PICKUP_MS + 30);
    }

    private triggerMagnetFx(roomId: number): void {
        this.magnetFxRoomId = roomId;
        this.magnetFxUntilMs = this.nowMs() + FX_MAGNET_MS;
        this.playUiCue("magnet");
        this.scheduleFxRefresh(FX_MAGNET_MS + 24);
    }

    private triggerImpactFx(roomIds: number[]): void {
        this.impactFxRoomIds = new Set<number>(roomIds.filter((roomId) => Number.isFinite(roomId)));
        this.impactFxUntilMs = this.nowMs() + FX_IMPACT_MS;
        this.playUiCue("drop");
        this.scheduleFxRefresh(FX_IMPACT_MS + 30);
    }

    private triggerIllegalFx(roomId: number): void {
        this.illegalFxRoomId = roomId;
        this.illegalFxUntilMs = this.nowMs() + FX_ILLEGAL_MS;
        this.playUiCue("illegal");
        this.scheduleFxRefresh(FX_ILLEGAL_MS + 24);
    }

    private triggerUndoFx(): void {
        this.steamRewindFxUntilMs = this.nowMs() + FX_STEAM_REWIND_MS;
        this.playUiCue("undo");
        this.scheduleFxRefresh(FX_STEAM_REWIND_MS + 24);
    }

    private triggerRivetPop(previousSwapsUsed: number, nextSwapsUsed: number): void {
        if (nextSwapsUsed <= previousSwapsUsed) return;
        const nextIndices: number[] = [];
        for (let idx = previousSwapsUsed; idx < nextSwapsUsed; idx += 1) {
            nextIndices.push(idx);
        }
        this.rivetPopIndices = nextIndices;
        this.rivetPopUntilMs = this.nowMs() + FX_RIVET_POP_MS;
        this.playUiCue("rivet");
        this.scheduleFxRefresh(FX_RIVET_POP_MS + 24);
    }

    private setPreviewTargetRoom(roomId: number | null, state: SimSimViewerState): void {
        const nextRoomId = roomId ?? null;
        if (this.previewTargetRoomId === nextRoomId) return;
        this.previewTargetRoomId = nextRoomId;
        if (
            nextRoomId !== null &&
            this.selectedRoomId !== null &&
            nextRoomId !== this.selectedRoomId &&
            !this.isIllegalFxActive(nextRoomId)
        ) {
            this.triggerMagnetFx(nextRoomId);
        }
        this.renderFromState(state);
    }

    private canSwapRoomPair(args: {
        sourceRoomId: number;
        targetRoomId: number;
        swapBudget: number;
    }): boolean {
        if (args.sourceRoomId === args.targetRoomId) return false;
        const nextDraft = this.swapDraftBetweenRooms({
            roomId: args.sourceRoomId,
            otherRoomId: args.targetRoomId,
        });
        return this.computeSwapsUsed(nextDraft, this.placementsBaseline) <= args.swapBudget;
    }

    private clearSelectionPreviewFx(): void {
        this.previewTargetRoomId = null;
        this.magnetFxRoomId = null;
    }

    private applyDevModeVisibility(): void {
        if (this.devModeMasterToggleEl) {
            this.devModeMasterToggleEl.textContent = this.devMode ? "Dev Panels: ON" : "Dev Panels: OFF";
            this.devModeMasterToggleEl.style.borderColor = this.devMode ? "rgba(243, 199, 106, 0.72)" : "rgba(140, 214, 200, 0.42)";
            this.devModeMasterToggleEl.style.background = this.devMode ? "rgba(37, 27, 12, 0.92)" : "rgba(10, 13, 18, 0.84)";
            this.devModeMasterToggleEl.style.color = this.devMode ? "#f5ddaa" : "#dce7ef";
        }
        if (this.eventsEl) {
            this.eventsEl.style.display = this.devMode && this.debugFeedVisible ? "block" : "none";
            if (!this.devMode) this.eventsEl.innerHTML = "";
        }
        if (this.devFeedToggleEl) {
            this.devFeedToggleEl.style.display = this.devMode ? "block" : "none";
            this.devFeedToggleEl.textContent = this.debugFeedVisible ? "Hide Debug Feed" : "Debug Feed";
        }
        if (this.devSchemaToggleEl) {
            this.devSchemaToggleEl.style.display = this.devMode ? "block" : "none";
            this.devSchemaToggleEl.textContent = this.debugVisible ? "Hide Schema Debug" : "Schema Debug";
        }
        if (this.debugPanelEl) {
            this.debugPanelEl.style.display = this.devMode && this.debugVisible ? "block" : "none";
            if (!this.devMode) this.debugPanelEl.innerHTML = "";
        }
    }

    private setAllDevPanelsVisible(enabled: boolean): void {
        this.debugVisible = enabled;
        this.debugFeedVisible = enabled;
        this.liveFeedCollapsed = !enabled;
        this.applyDevModeVisibility();
    }

    private setDevMode(enabled: boolean, opts?: { persist?: boolean; rerender?: boolean }): void {
        const next = !!enabled;
        if (this.devMode === next) {
            this.applyDevModeVisibility();
            return;
        }
        this.devMode = next;
        this.setAllDevPanelsVisible(this.devMode);
        if (opts?.persist !== false) persistSimSimDevUiFlag(this.devMode);
        this.applyDevModeVisibility();
        if (opts?.rerender !== false && this.lastState) {
            this.renderFromState(this.lastState);
        }
    }

    private installDevModeHotkey(): void {
        if (this.devModeHotkeyInstalled || typeof window === "undefined") return;
        window.addEventListener("keydown", (event: KeyboardEvent) => {
            if (event.repeat) return;
            const key = event.key.toLowerCase();
            const commandPressed = event.ctrlKey || event.metaKey;
            if (!commandPressed || !event.shiftKey || key !== "d") return;
            event.preventDefault();
            this.setDevMode(!this.devMode, { persist: true, rerender: true });
        });
        this.devModeHotkeyInstalled = true;
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
        this.maybeStartResolvingReplay(state, updateKey);

        this.roomLayer.removeChildren();
        this.supervisorLayer.removeChildren();
        this.uiLayer.removeChildren();
        this.updateLayoutModel();

        const rooms = Array.from(state.rooms.values()).sort((a, b) => a.room_id - b.room_id);
        this.syncPlacementEditorState(state, rooms);
        const events = sortedEvents(state.events);
        const securityDirective = deriveSecurityDirective(this.resolveSecurityLeadCode(state, rooms), events);
        const forecastByRoom = new Map<number, ForecastRoomBands>(
            deriveForecastBandsPerRoom(rooms, securityDirective).map((forecast) => [forecast.roomId, forecast])
        );
        const fallbackSwapBudget = ((state.worldMeta?.day ?? state.tick) <= 2 ? 1 : 2);
        const swapBudget = Math.max(0, nonNegativeInt(state.worldMeta?.supervisor_swaps?.swap_budget ?? fallbackSwapBudget));

        for (const room of rooms) {
            const draftSupervisorCode = this.placementsDraft[room.room_id] ?? room.supervisor ?? null;
            const supervisorName = draftSupervisorCode ? (state.supervisors.get(draftSupervisorCode)?.name ?? draftSupervisorCode) : "Unassigned";
            this.drawRoom(room, this.roomFeedRect(room.room_id), {
                draftSupervisorCode,
                supervisorName,
                forecast: forecastByRoom.get(room.room_id),
                tick: state.tick,
                swapBudget,
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
        caption.x = TOP_STRIP_LEFT_CLUSTER_RECT.x + 4;
        caption.y = TOP_STRIP_LEFT_CLUSTER_RECT.y + 2;
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
            banner.x = TOP_STRIP_LEFT_CLUSTER_RECT.x + 4;
            banner.y = CANONICAL_VIEWPORT.h - 38;
            this.uiLayer.addChild(banner);
        }

        const prompts = sortedPrompts(state.prompts);
        this.renderOverlay(state, events, prompts, {
            previousState,
            securityDirective,
            forecastByRoom,
        });
    }

    private roomFeedRect(roomId: number): Rect {
        const roomRect = this.directorLayout.canonical.cctvFeedsByRoom[roomId];
        if (roomRect) return roomRect;
        return CCTV_FEED_RECTS[6] ?? { x: 956, y: 503, w: 440, h: 317 };
    }

    private drawRoom(
        room: SimSimRoom,
        rect: Rect,
        data: {
            draftSupervisorCode: string | null;
            supervisorName: string;
            forecast: ForecastRoomBands | undefined;
            tick: number;
            swapBudget: number;
        }
    ): void {
        const { draftSupervisorCode, supervisorName, forecast, tick, swapBudget } = data;
        const topLeft: Vec2 = { x: rect.x, y: rect.y };
        const width = Math.max(8, rect.w);
        const height = Math.max(8, rect.h);
        const locked = room.locked;
        const fill = locked ? 0x402d2d : 0x223644;
        const line = locked ? 0xe89f8f : 0x8cd6c8;
        const frame = new PIXI.Graphics();
        frame.roundRect(topLeft.x, topLeft.y, width, height, 10);
        frame.fill({ color: fill, alpha: locked ? 0.92 : 0.82 });
        frame.stroke({ width: locked ? 3 : 2, color: line, alpha: 0.95 });
        this.roomLayer.addChild(frame);
        const selectedAsSource = !locked && this.selectedRoomId === room.room_id;
        const previewAsTarget =
            !locked &&
            this.previewTargetRoomId === room.room_id &&
            this.selectedRoomId !== null &&
            this.selectedRoomId !== room.room_id;
        const previewIsLegal =
            previewAsTarget &&
            this.selectedRoomId !== null &&
            this.canSwapRoomPair({
                sourceRoomId: this.selectedRoomId,
                targetRoomId: room.room_id,
                swapBudget,
            });
        if (selectedAsSource) {
            this.drawRoomSelectionLiftAura(topLeft, width, height, tick);
        }
        if (previewAsTarget) {
            this.drawRoomMagnetPreview(topLeft, width, height, tick, previewIsLegal);
        }
        if (this.isIllegalFxActive(room.room_id)) {
            this.drawRoomSealedStamp(topLeft, width, height, tick);
        }
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
            this.drawRoomSupervisorAnchor(topLeft, width, height, room.room_id, draftSupervisorCode, supervisorName, tick);
        }
    }

    private drawRoomSelectionLiftAura(topLeft: Vec2, width: number, height: number, tick: number): void {
        const pulse = 0.32 + ((((Math.sin((tick + 2) * 0.95) + 1) * 0.5) * 0.3));
        const glow = new PIXI.Graphics();
        glow.roundRect(topLeft.x - 4, topLeft.y - 4, width + 8, height + 8, 13);
        glow.stroke({
            width: 2.2,
            color: 0xf3c76a,
            alpha: pulse,
        });
        glow.fill({ color: 0xf3c76a, alpha: 0.07 + (pulse * 0.08) });
        this.roomLayer.addChild(glow);
    }

    private drawRoomMagnetPreview(topLeft: Vec2, width: number, height: number, tick: number, legal: boolean): void {
        const pulse = 0.22 + ((((Math.sin((tick + 4) * 1.1) + 1) * 0.5) * 0.38));
        const color = legal ? 0x8cd6c8 : 0xe89f8f;
        const ring = new PIXI.Graphics();
        ring.roundRect(topLeft.x - 5, topLeft.y - 5, width + 10, height + 10, 14);
        ring.stroke({
            width: legal ? 2.6 : 2.3,
            color,
            alpha: pulse,
        });
        this.roomLayer.addChild(ring);
    }

    private drawRoomSealedStamp(topLeft: Vec2, width: number, height: number, tick: number): void {
        const pulse = 0.35 + ((((Math.sin((tick + 3) * 1.25) + 1) * 0.5) * 0.4));
        const stampW = Math.min(112, Math.max(74, width * 0.45));
        const stampH = Math.min(28, Math.max(20, height * 0.19));
        const stampX = topLeft.x + (width - stampW) * 0.5;
        const stampY = topLeft.y + (height - stampH) * 0.5;

        const plate = new PIXI.Graphics();
        plate.roundRect(stampX, stampY, stampW, stampH, 5);
        plate.fill({ color: 0x4a1312, alpha: 0.62 + (pulse * 0.18) });
        plate.stroke({ width: 1.8, color: 0xe89f8f, alpha: 0.86 });
        plate.rotation = -0.06;
        plate.pivot.set(stampX + (stampW * 0.5), stampY + (stampH * 0.5));
        plate.position.set(stampX + (stampW * 0.5), stampY + (stampH * 0.5));
        this.roomLayer.addChild(plate);

        const seal = new PIXI.Text({
            text: "SEALED",
            style: {
                fontFamily: "Chivo Mono, monospace",
                fontSize: Math.max(11, Math.floor(stampH * 0.58)),
                fill: 0xffd8cf,
                fontWeight: "700",
                letterSpacing: 1,
                stroke: { color: 0x2e0f0f, width: 3 },
            },
        });
        seal.x = stampX + ((stampW - seal.width) * 0.5);
        seal.y = stampY + ((stampH - seal.height) * 0.5);
        seal.rotation = -0.06;
        this.roomLayer.addChild(seal);
    }

    private drawRoomSupervisorAnchor(
        topLeft: Vec2,
        width: number,
        height: number,
        roomId: number,
        code: string | null,
        supervisorName: string,
        tick: number
    ): void {
        const radius = Math.max(10, Math.min(16, Math.min(width, height) * 0.14));
        const x = topLeft.x + width - radius - 8;
        const y = topLeft.y + radius + 8;
        const assigned = Boolean(code);
        const selected = this.selectedRoomId === roomId;
        const picked = assigned && !!code && this.isPickupFxActive(roomId, code);
        const liftOffsetY = picked ? -2.8 : selected ? -1.2 : 0;
        const scaledRadius = radius * (picked ? 1.13 : selected ? 1.06 : 1);
        const impactFx = this.isImpactFxActive(roomId);
        const illegalFx = this.isIllegalFxActive(roomId);
        const magnetFx = this.isMagnetFxActive(roomId);

        if (selected || picked) {
            const shadow = new PIXI.Graphics();
            shadow.ellipse(x, y + radius + 3, scaledRadius * 0.95, Math.max(3, scaledRadius * 0.34));
            shadow.fill({ color: 0x05090d, alpha: picked ? 0.38 : 0.28 });
            this.supervisorLayer.addChild(shadow);
        }

        const socket = new PIXI.Graphics();
        socket.circle(x, y, radius + (impactFx ? 6 : 3));
        socket.stroke({
            width: magnetFx ? 2.1 : 1.5,
            color: illegalFx ? 0xe89f8f : assigned ? 0xf3c76a : 0x8b98a4,
            alpha: magnetFx ? 0.74 : assigned ? 0.55 : 0.4,
        });
        this.supervisorLayer.addChild(socket);

        const token = new PIXI.Graphics();
        token.circle(x, y + liftOffsetY, scaledRadius);
        token.fill({ color: assigned ? 0x2a3944 : 0x22252a, alpha: 0.96 });
        token.stroke({
            width: selected || picked ? 2.6 : assigned ? 2.2 : 1.4,
            color: illegalFx ? 0xe89f8f : assigned ? 0xf3c76a : 0x8b98a4,
            alpha: assigned ? 0.98 : 0.76,
        });
        this.supervisorLayer.addChild(token);
        if (impactFx) {
            const burst = new PIXI.Graphics();
            const phase = 0.28 + ((((Math.sin((tick + roomId + 3) * 1.45) + 1) * 0.5) * 0.62));
            burst.circle(x, y + liftOffsetY, scaledRadius + 9);
            burst.stroke({ width: 2.4, color: 0xf3c76a, alpha: phase });
            this.supervisorLayer.addChild(burst);

            const sparks = new PIXI.Graphics();
            const sparkCount = 7;
            for (let index = 0; index < sparkCount; index += 1) {
                const angle = ((Math.PI * 2) / sparkCount) * index + (((tick + index + roomId) % 3) * 0.18);
                const fromR = scaledRadius + 3;
                const toR = scaledRadius + 10 + ((index % 3) * 2);
                const x0 = x + Math.cos(angle) * fromR;
                const y0 = y + liftOffsetY + Math.sin(angle) * fromR;
                const x1 = x + Math.cos(angle) * toR;
                const y1 = y + liftOffsetY + Math.sin(angle) * toR;
                sparks.moveTo(x0, y0);
                sparks.lineTo(x1, y1);
            }
            sparks.stroke({ width: 1.6, color: 0xffd08b, alpha: 0.7 });
            this.supervisorLayer.addChild(sparks);
        }

        const label = new PIXI.Text({
            text: code ?? "—",
            style: {
                fontFamily: "Chivo Mono, monospace",
                fontSize: Math.max(10, Math.floor(scaledRadius * 0.95)),
                fill: assigned ? 0xf3efe3 : 0xb4bec8,
                fontWeight: "700",
                stroke: { color: 0x151a1f, width: 2 },
            },
        });
        label.x = x - label.width * 0.5;
        label.y = y + liftOffsetY - label.height * 0.52;
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

    private installOverlay(mountEl: HTMLElement): void {
        const root = document.createElement("div");
        root.style.position = "absolute";
        root.style.inset = "0";
        root.style.pointerEvents = "none";
        root.style.zIndex = "22";
        root.style.fontFamily = "\"Bricolage Grotesque\", sans-serif";
        root.style.color = "#f3efe3";
        installSwapFxStyles(root);

        const layoutDebugOverlay = document.createElement("div");
        layoutDebugOverlay.style.position = "absolute";
        layoutDebugOverlay.style.inset = "0";
        layoutDebugOverlay.style.pointerEvents = "none";
        layoutDebugOverlay.style.zIndex = "26";
        root.appendChild(layoutDebugOverlay);

        const hud = document.createElement("div");
        hud.style.position = "absolute";
        hud.style.padding = "9px 11px";
        hud.style.borderRadius = "10px";
        hud.style.background = "rgba(10, 13, 18, 0.82)";
        hud.style.border = "1px solid rgba(140, 214, 200, 0.36)";
        hud.style.fontSize = "11px";
        hud.style.lineHeight = "1.4";
        hud.style.pointerEvents = "auto";
        hud.style.maxHeight = "20vh";
        hud.style.overflow = "hidden auto";
        root.appendChild(hud);

        const advanceControls = document.createElement("div");
        advanceControls.style.position = "absolute";
        advanceControls.style.padding = "10px 12px";
        advanceControls.style.borderRadius = "10px";
        advanceControls.style.border = "1px solid rgba(243, 199, 106, 0.45)";
        advanceControls.style.background = "rgba(24, 17, 9, 0.82)";
        advanceControls.style.pointerEvents = "auto";

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

        const eodLayer = document.createElement("div");
        eodLayer.style.position = "absolute";
        eodLayer.style.padding = "10px 12px";
        eodLayer.style.borderRadius = "10px";
        eodLayer.style.border = "1px solid rgba(243, 199, 106, 0.45)";
        eodLayer.style.background = "linear-gradient(165deg, rgba(24, 17, 9, 0.92), rgba(17, 23, 28, 0.92))";
        eodLayer.style.pointerEvents = "auto";
        eodLayer.style.maxHeight = "48vh";
        eodLayer.style.overflow = "hidden auto";
        eodLayer.style.display = "none";
        root.appendChild(eodLayer);

        const supervisorPanel = document.createElement("div");
        supervisorPanel.style.position = "absolute";
        supervisorPanel.style.padding = "10px 12px";
        supervisorPanel.style.borderRadius = "10px";
        supervisorPanel.style.border = "1px solid rgba(140, 214, 200, 0.42)";
        supervisorPanel.style.background = "rgba(13, 20, 28, 0.86)";
        supervisorPanel.style.pointerEvents = "auto";
        supervisorPanel.style.maxHeight = "30vh";
        supervisorPanel.style.overflowY = "auto";
        root.appendChild(supervisorPanel);

        const placementControls = document.createElement("div");
        placementControls.style.position = "absolute";
        placementControls.style.padding = "10px 12px";
        placementControls.style.borderRadius = "10px";
        placementControls.style.border = "1px solid rgba(243, 199, 106, 0.45)";
        placementControls.style.background = "rgba(24, 17, 9, 0.86)";
        placementControls.style.pointerEvents = "auto";
        root.appendChild(placementControls);

        const roomCards = document.createElement("div");
        roomCards.style.position = "absolute";
        roomCards.style.maxHeight = "58vh";
        roomCards.style.overflowY = "auto";
        roomCards.style.display = "grid";
        roomCards.style.gap = "7px";
        roomCards.style.padding = "2px 0";
        root.appendChild(roomCards);

        const securityDirectivePanel = document.createElement("div");
        securityDirectivePanel.style.position = "absolute";
        securityDirectivePanel.style.padding = "10px 12px";
        securityDirectivePanel.style.borderRadius = "10px";
        securityDirectivePanel.style.pointerEvents = "auto";
        securityDirectivePanel.style.border = "1px solid rgba(140, 214, 200, 0.42)";
        securityDirectivePanel.style.background = "rgba(13, 20, 28, 0.86)";
        securityDirectivePanel.style.overflow = "hidden";
        root.appendChild(securityDirectivePanel);

        const events = document.createElement("div");
        events.style.position = "absolute";
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

        const prompts = document.createElement("div");
        prompts.style.position = "absolute";
        prompts.style.inset = "0";
        prompts.style.display = "none";
        prompts.style.pointerEvents = "none";
        prompts.style.zIndex = "60";
        root.appendChild(prompts);

        const resolvingLayer = document.createElement("div");
        resolvingLayer.style.position = "absolute";
        resolvingLayer.style.inset = "0";
        resolvingLayer.style.display = "none";
        resolvingLayer.style.pointerEvents = "none";
        resolvingLayer.style.zIndex = "58";
        root.appendChild(resolvingLayer);

        const recapLayer = document.createElement("div");
        recapLayer.style.position = "absolute";
        recapLayer.style.inset = "0";
        recapLayer.style.display = "none";
        recapLayer.style.pointerEvents = "none";
        recapLayer.style.zIndex = "55";
        root.appendChild(recapLayer);

        const devModeToggle = document.createElement("button");
        devModeToggle.type = "button";
        devModeToggle.textContent = "Dev Panels: OFF";
        devModeToggle.style.position = "absolute";
        devModeToggle.style.pointerEvents = "auto";
        devModeToggle.style.border = "1px solid rgba(140, 214, 200, 0.42)";
        devModeToggle.style.background = "rgba(10, 13, 18, 0.84)";
        devModeToggle.style.color = "#dce7ef";
        devModeToggle.style.borderRadius = "8px";
        devModeToggle.style.padding = "6px 10px";
        devModeToggle.style.fontSize = "11px";
        devModeToggle.style.letterSpacing = "0.06em";
        devModeToggle.style.textTransform = "uppercase";
        devModeToggle.style.zIndex = "70";
        devModeToggle.addEventListener("click", () => {
            this.setDevMode(!this.devMode, { persist: true, rerender: true });
        });
        root.appendChild(devModeToggle);

        const feedToggle = document.createElement("button");
        feedToggle.type = "button";
        feedToggle.textContent = "Debug Feed";
        feedToggle.style.position = "absolute";
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
            if (!this.devMode) return;
            this.debugFeedVisible = !this.debugFeedVisible;
            this.applyDevModeVisibility();
        });
        root.appendChild(feedToggle);

        const debugToggle = document.createElement("button");
        debugToggle.type = "button";
        debugToggle.textContent = "Schema Debug";
        debugToggle.style.position = "absolute";
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
            if (!this.devMode) return;
            this.debugVisible = !this.debugVisible;
            this.applyDevModeVisibility();
            if (this.lastState) this.renderFromState(this.lastState);
        });
        root.appendChild(debugToggle);

        const debugPanel = document.createElement("div");
        debugPanel.style.position = "absolute";
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

        this.overlayRoot = root;
        this.hudEl = hud;
        this.roomCardsEl = roomCards;
        this.securityDirectivePanelEl = securityDirectivePanel;
        this.eventsEl = events;
        this.devModeMasterToggleEl = devModeToggle;
        this.devFeedToggleEl = feedToggle;
        this.devSchemaToggleEl = debugToggle;
        this.promptsEl = prompts;
        this.resolvingLayerEl = resolvingLayer;
        this.recapLayerEl = recapLayer;
        this.debugPanelEl = debugPanel;
        this.layoutDebugOverlayEl = layoutDebugOverlay;
        this.advanceDayButtonEl = advanceButton;
        this.advanceControlsEl = advanceControls;
        this.advanceStatusEl = advanceStatus;
        this.eodLayerEl = eodLayer;
        this.supervisorPanelEl = supervisorPanel;
        this.placementControlsEl = placementControls;
        this.setAllDevPanelsVisible(this.devMode);
        this.applyDevModeVisibility();
        this.applyOverlayRegionLayout();

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
            !this.recapLayerEl ||
            !this.securityDirectivePanelEl ||
            !this.eodLayerEl ||
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
        const resolvingPhase = this.uiPhase === "resolving";
        const displayPhase = resolvingPhase ? "resolving" : currentPhase;
        const awaitingPrompts = currentPhase === "awaiting_prompts";
        const planningPhase = currentPhase === "planning";
        const endOfDayPhase = currentPhase === "end_of_day";
        const enteredRecapGate = previousPhase === "end_of_day" && planningPhase;
        if (!resolvingPhase && enteredRecapGate) {
            const triggerKey = `${previousState?.worldMeta?.run_id ?? "run"}:${previousState?.worldMeta?.day ?? "-"}:${previousState?.tick ?? "-"}->${state.worldMeta?.day ?? "-"}:${state.tick}`;
            if (this.lastRecapTriggerKey !== triggerKey) {
                this.lastRecapTriggerKey = triggerKey;
                this.recapStripModel = this.buildRecapStripModel(previousState, state);
                this.uiPhase = this.recapStripModel ? "recap" : "planning";
            }
        }
        if (!planningPhase && this.uiPhase === "recap") {
            this.uiPhase = "planning";
            this.recapStripModel = null;
        }
        const recapPhase = !resolvingPhase && planningPhase && this.uiPhase === "recap" && this.recapStripModel !== null;
        const controlsDisabled = !planningPhase || recapPhase || resolvingPhase || state.desynced;
        const enteredDecisionGate =
            (previousPhase === "planning" && (awaitingPrompts || endOfDayPhase)) ||
            (previousPhase === "awaiting_prompts" && endOfDayPhase);
        const enteredAwaitingPrompts = previousPhase === "planning" && awaitingPrompts;
        if (enteredDecisionGate && !resolvingPhase) {
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
            planningPhase && !recapPhase && !resolvingPhase
                ? `<div style="color:#c4d6e1;opacity:0.86;">Flow: swap on map → Apply Draft → Advance Day</div>`
                : "",
            recapPhase
                ? `<div style="color:#f5ddaa;">phase recap: review outcomes, then click NEXT DAY to resume planning</div>`
                : "",
            resolvingPhase
                ? `<div style="color:#f3c76a;">phase resolving: replaying day resolution beats...</div>`
                : "",
            awaitingPrompts
                ? `<div style="color:#f3c76a;">phase awaiting_prompts: placements and advance disabled until prompt resolution</div>`
                : "",
            endOfDayPhase
                ? `<div style="color:#f3c76a;">phase end_of_day: planning controls disabled until end-of-day actions are submitted</div>`
                : "",
        ].join("");

        const latestRejection = findLatestInputRejection(events);
        const advanceControlsEl = this.advanceControlsEl;
        if (advanceControlsEl) {
            advanceControlsEl.style.display = endOfDayPhase || recapPhase || resolvingPhase ? "none" : "block";
        }
        if (endOfDayPhase && !resolvingPhase) {
            this.renderEndOfDayLayer(state, latestRejection);
        } else if (this.eodLayerEl) {
            this.eodLayerEl.style.display = "none";
            this.eodLayerEl.innerHTML = "";
            this.lastEodDraftTick = null;
            this.eodDraft = makeZeroEndOfDayDraft();
        }
        if (this.advanceDayButtonEl) {
            const disabled = !planningPhase || recapPhase || resolvingPhase || state.desynced || this.advanceInFlight;
            this.advanceDayButtonEl.disabled = disabled;
            this.advanceDayButtonEl.style.opacity = disabled ? "0.55" : "1";
            this.advanceDayButtonEl.style.cursor = disabled ? "not-allowed" : "pointer";
            this.advanceDayButtonEl.onclick = disabled
                ? null
                : () => {
                      if (this.advanceInFlight) return;
                      this.startResolvingPhase(state, tickTarget);
                      this.advanceInFlight = true;
                      this.advanceInFlightStateKey = this.stateUpdateKey(state);
                      this.advanceStatusOverride = {
                          text: "RUN SHIFT submitted. Resolving...",
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
                          this.advanceStatusEl.textContent = "RUN SHIFT submitted. Resolving...";
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
            } else if (resolvingPhase) {
                this.advanceStatusEl.style.color = "#f3c76a";
                this.advanceStatusEl.textContent = "Resolving day outcome beats...";
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
            } else if (recapPhase) {
                this.advanceStatusEl.style.color = "#f5ddaa";
                this.advanceStatusEl.textContent = "Recap in progress. Click NEXT DAY to resume planning controls.";
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
        const backendSwapsUsedRaw = wm?.supervisor_swaps?.swaps_used_if_applied;
        const backendSwapsUsed =
            typeof backendSwapsUsedRaw === "number" && Number.isFinite(backendSwapsUsedRaw)
                ? Math.max(0, Math.floor(backendSwapsUsedRaw))
                : null;
        const backendSwapsRemainingRaw = wm?.supervisor_swaps?.swaps_remaining;
        const backendSwapsRemaining =
            typeof backendSwapsRemainingRaw === "number" && Number.isFinite(backendSwapsRemainingRaw)
                ? Math.max(0, Math.floor(backendSwapsRemainingRaw))
                : null;
        const changed = !this.isPlacementMapEqual(this.placementsDraft, this.placementsBaseline);
        if (this.placementControlsEl) {
            this.placementControlsEl.style.display = endOfDayPhase || recapPhase || resolvingPhase ? "none" : "block";
        }
        if (this.supervisorPanelEl) {
            this.supervisorPanelEl.style.display = endOfDayPhase || recapPhase || resolvingPhase ? "none" : "block";
        }
        if (!endOfDayPhase && !recapPhase && !resolvingPhase) {
            this.renderPlacementControlsCluster(state, currentPhase, {
                controlsDisabled,
                swapsUsed,
                swapBudget,
                swapsRemaining,
                backendSwapsUsed,
                backendSwapsRemaining,
                changed,
                latestRejection,
            });
        }
        const roomCardsHtml: string[] = [renderEventRailHtml(railCards, this.eventRailExpandedCardId)];
        if (this.devMode) {
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
                        phase: displayPhase,
                        tick: state.tick,
                        supervisorLabel,
                        supervisorToken,
                        accidents: acc,
                        forecast: overlayData.forecastByRoom.get(room.room_id),
                    });
                })
                .join("");
            roomCardsHtml.push(
                `<div style="font-size:11px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;opacity:0.75;margin:8px 0 4px 2px;">Inspection (Dev)</div>`,
                inspectionCards
            );
        }
        this.roomCardsEl.innerHTML = roomCardsHtml.join("");
        const railButtons = this.roomCardsEl.querySelectorAll<HTMLButtonElement>("[data-event-rail-card-id]");
        for (const button of railButtons) {
            button.onclick = () => {
                const cardId = button.dataset.eventRailCardId ?? "";
                this.eventRailExpandedCardId = this.eventRailExpandedCardId === cardId ? null : cardId;
                this.renderFromState(state);
            };
        }

        if (!endOfDayPhase && !recapPhase && !resolvingPhase) {
            this.renderSupervisorPlacementsPanel(state, rooms, {
                controlsDisabled,
                swapBudget,
                swapsUsed,
                swapsRemaining,
                changed,
            });
        }
        this.renderPromptsPanel(state, prompts, awaitingPrompts && !recapPhase && !resolvingPhase, events);
        this.renderRecapStripLayer(state, recapPhase);
        this.renderResolvingLayer(state);
        if (!recapPhase && !resolvingPhase && enteredAwaitingPrompts && firstUnresolvedPrompt(prompts)) {
            this.focusPromptsPanel();
        }

        if (this.eventsEl && this.devMode) {
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
        } else if (this.eventsEl) {
            this.eventsEl.style.display = "none";
            this.eventsEl.innerHTML = "";
        }

        if (this.debugPanelEl && this.devMode) {
            this.debugPanelEl.style.display = this.debugVisible ? "block" : "none";
            this.debugPanelEl.innerHTML = [
                `<div>schema_version: ${state.schemaVersion ?? state.kernelHello?.schema_version ?? "-"}</div>`,
                `<div>last_msg_type: ${state.lastMsgType ?? "-"}</div>`,
                `<div>last_applied_diff_count: ${state.lastAppliedDiffCount}</div>`,
                `<div>diffs_applied_total: ${state.diffsAppliedTotal}</div>`,
                `<div>prompts: ${state.prompts.size}</div>`,
                `<div>config: ${wm?.config_id ?? "-"}</div>`,
            ].join("");
        } else if (this.debugPanelEl) {
            this.debugPanelEl.style.display = "none";
            this.debugPanelEl.innerHTML = "";
        }
    }

    private buildRecapStripModel(previousState: SimSimViewerState | undefined, state: SimSimViewerState): RecapStripModel | null {
        if (!previousState) return null;

        const day = previousState.worldMeta?.day ?? Math.max(0, (state.worldMeta?.day ?? 1) - 1);
        const allEvents = sortedEvents(state.events);
        const minTick = Math.min(previousState.tick, state.tick);
        const maxTick = Math.max(previousState.tick, state.tick);
        const boundedEvents = allEvents.filter((event) => event.tick >= minTick && event.tick <= maxTick);
        const recapEvents = boundedEvents.length > 0 ? boundedEvents : allEvents.slice(-10);

        const rooms = Array.from(state.rooms.values()).sort((a, b) => a.room_id - b.room_id);
        const promptsForRecap = sortedPrompts(previousState.prompts);
        const fallbackPrompts = sortedPrompts(state.prompts);
        const activePrompts = promptsForRecap.length > 0 ? promptsForRecap : fallbackPrompts;
        const allCards = deriveEventRailCards(recapEvents, rooms, activePrompts)
            .filter((card) => card.source === "event")
            .filter((card) => !isPromptLifecycleCard(card));
        const notableCards = allCards.filter((card) => card.severity === "notable");
        const topRailCards = (notableCards.length > 0 ? notableCards : allCards).slice(-3).reverse();

        const recapDeltas = deriveRecapDeltasFromStateTransition(previousState, state);
        const supervisorChanges = deriveSupervisorChanges(previousState, state);
        const recapPanels = deriveRecapPanels(day, recapEvents, recapDeltas, supervisorChanges);

        const spotlightPrompt = deriveSpotlightPrompt(activePrompts);
        const spotlight = spotlightForRecap(spotlightPrompt, topRailCards[0]);
        const escalations = summarizeEscalations(supervisorChanges);
        const vibeTagline = deriveFactoryVibeTagline(recapPanels);
        const netResultLines = deriveNetResultLines(recapDeltas, recapPanels);

        return {
            day,
            spotlight,
            topRailCards,
            escalations,
            vibeTagline,
            netResultLines,
            recapPanels,
        };
    }

    private renderRecapStripLayer(state: SimSimViewerState, recapPhase: boolean): void {
        if (!this.recapLayerEl) return;
        if (!recapPhase || !this.recapStripModel) {
            this.recapLayerEl.style.display = "none";
            this.recapLayerEl.style.pointerEvents = "none";
            this.recapLayerEl.innerHTML = "";
            return;
        }

        const model = this.recapStripModel;
        const layer = this.recapLayerEl;
        layer.style.display = "block";
        layer.style.pointerEvents = "auto";
        layer.innerHTML = "";

        const backdrop = document.createElement("div");
        backdrop.style.position = "absolute";
        backdrop.style.inset = "0";
        backdrop.style.background = "radial-gradient(circle at 50% 12%, rgba(243, 199, 106, 0.1), rgba(4, 8, 13, 0.82) 42%, rgba(3, 5, 8, 0.92) 100%)";
        backdrop.style.backdropFilter = "blur(2px)";
        backdrop.style.pointerEvents = "auto";

        const card = document.createElement("section");
        card.style.position = "absolute";
        applyAbsoluteRect(card, this.directorLayout.scaled.overlays.recap);
        card.style.maxHeight = `${this.directorLayout.scaled.overlays.recap.h}px`;
        card.style.overflow = "hidden auto";
        card.style.borderRadius = "16px";
        card.style.border = "1px solid rgba(243, 199, 106, 0.5)";
        card.style.background = "linear-gradient(160deg, rgba(8, 15, 24, 0.95), rgba(18, 14, 9, 0.95))";
        card.style.boxShadow = "0 28px 56px rgba(4, 8, 13, 0.68)";
        card.style.padding = "16px 16px 14px";
        card.style.display = "grid";
        card.style.gap = "12px";
        backdrop.appendChild(card);

        const header = document.createElement("div");
        header.style.display = "flex";
        header.style.alignItems = "center";
        header.style.justifyContent = "space-between";
        header.style.gap = "10px";
        header.innerHTML = [
            `<div>`,
            `<div style="font-size:14px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:#f5dfae;">Recap Strip</div>`,
            `<div style="margin-top:2px;font-size:11px;opacity:0.88;">Day ${model.day} closed. Skim outcomes before reopening planning.</div>`,
            `</div>`,
            `<div style="font-size:10px;letter-spacing:0.08em;text-transform:uppercase;opacity:0.7;border:1px solid rgba(243, 199, 106, 0.52);border-radius:999px;padding:3px 8px;">phase recap</div>`,
        ].join("");
        card.appendChild(header);

        const panels = document.createElement("div");
        panels.style.display = "grid";
        panels.style.gridTemplateColumns = "repeat(auto-fit, minmax(240px, 1fr))";
        panels.style.gap = "10px";
        card.appendChild(panels);

        const happenedLines = model.topRailCards.length === 0
            ? `<div style="font-size:11px;opacity:0.82;">No notable cards captured this cycle.</div>`
            : model.topRailCards
                  .map(
                      (entry) =>
                          `<div style="padding:6px 7px;border-radius:8px;border:1px solid rgba(140, 214, 200, 0.28);background:rgba(8, 18, 24, 0.44);display:grid;gap:2px;"><div style="font-size:10px;opacity:0.72;">${escapeHtml(entry.stamp)}</div><div style="font-size:11px;font-weight:700;line-height:1.3;">${escapeHtml(entry.title)}</div><div style="font-size:10px;opacity:0.86;">${escapeHtml(entry.subtitle)}</div></div>`
                  )
                  .join("");
        panels.innerHTML = [
            `<article style="border:1px solid rgba(243, 199, 106, 0.36);background:rgba(11, 18, 24, 0.72);border-radius:10px;padding:10px;display:grid;gap:8px;">`,
            `<div style="font-size:11px;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;opacity:0.86;">What Happened</div>`,
            `<div style="padding:8px;border-radius:8px;border:1px solid rgba(243, 199, 106, 0.35);background:rgba(38, 29, 12, 0.45);display:grid;gap:4px;">`,
            `<div style="font-size:11px;font-weight:700;">${escapeHtml(model.spotlight.title)}</div>`,
            `<div style="font-size:10px;opacity:0.88;">${escapeHtml(model.spotlight.lead)}</div>`,
            `<div style="font-size:10px;opacity:0.86;">${escapeHtml(model.spotlight.body)}</div>`,
            `</div>`,
            `<div style="display:grid;gap:6px;">${happenedLines}</div>`,
            `</article>`,
            `<article style="border:1px solid rgba(140, 214, 200, 0.34);background:rgba(10, 19, 24, 0.72);border-radius:10px;padding:10px;display:grid;gap:8px;">`,
            `<div style="font-size:11px;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;opacity:0.86;">Who Escalated</div>`,
            `<div style="display:grid;gap:6px;">${model.escalations
                .map(
                    (line) =>
                        `<div style="font-size:11px;line-height:1.3;padding:6px 7px;border-radius:8px;border:1px solid rgba(140, 214, 200, 0.25);background:rgba(9, 16, 22, 0.42);">${escapeHtml(line)}</div>`
                )
                .join("")}</div>`,
            `</article>`,
            `<article style="border:1px solid rgba(243, 199, 106, 0.36);background:rgba(30, 22, 12, 0.68);border-radius:10px;padding:10px;display:grid;gap:8px;">`,
            `<div style="font-size:11px;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;opacity:0.86;">Factory Vibe</div>`,
            `<div style="font-size:12px;font-weight:700;line-height:1.35;">${escapeHtml(model.vibeTagline)}</div>`,
            `<div style="display:flex;flex-wrap:wrap;gap:6px;">${model.recapPanels
                .map((panel) => {
                    const tone = recapToneChipStyle(panel.tone);
                    return `<span style="font-size:10px;padding:2px 7px;border-radius:999px;${tone}">${escapeHtml(panel.title)}</span>`;
                })
                .join("")}</div>`,
            `</article>`,
            `<article style="border:1px solid rgba(140, 214, 200, 0.34);background:rgba(10, 19, 24, 0.72);border-radius:10px;padding:10px;display:grid;gap:8px;">`,
            `<div style="font-size:11px;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;opacity:0.86;">Net Results</div>`,
            `<div style="display:grid;gap:5px;">${model.netResultLines
                .map((line) => `<div style="font-size:11px;line-height:1.3;">${escapeHtml(line)}</div>`)
                .join("")}</div>`,
            `</article>`,
        ].join("");

        const ctaRow = document.createElement("div");
        ctaRow.style.display = "flex";
        ctaRow.style.justifyContent = "flex-end";
        ctaRow.style.marginTop = "2px";
        card.appendChild(ctaRow);

        const nextDayButton = document.createElement("button");
        nextDayButton.type = "button";
        nextDayButton.textContent = "NEXT DAY";
        nextDayButton.style.border = "1px solid rgba(243, 199, 106, 0.78)";
        nextDayButton.style.background = "rgba(38, 29, 12, 0.95)";
        nextDayButton.style.color = "#f3efe3";
        nextDayButton.style.borderRadius = "9px";
        nextDayButton.style.padding = "8px 14px";
        nextDayButton.style.fontSize = "12px";
        nextDayButton.style.fontWeight = "700";
        nextDayButton.style.letterSpacing = "0.06em";
        nextDayButton.style.cursor = "pointer";
        nextDayButton.style.pointerEvents = "auto";
        nextDayButton.onclick = () => {
            this.uiPhase = "planning";
            this.recapStripModel = null;
            this.renderFromState(state);
        };
        ctaRow.appendChild(nextDayButton);

        layer.appendChild(backdrop);
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

    private startResolvingPhase(state: SimSimViewerState, tickTarget: number): void {
        this.stopResolvingPlaybackTimer();
        this.uiPhase = "resolving";
        this.recapStripModel = null;
        this.resolvingSession = {
            tickTarget,
            submittedStateKey: this.stateUpdateKey(state),
            baselineState: state,
            awaitingResolution: true,
            beats: [],
            beatIndex: -1,
            timerId: null,
        };
        this.renderFromState(state);
    }

    private maybeStartResolvingReplay(state: SimSimViewerState, updateKey: string): void {
        const session = this.resolvingSession;
        if (!session || !session.awaitingResolution) return;
        if (updateKey === session.submittedStateKey) return;

        const phase = normalizePhaseToken(state.worldMeta?.phase);
        const reachedTargetTick = state.tick >= session.tickTarget;
        const enteredDecisionGate = phase === "awaiting_prompts" || phase === "end_of_day";
        const returnedPlanningAtTarget = phase === "planning" && reachedTargetTick;
        if (!enteredDecisionGate && !returnedPlanningAtTarget) return;

        session.awaitingResolution = false;
        session.beats = this.buildResolvingBeats(session.baselineState, state);
        session.beatIndex = -1;
        window.setTimeout(() => {
            this.playNextResolvingBeat();
        }, RESOLVING_REPLAY_START_DELAY_MS);
    }

    private playNextResolvingBeat(): void {
        const session = this.resolvingSession;
        if (!session) return;
        this.stopResolvingPlaybackTimer();

        const nextBeatIndex = session.beatIndex + 1;
        if (nextBeatIndex >= session.beats.length) {
            session.timerId = window.setTimeout(() => {
                this.finishResolvingPhase();
            }, RESOLVING_FINAL_HOLD_MS);
            return;
        }

        session.beatIndex = nextBeatIndex;
        if (this.lastState) this.renderFromState(this.lastState);
        session.timerId = window.setTimeout(() => {
            this.playNextResolvingBeat();
        }, RESOLVING_BEAT_CADENCE_MS);
    }

    private stopResolvingPlaybackTimer(): void {
        const timerId = this.resolvingSession?.timerId;
        if (timerId !== null && timerId !== undefined) {
            window.clearTimeout(timerId);
        }
        if (this.resolvingSession) {
            this.resolvingSession.timerId = null;
        }
    }

    private finishResolvingPhase(): void {
        this.stopResolvingPlaybackTimer();
        this.resolvingSession = null;
        this.uiPhase = "planning";
        if (this.lastState) this.renderFromState(this.lastState);
    }

    private buildResolvingBeats(baselineState: SimSimViewerState, state: SimSimViewerState): ResolvingBeat[] {
        const beats: ResolvingBeat[] = [];
        const currentEvents = sortedEvents(state.events);
        const baselineEventKeys = new Set(Array.from(baselineState.events.values()).map((event) => resolvingEventKey(event)));
        const resolutionEvents = currentEvents.filter((event) => !baselineEventKeys.has(resolvingEventKey(event)));
        const rooms = Array.from(state.rooms.values()).sort((a, b) => a.room_id - b.room_id);

        const securityDirective = deriveSecurityDirective(this.resolveSecurityLeadCode(state, rooms), currentEvents);
        beats.push({
            id: "security-flash",
            kind: "security",
            title: "Security effect flash",
            detail: `${securityDirective.display.label} under lead ${securityDirective.lead}`,
            stamp: securityDirective.stamp,
            tone:
                securityDirective.tone === "stable"
                    ? "success"
                    : securityDirective.tone === "watch"
                      ? "warning"
                      : "danger",
        });

        const conflictEvent = resolutionEvents.find(
            (event) => event.kind === "conflict_discovered" || event.kind === "conflict_event"
        );
        if (conflictEvent) {
            beats.push({
                id: `conflict-${conflictEvent.tick}-${conflictEvent.event_id}`,
                kind: "conflict",
                title: "Conflict stamp",
                detail: resolvingEventSummary(conflictEvent),
                stamp: resolvingStamp(conflictEvent),
                tone: "warning",
            });
        }

        for (const room of rooms) {
            const previousRoom = baselineState.rooms.get(room.room_id);
            const roomEvents = resolutionEvents.filter((event) => event.room_id === room.room_id);
            beats.push(this.buildRoomOutcomeBeat(room, previousRoom, roomEvents));
        }

        const accidentDelta = totalRoomAccidents(rooms) - totalRoomAccidents(Array.from(baselineState.rooms.values()));
        const casualtyDelta = totalRoomCasualties(rooms) - totalRoomCasualties(Array.from(baselineState.rooms.values()));
        if (accidentDelta > 0 || casualtyDelta > 0 || resolutionEvents.some((event) => isAccidentEvent(event.kind))) {
            beats.push({
                id: "accident-punch",
                kind: "accident",
                title: "Accident punch-in",
                detail: `accidents +${Math.max(0, accidentDelta)} • casualties +${Math.max(0, casualtyDelta)}`,
                stamp: `T${String(state.tick).padStart(2, "0")}`,
                tone: casualtyDelta > 0 ? "danger" : "warning",
            });
        }

        const stingerEvent =
            resolutionEvents.find((event) => event.kind === "critical_triggered" || event.kind === "critical_suppressed") ??
            resolutionEvents.find((event) => event.kind === "tension_zone");
        if (stingerEvent) {
            const suppressed = stingerEvent.kind === "critical_suppressed";
            beats.push({
                id: `stinger-${stingerEvent.tick}-${stingerEvent.event_id}`,
                kind: "stinger",
                title: stingerEvent.kind === "tension_zone" ? "Tension zone stinger" : "Critical stinger",
                detail: resolvingEventSummary(stingerEvent),
                stamp: resolvingStamp(stingerEvent),
                tone: suppressed ? "success" : "danger",
            });
        }
        return beats;
    }

    private buildRoomOutcomeBeat(
        room: SimSimRoom,
        previousRoom: SimSimRoom | undefined,
        roomEvents: SimSimEvent[]
    ): ResolvingBeat {
        const roomTitle = `Room ${room.room_id} · ${room.name}`;
        if (room.locked) {
            return {
                id: `room-${room.room_id}`,
                kind: "room",
                title: roomTitle,
                detail: "locked",
                stamp: `R${room.room_id}`,
                tone: "info",
            };
        }

        const notableEvent =
            roomEvents.find((event) => event.kind === "critical_triggered" || event.kind === "conflict_event") ?? roomEvents[0];
        if (notableEvent) {
            return {
                id: `room-${room.room_id}-${notableEvent.tick}-${notableEvent.event_id}`,
                kind: "room",
                title: roomTitle,
                detail: resolvingEventSummary(notableEvent),
                stamp: resolvingStamp(notableEvent),
                tone: eventTone(notableEvent.kind),
            };
        }

        const previousOutput = previousRoom ? totalSingleRoomOutput(previousRoom) : 0;
        const outputNow = totalSingleRoomOutput(room);
        const outputDelta = outputNow - previousOutput;
        const stressDelta = previousRoom ? numberOrZero(room.stress) - numberOrZero(previousRoom.stress) : 0;
        const disciplineDelta = previousRoom ? numberOrZero(room.discipline) - numberOrZero(previousRoom.discipline) : 0;

        if (outputDelta > 0 && stressDelta <= 0.01 && disciplineDelta >= -0.01) {
            return {
                id: `room-${room.room_id}`,
                kind: "room",
                title: roomTitle,
                detail: "throughput up, line stable",
                stamp: `R${room.room_id}`,
                tone: "success",
            };
        }
        if (stressDelta > 0.03 || disciplineDelta < -0.03) {
            return {
                id: `room-${room.room_id}`,
                kind: "room",
                title: roomTitle,
                detail: "stress raised or discipline dipped",
                stamp: `R${room.room_id}`,
                tone: "warning",
            };
        }
        return {
            id: `room-${room.room_id}`,
            kind: "room",
            title: roomTitle,
            detail: "holding pattern",
            stamp: `R${room.room_id}`,
            tone: "info",
        };
    }

    private renderResolvingLayer(state: SimSimViewerState): void {
        if (!this.resolvingLayerEl) return;
        const layer = this.resolvingLayerEl;
        const session = this.resolvingSession;
        const active = this.uiPhase === "resolving" && session !== null;
        if (!active || !session) {
            layer.style.display = "none";
            layer.style.pointerEvents = "none";
            layer.innerHTML = "";
            return;
        }

        layer.style.display = "block";
        layer.style.pointerEvents = "auto";
        layer.innerHTML = "";

        const backdrop = document.createElement("div");
        backdrop.style.position = "absolute";
        backdrop.style.inset = "0";
        backdrop.style.background = "radial-gradient(circle at 50% 8%, rgba(243,199,106,0.14), rgba(4,8,13,0.84) 40%, rgba(4,8,13,0.92) 100%)";
        backdrop.style.backdropFilter = "blur(1.6px)";
        backdrop.style.pointerEvents = "auto";
        layer.appendChild(backdrop);

        const panel = document.createElement("section");
        panel.style.position = "absolute";
        applyAbsoluteRect(panel, this.directorLayout.scaled.overlays.resolvingTracker);
        panel.style.borderRadius = "14px";
        panel.style.border = "1px solid rgba(243, 199, 106, 0.55)";
        panel.style.background = "linear-gradient(165deg, rgba(8, 15, 24, 0.96), rgba(18, 14, 9, 0.94))";
        panel.style.boxShadow = "0 24px 50px rgba(4, 8, 13, 0.72)";
        panel.style.padding = "12px 13px";
        panel.style.display = "grid";
        panel.style.gap = "8px";
        panel.style.overflow = "hidden";
        backdrop.appendChild(panel);

        const revealedCount = session.awaitingResolution ? 0 : Math.max(0, session.beatIndex + 1);
        const statusText = session.awaitingResolution
            ? "Awaiting snapshot/diff from kernel..."
            : `Revealing beat ${Math.min(revealedCount, session.beats.length)}/${session.beats.length}`;
        const currentBeat = !session.awaitingResolution && session.beatIndex >= 0 ? session.beats[session.beatIndex] : null;
        const beatListHeight = Math.max(20, Math.floor(this.directorLayout.scaled.overlays.resolvingTracker.h - 84));

        panel.innerHTML = [
            `<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">`,
            `<div style="font-size:12px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;color:#f5dfae;">Resolving</div>`,
            `<div style="font-size:10px;opacity:0.78;">day ${state.worldMeta?.day ?? "-"} • tick ${state.tick}</div>`,
            `</div>`,
            `<div style="font-size:11px;opacity:0.92;color:${session.awaitingResolution ? "#f3efe3" : "#f3c76a"};">${escapeHtml(statusText)}</div>`,
            `<div style="display:grid;gap:6px;max-height:${beatListHeight}px;overflow:auto;padding-right:2px;">`,
            session.beats
                .map((beat, index) => {
                    const revealed = index < revealedCount;
                    const activeBeat = index === session.beatIndex;
                    const styles = resolvingBeatStyle(beat.tone, revealed, activeBeat);
                    return [
                        `<div style="${styles.row}">`,
                        `<div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">`,
                        `<div style="font-size:11px;font-weight:700;line-height:1.3;">${escapeHtml(beat.title)}</div>`,
                        `<div style="font-size:10px;opacity:0.74;">${escapeHtml(beat.stamp)}</div>`,
                        `</div>`,
                        `<div style="font-size:10px;opacity:0.88;line-height:1.35;">${escapeHtml(beat.detail)}</div>`,
                        `</div>`,
                    ].join("");
                })
                .join(""),
            `</div>`,
            currentBeat?.kind === "security"
                ? `<div style="height:5px;border-radius:999px;background:linear-gradient(90deg, rgba(243,199,106,0.9), rgba(140,214,200,0.92));box-shadow:0 0 22px rgba(243,199,106,0.48);"></div>`
                : "",
        ].join("");
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
            this.clearSelectionPreviewFx();
            this.pickupFxUntilMs = 0;
            this.illegalFxUntilMs = 0;
            this.rivetPopUntilMs = 0;
            this.rivetPopIndices = [];
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
        this.placementsHistory = [this.clonePlacementMap(this.placementsDraft)];
    }

    private undo(): void {
        const previous = this.placementsHistory.pop();
        if (!previous) return;
        this.placementsDraft = this.clonePlacementMap(previous);
        this.triggerUndoFx();
        this.unselect();
    }

    private unselect(): void {
        this.selectedSupId = null;
        this.selectedRoomId = null;
        this.clearSelectionPreviewFx();
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
            this.triggerPickupFx(roomId, supervisorCode);
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
            this.triggerIllegalFx(roomId);
            this.placementInteractionStatus = { text: "SEALED: no swaps remaining.", color: "#ffd8cf" };
            this.renderFromState(state);
            return;
        }

        const sourceRoomId = this.selectedRoomId;
        const nextDraft = this.swapDraftBetweenRooms({
            roomId: sourceRoomId,
            otherRoomId: roomId,
        });
        const swapsUsedBefore = this.computeSwapsUsed(this.placementsDraft, this.placementsBaseline);
        const swapsUsedIfApplied = this.computeSwapsUsed(nextDraft, this.placementsBaseline);
        if (swapsUsedIfApplied > swapBudget) {
            this.triggerIllegalFx(roomId);
            this.placementInteractionStatus = { text: "SEALED: no swaps remaining.", color: "#ffd8cf" };
            this.renderFromState(state);
            return;
        }

        this.pushHistory();
        this.placementsDraft = nextDraft;
        this.triggerImpactFx([sourceRoomId, roomId]);
        this.triggerRivetPop(swapsUsedBefore, swapsUsedIfApplied);
        this.placementInteractionStatus = {
            text: `Swapped room ${sourceRoomId} with room ${roomId}.`,
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
            backendSwapsUsed: number | null;
            backendSwapsRemaining: number | null;
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

        const rivetRack = document.createElement("div");
        rivetRack.style.marginBottom = "8px";
        rivetRack.style.padding = "7px 8px";
        rivetRack.style.border = "1px solid rgba(243, 199, 106, 0.34)";
        rivetRack.style.borderRadius = "8px";
        rivetRack.style.background = "linear-gradient(165deg, rgba(31, 20, 9, 0.92), rgba(11, 17, 23, 0.9))";
        rivetRack.style.display = "grid";
        rivetRack.style.gap = "6px";

        const rivetTitle = document.createElement("div");
        rivetTitle.style.fontSize = "10px";
        rivetTitle.style.letterSpacing = "0.08em";
        rivetTitle.style.textTransform = "uppercase";
        rivetTitle.style.opacity = "0.82";
        rivetTitle.textContent = "Swap Rivets";
        rivetRack.appendChild(rivetTitle);

        const rivetRow = document.createElement("div");
        rivetRow.className = "simsim-rivet-row";
        const consumedSwapsForDisplay = data.changed ? data.swapsUsed : (data.backendSwapsUsed ?? data.swapsUsed);
        const remainingSwapsForDisplay = data.changed ? data.swapsRemaining : (data.backendSwapsRemaining ?? data.swapsRemaining);
        const activeRivetPop = this.nowMs() <= this.rivetPopUntilMs;
        const popIndexSet = new Set<number>(activeRivetPop ? this.rivetPopIndices : []);
        const slotCount = Math.max(0, Math.floor(data.swapBudget));
        for (let slot = 0; slot < slotCount; slot += 1) {
            const consumed = slot < consumedSwapsForDisplay;
            const rivet = document.createElement("div");
            rivet.className = `simsim-rivet ${consumed ? "is-consumed" : "is-armed"}${popIndexSet.has(slot) ? " is-pop" : ""}`;
            rivet.textContent = consumed ? "✖" : "⛓";
            rivetRow.appendChild(rivet);
        }
        if (slotCount <= 0) {
            const empty = document.createElement("div");
            empty.style.fontSize = "11px";
            empty.style.opacity = "0.8";
            empty.textContent = "No swaps available this day.";
            rivetRow.appendChild(empty);
        }
        rivetRack.appendChild(rivetRow);

        const rivetLegend = document.createElement("div");
        rivetLegend.style.fontSize = "11px";
        rivetLegend.style.opacity = "0.94";
        rivetLegend.style.color = remainingSwapsForDisplay > 0 ? "#f3efe3" : "#ffd8cf";
        rivetLegend.textContent = `${remainingSwapsForDisplay} remaining • ${consumedSwapsForDisplay} spent • budget ${data.swapBudget}`;
        rivetRack.appendChild(rivetLegend);

        if (data.backendSwapsRemaining !== null) {
            const kernelLedger = document.createElement("div");
            kernelLedger.style.fontSize = "10px";
            kernelLedger.style.opacity = "0.82";
            const backendUsedLabel = data.backendSwapsUsed !== null ? ` (${data.backendSwapsUsed} used)` : "";
            if (data.changed) {
                kernelLedger.style.color = "#f5ddaa";
                kernelLedger.textContent =
                    `Kernel ledger: ${data.backendSwapsRemaining} remaining${backendUsedLabel} • draft preview: ${data.swapsRemaining} remaining`;
            } else {
                kernelLedger.style.color = "#d2d8de";
                kernelLedger.textContent = `Kernel ledger: ${data.backendSwapsRemaining} remaining${backendUsedLabel}`;
            }
            rivetRack.appendChild(kernelLedger);
        }
        cluster.appendChild(rivetRack);

        if (this.placementInteractionStatus) {
            const status = document.createElement("div");
            status.style.fontSize = "11px";
            status.style.marginBottom = "8px";
            status.style.color = this.placementInteractionStatus.color;
            status.textContent = this.placementInteractionStatus.text;
            cluster.appendChild(status);
        }

        if (this.illegalFxRoomId !== null && this.isIllegalFxActive(this.illegalFxRoomId)) {
            const stamp = document.createElement("div");
            stamp.className = "simsim-sealed-stamp";
            stamp.textContent = "SEALED";
            cluster.appendChild(stamp);
        }

        if (this.isSteamRewindActive()) {
            const steam = document.createElement("div");
            steam.className = "simsim-steam-rewind";
            steam.innerHTML = `<span>Steam rewind engaged</span>`;
            cluster.appendChild(steam);
        }

        const controls = document.createElement("div");
        controls.style.display = "flex";
        controls.style.alignItems = "center";
        controls.style.gap = "6px";
        controls.style.marginBottom = "2px";

        const undoButton = document.createElement("button");
        undoButton.type = "button";
        undoButton.textContent = "Undo (1-step)";
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

    private renderEndOfDayLayer(
        state: SimSimViewerState,
        latestRejection: { reasonCode: string; reason: string } | null
    ): void {
        if (!this.eodLayerEl) return;
        if (this.lastEodDraftTick !== state.tick) {
            this.lastEodDraftTick = state.tick;
            this.eodDraft = makeZeroEndOfDayDraft();
        }

        const panel = this.eodLayerEl;
        panel.style.display = "block";
        panel.innerHTML = "";

        const plan = this.buildEndOfDayPlan(state.inventory, this.eodDraft);
        this.eodDraft = { ...plan.effective };
        const disabled = state.desynced || this.advanceInFlight;

        const title = document.createElement("div");
        title.style.fontSize = "12px";
        title.style.fontWeight = "700";
        title.style.letterSpacing = "0.06em";
        title.style.textTransform = "uppercase";
        title.textContent = "EOD Layer";
        panel.appendChild(title);

        const subtitle = document.createElement("div");
        subtitle.style.marginTop = "4px";
        subtitle.style.fontSize = "11px";
        subtitle.style.opacity = "0.9";
        subtitle.textContent = "Finalize SELL / CONVERT / UPGRADE actions, then confirm.";
        panel.appendChild(subtitle);

        const crates = document.createElement("div");
        crates.style.display = "grid";
        crates.style.gridTemplateColumns = "repeat(2, minmax(0, 1fr))";
        crates.style.gap = "6px";
        crates.style.marginTop = "9px";
        const inv = state.inventory?.inventories;
        const crateRows = [
            { label: "RAW BRAINS", value: `${inv?.raw_brains_dumb ?? 0}D / ${inv?.raw_brains_smart ?? 0}S` },
            { label: "WASHED BRAINS", value: `${inv?.washed_dumb ?? 0}D / ${inv?.washed_smart ?? 0}S` },
            { label: "SUBSTRATE", value: `${inv?.substrate_gallons ?? 0}` },
            { label: "RIBBON", value: `${inv?.ribbon_yards ?? 0}` },
        ];
        for (const crate of crateRows) {
            const card = document.createElement("div");
            card.style.border = "1px solid rgba(140, 214, 200, 0.3)";
            card.style.background = "rgba(7, 15, 22, 0.6)";
            card.style.borderRadius = "8px";
            card.style.padding = "6px 7px";

            const label = document.createElement("div");
            label.style.fontSize = "9px";
            label.style.letterSpacing = "0.06em";
            label.style.textTransform = "uppercase";
            label.style.opacity = "0.72";
            label.textContent = crate.label;
            card.appendChild(label);

            const value = document.createElement("div");
            value.style.marginTop = "2px";
            value.style.fontFamily = "\"Chivo Mono\", monospace";
            value.style.fontSize = "12px";
            value.style.fontWeight = "700";
            value.textContent = crate.value;
            card.appendChild(value);
            crates.appendChild(card);
        }
        panel.appendChild(crates);

        const setDraftValue = (key: keyof EndOfDayDraft, nextValue: number): void => {
            this.eodDraft = {
                ...this.eodDraft,
                [key]: Math.max(0, Math.floor(nextValue)),
            };
            this.renderFromState(state);
        };

        const renderMachineSection = (args: {
            title: string;
            note: string;
            controls: Array<{
                key: keyof EndOfDayDraft;
                label: string;
                value: number;
                max: number;
            }>;
        }): void => {
            const section = document.createElement("section");
            section.style.marginTop = "10px";
            section.style.border = "1px solid rgba(243, 199, 106, 0.32)";
            section.style.borderRadius = "8px";
            section.style.background = "rgba(33, 21, 12, 0.5)";
            section.style.padding = "8px";
            section.style.display = "grid";
            section.style.gap = "6px";

            const header = document.createElement("div");
            header.style.display = "flex";
            header.style.alignItems = "center";
            header.style.justifyContent = "space-between";
            header.style.gap = "8px";
            header.innerHTML = `<span style="font-size:10px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;">${escapeHtml(args.title)}</span><span style="font-size:10px;opacity:0.7;">${escapeHtml(args.note)}</span>`;
            section.appendChild(header);

            for (const control of args.controls) {
                const row = document.createElement("div");
                row.style.display = "grid";
                row.style.gap = "4px";

                const labelRow = document.createElement("div");
                labelRow.style.display = "flex";
                labelRow.style.alignItems = "center";
                labelRow.style.justifyContent = "space-between";
                labelRow.style.gap = "8px";
                labelRow.innerHTML = `<span style="font-size:11px;opacity:0.94;">${escapeHtml(control.label)}</span><span style="font-size:10px;opacity:0.72;">max ${control.max}</span>`;
                row.appendChild(labelRow);

                const stepper = document.createElement("div");
                stepper.style.display = "grid";
                stepper.style.gridTemplateColumns = "26px 1fr 26px";
                stepper.style.gap = "5px";
                const minusBtn = document.createElement("button");
                minusBtn.type = "button";
                minusBtn.textContent = "−";
                minusBtn.disabled = disabled || control.value <= 0;
                styleSecondaryButton(minusBtn, disabled || control.value <= 0);
                minusBtn.style.padding = "4px 0";
                if (!minusBtn.disabled) {
                    minusBtn.onclick = () => setDraftValue(control.key, control.value - 1);
                }
                stepper.appendChild(minusBtn);

                const input = document.createElement("input");
                input.type = "number";
                input.min = "0";
                input.max = String(control.max);
                input.step = "1";
                input.value = String(control.value);
                input.disabled = disabled;
                input.style.width = "100%";
                input.style.border = "1px solid rgba(140, 214, 200, 0.42)";
                input.style.background = "rgba(7, 15, 22, 0.72)";
                input.style.color = "#f3efe3";
                input.style.borderRadius = "7px";
                input.style.padding = "4px 8px";
                input.style.fontFamily = "\"Chivo Mono\", monospace";
                input.style.fontSize = "12px";
                input.style.outline = "none";
                input.onchange = () => {
                    const parsed = Number.parseInt(input.value, 10);
                    setDraftValue(control.key, Number.isFinite(parsed) ? parsed : 0);
                };
                stepper.appendChild(input);

                const plusBtn = document.createElement("button");
                plusBtn.type = "button";
                plusBtn.textContent = "+";
                plusBtn.disabled = disabled || control.value >= control.max;
                styleSecondaryButton(plusBtn, disabled || control.value >= control.max);
                plusBtn.style.padding = "4px 0";
                if (!plusBtn.disabled) {
                    plusBtn.onclick = () => setDraftValue(control.key, control.value + 1);
                }
                stepper.appendChild(plusBtn);
                row.appendChild(stepper);

                const presets = document.createElement("div");
                presets.style.display = "flex";
                presets.style.flexWrap = "wrap";
                presets.style.gap = "4px";
                for (const preset of [
                    { label: "0", value: 0 },
                    { label: "25%", value: pctOfMax(control.max, 0.25) },
                    { label: "50%", value: pctOfMax(control.max, 0.5) },
                    { label: "75%", value: pctOfMax(control.max, 0.75) },
                    { label: "Max", value: control.max },
                ]) {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.textContent = preset.label;
                    btn.disabled = disabled || control.max <= 0;
                    styleSecondaryButton(btn, btn.disabled);
                    btn.style.padding = "3px 7px";
                    btn.style.fontSize = "10px";
                    if (preset.value === control.value) {
                        btn.style.borderColor = "rgba(243, 199, 106, 0.78)";
                        btn.style.background = "rgba(43, 30, 12, 0.82)";
                    }
                    if (!btn.disabled) {
                        btn.onclick = () => setDraftValue(control.key, preset.value);
                    }
                    presets.appendChild(btn);
                }
                row.appendChild(presets);
                section.appendChild(row);
            }
            panel.appendChild(section);
        };

        renderMachineSection({
            title: "SELL",
            note: "washed -> cash",
            controls: [
                {
                    key: "sell_washed_dumb",
                    label: "Sell washed dumb",
                    value: plan.effective.sell_washed_dumb,
                    max: plan.max.sell_washed_dumb,
                },
                {
                    key: "sell_washed_smart",
                    label: "Sell washed smart",
                    value: plan.effective.sell_washed_smart,
                    max: plan.max.sell_washed_smart,
                },
            ],
        });
        renderMachineSection({
            title: "CONVERT",
            note: `${EOD_CONVERT_COST} washed -> 1 worker`,
            controls: [
                {
                    key: "convert_workers_dumb",
                    label: "Convert dumb workers",
                    value: plan.effective.convert_workers_dumb,
                    max: plan.max.convert_workers_dumb,
                },
                {
                    key: "convert_workers_smart",
                    label: "Convert smart workers",
                    value: plan.effective.convert_workers_smart,
                    max: plan.max.convert_workers_smart,
                },
            ],
        });
        renderMachineSection({
            title: "UPGRADE",
            note: "dumb washed -> smart washed",
            controls: [
                {
                    key: "upgrade_brains",
                    label: "Upgrade brains",
                    value: plan.effective.upgrade_brains,
                    max: plan.max.upgrade_brains,
                },
            ],
        });

        const preview = document.createElement("div");
        preview.style.marginTop = "9px";
        preview.style.fontSize = "11px";
        preview.style.opacity = "0.92";
        preview.textContent = `Projected Δ: cash +${plan.preview.cashDelta}, workers +${plan.preview.workersDumbDelta}D / +${plan.preview.workersSmartDelta}S`;
        panel.appendChild(preview);

        if (latestRejection) {
            const warning = document.createElement("div");
            warning.style.marginTop = "6px";
            warning.style.fontSize = "11px";
            warning.style.color = "#ffd8cf";
            warning.textContent = `Last rejection: ${latestRejection.reasonCode} — ${latestRejection.reason}`;
            panel.appendChild(warning);
        }

        const confirmButton = document.createElement("button");
        confirmButton.type = "button";
        confirmButton.textContent = "CONFIRM EOD";
        confirmButton.style.marginTop = "10px";
        confirmButton.style.width = "100%";
        confirmButton.style.border = "1px solid rgba(243, 199, 106, 0.75)";
        confirmButton.style.background = "rgba(38, 29, 12, 0.95)";
        confirmButton.style.color = "#f3efe3";
        confirmButton.style.borderRadius = "8px";
        confirmButton.style.padding = "8px 10px";
        confirmButton.style.fontSize = "12px";
        confirmButton.style.fontWeight = "700";
        confirmButton.style.letterSpacing = "0.05em";
        confirmButton.disabled = disabled;
        confirmButton.style.cursor = disabled ? "not-allowed" : "pointer";
        confirmButton.style.opacity = disabled ? "0.56" : "1";
        if (!disabled) {
            confirmButton.onclick = () => {
                if (this.advanceInFlight) return;
                this.advanceInFlight = true;
                this.advanceInFlightStateKey = this.stateUpdateKey(state);
                this.advanceStatusOverride = {
                    text: "Submitting end-of-day actions...",
                    color: "#f3efe3",
                    untilMs: Date.now() + 3000,
                };
                this.onAdvanceDay?.({
                    tickTarget: state.tick + 1,
                    endOfDay: { ...this.eodDraft },
                });
            };
        }
        panel.appendChild(confirmButton);
    }

    private buildEndOfDayPlan(inventory: SimSimViewerState["inventory"], draft: EndOfDayDraft): EndOfDayPlan {
        const inv = inventory?.inventories;
        const washedDumb = nonNegativeInt(inv?.washed_dumb);
        const washedSmart = nonNegativeInt(inv?.washed_smart);
        const substrate = nonNegativeInt(inv?.substrate_gallons);
        const ribbon = nonNegativeInt(inv?.ribbon_yards);

        const upgradeMax = Math.min(washedDumb, substrate, ribbon);
        const upgradeBrains = clampInt(draft.upgrade_brains, 0, upgradeMax);

        const washedDumbAfterUpgrade = washedDumb - upgradeBrains;
        const washedSmartAfterUpgrade = washedSmart + upgradeBrains;

        const sellDumbMax = washedDumbAfterUpgrade;
        const sellSmartMax = washedSmartAfterUpgrade;
        const sellWashedDumb = clampInt(draft.sell_washed_dumb, 0, sellDumbMax);
        const sellWashedSmart = clampInt(draft.sell_washed_smart, 0, sellSmartMax);

        const washedDumbAfterSell = washedDumbAfterUpgrade - sellWashedDumb;
        const washedSmartAfterSell = washedSmartAfterUpgrade - sellWashedSmart;

        const convertDumbMax = Math.floor(washedDumbAfterSell / EOD_CONVERT_COST);
        const convertSmartMax = Math.floor(washedSmartAfterSell / EOD_CONVERT_COST);
        const convertWorkersDumb = clampInt(draft.convert_workers_dumb, 0, convertDumbMax);
        const convertWorkersSmart = clampInt(draft.convert_workers_smart, 0, convertSmartMax);

        return {
            max: {
                sell_washed_dumb: sellDumbMax,
                sell_washed_smart: sellSmartMax,
                convert_workers_dumb: convertDumbMax,
                convert_workers_smart: convertSmartMax,
                upgrade_brains: upgradeMax,
            },
            effective: {
                sell_washed_dumb: sellWashedDumb,
                sell_washed_smart: sellWashedSmart,
                convert_workers_dumb: convertWorkersDumb,
                convert_workers_smart: convertWorkersSmart,
                upgrade_brains: upgradeBrains,
            },
            preview: {
                cashDelta: (sellWashedDumb * EOD_SELL_WASHED_DUMB_PRICE) + (sellWashedSmart * EOD_SELL_WASHED_SMART_PRICE),
                workersDumbDelta: convertWorkersDumb,
                workersSmartDelta: convertWorkersSmart,
            },
        };
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
        if (this.selectedRoomId === null) {
            this.previewTargetRoomId = null;
        } else if (!unlockedRooms.some((room) => room.room_id === this.previewTargetRoomId)) {
            this.previewTargetRoomId = null;
        }

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
        hint.textContent = "Click to pick a token, then click target token to place (mouse + trackpad friendly).";
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
        summary.innerHTML = [
            `<div>Selected: ${this.selectedRoomId !== null ? `room ${this.selectedRoomId}` : "none"}${this.selectedSupId ? ` -> ${this.selectedSupId}` : ""}</div>`,
            `<div style="opacity:0.78;">Target: ${this.previewTargetRoomId !== null ? `room ${this.previewTargetRoomId} (magnet preview)` : "none"}</div>`,
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
            const assignedRoom = Object.keys(this.placementsDraft)
                .map((roomId) => Number(roomId))
                .find((roomId) => this.placementsDraft[roomId] === supervisor.code);
            let highlighted = false;
            let ineligible = false;
            if (this.selectedRoomId !== null && assignedRoom !== undefined && this.selectedRoomId !== assignedRoom) {
                if (data.swapsRemaining <= 0) {
                    ineligible = true;
                } else {
                    highlighted = this.canSwapRoomPair({
                        sourceRoomId: this.selectedRoomId,
                        targetRoomId: assignedRoom,
                        swapBudget: data.swapBudget,
                    });
                    ineligible = !highlighted;
                }
            }
            const hardDisabled = data.controlsDisabled || assignedRoom === undefined;
            const pickupActive = assignedRoom !== undefined && this.isPickupFxActive(assignedRoom, supervisor.code);
            const impactActive = assignedRoom !== undefined && this.isImpactFxActive(assignedRoom);
            const illegalActive = assignedRoom !== undefined && this.isIllegalFxActive(assignedRoom);
            const magnetPreviewed =
                assignedRoom !== undefined &&
                this.previewTargetRoomId !== null &&
                this.previewTargetRoomId === assignedRoom &&
                this.selectedRoomId !== null &&
                this.selectedRoomId !== assignedRoom;
            const token = createSupervisorToken({
                label: supervisor.code,
                name: supervisor.name,
                selected: this.selectedSupId === supervisor.code,
                disabled: hardDisabled,
                highlighted: this.selectedSupId === supervisor.code || highlighted || magnetPreviewed,
                ineligible,
                picked: pickupActive,
                impacted: impactActive,
                illegal: illegalActive,
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
                onHoverChange:
                    hardDisabled || assignedRoom === undefined
                        ? undefined
                        : (hovered: boolean) => {
                              if (this.selectedRoomId === null || this.selectedRoomId === assignedRoom) {
                                  if (!hovered) this.setPreviewTargetRoom(null, state);
                                  return;
                              }
                              this.setPreviewTargetRoom(hovered ? assignedRoom : null, state);
                          },
            });
            token.title = assignedRoom ? `Room ${assignedRoom}` : "Unassigned";
            supervisorBar.appendChild(token);
        }
        panel.appendChild(supervisorBar);

        if (this.devMode && this.debugVisible) {
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
                    picked: !!selectedCode && this.isPickupFxActive(room.room_id, selectedCode),
                    impacted: this.isImpactFxActive(room.room_id),
                    illegal: this.isIllegalFxActive(room.room_id),
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
                    onHoverChange: hardDisabled
                        ? undefined
                        : (hovered: boolean) => {
                              if (this.selectedRoomId === null || this.selectedRoomId === room.room_id) {
                                  if (!hovered) this.setPreviewTargetRoom(null, state);
                                  return;
                              }
                              this.setPreviewTargetRoom(hovered ? room.room_id : null, state);
                          },
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
        backdrop.style.background = "radial-gradient(circle at 50% 22%, rgba(243, 199, 106, 0.08), rgba(4, 8, 13, 0.72) 35%, rgba(3, 5, 8, 0.88) 100%)";
        backdrop.style.backdropFilter = "blur(1.6px)";
        backdrop.style.pointerEvents = "auto";

        const card = document.createElement("div");
        card.dataset.spotlightPopup = "1";
        card.style.position = "absolute";
        applyAbsoluteRect(card, this.directorLayout.scaled.overlays.spotlight);
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

function applyAbsoluteRect(element: HTMLElement, rect: Rect): void {
    element.style.left = `${Math.round(rect.x)}px`;
    element.style.top = `${Math.round(rect.y)}px`;
    element.style.width = `${Math.max(0, Math.round(rect.w))}px`;
    element.style.height = `${Math.max(0, Math.round(rect.h))}px`;
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

function resolvingEventKey(event: SimSimEvent): string {
    return `${event.tick}:${event.event_id}`;
}

function resolvingStamp(event: SimSimEvent): string {
    return `T${String(event.tick).padStart(2, "0")} · #${event.event_id}`;
}

function resolvingEventSummary(event: SimSimEvent): string {
    const bits: string[] = [humanizeEventKind(event.kind)];
    if (typeof event.room_id === "number") bits.push(`room ${event.room_id}`);
    if (typeof event.supervisor === "string" && event.supervisor.trim().length > 0) bits.push(`sup ${event.supervisor}`);
    return bits.join(" • ");
}

function humanizeEventKind(kind: string): string {
    return kind
        .split("_")
        .filter((token) => token.length > 0)
        .map((token) => token[0].toUpperCase() + token.slice(1))
        .join(" ");
}

function eventTone(kind: string): ResolvingBeatTone {
    const token = kind.toLowerCase();
    if (token === "critical_suppressed" || token === "assignment_resolved" || token === "security_redistribution") return "success";
    if (token === "critical_triggered" || token === "conflict_event" || token === "input_rejected") return "danger";
    if (token.includes("conflict") || token.includes("critical") || token.includes("tension")) return "warning";
    return "info";
}

function isAccidentEvent(kind: string): boolean {
    const token = kind.toLowerCase();
    return token.includes("accident") || token.includes("casual");
}

function resolvingBeatStyle(tone: ResolvingBeatTone, revealed: boolean, activeBeat: boolean): { row: string } {
    const palette =
        tone === "danger"
            ? { border: "rgba(231,123,75,0.66)", bg: "rgba(46, 19, 16, 0.76)" }
            : tone === "warning"
              ? { border: "rgba(243,199,106,0.62)", bg: "rgba(44, 30, 12, 0.72)" }
              : tone === "success"
                ? { border: "rgba(118,214,161,0.62)", bg: "rgba(12, 37, 33, 0.72)" }
                : { border: "rgba(140,214,200,0.44)", bg: "rgba(12, 24, 30, 0.62)" };
    const opacity = revealed ? 1 : 0.4;
    const ring = activeBeat ? `;box-shadow:0 0 0 1px ${palette.border}, 0 0 14px rgba(243,199,106,0.24)` : "";
    return {
        row: `border:1px solid ${palette.border};background:${palette.bg};border-radius:9px;padding:7px 8px;display:grid;gap:3px;opacity:${opacity}${ring};`,
    };
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

function clampInt(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, Math.floor(value)));
}

function nonNegativeInt(value: number | null | undefined): number {
    if (!Number.isFinite(value)) return 0;
    return Math.max(0, Math.floor(value ?? 0));
}

function pctOfMax(max: number, factor: number): number {
    if (max <= 0) return 0;
    return Math.max(0, Math.min(max, Math.floor(max * factor)));
}

function makeZeroEndOfDayDraft(): EndOfDayDraft {
    return {
        sell_washed_dumb: 0,
        sell_washed_smart: 0,
        convert_workers_dumb: 0,
        convert_workers_smart: 0,
        upgrade_brains: 0,
    };
}

function normalizePhaseToken(phase: string | undefined | null): string {
    return (phase ?? "").trim().toLowerCase();
}

function installSwapFxStyles(root: HTMLElement): void {
    if (root.querySelector("style[data-simsim-swap-fx='1']")) return;
    const style = document.createElement("style");
    style.dataset.simsimSwapFx = "1";
    style.textContent = [
        "@keyframes simsimTokenLift {",
        "  0% { transform: translateY(0) scale(1); }",
        "  40% { transform: translateY(-5px) scale(1.09); }",
        "  100% { transform: translateY(-2px) scale(1.04); }",
        "}",
        "@keyframes simsimImpactPulse {",
        "  0% { box-shadow: 0 0 0 1px rgba(243,199,106,0.22), 0 0 10px rgba(243,199,106,0.28); }",
        "  45% { box-shadow: 0 0 0 3px rgba(243,199,106,0.45), 0 0 24px rgba(243,199,106,0.6); }",
        "  100% { box-shadow: 0 0 0 1px rgba(243,199,106,0.2), 0 0 12px rgba(243,199,106,0.3); }",
        "}",
        "@keyframes simsimIllegalBounce {",
        "  0% { transform: translateY(0) scale(1); }",
        "  30% { transform: translateY(-3px) scale(1.04); }",
        "  55% { transform: translateY(3px) scale(0.94); }",
        "  100% { transform: translateY(0) scale(1); }",
        "}",
        "@keyframes simsimRivetPop {",
        "  0% { transform: scale(1); }",
        "  25% { transform: scale(1.35); }",
        "  100% { transform: scale(1); }",
        "}",
        "@keyframes simsimSteamRewind {",
        "  0% { opacity: 0; transform: translateY(6px); filter: blur(2px); }",
        "  30% { opacity: 1; transform: translateY(0); filter: blur(0); }",
        "  100% { opacity: 0.85; transform: translateY(-2px); filter: blur(0.4px); }",
        "}",
        "@keyframes simsimSealStamp {",
        "  0% { transform: rotate(-8deg) scale(1.25); opacity: 0; }",
        "  35% { transform: rotate(-8deg) scale(1); opacity: 1; }",
        "  100% { transform: rotate(-8deg) scale(1); opacity: 1; }",
        "}",
        ".simsim-token-picked { animation: simsimTokenLift 180ms ease-out; }",
        ".simsim-token-impact { animation: simsimImpactPulse 320ms ease-out; }",
        ".simsim-token-illegal { animation: simsimIllegalBounce 220ms cubic-bezier(.16,.67,.32,1.03); }",
        ".simsim-rivet-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }",
        ".simsim-rivet { width: 22px; height: 22px; border-radius: 999px; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; }",
        ".simsim-rivet.is-armed { color: #f5ddaa; border: 1px solid rgba(243, 199, 106, 0.72); background: radial-gradient(circle at 33% 32%, rgba(243, 199, 106, 0.34), rgba(31, 22, 11, 0.94) 72%); box-shadow: 0 0 12px rgba(243, 199, 106, 0.24); }",
        ".simsim-rivet.is-consumed { color: #ffd8cf; border: 1px solid rgba(232, 159, 143, 0.68); background: radial-gradient(circle at 33% 32%, rgba(232, 159, 143, 0.30), rgba(36, 19, 16, 0.94) 72%); box-shadow: 0 0 10px rgba(232, 159, 143, 0.18); }",
        ".simsim-rivet.is-pop { animation: simsimRivetPop 260ms ease-out; }",
        ".simsim-steam-rewind { margin-top: 8px; border: 1px solid rgba(140, 214, 200, 0.46); border-radius: 8px; padding: 6px 8px; background: linear-gradient(160deg, rgba(12, 24, 30, 0.86), rgba(19, 29, 24, 0.72)); font-size: 11px; color: #d6efe7; letter-spacing: 0.03em; text-transform: uppercase; animation: simsimSteamRewind 380ms ease-out; }",
        ".simsim-sealed-stamp { margin-bottom: 8px; width: fit-content; border: 2px solid rgba(232, 159, 143, 0.86); color: #ffd8cf; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 800; letter-spacing: 0.14em; background: rgba(64, 19, 19, 0.66); transform: rotate(-8deg); animation: simsimSealStamp 210ms ease-out; }",
    ].join("\n");
    root.appendChild(style);
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

function deriveRecapDeltasFromStateTransition(previousState: SimSimViewerState, state: SimSimViewerState): RecapDeltas {
    const previousRooms = Array.from(previousState.rooms.values());
    const currentRooms = Array.from(state.rooms.values());
    const previousRoomsById = new Map(previousRooms.map((room) => [room.room_id, room]));
    const currentRoomsById = new Map(currentRooms.map((room) => [room.room_id, room]));

    const factoryStress = deltaNumber(averageMetric(currentRooms, "stress"), averageMetric(previousRooms, "stress"));
    const factoryDiscipline = deltaNumber(averageMetric(currentRooms, "discipline"), averageMetric(previousRooms, "discipline"));
    const factoryAlignment = deltaNumber(averageMetric(currentRooms, "alignment"), averageMetric(previousRooms, "alignment"));
    const cashDelta = deltaNumber(state.inventory?.cash, previousState.inventory?.cash);
    const outputDelta = deltaNumber(totalRoomOutput(currentRooms), totalRoomOutput(previousRooms));
    const accidentsDelta = deltaNumber(totalRoomAccidents(currentRooms), totalRoomAccidents(previousRooms));
    const casualtiesDelta = deltaNumber(totalRoomCasualties(currentRooms), totalRoomCasualties(previousRooms));

    const factory: RecapDeltas["factory"] = {};
    if (factoryStress !== undefined) factory.stress = factoryStress;
    if (factoryDiscipline !== undefined) factory.discipline = factoryDiscipline;
    if (factoryAlignment !== undefined) factory.alignment = factoryAlignment;
    if (cashDelta !== undefined) factory.cash = cashDelta;
    if (outputDelta !== undefined) factory.output = outputDelta;
    if (accidentsDelta !== undefined) factory.accidents = accidentsDelta;
    if (casualtiesDelta !== undefined) factory.casualties = casualtiesDelta;

    const rooms: NonNullable<RecapDeltas["rooms"]> = {};
    const roomIds = new Set<number>([...previousRoomsById.keys(), ...currentRoomsById.keys()]);
    for (const roomId of roomIds) {
        const previousRoom = previousRoomsById.get(roomId);
        const currentRoom = currentRoomsById.get(roomId);
        if (!previousRoom || !currentRoom) continue;

        const row: NonNullable<RecapDeltas["rooms"]>[number] = {};
        const stress = deltaNumber(currentRoom.stress, previousRoom.stress);
        const discipline = deltaNumber(currentRoom.discipline, previousRoom.discipline);
        const alignment = deltaNumber(currentRoom.alignment, previousRoom.alignment);
        const equipment = deltaNumber(currentRoom.equipment_condition, previousRoom.equipment_condition);
        const output = deltaNumber(totalSingleRoomOutput(currentRoom), totalSingleRoomOutput(previousRoom));
        const casualties = deltaNumber(currentRoom.accidents_today?.casualties, previousRoom.accidents_today?.casualties);
        if (stress !== undefined) row.stress = stress;
        if (discipline !== undefined) row.discipline = discipline;
        if (alignment !== undefined) row.alignment = alignment;
        if (equipment !== undefined) row.equipment_condition = equipment;
        if (output !== undefined) row.output = output;
        if (casualties !== undefined) row.casualties = casualties;
        if (Object.keys(row).length > 0) rooms[roomId] = row;
    }

    return {
        factory,
        rooms,
    };
}

function deriveSupervisorChanges(previousState: SimSimViewerState, state: SimSimViewerState): SupervisorChange[] {
    const codes = new Set<string>([...previousState.supervisors.keys(), ...state.supervisors.keys()]);
    const changes: SupervisorChange[] = [];
    for (const code of codes) {
        const previousSupervisor = previousState.supervisors.get(code);
        const currentSupervisor = state.supervisors.get(code);
        if (!previousSupervisor && !currentSupervisor) continue;

        const fromRoom = previousSupervisor?.assigned_room ?? null;
        const toRoom = currentSupervisor?.assigned_room ?? null;
        const confidenceDelta = deltaNumber(currentSupervisor?.confidence, previousSupervisor?.confidence);
        const loyaltyDelta = deltaNumber(currentSupervisor?.loyalty, previousSupervisor?.loyalty);
        const influenceDelta = deltaNumber(currentSupervisor?.influence, previousSupervisor?.influence);
        const cooldownChanged =
            currentSupervisor !== undefined &&
            previousSupervisor !== undefined &&
            currentSupervisor.cooldown_days !== previousSupervisor.cooldown_days;
        const moved = fromRoom !== toRoom;
        const changedMagnitude = Math.abs(numberOrZero(confidenceDelta)) + Math.abs(numberOrZero(loyaltyDelta)) + Math.abs(numberOrZero(influenceDelta));
        if (!moved && !cooldownChanged && changedMagnitude < 0.01) continue;

        changes.push({
            code,
            fromRoom,
            toRoom,
            confidenceDelta,
            loyaltyDelta,
            influenceDelta,
            cooldownDays: currentSupervisor?.cooldown_days ?? previousSupervisor?.cooldown_days,
        });
    }
    return changes.sort((a, b) => supervisorChangeMagnitude(b) - supervisorChangeMagnitude(a));
}

function spotlightForRecap(spotlightPrompt: SpotlightPrompt | null, topCard: EventRailCard | undefined): RecapStripModel["spotlight"] {
    if (spotlightPrompt) {
        return {
            title: spotlightPrompt.title,
            lead: spotlightPrompt.cinematicLead,
            body: spotlightPrompt.body,
        };
    }
    if (topCard) {
        return {
            title: topCard.title,
            lead: topCard.subtitle,
            body: `Most visible shift: ${topCard.kind.replace(/_/g, " ")}.`,
        };
    }
    return {
        title: "Stable close",
        lead: "No major flashpoint logged at close.",
        body: "Operations advanced without a dominant escalation card.",
    };
}

function summarizeEscalations(changes: SupervisorChange[]): string[] {
    if (changes.length === 0) return ["No supervisor escalations registered this close."];
    return changes.slice(0, 4).map((change) => {
        const parts: string[] = [];
        parts.push(`${change.code} ${roomMoveLabel(change.fromRoom)} -> ${roomMoveLabel(change.toRoom)}`);
        if (change.confidenceDelta !== undefined) parts.push(`conf ${fmtSignedNumber(change.confidenceDelta)}`);
        if (change.loyaltyDelta !== undefined) parts.push(`loyalty ${fmtSignedNumber(change.loyaltyDelta)}`);
        if (change.influenceDelta !== undefined) parts.push(`influence ${fmtSignedNumber(change.influenceDelta)}`);
        return parts.join(" · ");
    });
}

function deriveFactoryVibeTagline(recapPanels: RecapPanel[]): string {
    const positive = recapPanels.filter((panel) => panel.tone === "positive").length;
    const negative = recapPanels.filter((panel) => panel.tone === "negative").length;
    if (negative >= 2) return "Factory vibe: brittle edges and loud fault lines.";
    if (positive >= 2) return "Factory vibe: disciplined momentum with clean handoffs.";
    if (negative === 1 && positive === 0) return "Factory vibe: tense, controlled, and watching for slips.";
    return "Factory vibe: mixed signal, holding the center line.";
}

function deriveNetResultLines(deltas: RecapDeltas, recapPanels: RecapPanel[]): string[] {
    const lines: string[] = [];
    const factory = deltas.factory ?? {};
    if (factory.cash !== undefined) lines.push(`Cash Δ ${fmtSignedNumber(factory.cash)}`);
    if (factory.output !== undefined) lines.push(`Output Δ ${fmtSignedNumber(factory.output)}`);
    if (factory.stress !== undefined || factory.discipline !== undefined || factory.alignment !== undefined) {
        lines.push(
            `Factory metrics Δ stress ${fmtSignedNumber(factory.stress)} / discipline ${fmtSignedNumber(factory.discipline)} / alignment ${fmtSignedNumber(factory.alignment)}`
        );
    }
    if (factory.accidents !== undefined || factory.casualties !== undefined) {
        lines.push(`Safety Δ accidents ${fmtSignedNumber(factory.accidents)} / casualties ${fmtSignedNumber(factory.casualties)}`);
    }
    for (const panel of recapPanels) {
        if (panel.lines.length > 0) lines.push(`${panel.title}: ${panel.lines[0]}`);
    }
    return lines.slice(0, 5);
}

function recapToneChipStyle(tone: RecapPanel["tone"]): string {
    if (tone === "positive") return "border:1px solid rgba(118,214,161,0.86);background:rgba(11,44,38,0.72);color:#d6f8ee;";
    if (tone === "negative") return "border:1px solid rgba(231,123,75,0.9);background:rgba(54,18,16,0.84);color:#ffd9ca;";
    return "border:1px solid rgba(243,199,106,0.85);background:rgba(51,34,12,0.72);color:#f5ddaa;";
}

function supervisorChangeMagnitude(change: SupervisorChange): number {
    return (
        Math.abs(numberOrZero(change.confidenceDelta)) +
        Math.abs(numberOrZero(change.loyaltyDelta)) +
        Math.abs(numberOrZero(change.influenceDelta)) +
        (change.fromRoom !== change.toRoom ? 0.6 : 0)
    );
}

function roomMoveLabel(roomId: number | null | undefined): string {
    if (roomId === null || roomId === undefined) return "R-";
    return `R${roomId}`;
}

function totalRoomOutput(rooms: SimSimRoom[]): number {
    return rooms.reduce((sum, room) => sum + totalSingleRoomOutput(room), 0);
}

function totalSingleRoomOutput(room: SimSimRoom): number {
    const out = room.output_today;
    return (
        numberOrZero(out.raw_brains_dumb) +
        numberOrZero(out.raw_brains_smart) +
        numberOrZero(out.washed_dumb) +
        numberOrZero(out.washed_smart) +
        numberOrZero(out.substrate_gallons) +
        numberOrZero(out.ribbon_yards)
    );
}

function totalRoomAccidents(rooms: SimSimRoom[]): number {
    return rooms.reduce((sum, room) => sum + numberOrZero(room.accidents_today?.count), 0);
}

function totalRoomCasualties(rooms: SimSimRoom[]): number {
    return rooms.reduce((sum, room) => sum + numberOrZero(room.accidents_today?.casualties), 0);
}

function averageMetric(rooms: SimSimRoom[], metric: "stress" | "discipline" | "alignment"): number | undefined {
    let total = 0;
    let count = 0;
    for (const room of rooms) {
        const value = room[metric];
        if (!Number.isFinite(value)) continue;
        total += value as number;
        count += 1;
    }
    if (count === 0) return undefined;
    return total / count;
}

function deltaNumber(current: number | null | undefined, previous: number | null | undefined): number | undefined {
    if (!Number.isFinite(current) || !Number.isFinite(previous)) return undefined;
    return roundTo3((current as number) - (previous as number));
}

function roundTo3(value: number): number {
    return Math.round(value * 1000) / 1000;
}

function fmtSignedNumber(value: number | undefined): string {
    if (!Number.isFinite(value)) return "0.000";
    const n = value as number;
    return `${n >= 0 ? "+" : ""}${n.toFixed(3)}`;
}

function numberOrZero(value: number | undefined | null): number {
    if (!Number.isFinite(value)) return 0;
    return value as number;
}

function isSimSimDevUiEnabled(): boolean {
    if (typeof window === "undefined") return false;
    const query = new URLSearchParams(window.location.search);
    const queryValue = query.get(DEV_UI_QUERY_PARAM)?.trim().toLowerCase();
    if (queryValue === "1" || queryValue === "true" || queryValue === "on") return true;
    if (queryValue === "0" || queryValue === "false" || queryValue === "off") return false;
    try {
        return window.localStorage.getItem(DEV_UI_STORAGE_KEY) === "1";
    } catch {
        return false;
    }
}

function persistSimSimDevUiFlag(enabled: boolean): void {
    if (typeof window === "undefined") return;
    try {
        window.localStorage.setItem(DEV_UI_STORAGE_KEY, enabled ? "1" : "0");
    } catch {
        // Ignore storage write failures (e.g., private mode restrictions).
    }
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
    picked?: boolean;
    impacted?: boolean;
    illegal?: boolean;
    sizePx: number;
    onClick?: () => void;
    onHoverChange?: (hovered: boolean) => void;
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
    btn.style.transition = "transform 110ms ease";
    btn.style.transform = opts.picked ? "translateY(-4px) scale(1.05)" : "translateY(0) scale(1)";

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
        : opts.illegal || opts.ineligible
          ? "1px solid rgba(232, 159, 143, 0.58)"
          : opts.highlighted || opts.impacted
            ? "1px solid rgba(243, 199, 106, 0.74)"
            : "1px solid rgba(140, 214, 200, 0.48)";
    circle.style.background = opts.illegal
        ? "radial-gradient(circle at 35% 30%, rgba(232,159,143,0.26), rgba(26,20,22,0.95) 72%)"
        : opts.selected
        ? "radial-gradient(circle at 35% 30%, rgba(243,199,106,0.28), rgba(20,29,37,0.94) 70%)"
        : opts.ineligible
          ? "radial-gradient(circle at 35% 30%, rgba(232,159,143,0.20), rgba(26,20,22,0.95) 72%)"
          : "radial-gradient(circle at 35% 30%, rgba(140,214,200,0.24), rgba(18,24,30,0.94) 72%)";
    circle.style.boxShadow = opts.impacted
        ? "0 0 0 2px rgba(243,199,106,0.38), 0 0 20px rgba(243,199,106,0.54)"
        : opts.selected
        ? "0 0 0 2px rgba(243,199,106,0.26), 0 0 18px rgba(243,199,106,0.35)"
        : opts.highlighted
          ? "0 0 0 1px rgba(243,199,106,0.24), 0 0 14px rgba(243,199,106,0.30)"
          : opts.ineligible
            ? "0 0 8px rgba(232,159,143,0.20)"
            : "0 0 10px rgba(140,214,200,0.18)";
    circle.style.transition = "box-shadow 120ms ease, border-color 120ms ease, transform 120ms ease";
    if (opts.picked) {
        circle.classList.add("simsim-token-picked");
    }
    if (opts.impacted) {
        circle.classList.add("simsim-token-impact");
    }
    if (opts.illegal) {
        circle.classList.add("simsim-token-illegal");
    }
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

    if (!opts.disabled && opts.onHoverChange) {
        btn.addEventListener("mouseenter", () => opts.onHoverChange?.(true));
        btn.addEventListener("mouseleave", () => opts.onHoverChange?.(false));
    }

    if (!opts.disabled && opts.onClick) {
        btn.addEventListener("click", opts.onClick);
        btn.addEventListener("mouseenter", () => {
            if (opts.selected || opts.ineligible || opts.illegal) return;
            circle.style.borderColor = "rgba(243, 199, 106, 0.66)";
            circle.style.boxShadow = "0 0 0 1px rgba(243,199,106,0.2), 0 0 14px rgba(243,199,106,0.30)";
            circle.style.transform = "translateY(-1px)";
        });
        btn.addEventListener("mouseleave", () => {
            if (opts.selected || opts.ineligible || opts.illegal) return;
            circle.style.borderColor = opts.highlighted || opts.impacted ? "rgba(243, 199, 106, 0.74)" : "rgba(140, 214, 200, 0.48)";
            circle.style.boxShadow = opts.highlighted || opts.impacted
                ? "0 0 0 1px rgba(243,199,106,0.24), 0 0 14px rgba(243,199,106,0.30)"
                : "0 0 10px rgba(140,214,200,0.18)";
            circle.style.transform = "translateY(0)";
        });
    }

    return btn;
}
