// src/ui/hud.ts
import type { WorldStore, WorldState, KvpEvent, KvpRoom } from "../state/worldStore";
import { buildMbamCaseSetupGuide, buildMbamOnboardingView } from "./mbamOnboarding";
import type { OverlayStore, OverlayState, UIOverlayEvent } from "../state/overlayStore";
import { createScopedTranslator, getSharedLocaleStore, type TranslateFn } from "../i18n";
import { resolvePresentationText } from "../app/presentationText";

export type HudProfile = "demo" | "playtest" | "dev";

export type HudOpts = {
    profile?: HudProfile;
};

export type HudHandle = {
    root: HTMLElement;
    setProfile: (profile: HudProfile) => void;
};

export function mountHud(
    store: WorldStore,
    overlayStore?: OverlayStore,
    opts: HudOpts = {}
): HudHandle {
    let profile: HudProfile = opts.profile ?? "dev";
    const localeStore = getSharedLocaleStore();
    const t = createScopedTranslator(() => localeStore.getLocale());

    const root = document.createElement("div");
    root.className = "hud-root";

    const panel = document.createElement("div");
    panel.className = "hud-panel hud-panel-main";
    root.appendChild(panel);

    const dot = document.createElement("span");
    dot.className = "hud-status-dot";

    const header = document.createElement("div");
    header.className = "hud-panel-header";

    const title = document.createElement("span");
    title.className = "hud-panel-title";

    header.appendChild(dot);
    header.appendChild(title);

    const body = document.createElement("div");
    body.className = "hud-panel-body";

    panel.appendChild(header);
    panel.appendChild(body);

    const feedPanel = document.createElement("div");
    feedPanel.className = "hud-panel hud-panel-feed";

    const feedTitle = document.createElement("div");
    feedTitle.className = "hud-feed-title";

    const feedBody = document.createElement("div");
    feedBody.className = "hud-feed-body";

    feedPanel.appendChild(feedTitle);
    feedPanel.appendChild(feedBody);
    root.appendChild(feedPanel);

    let lastWorldState: WorldState | null = null;
    let lastOverlayState: OverlayState | null = null;

    const rerender = (): void => {
        if (!lastWorldState) return;
        renderHud({ dot, body }, lastWorldState, profile, t);
        renderFeed({ feedBody }, lastWorldState, lastOverlayState, profile, t);
    };

    const updateHeaderTexts = (): void => {
        title.textContent = profile === "dev" ? t("hud.title.dev") : t("hud.title.case_status");
        if (profile === "dev") {
            feedTitle.textContent = t("hud.feed_title.live_feed");
            return;
        }
        feedTitle.textContent = profile === "demo"
            ? t("hud.feed_title.recent_activity")
            : t("hud.feed_title.case_feed");
    };

    store.subscribe((state) => {
        lastWorldState = state;
        rerender();
    });

    if (overlayStore) {
        overlayStore.subscribe((overlayState) => {
            lastOverlayState = overlayState;
            rerender();
        });
    }

    const setProfile = (nextProfile: HudProfile): void => {
        if (profile === nextProfile) return;
        profile = nextProfile;
        updateHeaderTexts();
        rerender();
    };

    let localeReady = false;
    localeStore.subscribe(() => {
        if (!localeReady) {
            localeReady = true;
            updateHeaderTexts();
            return;
        }
        updateHeaderTexts();
        rerender();
    });

    return {
        root,
        setProfile,
    };
}

