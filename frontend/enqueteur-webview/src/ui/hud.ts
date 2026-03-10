// src/ui/hud.ts
import type { WorldStore, WorldState, KvpEvent, KvpRoom } from "../state/worldStore";
import type { OverlayStore, OverlayState, UIOverlayEvent } from "../state/overlayStore";

export type HudProfile = "playtest" | "dev";

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

    const root = document.createElement("div");
    root.style.position = "absolute";
    root.style.top = "10px";
    root.style.right = "10px";
    root.style.zIndex = "10";
    root.style.pointerEvents = "none";
    root.style.fontFamily = "Chivo Mono, JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace";
    root.style.fontSize = "12px";
    root.style.color = "rgba(31, 36, 43, 0.95)";

    const panel = document.createElement("div");
    panel.style.padding = "10px 12px";
    panel.style.borderRadius = "12px";
    panel.style.background = "rgba(247, 242, 233, 0.85)";
    panel.style.backdropFilter = "blur(8px)";
    panel.style.border = "2px solid rgba(31, 36, 43, 0.65)";
    panel.style.minWidth = "280px";
    panel.style.whiteSpace = "pre";
    panel.style.lineHeight = "1.35";
    root.appendChild(panel);

    const dot = document.createElement("span");
    dot.style.display = "inline-block";
    dot.style.width = "8px";
    dot.style.height = "8px";
    dot.style.borderRadius = "999px";
    dot.style.marginRight = "8px";
    dot.style.verticalAlign = "middle";

    const header = document.createElement("div");
    header.style.marginBottom = "8px";
    header.style.fontWeight = "600";
    header.style.opacity = "0.95";

    const title = document.createElement("span");
    title.textContent = profile === "dev" ? "Enqueteur WebView" : "Case Status";

    header.appendChild(dot);
    header.appendChild(title);

    const body = document.createElement("div");

    panel.appendChild(header);
    panel.appendChild(body);

    const feedPanel = document.createElement("div");
    feedPanel.style.marginTop = "10px";
    feedPanel.style.padding = "10px 12px";
    feedPanel.style.borderRadius = "12px";
    feedPanel.style.background = "rgba(247, 242, 233, 0.78)";
    feedPanel.style.border = "2px solid rgba(31, 36, 43, 0.35)";
    feedPanel.style.minWidth = "280px";
    feedPanel.style.maxWidth = "320px";
    feedPanel.style.whiteSpace = "pre";
    feedPanel.style.lineHeight = "1.35";

    const feedTitle = document.createElement("div");
    feedTitle.textContent = profile === "dev" ? "Live Feed" : "Case Feed";
    feedTitle.style.fontWeight = "600";
    feedTitle.style.marginBottom = "6px";

    const feedBody = document.createElement("div");
    feedBody.style.opacity = "0.9";

    feedPanel.appendChild(feedTitle);
    feedPanel.appendChild(feedBody);
    root.appendChild(feedPanel);

    let lastWorldState: WorldState | null = null;
    let lastOverlayState: OverlayState | null = null;

    const rerender = (): void => {
        if (!lastWorldState) return;
        renderHud({ dot, body }, lastWorldState, profile);
        renderFeed({ feedBody }, lastWorldState, lastOverlayState, profile);
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
        title.textContent = profile === "dev" ? "Enqueteur WebView" : "Case Status";
        feedTitle.textContent = profile === "dev" ? "Live Feed" : "Case Feed";
        rerender();
    };

    return {
        root,
        setProfile,
    };
}

function renderHud(
    el: { dot: HTMLSpanElement; body: HTMLDivElement },
    state: WorldState,
    profile: HudProfile
): void {
    const connected = state.connected;
    const desynced = state.desynced;

    if (!connected) el.dot.style.background = "rgba(59, 75, 90, 0.35)";
    else if (desynced) el.dot.style.background = "rgba(242, 160, 129, 0.9)";
    else el.dot.style.background = "rgba(90, 169, 178, 0.95)";

    const lines: string[] = [];
    if (profile === "dev") {
        const kernelHello = state.kernelHello;
        lines.push(`mode:      ${state.mode}`);
        lines.push(`connected: ${connected ? "yes" : "no"}`);
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
            lines.push("kernel:    -");
        }
    } else {
        lines.push(`Session:   ${connected ? "Live" : "Connecting..."}`);
        lines.push(`Day:       ${state.world?.day_index ?? 1}`);
        lines.push(`Phase:     ${state.world?.day_phase ?? "-"}`);
        lines.push(`Time:      ${formatTimeOfDay(state.world?.time_of_day)}`);
        lines.push(`Clues:     ${state.investigation?.facts.known_fact_ids.length ?? 0} facts`);
        const evidenceCount =
            (state.investigation?.evidence.discovered_ids.length ?? 0)
            + (state.investigation?.evidence.collected_ids.length ?? 0);
        lines.push(`Evidence:  ${evidenceCount} found`);
        lines.push(`Scene:     ${state.dialogue?.active_scene_id ?? "-"}`);
    }

    const world = state.world;
    if (world && (world.time_of_day !== undefined || world.day_phase !== undefined) && profile === "dev") {
        const timeOfDay = formatTimeOfDay(world.time_of_day);
        lines.push("");
        lines.push(`day:       ${world.day_index ?? 1}`);
        lines.push(`phase:     ${world.day_phase ?? "-"}`);
        lines.push(`time:      ${timeOfDay}`);
    }

    lines.push("");
    if (desynced) {
        lines.push(profile === "dev" ? "DESYNC:    YES" : "Sync:      issue detected");
        lines.push(`reason:    ${state.desyncReason ?? "-"}`);
    } else {
        lines.push(profile === "dev" ? "DESYNC:    no" : "Sync:      stable");
    }

    el.body.textContent = lines.join("\n");
}

