// src/ui/hud.ts
import type { WorldStore, WorldState, KvpEvent, KvpRoom } from "../state/worldStore";
import type { OverlayStore, OverlayState, UIOverlayEvent } from "../state/overlayStore";

/**
 * HUD (WEBVIEW-0001)
 * -----------------------------------------------------------------------------
 * Minimal DOM overlay for:
 * - connection status
 * - tick + step hash
 * - kernel hello summary
 * - desync banner (read-only; recovery click lives in PixiScene)
 *
 * Non-goals:
 * - No mutation of simulation state
 * - No protocol logic
 * - No heavy UI framework
 */

export function mountHud(store: WorldStore, overlayStore?: OverlayStore): HTMLElement {
    const root = document.createElement("div");
    root.style.position = "absolute";
    root.style.top = "10px";
    root.style.right = "10px";
    root.style.zIndex = "10";
    root.style.pointerEvents = "none"; // HUD is informational; interactive controls come later.
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

    // Optional: a small status dot
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
    title.textContent = "Loopforge WebView";

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
    feedTitle.textContent = "Live Feed";
    feedTitle.style.fontWeight = "600";
    feedTitle.style.marginBottom = "6px";

    const feedBody = document.createElement("div");
    feedBody.style.opacity = "0.9";

    feedPanel.appendChild(feedTitle);
    feedPanel.appendChild(feedBody);
    root.appendChild(feedPanel);

    let lastWorldState: WorldState | null = null;
    let lastOverlayState: OverlayState | null = null;

    // Render loop: on store updates
    store.subscribe((s) => {
        lastWorldState = s;
        renderHud({ dot, body }, s);
        renderFeed({ feedBody }, s, lastOverlayState);
    });

    if (overlayStore) {
        overlayStore.subscribe((o) => {
            lastOverlayState = o;
            if (lastWorldState) renderFeed({ feedBody }, lastWorldState, o);
        });
    }

    return root;
}

function renderHud(
    el: { dot: HTMLSpanElement; body: HTMLDivElement },
    s: WorldState
): void {
    const kh = s.kernelHello;

    const connected = s.connected;
    const desynced = s.desynced;

    // Dot color (small, simple signal)
    if (!connected) el.dot.style.background = "rgba(59, 75, 90, 0.35)";
    else if (desynced) el.dot.style.background = "rgba(242, 160, 129, 0.9)";
    else el.dot.style.background = "rgba(90, 169, 178, 0.95)";

    const lines: string[] = [];

    lines.push(`mode:      ${s.mode}`);
    lines.push(`connected: ${connected ? "yes" : "no"}`);
    lines.push(`tick:      ${padLeft(String(s.tick), 8)}`);
    lines.push(`stepHash:  ${truncateHash(s.stepHash)}`);

    if (kh) {
        lines.push("");
        lines.push(`kernel:    ${kh.engine_name}@${kh.engine_version}`);
        lines.push(`schema:    ${kh.schema_version}`);
        lines.push(`world_id:  ${kh.world_id}`);
        lines.push(`run_id:    ${kh.run_id}`);
        lines.push(`seed:      ${kh.seed}`);
        lines.push(`tick_hz:   ${kh.tick_rate_hz}`);
    } else {
        lines.push("");
        lines.push("kernel:    -");
    }

    if (desynced) {
        lines.push("");
        lines.push("DESYNC:    YES");
        lines.push(`reason:    ${s.desyncReason ?? "-"}`);
        lines.push("");
        lines.push("(See Pixi banner to recover)");
    } else {
        lines.push("");
        lines.push("DESYNC:    no");
    }

    el.body.textContent = lines.join("\n");
}

function renderFeed(
    el: { feedBody: HTMLDivElement },
    s: WorldState,
    overlay: OverlayState | null
): void {
    const lines: string[] = [];
    const roomMap = s.rooms;

    if (overlay && overlay.recentEvents.length > 0) {
        const events = overlay.recentEvents.slice(-6);
        for (const ev of events) {
            lines.push(formatOverlayEvent(ev, roomMap));
        }
    } else {
        const events = Array.from(s.events.values())
            .sort((a, b) => b.tick - a.tick)
            .slice(0, 6);
        for (const ev of events) {
            lines.push(formatWorldEvent(ev, roomMap));
        }
    }

    if (lines.length === 0) {
        el.feedBody.textContent = "No events yet";
        return;
    }

    el.feedBody.textContent = lines.join("\n");
}

function padLeft(s: string, n: number): string {
    if (s.length >= n) return s;
    return " ".repeat(n - s.length) + s;
}

function truncateHash(h: string): string {
    if (!h) return "-";
    if (h.length <= 16) return h;
    return `${h.slice(0, 8)}…${h.slice(-8)}`;
}

function formatWorldEvent(ev: KvpEvent, rooms: Map<number, KvpRoom>): string {
    const payload = (ev.payload ?? {}) as Record<string, unknown>;
    const kind = String(payload.kind ?? ev.origin ?? "event");
    const roomId = toNumber(payload.room_id ?? payload.previous_room_id);
    const roomLabel = roomId !== null ? rooms.get(roomId)?.label : null;
    const detail = roomLabel ? ` · ${roomLabel}` : "";
    return `${padLeft(String(ev.tick), 6)} · ${kind}${detail}`;
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

function toNumber(val: unknown): number | null {
    if (typeof val === "number" && Number.isFinite(val)) return val;
    if (typeof val === "string" && val.trim() !== "" && Number.isFinite(Number(val))) return Number(val);
    return null;
}