function renderHud(
    el: { dot: HTMLSpanElement; body: HTMLDivElement },
    state: WorldState,
    profile: HudProfile,
    t: TranslateFn
): void {
    const connected = state.connected;
    const desynced = state.desynced;

    el.dot.dataset.status = !connected ? "offline" : desynced ? "desync" : "live";

    const lines: string[] = [];
    if (profile === "dev") {
        const kernelHello = state.kernelHello;
        lines.push(`mode:      ${state.mode}`);
        lines.push(`connected: ${connected ? t("hud.status.yes") : t("hud.status.no")}`);
        lines.push(`tick:      ${padLeft(String(state.tick), 8)}`);
        lines.push(`stepHash:  ${truncateHash(state.stepHash)}`);

        if (kernelHello) {
            lines.push("");
            lines.push(`kernel:    ${kernelHello.engine_name}@${kernelHello.engine_version}`);
            lines.push(`schema:    ${kernelHello.schema_version}`);
            lines.push(`world_id:  ${kernelHello.world_id}`);
            lines.push(`run_id:    ${kernelHello.run_id}`);
            lines.push(`seed:      ${kernelHello.seed}`);
            lines.push(`tick_hz:   ${kernelHello.tick_rate_hz}`);
        } else {
            lines.push("");
            lines.push(`kernel:    ${t("hud.value.none")}`);
        }
    } else if (profile === "playtest") {
        const onboarding = buildMbamOnboardingView(state);
        const setupGuide = buildMbamCaseSetupGuide(state);
        lines.push(`${t("hud.line.session")}:   ${connected ? t("hud.session.live") : t("hud.session.connecting")}`);
        lines.push(`${t("hud.line.case")}:      ${onboarding.caseTitle}`);
        lines.push(`${t("hud.line.day")}:       ${state.world?.day_index ?? 1}`);
        lines.push(`${t("hud.line.phase")}:     ${state.world?.day_phase ?? t("hud.value.none")}`);
        lines.push(`${t("hud.line.time")}:      ${formatTimeOfDay(state.world?.time_of_day)}`);
        lines.push(
            `${t("hud.line.clues")}:     ${state.investigation?.facts.known_fact_ids.length ?? 0} ${t("hud.value.facts")}`
        );
        const evidenceCount =
            (state.investigation?.evidence.discovered_ids.length ?? 0)
            + (state.investigation?.evidence.collected_ids.length ?? 0);
        lines.push(`${t("hud.line.evidence")}:  ${evidenceCount} ${t("hud.value.found")}`);
        lines.push(`${t("hud.line.scene")}:     ${state.dialogue?.active_scene_id ?? t("hud.value.none")}`);
        lines.push(`${t("hud.line.lead")}:      ${truncateText(onboarding.currentLead, 44)}`);
        lines.push(`${t("hud.line.start")}:     ${truncateText(setupGuide.firstInspect, 44)}`);
    } else {
        const onboarding = buildMbamOnboardingView(state);
        const setupGuide = buildMbamCaseSetupGuide(state);
        lines.push(`${t("hud.line.session")}:   ${connected ? t("hud.session.live") : t("hud.session.connecting")}`);
        lines.push(`${t("hud.line.case")}:      ${onboarding.caseTitle}`);
        lines.push(`${t("hud.line.objective")}: ${t("hud.objective.recover_medallion")}`);
        lines.push(`${t("hud.line.route")}:     ${t("hud.route.default")}`);
        lines.push(`${t("hud.line.incident")}:  ${truncateText(setupGuide.incident, 52)}`);
        lines.push(`${t("hud.line.inspect")}:   ${truncateText(setupGuide.firstInspect, 52)}`);
        lines.push(`${t("hud.line.talk_to")}:   ${truncateText(setupGuide.firstTalkTo, 52)}`);
        lines.push(`${t("hud.line.scene")}:     ${state.dialogue?.active_scene_id ?? t("hud.value.none")}`);
        lines.push(`${t("hud.line.lead")}:      ${truncateText(onboarding.currentLead, 52)}`);
    }

    const world = state.world;
    if (world && (world.time_of_day !== undefined || world.day_phase !== undefined) && profile === "dev") {
        const timeOfDay = formatTimeOfDay(world.time_of_day);
        lines.push("");
        lines.push(`day:       ${world.day_index ?? 1}`);
        lines.push(`phase:     ${world.day_phase ?? t("hud.value.none")}`);
        lines.push(`time:      ${timeOfDay}`);
    }

    lines.push("");
    if (desynced) {
        lines.push(profile === "dev" ? "DESYNC:    YES" : `${t("hud.line.sync")}:      ${t("hud.sync.issue_detected")}`);
        lines.push(`reason:    ${state.desyncReason ?? t("hud.value.none")}`);
    } else {
        lines.push(profile === "dev" ? "DESYNC:    no" : `${t("hud.line.sync")}:      ${t("hud.sync.stable")}`);
    }

    el.body.textContent = lines.join("\n");
}

function renderFeed(
    el: { feedBody: HTMLDivElement },
    state: WorldState,
    overlay: OverlayState | null,
    profile: HudProfile,
    t: TranslateFn
): void {
    const lines: string[] = [];
    const roomMap = state.rooms;
    const maxRows = profile === "dev" ? 6 : profile === "demo" ? 3 : 4;

    if (overlay && overlay.recentEvents.length > 0) {
        const events = overlay.recentEvents.slice(-maxRows);
        for (const ev of events) {
            lines.push(profile === "dev" ? formatOverlayEvent(ev, roomMap, t) : formatOverlayEventPlaytest(ev, roomMap, t));
        }
    } else {
        const events = Array.from(state.events.values())
            .sort((a, b) => b.tick - a.tick)
            .slice(0, maxRows);
        for (const ev of events) {
            lines.push(profile === "dev" ? formatWorldEvent(ev, roomMap, t) : formatWorldEventPlaytest(ev, roomMap, t));
        }
    }

    if (lines.length === 0) {
        if (profile === "dev") {
            el.feedBody.textContent = t("hud.feed.no_events");
        } else {
            const onboarding = buildMbamOnboardingView(state);
            const setupGuide = buildMbamCaseSetupGuide(state);
            el.feedBody.textContent = (
                `${t("hud.feed.no_activity")}\n`
                + `${t("hud.feed.start")}: ${truncateText(setupGuide.firstInspect, 48)}\n`
                + `${t("hud.feed.then")}: ${truncateText(setupGuide.firstTalkTo, 48)}\n`
                + `${t("hud.feed.tip")}: ${truncateText(onboarding.currentLead, 48)}`
            );
        }
        return;
    }

    el.feedBody.textContent = lines.join("\n");
}

