// src/render/pixiScene.ts
import * as PIXI from "pixi.js";
import type { WorldState, RoomSnapshot, AgentSnapshot, NarrativeFragment } from "../state/worldStore";
import { isoProject } from "./iso";

/**
 * PixiScene (WEBVIEW-0001)
 * -----------------------------------------------------------------------------
 * Responsibilities:
 * - Render the viewer’s mirrored WorldState (rooms, agents, narrative overlays)
 * - Provide minimal camera pan/zoom hooks (no fancy UX yet)
 * - Surface desync banner and allow requesting a fresh snapshot
 *
 * Non-goals:
 * - No simulation logic
 * - No state mutation except view-local visuals (interpolation can come later)
 */

export class PixiScene {
    public readonly app: PIXI.Application;

    private readonly root = new PIXI.Container();
    private readonly roomsLayer = new PIXI.Container();
    private readonly agentsLayer = new PIXI.Container();
    private readonly overlayLayer = new PIXI.Container();
    private readonly uiLayer = new PIXI.Container();

    // Render objects keyed by IDs
    private readonly roomGfx = new Map<number, PIXI.Graphics>();
    private readonly agentNodes = new Map<number, PIXI.Container>();

    // Narrative bubbles keyed by a stable-ish key
    private readonly bubbleNodes = new Map<string, PIXI.Container>();

    // Camera state
    private camX = 0;
    private camY = 0;
    private camZoom = 1;

    // Desync UI
    private desyncBanner?: PIXI.Container;
    private requestFreshSnapshotCb?: () => void;

    // Optional: basic background
    private bg?: PIXI.Graphics;

    // Pixi v8 init is async; gate rendering & input until ready.
    private ready = false;

    // Optional: stash latest state so we can render immediately after init completes.
    private pendingState?: WorldState;

    constructor(mountEl: HTMLElement) {
        this.app = new PIXI.Application();

        // Pixi v8: Application.init() is async. Constructors cannot be async.
        // We kick it off and gate render/input via `this.ready`.
        void this.init(mountEl);
    }

    private async init(mountEl: HTMLElement): Promise<void> {
        await this.app.init({
            resizeTo: mountEl,
            antialias: true,
            backgroundAlpha: 1,
        });

        mountEl.appendChild(this.app.canvas);

        // Layering
        this.root.addChild(this.roomsLayer, this.agentsLayer, this.overlayLayer, this.uiLayer);
        this.app.stage.addChild(this.root);

        // Simple background (keeps contrast predictable)
        this.bg = new PIXI.Graphics();
        this.app.stage.addChildAt(this.bg, 0);

        // Keep background covering canvas
        this.app.ticker.add(() => {
            if (!this.bg) return;
            this.bg.clear();
            this.bg.rect(0, 0, this.app.renderer.width, this.app.renderer.height);
            this.bg.fill({ color: 0x0b0b0b, alpha: 1 });
        });

        // --- DEBUG: origin marker so we *always* see something if root is visible
        const origin = new PIXI.Graphics();
        origin.circle(0, 0, 6);
        origin.fill({ color: 0xff3366, alpha: 0.9 });
        origin.name = "__origin__";
        this.root.addChild(origin);

        const cross = new PIXI.Graphics();
        cross.moveTo(-20, 0).lineTo(20, 0).stroke({ width: 2, color: 0xffffff, alpha: 0.25 });
        cross.moveTo(0, -20).lineTo(0, 20).stroke({ width: 2, color: 0xffffff, alpha: 0.25 });
        cross.name = "__cross__";
        this.root.addChild(cross);

        // Recenter camera relative to canvas size (more robust than a hardcoded offset)
        const recenter = () => {
            this.setCamera({
                x: Math.floor(this.app.renderer.width * 0.5),
                y: Math.floor(this.app.renderer.height * 0.5), // was 0.35; 0.5 is safer for iso
                zoom: this.camZoom,
            });
        };
        recenter();
        this.app.renderer.on("resize", recenter);

        // Basic wheel zoom (Phase 2 polish later) — only after canvas exists.
        this.enableWheelZoom();
        this.enableDragPan();

        this.ready = true;

        // If state arrived before init completed, render once now.
        if (this.pendingState) {
            const s = this.pendingState;
            this.pendingState = undefined;
            this.renderFromState(s);
        }
    }

    /** Hook: used by boot.ts to wire the desync banner click. */
    onRequestFreshSnapshot(cb: () => void): void {
        this.requestFreshSnapshotCb = cb;
    }

    /** Main render entry (called from WorldStore subscription). */
    renderFromState(s: WorldState): void {
        if (!this.ready) {
            // Store latest; render after init completes.
            this.pendingState = s;
            return;
        }

        // --- DEBUG: one-line visibility check
        // console.debug("[pixi] render", { rooms: s.rooms.size, agents: s.agents.size, narrative: s.narrative.size });

        if (s.desynced) {
            this.showDesyncBanner(s.desyncReason ?? "Desync detected");
            return;
        } else {
            this.hideDesyncBanner();
        }

        this.renderRooms(s);
        this.renderAgents(s);
        this.renderNarrative(s);
    }

