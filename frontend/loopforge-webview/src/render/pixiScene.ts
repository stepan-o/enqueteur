// src/render/pixiScene.ts
import * as PIXI from "pixi.js";
import type { KvpAgent, KvpItem, KvpRoom, RenderSpec, WorldState } from "../state/worldStore";
import { isoProject, setIsoTileSize } from "./iso";

/**
 * PixiScene (WEBVIEW-0001)
 * -----------------------------------------------------------------------------
 * Render the viewer’s mirrored WorldState with a noir-neon visual direction.
 * Viewer-only: no sim logic, no mutation of kernel state.
 */

const PALETTE = {
    night: 0x0a0b10,
    grid: 0x1b1f2a,
    neonCyan: 0x4de1ff,
    neonMagenta: 0xff4fd8,
    neonViolet: 0x7a5cff,
    neonAmber: 0xffb84d,
    neonMint: 0x2dffb3,
    ink: 0x0b0b12,
};

type RoomCenter = { x: number; y: number };

export class PixiScene {
    public readonly app: PIXI.Application;

    private readonly root = new PIXI.Container();
    private readonly gridLayer = new PIXI.Container();
    private readonly roomsLayer = new PIXI.Container();
    private readonly itemsLayer = new PIXI.Container();
    private readonly agentsLayer = new PIXI.Container();
    private readonly uiLayer = new PIXI.Container();

    private readonly gridGfx = new PIXI.Graphics();
    private readonly roomGfx = new Map<number, PIXI.Graphics>();
    private readonly agentNodes = new Map<number, PIXI.Container>();
    private readonly itemNodes = new Map<number, PIXI.Graphics>();

    // Camera state
    private camX = 0;
    private camY = 0;
    private camZoom = 1;

    // Desync UI
    private desyncBanner?: PIXI.Container;
    private requestFreshSnapshotCb?: () => void;

    // Pixi v8 init is async; gate rendering & input until ready.
    private ready = false;

    // Optional: stash latest state so we can render immediately after init completes.
    private pendingState?: WorldState;

    private lastIsoKey = "";
    private lastGridKey = "";
    private lastLayoutKey = "";
    private lastAutoFitKey = "";
    private autoFitLocked = false;
    private roomLayout = new Map<number, RoomCenter>();

    constructor(mountEl: HTMLElement) {
        this.app = new PIXI.Application();
        void this.init(mountEl);
    }

    private async init(mountEl: HTMLElement): Promise<void> {
        await this.app.init({
            resizeTo: mountEl,
            antialias: true,
            backgroundAlpha: 0,
        });

        mountEl.appendChild(this.app.canvas);

        // Layering
        this.root.addChild(this.gridLayer, this.roomsLayer, this.itemsLayer, this.agentsLayer, this.uiLayer);
        this.app.stage.addChild(this.root);

        this.gridLayer.addChild(this.gridGfx);

        const recenter = () => {
            this.setCamera({
                x: Math.floor(this.app.renderer.width * 0.5),
                y: Math.floor(this.app.renderer.height * 0.45),
                zoom: this.camZoom,
            });
        };
        recenter();
        this.app.renderer.on("resize", recenter);

        this.enableWheelZoom();
        this.enableDragPan();

        this.ready = true;

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
            this.pendingState = s;
            return;
        }

        if (s.desynced) {
            this.showDesyncBanner(s.desyncReason ?? "Desync detected");
            return;
        } else {
            this.hideDesyncBanner();
        }

        this.applyRenderSpec(s.renderSpec);
        this.renderGrid(s.renderSpec);