function padLeft(s: string, n: number): string {
    if (s.length >= n) return s;
    return " ".repeat(n - s.length) + s;
}

function truncateHash(h?: string): string {
    if (!h) return "-";
    if (h.length <= 16) return h;
    return `${h.slice(0, 8)}…${h.slice(-8)}`;
}

function truncateText(value: string, maxLength: number): string {
    if (value.length <= maxLength) return value;
    if (maxLength <= 3) return value.slice(0, maxLength);
    return `${value.slice(0, maxLength - 3)}...`;
}

function formatTimeOfDay(value: number | undefined): string {
    if (value === undefined || !Number.isFinite(value)) return "-";
    const clamped = Math.max(0, Math.min(1, value));
    const totalMinutes = Math.floor(clamped * 24 * 60);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    const hh = String(hours).padStart(2, "0");
    const mm = String(minutes).padStart(2, "0");
    return `${hh}:${mm}`;
}

function formatWorldEvent(ev: KvpEvent, rooms: Map<number, KvpRoom>, t: TranslateFn): string {
    const payload = (ev.payload ?? {}) as Record<string, unknown>;
    const kind = String(payload.kind ?? ev.origin ?? t("hud.event.generic"));
    const roomId = toNumber(payload.room_id ?? payload.previous_room_id);
    const roomLabel = roomId !== null
        ? resolveRoomLabel(rooms.get(roomId), t)
        : null;
    const detail = roomLabel ? ` · ${roomLabel}` : "";
    return `${padLeft(String(ev.tick), 6)} · ${kind}${detail}`;
}

function formatWorldEventPlaytest(ev: KvpEvent, rooms: Map<number, KvpRoom>, t: TranslateFn): string {
    const payload = (ev.payload ?? {}) as Record<string, unknown>;
    const kind = String(payload.kind ?? ev.origin ?? t("hud.event.generic"));
    const userKind = describePlayerFacingEvent(kind, t);
    const roomId = toNumber(payload.room_id ?? payload.previous_room_id);
    const roomLabel = roomId !== null
        ? resolveRoomLabel(rooms.get(roomId), t)
        : null;
    const detail = roomLabel ? ` · ${roomLabel}` : "";
    return `${userKind}${detail}`;
}

function formatOverlayEvent(ev: UIOverlayEvent, rooms: Map<number, KvpRoom>, t: TranslateFn): string {
    const data = ev.data ?? {};
    const roomId = toNumber(data.room_id);
    const agentId = toNumber(data.agent_id);
    let detail = "";
    if (roomId !== null) {
        const label = resolveRoomLabel(rooms.get(roomId), t) ?? `Room ${roomId}`;
        detail = ` · ${label}`;
    } else if (agentId !== null) {
        detail = ` · ${t("hud.entity.agent")} ${agentId}`;
    }
    return `${padLeft(String(ev.tick), 6)} · ${ev.kind}${detail}`;
}

function formatOverlayEventPlaytest(ev: UIOverlayEvent, rooms: Map<number, KvpRoom>, t: TranslateFn): string {
    const data = ev.data ?? {};
    const userKind = describePlayerFacingEvent(ev.kind, t);
    const roomId = toNumber(data.room_id);
    const agentId = toNumber(data.agent_id);
    let detail = "";
    if (roomId !== null) {
        const label = resolveRoomLabel(rooms.get(roomId), t) ?? `Room ${roomId}`;
        detail = ` · ${label}`;
    } else if (agentId !== null) {
        detail = ` · ${t("hud.entity.agent")} ${agentId}`;
    }
    return `${userKind}${detail}`;
}

function describePlayerFacingEvent(kind: string, t: TranslateFn): string {
    const lower = kind.toLowerCase();
    if (lower.includes("dialogue")) return t("hud.event.dialogue_updated");
    if (lower.includes("investigation")) return t("hud.event.investigation_updated");
    if (lower.includes("object")) return t("hud.event.object_updated");
    if (lower.includes("minigame")) return t("hud.event.minigame_updated");
    if (lower.includes("contradiction")) return t("hud.event.contradiction_updated");
    if (lower.includes("resolution") || lower.includes("outcome")) return t("hud.event.outcome_updated");
    if (lower.includes("warning")) return t("hud.event.warning");
    return humanizeEventKind(kind, t);
}

function humanizeEventKind(kind: string, t: TranslateFn): string {
    const normalized = kind
        .replace(/[._:]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
    if (!normalized) return t("hud.event.case_update");
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function toNumber(val: unknown): number | null {
    if (typeof val === "number" && Number.isFinite(val)) return val;
    if (typeof val === "string" && val.trim() !== "" && Number.isFinite(Number(val))) return Number(val);
    return null;
}

function resolveRoomLabel(room: KvpRoom | undefined, t: TranslateFn): string | null {
    if (!room) return null;
    return resolvePresentationText({
        text: room.label,
        textKey: room.label_key,
        fallbackText: t("inspect.title.room_with_id", { id: room.room_id }),
    });
}