    /* --------------------------------------------------------------------------
     * Rooms
     * ------------------------------------------------------------------------ */

    private renderRooms(s: WorldState): void {
        const rooms = Array.from(s.rooms.values()).sort((a, b) => a.room_id - b.room_id);

        for (const r of rooms) {
            let g = this.roomGfx.get(r.room_id);
            if (!g) {
                g = new PIXI.Graphics();
                this.roomGfx.set(r.room_id, g);
                this.roomsLayer.addChild(g);
            }

            this.drawRoom(g, r);
        }

        // Cleanup rooms no longer present
        for (const id of Array.from(this.roomGfx.keys())) {
            if (!s.rooms.has(id)) {
                const g = this.roomGfx.get(id)!;
                g.destroy();
                this.roomGfx.delete(id);
            }
        }
    }

    private drawRoom(g: PIXI.Graphics, r: RoomSnapshot): void {
        g.clear();

        const b = r.bounds;

        if (!b) {
            g.circle(0, 0, 6);
            g.stroke({ width: 1, color: 0xffffff, alpha: 0.25 });
            return;
        }

        const p0 = isoProject({ x: b.x, y: b.y });
        const p1 = isoProject({ x: b.x + b.w, y: b.y });
        const p2 = isoProject({ x: b.x + b.w, y: b.y + b.h });
        const p3 = isoProject({ x: b.x, y: b.y + b.h });

        // Pixi v8-safe poly drawing (more reliable than moveTo/lineTo path reuse)
        const pts = [p0.x, p0.y, p1.x, p1.y, p2.x, p2.y, p3.x, p3.y];

        // Optional: encode tension as fill alpha (still neutral)
        const t = clamp01((r.tension ?? 0) / 100);
        if (t > 0) {
            g.poly(pts, true);
            g.fill({ color: 0xffffff, alpha: 0.03 + t * 0.06 });
        }

        // Outline
        g.poly(pts, true);
        g.stroke({ width: 1, color: 0xffffff, alpha: 0.18 });

        // Room label (minimal, optional)
        if (r.name) {
            let label = g.getChildByName("label") as PIXI.Text | null;
            if (!label) {
                label = new PIXI.Text({
                    text: r.name,
                    style: { fontFamily: "monospace", fontSize: 10, fill: 0xffffff },
                });
                label.name = "label";
                g.addChild(label);
            }
            label.text = r.name;

            const center = isoProject({ x: b.x + b.w * 0.5, y: b.y + b.h * 0.5 });
            label.x = center.x + 6;
            label.y = center.y - 10;
            label.alpha = 0.6;
        }
    }

    /* --------------------------------------------------------------------------
     * Agents
     * ------------------------------------------------------------------------ */

    private renderAgents(s: WorldState): void {
        const agents = Array.from(s.agents.values()).sort((a, b) => a.agent_id - b.agent_id);

        for (const a of agents) {
            let node = this.agentNodes.get(a.agent_id);
            if (!node) {
                node = this.makeAgentNode(a);
                this.agentNodes.set(a.agent_id, node);
                this.agentsLayer.addChild(node);
            }

            // Update position
            const p = isoProject(a.pos);
            node.x = p.x;
            node.y = p.y;

            // Update label
            const label = node.getChildByName("label") as PIXI.Text | null;
            if (label) label.text = a.public_state?.label ?? `Agent ${a.agent_id}`;

            // Optional: speaking indicator
            const speak = node.getChildByName("speak") as PIXI.Graphics | null;
            if (speak) speak.alpha = a.public_state?.speaking ? 0.9 : 0.15;
        }

        // Cleanup despawned agents
        for (const id of Array.from(this.agentNodes.keys())) {
            if (!s.agents.has(id)) {
                const node = this.agentNodes.get(id)!;
                node.destroy({ children: true });
                this.agentNodes.delete(id);
            }
        }
    }

    private makeAgentNode(a: AgentSnapshot): PIXI.Container {
        const c = new PIXI.Container();

        const dot = new PIXI.Graphics();
        dot.circle(0, 0, 4);
        dot.fill({ color: 0xffffff, alpha: 0.9 });
        c.addChild(dot);

        const speak = new PIXI.Graphics();
        speak.name = "speak";
        speak.circle(0, -10, 2);
        speak.fill({ color: 0xffffff, alpha: 0.15 });
        c.addChild(speak);

        const label = new PIXI.Text({
            text: a.public_state?.label ?? `Agent ${a.agent_id}`,
            style: { fontFamily: "monospace", fontSize: 10, fill: 0xffffff },
        });
        label.name = "label";
        label.x = 8;
        label.y = -18;
        label.alpha = 0.8;
        c.addChild(label);

        return c;
    }

    /* --------------------------------------------------------------------------
     * Narrative (bubbles) — Phase 2 hook (still minimal)
     * ------------------------------------------------------------------------ */