function renderFeed(
    el: { feedBody: HTMLDivElement },
    state: WorldState,
    overlay: OverlayState | null,
    profile: HudProfile
): void {
    const lines: string[] = [];
    const roomMap = state.rooms;
    const maxRows = profile === "dev" ? 6 : 4;

    if (overlay && overlay.recentEvents.length > 0) {
        const events = overlay.recentEvents.slice(-maxRows);
        for (const ev of events) {
            lines.push(profile === "dev" ? formatOverlayEvent(ev, roomMap) : formatOverlayEventPlaytest(ev, roomMap));
        }
    } else {
        const events = Array.from(state.events.values())
            .sort((a, b) => b.tick - a.tick)
            .slice(0, maxRows);
        for (const ev of events) {
            lines.push(profile === "dev" ? formatWorldEvent(ev, roomMap) : formatWorldEventPlaytest(ev, roomMap));
        }
    }

    if (lines.length === 0) {
        el.feedBody.textContent = profile === "dev" ? "No events yet" : "No activity yet";
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

function formatWorldEvent(ev: KvpEvent, rooms: Map<number, KvpRoom>): string {
    const payload = (ev.payload ?? {}) as Record<string, unknown>;
    const kind = String(payload.kind ?? ev.origin ?? "event");
    const roomId = toNumber(payload.room_id ?? payload.previous_room_id);
    const roomLabel = roomId !== null ? rooms.get(roomId)?.label : null;
    const detail = roomLabel ? ` · ${roomLabel}` : "";
    return `${padLeft(String(ev.tick), 6)} · ${kind}${detail}`;
}

function formatWorldEventPlaytest(ev: KvpEvent, rooms: Map<number, KvpRoom>): string {
    const payload = (ev.payload ?? {}) as Record<string, unknown>;
    const kind = String(payload.kind ?? ev.origin ?? "event");
    const roomId = toNumber(payload.room_id ?? payload.previous_room_id);
    const roomLabel = roomId !== null ? rooms.get(roomId)?.label : null;
    const detail = roomLabel ? ` · ${roomLabel}` : "";
    return `${kind}${detail}`;
}

function formatOverlayEvent(ev: UIOverlayEvent, rooms: Map<number, KvpRoom>): string {
    const data = ev.data ?? {};
    const roomId = toNumber(data.room_id);
    const agentId = toNumber(data.agent_id);
    let detail = "";
    if (roomId !== null) {
        const label = rooms.get(roomId)?.label ?? `Room ${roomId}`;
        detail = ` · ${label}`;
    } else if (agentId !== null) {
        detail = ` · Agent ${agentId}`;
    }
    return `${padLeft(String(ev.tick), 6)} · ${ev.kind}${detail}`;
}

function formatOverlayEventPlaytest(ev: UIOverlayEvent, rooms: Map<number, KvpRoom>): string {
    const data = ev.data ?? {};
    const roomId = toNumber(data.room_id);
    const agentId = toNumber(data.agent_id);
    let detail = "";
    if (roomId !== null) {
        const label = rooms.get(roomId)?.label ?? `Room ${roomId}`;
        detail = ` · ${label}`;
    } else if (agentId !== null) {
        detail = ` · Agent ${agentId}`;
    }
    return `${ev.kind}${detail}`;
}

function toNumber(val: unknown): number | null {
    if (typeof val === "number" && Number.isFinite(val)) return val;
    if (typeof val === "string" && val.trim() !== "" && Number.isFinite(Number(val))) return Number(val);
    return null;
}
