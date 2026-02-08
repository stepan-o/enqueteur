// src/ui/hud.ts
import type { WorldStore, WorldState } from "../state/worldStore";

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

export function mountHud(store: WorldStore): HTMLElement {
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

    // Render loop: on store updates
    store.subscribe((s) => {
        renderHud({ dot, body }, s);
    });

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

function padLeft(s: string, n: number): string {
    if (s.length >= n) return s;
    return " ".repeat(n - s.length) + s;
}

function truncateHash(h: string): string {
    if (!h) return "-";
    if (h.length <= 16) return h;
    return `${h.slice(0, 8)}…${h.slice(-8)}`;
}