    private renderNarrative(s: WorldState): void {
        const frags = Array.from(s.narrative.values());
        const seen = new Set<string>();

        for (const n of frags) {
            const key = narrativeKey(n);
            seen.add(key);

            let bubble = this.bubbleNodes.get(key);
            if (!bubble) {
                bubble = this.makeBubble(n);
                this.bubbleNodes.set(key, bubble);
                this.overlayLayer.addChild(bubble);
            }

            // Position bubble above entity if it exists
            const agentId = n.entity_id;
            const agent = s.agents.get(agentId);
            if (agent) {
                const p = isoProject(agent.pos);
                bubble.x = p.x + 10;
                bubble.y = p.y - 48;
                bubble.alpha = 0.95;
            } else {
                bubble.alpha = 0;
            }

            const text = bubble.getChildByName("text") as PIXI.Text | null;
            if (text) text.text = n.text;
        }

        // Cleanup stale bubbles
        for (const key of Array.from(this.bubbleNodes.keys())) {
            if (!seen.has(key)) {
                const node = this.bubbleNodes.get(key)!;
                node.destroy({ children: true });
                this.bubbleNodes.delete(key);
            }
        }
    }

    private makeBubble(n: NarrativeFragment): PIXI.Container {
        const c = new PIXI.Container();

        const bg = new PIXI.Graphics();
        bg.roundRect(0, 0, 220, 44, 8);
        bg.fill({ color: 0x000000, alpha: 0.75 });
        bg.stroke({ width: 1, color: 0xffffff, alpha: 0.15 });
        c.addChild(bg);

        const t = new PIXI.Text({
            text: n.text,
            style: { fontFamily: "monospace", fontSize: 11, fill: 0xffffff, wordWrap: true, wordWrapWidth: 200 },
        });
        t.name = "text";
        t.x = 10;
        t.y = 8;
        c.addChild(t);

        if (n.nondeterministic) c.alpha = 0.9;
        return c;
    }

    /* --------------------------------------------------------------------------
     * Camera controls (basic)
     * ------------------------------------------------------------------------ */

    private setCamera(v: { x: number; y: number; zoom: number }): void {
        this.camX = v.x;
        this.camY = v.y;
        this.camZoom = v.zoom;

        this.root.x = this.camX;
        this.root.y = this.camY;
        this.root.scale.set(this.camZoom);
    }

    private enableWheelZoom(): void {
        const canvas = this.app.canvas;

        canvas.addEventListener(
            "wheel",
            (e) => {
                e.preventDefault();
                const delta = Math.sign(e.deltaY);
                const factor = delta > 0 ? 0.9 : 1.1;
                const next = clamp(this.camZoom * factor, 0.25, 3);
                this.setCamera({ x: this.camX, y: this.camY, zoom: next });
            },
            { passive: false }
        );
    }

    private enableDragPan(): void {
        const canvas = this.app.canvas;

        let dragging = false;
        let lastX = 0;
        let lastY = 0;

        canvas.addEventListener("mousedown", (e) => {
            dragging = true;
            lastX = e.clientX;
            lastY = e.clientY;
        });

        window.addEventListener("mouseup", () => {
            dragging = false;
        });

        window.addEventListener("mousemove", (e) => {
            if (!dragging) return;
            const dx = e.clientX - lastX;
            const dy = e.clientY - lastY;
            lastX = e.clientX;
            lastY = e.clientY;

            this.setCamera({ x: this.camX + dx, y: this.camY + dy, zoom: this.camZoom });
        });
    }

    /* --------------------------------------------------------------------------
     * Desync UI
     * ------------------------------------------------------------------------ */

    private showDesyncBanner(reason: string): void {
        if (this.desyncBanner) return;

        const banner = new PIXI.Container();
        banner.eventMode = "static";
        banner.cursor = "pointer";

        const bg = new PIXI.Graphics();
        bg.roundRect(0, 0, 520, 84, 10);
        bg.fill({ color: 0x000000, alpha: 0.85 });
        bg.stroke({ width: 1, color: 0xffffff, alpha: 0.2 });
        banner.addChild(bg);

        const txt = new PIXI.Text({
            text: `DESYNC\n${reason}\nClick to request fresh snapshot.`,
            style: { fontFamily: "monospace", fontSize: 12, fill: 0xffffff, wordWrap: true, wordWrapWidth: 500 },
        });
        txt.x = 12;
        txt.y = 10;
        banner.addChild(txt);

        banner.x = 16;
        banner.y = 16;

        banner.on("pointertap", () => {
            if (this.requestFreshSnapshotCb) this.requestFreshSnapshotCb();
        });

        this.uiLayer.addChild(banner);
        this.desyncBanner = banner;
    }

    private hideDesyncBanner(): void {
        if (!this.desyncBanner) return;
        this.desyncBanner.destroy({ children: true });
        this.desyncBanner = undefined;
    }
}

/* --------------------------------------------------------------------------
 * Helpers
 * ------------------------------------------------------------------------ */

function narrativeKey(n: NarrativeFragment): string {
    return `${n.entity_id}:${n.kind}:${n.text}`;
}

function clamp(v: number, lo: number, hi: number): number {
    return Math.max(lo, Math.min(hi, v));
}

function clamp01(v: number): number {
    return clamp(v, 0, 1);
}