        const roomCenters = this.ensureRoomLayout(s, s.renderSpec);
        this.autoFitCameraIfNeeded(s, s.renderSpec, roomCenters);
        this.renderRooms(s, roomCenters);
        this.renderItems(s, roomCenters);
        this.renderAgents(s);
    }

    /* --------------------------------------------------------------------------
     * RenderSpec / Grid
     * ------------------------------------------------------------------------ */

    private applyRenderSpec(spec?: RenderSpec): void {
        const iso = spec?.projection;
        const isoKey = `${iso?.recommended_iso_tile_w ?? 64}x${iso?.recommended_iso_tile_h ?? 32}`;
        if (isoKey !== this.lastIsoKey) {
            this.lastIsoKey = isoKey;
            setIsoTileSize(iso?.recommended_iso_tile_w ?? 64, iso?.recommended_iso_tile_h ?? 32);
        }
    }

    private renderGrid(spec?: RenderSpec): void {
        const bounds = getWorldBounds(spec);
        const key = `${bounds.min_x}:${bounds.min_y}:${bounds.max_x}:${bounds.max_y}:${this.lastIsoKey}`;
        if (key === this.lastGridKey) return;
        this.lastGridKey = key;

        const g = this.gridGfx;
        g.clear();

        const step = 1;
        const color = PALETTE.grid;
        const alpha = 0.25;

        for (let x = Math.floor(bounds.min_x); x <= Math.ceil(bounds.max_x); x += step) {
            const p0 = isoProject({ x, y: bounds.min_y });
            const p1 = isoProject({ x, y: bounds.max_y });
            g.moveTo(p0.x, p0.y);
            g.lineTo(p1.x, p1.y);
        }

        for (let y = Math.floor(bounds.min_y); y <= Math.ceil(bounds.max_y); y += step) {
            const p0 = isoProject({ x: bounds.min_x, y });
            const p1 = isoProject({ x: bounds.max_x, y });
            g.moveTo(p0.x, p0.y);
            g.lineTo(p1.x, p1.y);
        }

        g.stroke({ width: 1, color, alpha });
    }

    /* --------------------------------------------------------------------------
     * Rooms
     * ------------------------------------------------------------------------ */

    private ensureRoomLayout(s: WorldState, spec?: RenderSpec): Map<number, RoomCenter> {
        const bounds = getWorldBounds(spec);
        const roomIds = Array.from(s.rooms.keys()).sort((a, b) => a - b);
        const key = `${roomIds.join(",")}|${bounds.min_x}:${bounds.min_y}:${bounds.max_x}:${bounds.max_y}`;

        if (key === this.lastLayoutKey && this.roomLayout.size > 0) {
            return this.roomLayout;
        }

        const centers = new Map<number, RoomCenter>();
        const agentBuckets = new Map<number, { x: number; y: number; count: number }>();

        for (const a of s.agents.values()) {
            const bucket = agentBuckets.get(a.room_id) ?? { x: 0, y: 0, count: 0 };
            bucket.x += a.transform.x;
            bucket.y += a.transform.y;
            bucket.count += 1;
            agentBuckets.set(a.room_id, bucket);
        }

        for (const r of s.rooms.values()) {
            const bucket = agentBuckets.get(r.room_id);
            if (bucket && bucket.count > 0) {
                centers.set(r.room_id, clampPoint({ x: bucket.x / bucket.count, y: bucket.y / bucket.count }, bounds));
            } else {
                centers.set(r.room_id, scatterPoint(r.room_id, bounds));
            }
        }

        this.roomLayout = centers;
        this.lastLayoutKey = key;
        this.lastAutoFitKey = "";
        this.autoFitLocked = false;
        return this.roomLayout;
    }

    private renderRooms(s: WorldState, centers: Map<number, RoomCenter>): void {
        const rooms = Array.from(s.rooms.values()).sort((a, b) => a.room_id - b.room_id);

        for (const r of rooms) {
            let g = this.roomGfx.get(r.room_id);
            if (!g) {
                g = new PIXI.Graphics();
                this.roomGfx.set(r.room_id, g);
                this.roomsLayer.addChild(g);
            }

            const center = centers.get(r.room_id) ?? { x: 0, y: 0 };
            this.drawRoom(g, r, center);
        }

        for (const id of Array.from(this.roomGfx.keys())) {
            if (!s.rooms.has(id)) {
                const g = this.roomGfx.get(id)!;
                g.destroy({ children: true });
                this.roomGfx.delete(id);
            }
        }
    }

    private drawRoom(g: PIXI.Graphics, r: KvpRoom, center: RoomCenter): void {
        g.clear();

        const occupants = r.occupants?.length ?? 0;
        const size = clamp(0.9 + occupants * 0.12, 0.8, 2.2);

        const p0 = isoProject({ x: center.x, y: center.y - size });
        const p1 = isoProject({ x: center.x + size, y: center.y });
        const p2 = isoProject({ x: center.x, y: center.y + size });
        const p3 = isoProject({ x: center.x - size, y: center.y });
        const pts = [p0.x, p0.y, p1.x, p1.y, p2.x, p2.y, p3.x, p3.y];

        const { fill, stroke } = roomColors(r.tension_tier);

        g.poly(pts, true);
        g.fill({ color: fill, alpha: 0.08 });
        g.stroke({ width: 2, color: stroke, alpha: r.highlight ? 0.9 : 0.45 });

        const halo = size * 1.5;
        const h0 = isoProject({ x: center.x, y: center.y - halo });
        const h1 = isoProject({ x: center.x + halo, y: center.y });
        const h2 = isoProject({ x: center.x, y: center.y + halo });
        const h3 = isoProject({ x: center.x - halo, y: center.y });
        const hpts = [h0.x, h0.y, h1.x, h1.y, h2.x, h2.y, h3.x, h3.y];
        g.poly(hpts, true);
        g.stroke({ width: 1, color: stroke, alpha: 0.18 });

        let label = g.getChildByName("label") as PIXI.Text | null;
        if (!label) {
            label = new PIXI.Text({
                text: r.label ?? `Room ${r.room_id}`,
                style: {
                    fontFamily: "Space Grotesk, sans-serif",
                    fontSize: 11,
                    fill: 0xffffff,
                    letterSpacing: 0.5,
                },
            });
            label.name = "label";
            g.addChild(label);
        }
        label.text = r.label ?? `Room ${r.room_id}`;
        label.x = p0.x + 6;
        label.y = p0.y - 20;
        label.alpha = 0.7;
    }

    /* --------------------------------------------------------------------------
     * Items
     * ------------------------------------------------------------------------ */

    private renderItems(s: WorldState, centers: Map<number, RoomCenter>): void {
        const items = Array.from(s.items.values()).sort((a, b) => a.item_id - b.item_id);

        for (const item of items) {
            let node = this.itemNodes.get(item.item_id);
            if (!node) {
                node = new PIXI.Graphics();
                this.itemNodes.set(item.item_id, node);
                this.itemsLayer.addChild(node);
            }
            this.drawItem(node, item, centers);
        }

        for (const id of Array.from(this.itemNodes.keys())) {
            if (!s.items.has(id)) {
                const node = this.itemNodes.get(id)!;
                node.destroy();
                this.itemNodes.delete(id);
            }
        }
    }

    private drawItem(node: PIXI.Graphics, item: KvpItem, centers: Map<number, RoomCenter>): void {
        node.clear();
        const center = centers.get(item.room_id) ?? { x: 0, y: 0 };
        const angle = (item.item_id * 2.3999632297) % (Math.PI * 2);
        const radius = 0.35;
        const pos = {
            x: center.x + Math.cos(angle) * radius,
            y: center.y + Math.sin(angle) * radius,
        };
        const p = isoProject(pos);

        node.circle(p.x, p.y, 2.2);
        node.fill({ color: PALETTE.neonAmber, alpha: 0.75 });
        node.stroke({ width: 1, color: PALETTE.neonMagenta, alpha: 0.35 });
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

            const p = isoProject({ x: a.transform.x, y: a.transform.y });
            node.x = p.x;
            node.y = p.y;

            const label = node.getChildByName("label") as PIXI.Text | null;
            if (label) label.text = `Agent ${a.agent_id}`;
        }

        for (const id of Array.from(this.agentNodes.keys())) {
            if (!s.agents.has(id)) {
                const node = this.agentNodes.get(id)!;
                node.destroy({ children: true });
                this.agentNodes.delete(id);
            }
        }
    }

    private makeAgentNode(a: KvpAgent): PIXI.Container {
        const c = new PIXI.Container();

        const color = agentColor(a);
        const ring = new PIXI.Graphics();
        ring.circle(0, 0, 6);
        ring.stroke({ width: 2, color, alpha: 0.85 });
        c.addChild(ring);

        const core = new PIXI.Graphics();
        core.circle(0, 0, 2.5);
        core.fill({ color: PALETTE.neonMint, alpha: 0.9 });
        c.addChild(core);

        const label = new PIXI.Text({
            text: `Agent ${a.agent_id}`,
            style: {
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 10,
                fill: 0xffffff,
            },
        });
        label.name = "label";
        label.x = 8;
        label.y = -18;
        label.alpha = 0.75;
        c.addChild(label);

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
                this.autoFitLocked = true;
                const delta = Math.sign(e.deltaY);
                const factor = delta > 0 ? 0.9 : 1.1;
                const next = clamp(this.camZoom * factor, 0.35, 3.2);
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
            this.autoFitLocked = true;
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

    private autoFitCameraIfNeeded(
        s: WorldState,
        spec: RenderSpec | undefined,
        centers: Map<number, RoomCenter>
    ): void {
        if (this.autoFitLocked) return;

        const bounds = getWorldBounds(spec);
        const key = `${bounds.min_x}:${bounds.min_y}:${bounds.max_x}:${bounds.max_y}:${this.lastIsoKey}`;
        if (key === this.lastAutoFitKey) return;
        this.lastAutoFitKey = key;

        const isoBounds = computeIsoBounds(bounds, centers, s.agents);
        const viewW = this.app.renderer.width;
        const viewH = this.app.renderer.height;
        if (viewW <= 0 || viewH <= 0) return;

        const pad = 0.12;
        const usableW = viewW * (1 - pad * 2);
        const usableH = viewH * (1 - pad * 2);

        const worldW = Math.max(1, isoBounds.max_x - isoBounds.min_x);
        const worldH = Math.max(1, isoBounds.max_y - isoBounds.min_y);
        const zoom = Math.min(usableW / worldW, usableH / worldH);

        const centerX = (isoBounds.min_x + isoBounds.max_x) * 0.5;
        const centerY = (isoBounds.min_y + isoBounds.max_y) * 0.5;

        const camX = Math.floor(viewW * 0.5 - centerX * zoom);
        const camY = Math.floor(viewH * 0.5 - centerY * zoom);

        this.setCamera({ x: camX, y: camY, zoom: clamp(zoom, 0.4, 3.5) });
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
        bg.fill({ color: PALETTE.ink, alpha: 0.92 });
        bg.stroke({ width: 1, color: PALETTE.neonMagenta, alpha: 0.4 });
        banner.addChild(bg);

        const txt = new PIXI.Text({
            text: `DESYNC\n${reason}\nClick to request fresh snapshot.`,
            style: {
                fontFamily: "JetBrains Mono, monospace",
                fontSize: 12,
                fill: 0xffffff,
                wordWrap: true,
                wordWrapWidth: 500,
            },
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

function getWorldBounds(spec?: RenderSpec): { min_x: number; min_y: number; max_x: number; max_y: number } {
    const b = spec?.coord_system?.bounds;
    if (b) {
        return { min_x: b.min_x, min_y: b.min_y, max_x: b.max_x, max_y: b.max_y };
    }
    return { min_x: 0, min_y: 0, max_x: 10, max_y: 6 };
}

function scatterPoint(seed: number, bounds: { min_x: number; min_y: number; max_x: number; max_y: number }): RoomCenter {
    const u = fract(Math.sin(seed * 12.9898) * 43758.5453);
    const v = fract(Math.sin((seed + 77) * 78.233) * 12345.678);
    const pad = 0.8;
    const x = lerp(bounds.min_x + pad, bounds.max_x - pad, u);
    const y = lerp(bounds.min_y + pad, bounds.max_y - pad, v);
    return { x, y };
}

function clampPoint(
    p: RoomCenter,
    bounds: { min_x: number; min_y: number; max_x: number; max_y: number }
): RoomCenter {
    return {
        x: clamp(p.x, bounds.min_x + 0.5, bounds.max_x - 0.5),
        y: clamp(p.y, bounds.min_y + 0.5, bounds.max_y - 0.5),
    };
}

function computeIsoBounds(
    bounds: { min_x: number; min_y: number; max_x: number; max_y: number },
    centers: Map<number, RoomCenter>,
    agents: Map<number, KvpAgent>
): { min_x: number; min_y: number; max_x: number; max_y: number } {
    const points: RoomCenter[] = [];

    points.push({ x: bounds.min_x, y: bounds.min_y });
    points.push({ x: bounds.min_x, y: bounds.max_y });
    points.push({ x: bounds.max_x, y: bounds.min_y });
    points.push({ x: bounds.max_x, y: bounds.max_y });

    for (const c of centers.values()) points.push(c);
    for (const a of agents.values()) points.push({ x: a.transform.x, y: a.transform.y });

    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    for (const p of points) {
        const iso = isoProject(p);
        minX = Math.min(minX, iso.x);
        minY = Math.min(minY, iso.y);
        maxX = Math.max(maxX, iso.x);
        maxY = Math.max(maxY, iso.y);
    }

    if (!Number.isFinite(minX)) {
        return { min_x: -50, min_y: -50, max_x: 50, max_y: 50 };
    }

    return { min_x: minX, min_y: minY, max_x: maxX, max_y: maxY };
}

function roomColors(tension: string): { fill: number; stroke: number } {
    switch (tension) {
        case "high":
            return { fill: PALETTE.neonMagenta, stroke: PALETTE.neonMagenta };
        case "medium":
            return { fill: PALETTE.neonAmber, stroke: PALETTE.neonAmber };
        default:
            return { fill: PALETTE.neonCyan, stroke: PALETTE.neonCyan };
    }
}

function agentColor(a: KvpAgent): number {
    switch (a.role_code % 4) {
        case 0:
            return PALETTE.neonCyan;
        case 1:
            return PALETTE.neonMagenta;
        case 2:
            return PALETTE.neonViolet;
        default:
            return PALETTE.neonAmber;
    }
}

function clamp(v: number, lo: number, hi: number): number {
    return Math.max(lo, Math.min(hi, v));
}

function lerp(a: number, b: number, t: number): number {
    return a + (b - a) * t;
}

function fract(v: number): number {
    return v - Math.floor(v);
}
