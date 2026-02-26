import * as PIXI from "pixi.js";
import type { SimSimAgent, SimSimRoom, SimSimViewerState } from "./simSimStore";

type Vec2 = { x: number; y: number };
type Bounds = { min_x: number; min_y: number; max_x: number; max_y: number };

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
    private readonly agentLayer = new PIXI.Container();
    private readonly uiLayer = new PIXI.Container();
    private lastState?: SimSimViewerState;

    constructor(mountEl: HTMLElement) {
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
        this.root.addChild(this.roomLayer, this.agentLayer, this.uiLayer);
        this.app.stage.addChild(this.root);
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
        this.lastState = state;

        this.roomLayer.removeChildren();
        this.agentLayer.removeChildren();
        this.uiLayer.removeChildren();

        const rooms = Array.from(state.rooms.values()).sort((a, b) => a.room_id - b.room_id);
        const stageBounds = this.computeStageBounds(rooms);
        const toScreen = this.makeProjector(stageBounds);

        for (const room of rooms) {
            this.drawRoom(room, toScreen);
        }

        const roomCenters = new Map<number, Vec2>();
        for (const room of rooms) {
            const b = this.roomBounds(room);
            roomCenters.set(room.room_id, toScreen((b.min_x + b.max_x) * 0.5, (b.min_y + b.max_y) * 0.5));
        }

        const agents = Array.from(state.agents.values()).sort((a, b) => a.agent_id - b.agent_id);
        for (const agent of agents) this.drawAgent(agent, roomCenters, toScreen);

        const events = Array.from(state.events.values()).sort((a, b) => (a.tick - b.tick) || (a.event_id - b.event_id));
        const eventLines = events.slice(-4).map((ev) => {
            const kind = (ev.payload?.kind as string | undefined) ?? "event";
            return `t${ev.tick} #${ev.event_id} ${kind}`;
        });
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

    private drawRoom(room: SimSimRoom, toScreen: (x: number, y: number) => Vec2): void {
        const b = this.roomBounds(room);
        const topLeft = toScreen(b.min_x, b.min_y);
        const bottomRight = toScreen(b.max_x, b.max_y);
        const width = Math.max(8, bottomRight.x - topLeft.x);
        const height = Math.max(8, bottomRight.y - topLeft.y);
        const locked = (room.zone ?? "").toLowerCase() === "locked";
        const fill = locked ? 0x402d2d : 0x223644;
        const line = locked ? 0xe89f8f : 0x8cd6c8;
        const rect = new PIXI.Graphics();
        rect.roundRect(topLeft.x, topLeft.y, width, height, 10);
        rect.fill({ color: fill, alpha: room.highlight ? 0.9 : 0.8 });
        rect.stroke({ width: room.highlight ? 3 : 2, color: line, alpha: 0.95 });
        this.roomLayer.addChild(rect);

        const label = new PIXI.Text({
            text: room.label ?? `Room ${room.room_id}`,
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
    }

    private drawAgent(agent: SimSimAgent, roomCenters: Map<number, Vec2>, toScreen: (x: number, y: number) => Vec2): void {
        const pos =
            agent.transform && Number.isFinite(agent.transform.x) && Number.isFinite(agent.transform.y)
                ? toScreen(agent.transform.x, agent.transform.y)
                : roomCenters.get(agent.room_id) ?? { x: 32, y: 32 };
        const color = 0xf3c76a;
        const node = new PIXI.Graphics();
        node.circle(pos.x, pos.y, 7);
        node.fill({ color, alpha: 0.98 });
        node.stroke({ width: 2, color: 0x1a2128, alpha: 0.95 });
        this.agentLayer.addChild(node);

        const label = new PIXI.Text({
            text: String(agent.agent_id),
            style: {
                fontFamily: "Chivo Mono, monospace",
                fontSize: 10,
                fill: 0x161b20,
            },
        });
        label.x = pos.x - label.width * 0.5;
        label.y = pos.y - 5;
        this.agentLayer.addChild(label);
    }

    private roomBounds(room: SimSimRoom): Bounds {
        if (room.bounds) return room.bounds;
        return FALLBACK_LAYOUT[room.room_id] ?? { min_x: 0, min_y: 0, max_x: 10, max_y: 6 };
    }
}
