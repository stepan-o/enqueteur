// src/render/pixiScene.ts
import * as PIXI from "pixi.js";
import type { KvpAgent, KvpItem, KvpObject, KvpRoom, RenderSpec, WorldState } from "../state/worldStore";
import type { UIOverlayEvent } from "../state/overlayStore";
import { isoProject, setIsoTileSize } from "./iso";
import { getObjectVisual, type ObjectPartSpec } from "./objectRegistry";

/**
 * PixiScene (WEBVIEW-0001)
 * -----------------------------------------------------------------------------
 * Render the viewer’s mirrored WorldState with a stylized industrial-illustration direction.
 * Viewer-only: no sim logic, no mutation of kernel state.
 */

const PALETTE = {
    paper: 0xf7f2e9,
    mist: 0xd8efe9,
    teal: 0x5aa9b2,
    sea: 0x6bc5c2,
    mint: 0x9dd7c7,
    coral: 0xf2a081,
    mustard: 0xf0c35a,
    lilac: 0xb7b9d9,
    slate: 0x3b4b5a,
    ink: 0x1f242b,
    shadow: 0x182128,
    grid: 0x2f3b47,
};

type RoomCenter = { x: number; y: number };
type RoomBounds = { min_x: number; min_y: number; max_x: number; max_y: number };
type AgentMotion = { current: RoomCenter; target: RoomCenter; facing: number };
type InspectSelection =
    | { kind: "room"; id: number }
    | { kind: "agent"; id: number }
    | { kind: "object"; id: number }
    | null;
const DEFAULT_WORLD_UNITS_PER_TILE = 20;
let worldUnitsPerTile = DEFAULT_WORLD_UNITS_PER_TILE;
let worldRotationQuarterTurns = 0;
let worldCenter: RoomCenter = { x: 0, y: 0 };

function resolveUnitsPerTile(spec?: RenderSpec): number {
    const units = spec?.coord_system?.units_per_tile;
    return Number.isFinite(units) && (units ?? 0) > 0 ? (units as number) : DEFAULT_WORLD_UNITS_PER_TILE;
}

function normalizeQuarterTurns(turns: number): number {
    const raw = Math.round(turns);
    return ((raw % 4) + 4) % 4;
}

export class PixiScene {
    public readonly app: PIXI.Application;

    private mountEl?: HTMLElement;
    private lastKnownWidth = 0;
    private lastKnownHeight = 0;
    private readonly root = new PIXI.Container();
    private readonly gridLayer = new PIXI.Container();
    private readonly pathsLayer = new PIXI.Container();
    private readonly roomsLayer = new PIXI.Container();
    private readonly objectsLayer = new PIXI.Container();
    private readonly itemsLayer = new PIXI.Container();
    private readonly agentsLayer = new PIXI.Container();
    private readonly overlayLayer = new PIXI.Container();
    private readonly uiLayer = new PIXI.Container();

    private readonly gridGfx = new PIXI.Graphics();
    private readonly pathsGfx = new PIXI.Graphics();
    private readonly roomGfx = new Map<number, PIXI.Graphics>();
    private readonly objectGfx = new Map<number, PIXI.Graphics>();
    private readonly agentNodes = new Map<number, PIXI.Container>();
    private readonly itemNodes = new Map<number, PIXI.Graphics>();
    private readonly agentMotion = new Map<number, AgentMotion>();
    private selectedRoomId?: number;
    private lastState?: WorldState;
    private lastCenters?: Map<number, RoomCenter>;
    private readonly roomBounds = new Map<number, RoomBounds>();
    private readonly roomFloors = new Map<number, number>();
    private readonly roomCutout = new Map<number, number>();
    private readonly roomCutoutTarget = new Map<number, number>();
    private readonly roomPings = new Map<number, number>();
    private readonly seenEventKeys = new Map<string, number>();
    private readonly seenOverlayKeys = new Set<string>();
    private readonly agentOverlayBubbles = new Map<number, OverlayBubble>();
    private readonly roomOverlayBubbles = new Map<number, OverlayBubble>();
    private isoTileW = 64;
    private isoTileH = 32;
    private floorFilter: "all" | 0 | 1 = 0;
    private viewRotation = 0;

    // Camera state
    private camX = 0;
    private camY = 0;
    private camZoom = 1;
    private cameraMode: "free" | "follow" | "auto" = "free";
    private followAgentId?: number;
    private autoDirectorRoomId?: number;
    private autoDirectorNextSwitch = 0;

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
    private inspectSelectionCb?: (sel: InspectSelection) => void;
    private lastRoomClickAt = 0;
    private lastRoomClickId?: number;

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

        // Layering
        this.root.addChild(
            this.gridLayer,
            this.pathsLayer,
            this.roomsLayer,
            this.objectsLayer,
            this.itemsLayer,
            this.agentsLayer,
            this.overlayLayer,
            this.uiLayer
        );
        this.app.stage.addChild(this.root);
        this.gridLayer.addChild(this.gridGfx);
        this.pathsLayer.addChild(this.pathsGfx);

        this.roomsLayer.sortableChildren = true;
        this.objectsLayer.sortableChildren = true;
        this.itemsLayer.sortableChildren = true;
        this.agentsLayer.sortableChildren = true;
        this.overlayLayer.sortableChildren = true;

        this.gridLayer.eventMode = "static";
        this.gridLayer.on("pointertap", () => {
            this.inspectSelectionCb?.(null);
        });

        this.recenterCamera();
        this.app.renderer.on("resize", () => this.recenterCamera());

        this.enableWheelZoom();
        this.enableDragPan();
        this.enableMotionTicker();

        this.ready = true;

        if (this.pendingState) {
            const s = this.pendingState;
            this.pendingState = undefined;
            this.renderFromState(s);
        }
    }

    /** Force Pixi to match the current container size, optionally re-auto-fit. */
    refreshLayout(opts?: { forceAutoFit?: boolean }): void {
        if (!this.ready || !this.mountEl) return;
        const rect = this.mountEl.getBoundingClientRect();
        const width = Math.max(1, Math.floor(rect.width));
        const height = Math.max(1, Math.floor(rect.height));
        if (width !== this.lastKnownWidth || height !== this.lastKnownHeight) {
            this.lastKnownWidth = width;
            this.lastKnownHeight = height;
            this.app.renderer.resize(width, height);
        }
        this.recenterCamera();
        if (opts?.forceAutoFit) {
            this.autoFitLocked = false;
            this.lastAutoFitKey = "";
        }
        if (this.lastState) this.renderFromState(this.lastState);
    }

    /** Hook: used by boot.ts to wire the desync banner click. */
    onRequestFreshSnapshot(cb: () => void): void {
        this.requestFreshSnapshotCb = cb;
    }

    onInspectSelection(cb: (sel: InspectSelection) => void): void {
        this.inspectSelectionCb = cb;
    }

    setFloorFilter(filter: "all" | 0 | 1): void {
        this.floorFilter = filter;
        if (this.selectedRoomId !== undefined && !isRoomVisible(this.selectedRoomId, this.roomFloors, filter)) {
            this.selectedRoomId = undefined;
        }
        if (this.lastState) this.renderFromState(this.lastState);
    }

    ingestOverlayEvents(events: UIOverlayEvent[]): void {
        if (!events || events.length === 0) return;
        const now = performance.now();
        for (const ev of events) {
            const key = `${ev.tick}:${ev.event_id}:${ev.kind}`;
            if (this.seenOverlayKeys.has(key)) continue;
            this.seenOverlayKeys.add(key);

            const roomId = getRecordNumber(ev.data, "room_id");
            const agentId = getRecordNumber(ev.data, "agent_id");
            const type = overlayBubbleType(ev.kind);
            const text = overlayBubbleText(ev);

            if (agentId !== null) {
                this.spawnAgentBubble(agentId, text, type, now);
            } else if (roomId !== null) {
                this.spawnRoomBubble(roomId, text, type, now);
            }
        }
    }

    setCameraMode(mode: "free" | "auto"): void {
        if (mode === "free") {
            this.cameraMode = "free";
            this.followAgentId = undefined;
            return;
        }
        this.cameraMode = "auto";
        this.autoDirectorNextSwitch = 0;
        this.autoFitLocked = true;
    }

    private recenterCamera(): void {
        this.setCamera({
            x: Math.floor(this.app.renderer.width * 0.5),
            y: Math.floor(this.app.renderer.height * 0.45),
            zoom: this.camZoom,
        });
    }

    setViewRotation(turns: number): void {
        const next = normalizeQuarterTurns(turns);
        if (next === this.viewRotation) return;
        this.viewRotation = next;
        worldRotationQuarterTurns = next;
        this.lastGridKey = "";
        this.lastLayoutKey = "";
        this.lastAutoFitKey = "";
        this.lastIsoKey = "";
        if (this.lastState) this.renderFromState(this.lastState);
    }

    rotateView(deltaQuarterTurns: number): void {
        this.setViewRotation(this.viewRotation + deltaQuarterTurns);
    }

    followAgent(agentId?: number): void {
        if (!agentId) {
            if (this.cameraMode === "follow") this.cameraMode = "free";
            this.followAgentId = undefined;
            return;
        }
        this.cameraMode = "follow";
        this.followAgentId = agentId;
        this.autoFitLocked = true;
    }

    /** Main render entry (called from WorldStore subscription). */
    renderFromState(s: WorldState): void {
        if (!this.ready) {
            this.pendingState = s;
            return;
        }
        this.lastState = s;

        if (s.desynced) {
            this.showDesyncBanner(s.desyncReason ?? "Desync detected");
            return;
        } else {
            this.hideDesyncBanner();
        }

        if (this.selectedRoomId !== undefined) {
            this.setSelectedRoom(this.selectedRoomId);
        }

        this.applyRenderSpec(s.renderSpec);
        this.renderFloor(s.renderSpec);

        this.applyEventPings(s);

        const roomCenters = this.ensureRoomLayout(s, s.renderSpec);
        this.lastCenters = roomCenters;
        this.autoFitCameraIfNeeded(s, s.renderSpec, roomCenters);
        this.renderPaths(s, roomCenters);
        this.renderRooms(s, roomCenters);
        this.renderObjects(s);
        // Items are intentionally hidden for now (visual clarity).
        this.clearItems();
        this.renderAgents(s);
    }

    /* --------------------------------------------------------------------------
     * RenderSpec / Floor
     * ------------------------------------------------------------------------ */

    private applyRenderSpec(spec?: RenderSpec): void {
        const bounds = getWorldBounds(spec);
        worldCenter = {
            x: (bounds.min_x + bounds.max_x) * 0.5,
            y: (bounds.min_y + bounds.max_y) * 0.5,
        };
        const iso = spec?.projection;
        const nextUnits = resolveUnitsPerTile(spec);
        const isoKey = `${iso?.recommended_iso_tile_w ?? 64}x${iso?.recommended_iso_tile_h ?? 32}@${nextUnits}:r${this.viewRotation}`;
        if (isoKey !== this.lastIsoKey) {
            this.lastIsoKey = isoKey;
            this.isoTileW = iso?.recommended_iso_tile_w ?? 64;
            this.isoTileH = iso?.recommended_iso_tile_h ?? 32;
            setIsoTileSize(this.isoTileW, this.isoTileH);
            worldUnitsPerTile = nextUnits;
            this.lastGridKey = "";
            this.lastLayoutKey = "";
            this.lastAutoFitKey = "";
        }
    }

    private renderFloor(spec?: RenderSpec): void {
        const bounds = getWorldBounds(spec);
        const key = `${bounds.min_x}:${bounds.min_y}:${bounds.max_x}:${bounds.max_y}:${this.lastIsoKey}`;
        if (key === this.lastGridKey) return;
        this.lastGridKey = key;

        const g = this.gridGfx;
        g.clear();

        const base = isoRect(bounds);
        g.poly(base, true);
        g.fill({ color: PALETTE.paper, alpha: 0.85 });
        g.stroke({ width: 2, color: PALETTE.ink, alpha: 0.15 });

        // Large city-block grid (lighter than the old blueprint)
        const step = Math.max(1, worldUnitsPerTile);
        const color = PALETTE.grid;
        const alpha = 0.18;

        for (let x = Math.floor(bounds.min_x); x <= Math.ceil(bounds.max_x); x += step) {
            const p0 = isoProjectWorld({ x, y: bounds.min_y });
            const p1 = isoProjectWorld({ x, y: bounds.max_y });
            g.moveTo(p0.x, p0.y);
            g.lineTo(p1.x, p1.y);
        }

        for (let y = Math.floor(bounds.min_y); y <= Math.ceil(bounds.max_y); y += step) {
            const p0 = isoProjectWorld({ x: bounds.min_x, y });
            const p1 = isoProjectWorld({ x: bounds.max_x, y });
            g.moveTo(p0.x, p0.y);
            g.lineTo(p1.x, p1.y);
        }

        g.stroke({ width: 1, color, alpha });

        // Subtle diagonal hatch for texture
        drawIsoHatch(g, bounds, 28, PALETTE.slate, 0.08);
    }


    private setSelectedRoom(roomId: number | undefined): void {
        this.selectedRoomId = roomId;
        if (this.lastState) {
            for (const r of this.lastState.rooms.values()) {
                this.roomCutoutTarget.set(r.room_id, roomId === r.room_id ? 1 : 0);
            }
        }
    }

    private isRoomFocused(roomId: number): boolean {
        if (this.selectedRoomId !== roomId) return false;
        const open = this.roomCutout.get(roomId) ?? 0;
        return open > 0.45;
    }

    private handleRoomTap(roomId: number): void {
        const now = performance.now();
        const isDouble =
            this.lastRoomClickId === roomId && now - this.lastRoomClickAt > 0 && now - this.lastRoomClickAt < 320;
        this.lastRoomClickAt = now;
        this.lastRoomClickId = roomId;
        if (!isDouble) return;

        if (this.selectedRoomId === roomId) {
            this.exitRoomFocus();
        } else {
            this.focusRoom(roomId);
        }
    }

    private focusRoom(roomId: number): void {
        this.setSelectedRoom(roomId);
        this.cameraMode = "free";
        this.followAgentId = undefined;
        this.autoFitLocked = true;

        const room = this.lastState?.rooms.get(roomId);
        const rb = room ? this.roomBounds.get(roomId) ?? roomBoundsFromRoom(room) : null;
        if (!rb) return;
        const center = boundsCenter(rb);
        const map = new Map<number, RoomBounds>();
        map.set(roomId, rb);
        const centers = new Map<number, RoomCenter>();
        centers.set(roomId, center);
        const isoBounds = computeIsoBounds(rb, centers, map, []);
        const viewW = this.app.renderer.width;
        const viewH = this.app.renderer.height;
        if (viewW <= 0 || viewH <= 0) return;
        const pad = 0.16;
        const usableW = viewW * (1 - pad * 2);
        const usableH = viewH * (1 - pad * 2);
        const worldW = Math.max(1, isoBounds.max_x - isoBounds.min_x);
        const worldH = Math.max(1, isoBounds.max_y - isoBounds.min_y);
        const zoom = clamp(Math.min(usableW / worldW, usableH / worldH), 0.6, 6);
        const centerX = (isoBounds.min_x + isoBounds.max_x) * 0.5;
        const centerY = (isoBounds.min_y + isoBounds.max_y) * 0.5;
        const camX = Math.floor(viewW * 0.5 - centerX * zoom);
        const camY = Math.floor(viewH * 0.5 - centerY * zoom);
        this.setCamera({ x: camX, y: camY, zoom });
        this.inspectSelectionCb?.({ kind: "room", id: roomId });
    }

    private exitRoomFocus(): void {
        this.setSelectedRoom(undefined);
        this.autoFitLocked = false;
        this.lastAutoFitKey = "";
        this.inspectSelectionCb?.(null);
        if (this.lastState && this.lastCenters) {
            this.autoFitCameraIfNeeded(this.lastState, this.lastState.renderSpec, this.lastCenters);
        }
    }

    /* --------------------------------------------------------------------------
     * Rooms
     * ------------------------------------------------------------------------ */

    private renderPaths(s: WorldState, centers: Map<number, RoomCenter>): void {
        const g = this.pathsGfx;
        g.clear();

        const pairs = new Set<string>();
        for (const r of s.rooms.values()) {
            if (!isRoomVisible(r.room_id, this.roomFloors, this.floorFilter)) continue;
            for (const n of r.neighbors ?? []) {
                const a = Math.min(r.room_id, n);
                const b = Math.max(r.room_id, n);
                pairs.add(`${a}:${b}`);
            }
        }

        for (const key of pairs) {
            const [aStr, bStr] = key.split(":");
            const aId = Number(aStr);
            const bId = Number(bStr);
            const a = centers.get(aId);
            const b = centers.get(bId);
            if (!a || !b) continue;
            if (!isRoomVisible(aId, this.roomFloors, this.floorFilter)) continue;
            if (!isRoomVisible(bId, this.roomFloors, this.floorFilter)) continue;
            const ra = s.rooms.get(aId);
            const rb = s.rooms.get(bId);
            const floorA = this.roomFloors.get(aId) ?? 0;
            const floorB = this.roomFloors.get(bId) ?? 0;
            if (floorA !== floorB && !isElevatorRoom(ra) && !isElevatorRoom(rb)) {
                continue;
            }
            const ba = this.roomBounds.get(aId) ?? null;
            const bb = this.roomBounds.get(bId) ?? null;
            const aEdge = ba ? rectEdgePoint(ba, b) : a;
            const bEdge = bb ? rectEdgePoint(bb, a) : b;
            const p0 = isoProjectWorld(aEdge);
            const p1 = isoProjectWorld(bEdge);
            g.moveTo(p0.x, p0.y);
            g.lineTo(p1.x, p1.y);
        }

        g.stroke({ width: 6, color: PALETTE.paper, alpha: 0.22 });
        g.stroke({ width: 2, color: PALETTE.slate, alpha: 0.4 });
    }

    private ensureRoomLayout(s: WorldState, spec?: RenderSpec): Map<number, RoomCenter> {
        const bounds = getWorldBounds(spec);
        const roomSig = Array.from(s.rooms.values())
            .map((r) => `${r.room_id}:${r.label ?? ""}:${r.zone ?? ""}:${r.level ?? ""}:${r.bounds ? "b" : "n"}`)
            .sort()
            .join("|");
        const key = `${roomSig}|${bounds.min_x}:${bounds.min_y}:${bounds.max_x}:${bounds.max_y}`;

        if (key === this.lastLayoutKey && this.roomLayout.size > 0) {
            return this.roomLayout;
        }

        const rooms = Array.from(s.rooms.values());
        const hasBounds = rooms.length > 0 && rooms.every((r) => !!r.bounds);
        const centers = new Map<number, RoomCenter>();
        this.roomBounds.clear();
        this.roomFloors.clear();

        if (hasBounds) {
            for (const r of rooms) {
                const rb = roomBoundsFromRoom(r)!;
                this.roomBounds.set(r.room_id, rb);
                centers.set(r.room_id, boundsCenter(rb));
                this.roomFloors.set(r.room_id, r.level ?? 0);
            }
        } else {
            const layout = buildTileLayout(rooms, bounds);
            for (const [id, rb] of layout.boundsById.entries()) {
                this.roomBounds.set(id, rb);
                centers.set(id, boundsCenter(rb));
            }
            for (const [id, floor] of layout.floorById.entries()) {
                this.roomFloors.set(id, floor);
            }
        }

        // Initialize cutout state
        for (const r of s.rooms.values()) {
            if (!this.roomCutout.has(r.room_id)) {
                this.roomCutout.set(r.room_id, 0);
                this.roomCutoutTarget.set(r.room_id, 0);
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
            if (!isRoomVisible(r.room_id, this.roomFloors, this.floorFilter)) {
                const existing = this.roomGfx.get(r.room_id);
                if (existing) existing.visible = false;
                continue;
            }
            let g = this.roomGfx.get(r.room_id);
            if (!g) {
                g = new PIXI.Graphics();
                this.roomGfx.set(r.room_id, g);
                this.roomsLayer.addChild(g);
                g.eventMode = "static";
                g.cursor = "pointer";
                g.on("pointertap", (ev) => {
                    ev.stopPropagation();
                    this.handleRoomTap(r.room_id);
                });
            }

            const center = centers.get(r.room_id) ?? { x: 0, y: 0 };
            const rb = this.roomBounds.get(r.room_id) ?? roomBoundsFromRoom(r) ?? boundsFromCenter(center, 2);
            const floor = this.roomFloors.get(r.room_id) ?? 0;
            const cutout = this.roomCutout.get(r.room_id) ?? 0;
            this.drawRoom(g, r, center, rb, floor, cutout);
            g.visible = true;
            g.zIndex = isoProjectWorld(center).y;

            const hit = isoRectPoints(rb, 0, floorElevationPx(floor, this.isoTileH));
            g.hitArea = new PIXI.Polygon(pointsToArray(hit));
        }

        for (const id of Array.from(this.roomGfx.keys())) {
            if (!s.rooms.has(id)) {
                const g = this.roomGfx.get(id)!;
                g.destroy({ children: true });
                this.roomGfx.delete(id);
            }
        }
    }

    private renderObjects(s: WorldState): void {
        const objects = Array.from(s.objects.values()).sort((a, b) => a.object_id - b.object_id);
        const focusedRoom = this.selectedRoomId;
        const focusOpen = focusedRoom !== undefined && this.isRoomFocused(focusedRoom);
        for (const obj of objects) {
            if (!isRoomVisible(obj.room_id, this.roomFloors, this.floorFilter)) {
                const existing = this.objectGfx.get(obj.object_id);
                if (existing) existing.visible = false;
                continue;
            }
            if (!focusOpen || focusedRoom !== obj.room_id) {
                const existing = this.objectGfx.get(obj.object_id);
                if (existing) existing.visible = false;
                continue;
            }
            const room = s.rooms.get(obj.room_id);
            const rb = room ? roomBoundsFromRoom(room) : null;
            if (!room || !rb) {
                const existing = this.objectGfx.get(obj.object_id);
                if (existing) existing.visible = false;
                continue;
            }

            let g = this.objectGfx.get(obj.object_id);
            if (!g) {
                g = new PIXI.Graphics();
                this.objectGfx.set(obj.object_id, g);
                this.objectsLayer.addChild(g);
                g.eventMode = "static";
                g.cursor = "pointer";
                g.on("pointertap", (ev) => {
                    ev.stopPropagation();
                    const currentRoom = this.lastState?.objects.get(obj.object_id)?.room_id ?? obj.room_id;
                    if (!this.isRoomFocused(currentRoom)) return;
                    this.inspectSelectionCb?.({ kind: "object", id: obj.object_id });
                });
            }

            const floor = this.roomFloors.get(obj.room_id) ?? 0;
            const center = objectWorldCenter(obj, rb);
            this.drawObject(g, obj, room, rb, floor);
            g.visible = true;
            g.zIndex = isoProjectWorld(center).y;
        }

        for (const id of Array.from(this.objectGfx.keys())) {
            if (!s.objects.has(id)) {
                const g = this.objectGfx.get(id)!;
                g.destroy({ children: true });
                this.objectGfx.delete(id);
            }
        }
    }

    private drawObject(
        g: PIXI.Graphics,
        obj: KvpObject,
        room: KvpRoom,
        rb: RoomBounds,
        floor: number
    ): void {
        g.clear();
        const visual = getObjectVisual(obj.class_code);
        const parts = visual?.parts ?? [
            {
                shape: "box",
                size: { w: Math.max(1, obj.size_w), h: Math.max(1, obj.size_h), z: Math.max(0.5, obj.height ?? 1) },
                color: 0xb6c4c3,
            },
        ];
        const baseCenter = objectWorldCenter(obj, rb);
        const turns = normalizeQuarterTurns(obj.orientation ?? 0);
        const scale = obj.scale && obj.scale > 0 ? obj.scale : 1.0;
        const footprint = visual?.footprint ?? { w: obj.size_w, h: obj.size_h };
        const scaleX = scale * (obj.size_w / Math.max(0.001, footprint.w));
        const scaleY = scale * (obj.size_h / Math.max(0.001, footprint.h));
        let scaleZ = scale;
        if (obj.height && visual?.height_ref && visual.height_ref > 0) {
            scaleZ = (obj.height / visual.height_ref) * scale;
        }
        const elevBase = floorElevationPx(floor, this.isoTileH);

        for (const part of parts) {
            drawObjectPart(
                g,
                part,
                baseCenter,
                turns,
                scaleX,
                scaleY,
                scaleZ,
                elevBase,
                this.isoTileH
            );
        }
    }

    private applyEventPings(s: WorldState): void {
        const pruneBefore = s.tick - 600;
        for (const [key, tick] of this.seenEventKeys.entries()) {
            if (tick < pruneBefore) this.seenEventKeys.delete(key);
        }

        for (const [key, ev] of s.events.entries()) {
            if (this.seenEventKeys.has(key)) continue;
            this.seenEventKeys.set(key, ev.tick);
            const roomId = extractRoomIdFromEvent(ev);
            if (roomId !== null) this.roomPings.set(roomId, 1);
        }
    }

    private drawRoom(
        g: PIXI.Graphics,
        r: KvpRoom,
        center: RoomCenter,
        rb: RoomBounds,
        floor: number,
        cutout: number
    ): void {
        g.clear();

        const height = roomHeightPx(r, this.isoTileH);
        const colors = roomColors(r);
        const elev = floorElevationPx(floor, this.isoTileH);
        const ping = this.roomPings.get(r.room_id) ?? 0;
        const pulse = tensionPulse(r);

        const base = isoRectPoints(rb, 0, elev);
        const top = isoRectPoints(rb, height, elev);

        // Base shadow (grounding)
        g.poly(pointsToArray(base), true);
        g.fill({ color: PALETTE.shadow, alpha: 0.1 });

        const open = clamp(cutout, 0, 1);
        const outdoor = isOutdoorRoom(r);
        const wallAlphaA = outdoor ? 0.0 : lerp(0.82, 0.12, open);
        const wallAlphaB = outdoor ? 0.0 : lerp(0.85, 0.12, open);
        const roofAlpha = outdoor ? 0.0 : lerp(0.95, 0.4, open);
        const floorAlpha = outdoor ? 0.9 : lerp(0.0, 0.9, open);
        const cutHeight = height * (1 - open * 0.8);
        const wallTop = isoRectPoints(rb, cutHeight, elev);

        // Right face (east)
        g.poly(pointsToArray([base[1], base[2], wallTop[2], wallTop[1]]), true);
        g.fill({ color: colors.sideA, alpha: wallAlphaA });

        // Left face (south)
        g.poly(pointsToArray([base[2], base[3], wallTop[3], wallTop[2]]), true);
        g.fill({ color: colors.sideB, alpha: wallAlphaB });

        // Top face
        g.poly(pointsToArray(top), true);
        g.fill({ color: colors.top, alpha: roofAlpha });

        if (pulse > 0.01) {
            g.poly(pointsToArray(top), true);
            g.fill({ color: colors.glow, alpha: pulse * 0.22 });
        }

        // Outline
        g.stroke({ width: 2, color: colors.stroke, alpha: r.highlight ? 0.95 : 0.7 });

        // Subtle hatch texture (roof)
        if (!outdoor) {
            drawRoomHatch(g, top, colors.stroke);
        }

        // Interior floor on selection
        if (floorAlpha > 0.01) {
            g.poly(pointsToArray(base), true);
            g.fill({ color: colors.floor, alpha: floorAlpha });
            drawRoomHatch(g, base, colors.stroke);
        }

        if (r.highlight) {
            g.poly(pointsToArray(top), true);
            g.stroke({ width: 2, color: colors.glow, alpha: 0.35 });
        }

        if (ping > 0.01) {
            const pingAlpha = clamp(ping, 0, 1) * 0.65;
            g.poly(pointsToArray(top), true);
            g.stroke({ width: 3, color: colors.glow, alpha: pingAlpha });
            g.poly(pointsToArray(base), true);
            g.stroke({ width: 2, color: colors.glow, alpha: pingAlpha * 0.7 });
        }

        let label = g.getChildByName("label") as PIXI.Text | null;
        if (!label) {
            label = new PIXI.Text({
                text: r.label ?? `Room ${r.room_id}`,
                style: {
                    fontFamily: "Bricolage Grotesque, Space Grotesk, sans-serif",
                    fontSize: 12,
                    fill: 0x1f242b,
                    letterSpacing: 0.2,
                },
            });
            label.name = "label";
            g.addChild(label);
        }
        label.text = r.label ?? `Room ${r.room_id}`;
        const topCenter = centerOfPoints(top);
        label.x = topCenter.x - label.width * 0.5;
        label.y = open > 0.5 ? topCenter.y + 6 : topCenter.y - 14;
        label.alpha = 0.85;
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
            this.drawItem(node, item, centers, this.roomBounds);
        }

        for (const id of Array.from(this.itemNodes.keys())) {
            if (!s.items.has(id)) {
                const node = this.itemNodes.get(id)!;
                node.destroy();
                this.itemNodes.delete(id);
            }
        }
    }

    private clearItems(): void {
        for (const id of Array.from(this.itemNodes.keys())) {
            const node = this.itemNodes.get(id)!;
            node.destroy();
            this.itemNodes.delete(id);
        }
    }

    private drawItem(
        node: PIXI.Graphics,
        item: KvpItem,
        centers: Map<number, RoomCenter>,
        rooms: Map<number, KvpRoom>
    ): void {
        node.clear();
        const pos = resolveItemWorldPos(item, rooms, centers);
        const size = 0.6;
        const rb = boundsFromCenter(pos, size);
        const top = isoRectPoints(rb, 6, 0);
        const base = isoRectPoints(rb, 0, 0);

        node.zIndex = top[2].y;

        node.poly(pointsToArray([base[1], base[2], top[2], top[1]]), true);
        node.fill({ color: PALETTE.mint, alpha: 0.9 });
        node.poly(pointsToArray([base[2], base[3], top[3], top[2]]), true);
        node.fill({ color: PALETTE.teal, alpha: 0.85 });
        node.poly(pointsToArray(top), true);
        node.fill({ color: PALETTE.paper, alpha: 0.95 });
        node.stroke({ width: 1.4, color: PALETTE.ink, alpha: 0.65 });
    }

    /* --------------------------------------------------------------------------
     * Agents
     * ------------------------------------------------------------------------ */

    private renderAgents(s: WorldState): void {
        const agents = Array.from(s.agents.values()).sort((a, b) => a.agent_id - b.agent_id);
        const localExtents = computeLocalExtents(agents, this.roomBounds);
        const focusedRoom = this.selectedRoomId;
        const focusOpen = focusedRoom !== undefined && this.isRoomFocused(focusedRoom);

        for (const a of agents) {
            if (!isRoomVisible(a.room_id, this.roomFloors, this.floorFilter)) {
                const existing = this.agentNodes.get(a.agent_id);
                if (existing) existing.visible = false;
                continue;
            }
            let node = this.agentNodes.get(a.agent_id);
            if (!node) {
                node = this.makeAgentNode(a);
                node.eventMode = "static";
                node.cursor = "pointer";
                node.on("pointertap", (ev) => {
                    ev.stopPropagation();
                    const agentId = a.agent_id;
                    const currentRoom = this.lastState?.agents.get(agentId)?.room_id ?? a.room_id;
                    if (this.isRoomFocused(currentRoom)) {
                        this.inspectSelectionCb?.({ kind: "agent", id: agentId });
                        return;
                    }
                    const next = this.followAgentId === agentId ? undefined : agentId;
                    this.followAgent(next);
                });
                this.agentNodes.set(a.agent_id, node);
                this.agentsLayer.addChild(node);
            }

            const target = resolveAgentWorldPos(a, this.roomBounds, localExtents);
            const motion = this.agentMotion.get(a.agent_id);
            if (!motion) {
                this.agentMotion.set(a.agent_id, { current: { ...target }, target, facing: 0 });
            } else {
                motion.target = target;
            }

            const label = node.getChildByName("label") as PIXI.Text | null;
            if (label) label.text = `Agent ${a.agent_id}`;

            this.updateAgentSignals(node, a);
            node.visible = true;

            if (focusOpen && a.room_id === focusedRoom) {
                node.eventMode = "static";
                node.cursor = "pointer";
            } else if (focusOpen) {
                node.eventMode = "none";
                node.cursor = "default";
            } else {
                node.eventMode = "static";
                node.cursor = "pointer";
            }
        }

        for (const id of Array.from(this.agentNodes.keys())) {
            if (!s.agents.has(id)) {
                const node = this.agentNodes.get(id)!;
                node.destroy({ children: true });
                this.agentNodes.delete(id);
                this.agentMotion.delete(id);
            }
        }
    }

    private updateAgentSignals(node: PIXI.Container, a: KvpAgent): void {
        const ring = node.getChildByName("moodRing") as PIXI.Graphics | null;
        if (ring) {
            const color = agentMoodColor(a);
            ring.clear();
            ring.ellipse(0, 8, 11, 5);
            ring.stroke({ width: 2, color, alpha: 0.5 });
        }

        const bubble = node.getChildByName("bubble") as PIXI.Graphics | null;
        if (bubble) {
            bubble.visible = agentIsSpeaking(a);
        }
    }

    private makeAgentNode(a: KvpAgent): PIXI.Container {
        const c = new PIXI.Container();

        const color = agentColor(a);
        const ring = new PIXI.Graphics();
        ring.name = "moodRing";
        ring.ellipse(0, 8, 11, 5);
        ring.stroke({ width: 2, color: color, alpha: 0.45 });
        c.addChild(ring);

        const body = new PIXI.Graphics();
        body.roundRect(-6, -10, 12, 20, 5);
        body.fill({ color, alpha: 0.95 });
        body.stroke({ width: 2, color: PALETTE.ink, alpha: 0.85 });
        c.addChild(body);

        const visor = new PIXI.Graphics();
        visor.roundRect(-4.5, -3, 9, 5, 2);
        visor.fill({ color: PALETTE.paper, alpha: 0.9 });
        visor.stroke({ width: 1, color: PALETTE.ink, alpha: 0.7 });
        c.addChild(visor);

        const facing = new PIXI.Graphics();
        facing.name = "facing";
        facing.poly([-2, -12, 2, -12, 0, -18], true);
        facing.fill({ color: PALETTE.ink, alpha: 0.8 });
        c.addChild(facing);

        const label = new PIXI.Text({
            text: `Agent ${a.agent_id}`,
            style: {
                fontFamily: "Chivo Mono, JetBrains Mono, monospace",
                fontSize: 10,
                fill: 0x1f242b,
            },
        });
        label.name = "label";
        label.x = 8;
        label.y = -22;
        label.alpha = 0.85;
        c.addChild(label);

        const bubble = new PIXI.Graphics();
        bubble.name = "bubble";
        bubble.roundRect(6, -34, 14, 10, 4);
        bubble.fill({ color: PALETTE.paper, alpha: 0.9 });
        bubble.stroke({ width: 1, color: PALETTE.ink, alpha: 0.6 });
        bubble.poly([10, -24, 12, -18, 8, -22], true);
        bubble.fill({ color: PALETTE.paper, alpha: 0.9 });
        bubble.visible = false;
        c.addChild(bubble);

        return c;
    }

    /* --------------------------------------------------------------------------
     * Camera controls (basic)
     * ------------------------------------------------------------------------ */

    private enableMotionTicker(): void {
        this.app.ticker.add((t) => {
            const dt = Math.max(1, t.deltaMS);
            this.tickAgentMotion(dt);
            this.tickRoomCutout(dt);
            this.tickRoomPings(dt);
            this.tickCameraDirector(dt);
            this.tickOverlayBubbles(dt);
        });
    }

    private tickAgentMotion(dtMs: number): void {
        if (this.agentMotion.size === 0) return;

        const smooth = 1 - Math.exp(-dtMs / 120);

        for (const [id, motion] of this.agentMotion.entries()) {
            const dx = motion.target.x - motion.current.x;
            const dy = motion.target.y - motion.current.y;
            motion.current.x += dx * smooth;
            motion.current.y += dy * smooth;

            if (Math.abs(dx) + Math.abs(dy) > 0.001) {
                motion.facing = Math.atan2(dy, dx);
            }

            const node = this.agentNodes.get(id);
            if (!node) continue;

            const p = isoProjectWorld(motion.current);
            const bob = Math.sin(performance.now() * 0.004 + id) * 1.2;
            node.x = p.x;
            node.y = p.y - 6 + bob;
            node.zIndex = node.y;

            const facing = node.getChildByName("facing") as PIXI.Graphics | null;
            if (facing) facing.rotation = motion.facing + Math.PI / 2;
        }
    }

    private tickRoomCutout(dtMs: number): void {
        if (this.roomCutout.size === 0) return;
        const smooth = 1 - Math.exp(-dtMs / 180);
        let changed = false;

        for (const [id, current] of this.roomCutout.entries()) {
            const target = this.roomCutoutTarget.get(id) ?? 0;
            const next = current + (target - current) * smooth;
            if (Math.abs(next - current) > 0.001) changed = true;
            this.roomCutout.set(id, next);
        }

        if (changed && this.lastState && this.lastCenters) {
            this.renderRooms(this.lastState, this.lastCenters);
        }
    }

    private tickRoomPings(dtMs: number): void {
        if (this.roomPings.size === 0) return;
        const decay = Math.exp(-dtMs / 700);
        let changed = false;

        for (const [id, current] of this.roomPings.entries()) {
            const next = current * decay;
            if (next < 0.02) {
                this.roomPings.delete(id);
                changed = true;
                continue;
            }
            if (Math.abs(next - current) > 0.002) changed = true;
            this.roomPings.set(id, next);
        }

        if (changed && this.lastState && this.lastCenters) {
            this.renderRooms(this.lastState, this.lastCenters);
        }
    }

    private tickOverlayBubbles(dtMs: number): void {
        void dtMs;
        if (this.agentOverlayBubbles.size === 0 && this.roomOverlayBubbles.size === 0) return;
        const now = performance.now();
        this.tickAgentBubbles(now);
        this.tickRoomBubbles(now);
    }

    private tickAgentBubbles(now: number): void {
        for (const [agentId, bubble] of this.agentOverlayBubbles.entries()) {
            const node = bubble.node;
            const pos = this.getAgentWorldPos(agentId);
            if (pos) {
                const iso = isoProjectWorld(pos);
                node.x = iso.x + 10;
                node.y = iso.y - 38;
                node.zIndex = node.y;
                node.visible = true;
            } else {
                node.visible = false;
            }
            const life = bubble.expiresAt - now;
            if (life <= 0) {
                node.destroy({ children: true });
                this.agentOverlayBubbles.delete(agentId);
                continue;
            }
            const alpha = Math.min(1, life / 2200);
            node.alpha = alpha;
        }
    }

    private tickRoomBubbles(now: number): void {
        for (const [roomId, bubble] of this.roomOverlayBubbles.entries()) {
            const node = bubble.node;
            const rb = this.roomBounds.get(roomId);
            const floor = this.roomFloors.get(roomId) ?? 0;
            const room = this.lastState?.rooms.get(roomId);
            if (rb && room) {
                const height = roomHeightPx(room, this.isoTileH);
                const topCenter = roomTopCenter(rb, floor, height, this.isoTileH);
                node.x = topCenter.x - node.width * 0.5;
                node.y = topCenter.y - 34;
                node.zIndex = node.y;
                node.visible = isRoomVisible(roomId, this.roomFloors, this.floorFilter);
            } else {
                node.visible = false;
            }
            const life = bubble.expiresAt - now;
            if (life <= 0) {
                node.destroy({ children: true });
                this.roomOverlayBubbles.delete(roomId);
                continue;
            }
            const alpha = Math.min(1, life / 2400);
            node.alpha = alpha;
        }
    }

    private spawnAgentBubble(agentId: number, text: string, type: OverlayBubbleType, now: number): void {
        const bubble = this.agentOverlayBubbles.get(agentId);
        if (bubble) {
            bubble.expiresAt = now + 2400;
            const label = bubble.node.getChildByName("label") as PIXI.Text | null;
            if (label) label.text = text;
            return;
        }
        const node = makeOverlayBubble(text, type);
        node.zIndex = 9999;
        this.overlayLayer.addChild(node);
        this.agentOverlayBubbles.set(agentId, { node, expiresAt: now + 2400 });
    }

    private spawnRoomBubble(roomId: number, text: string, type: OverlayBubbleType, now: number): void {
        const bubble = this.roomOverlayBubbles.get(roomId);
        if (bubble) {
            bubble.expiresAt = now + 2600;
            const label = bubble.node.getChildByName("label") as PIXI.Text | null;
            if (label) label.text = text;
            return;
        }
        const node = makeOverlayBubble(text, type);
        node.zIndex = 9999;
        this.overlayLayer.addChild(node);
        this.roomOverlayBubbles.set(roomId, { node, expiresAt: now + 2600 });
    }

    private setCamera(v: { x: number; y: number; zoom: number }): void {
        const zoom = Number.isFinite(v.zoom) && v.zoom > 0 ? v.zoom : this.camZoom || 1;
        const x = Number.isFinite(v.x) ? v.x : this.camX;
        const y = Number.isFinite(v.y) ? v.y : this.camY;
        this.camX = x;
        this.camY = y;
        this.camZoom = zoom;

        this.root.x = Math.round(this.camX);
        this.root.y = Math.round(this.camY);
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
            if (this.cameraMode !== "free") return;
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

    private tickCameraDirector(dtMs: number): void {
        if (this.cameraMode === "free") return;
        if (this.cameraMode === "follow") {
            if (!this.followAgentId) return;
            const target = this.getAgentWorldPos(this.followAgentId);
            if (!target) return;
            this.panCameraToWorld(target, dtMs);
            return;
        }

        const now = performance.now();
        if (now >= this.autoDirectorNextSwitch) {
            this.autoDirectorRoomId = this.pickAutoDirectorRoom();
            this.autoDirectorNextSwitch = now + 6200;
        }
        if (!this.autoDirectorRoomId) return;
        const center = this.lastCenters?.get(this.autoDirectorRoomId);
        if (!center) return;
        this.panCameraToWorld(center, dtMs);
    }

    private panCameraToWorld(target: RoomCenter, dtMs: number): void {
        const iso = isoProjectWorld(target);
        const viewW = this.app.renderer.width;
        const viewH = this.app.renderer.height;
        const desiredX = viewW * 0.5 - iso.x * this.camZoom;
        const desiredY = viewH * 0.45 - iso.y * this.camZoom;
        const smooth = 1 - Math.exp(-dtMs / 260);
        const nextX = lerp(this.camX, desiredX, smooth);
        const nextY = lerp(this.camY, desiredY, smooth);
        this.setCamera({ x: nextX, y: nextY, zoom: this.camZoom });
    }

    private getAgentWorldPos(agentId: number): RoomCenter | null {
        const motion = this.agentMotion.get(agentId);
        if (motion) return motion.current;
        if (!this.lastState) return null;
        const agent = this.lastState.agents.get(agentId);
        if (!agent) return null;
        const localExtents = computeLocalExtents(Array.from(this.lastState.agents.values()), this.roomBounds);
        return resolveAgentWorldPos(agent, this.roomBounds, localExtents);
    }

    private pickAutoDirectorRoom(): number | undefined {
        if (!this.lastState) return undefined;
        const rooms = Array.from(this.lastState.rooms.values()).filter((r) =>
            isRoomVisible(r.room_id, this.roomFloors, this.floorFilter)
        );
        if (rooms.length === 0) return undefined;
        let best: { id: number; score: number } | null = null;
        for (const r of rooms) {
            const ping = this.roomPings.get(r.room_id) ?? 0;
            const tension = tensionWeight(r);
            const jitter = Math.sin(performance.now() * 0.001 + r.room_id) * 0.05;
            const score = ping * 2.0 + tension + jitter;
            if (!best || score > best.score) best = { id: r.room_id, score };
        }
        return best?.id;
    }

    private autoFitCameraIfNeeded(
        s: WorldState,
        spec: RenderSpec | undefined,
        centers: Map<number, RoomCenter>
    ): void {
        if (this.autoFitLocked) return;

        const bounds = getWorldBounds(spec);
        const viewW = Math.round(this.app.renderer.width);
        const viewH = Math.round(this.app.renderer.height);
        if (viewW <= 0 || viewH <= 0) return;

        const key = `${bounds.min_x}:${bounds.min_y}:${bounds.max_x}:${bounds.max_y}:${viewW}x${viewH}:${this.lastIsoKey}`;
        if (key === this.lastAutoFitKey) return;
        this.lastAutoFitKey = key;

        const visibleRooms = new Map<number, RoomBounds>();
        for (const [id, rb] of this.roomBounds.entries()) {
            if (isRoomVisible(id, this.roomFloors, this.floorFilter)) visibleRooms.set(id, rb);
        }

        const visibleAgents = Array.from(s.agents.values()).filter((a) =>
            isRoomVisible(a.room_id, this.roomFloors, this.floorFilter)
        );
        const localExtents = computeLocalExtents(visibleAgents, this.roomBounds);
        const agentPoints = visibleAgents.map((a) => resolveAgentWorldPos(a, this.roomBounds, localExtents));
        const isoBounds = computeIsoBounds(bounds, centers, visibleRooms, agentPoints);
        const maxFloor = Math.max(0, ...Array.from(this.roomFloors.values()));
        const elev = floorElevationPx(maxFloor, this.isoTileH);
        isoBounds.min_y -= elev;
        // viewW/viewH already validated above

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
        bg.stroke({ width: 2, color: PALETTE.coral, alpha: 0.6 });
        banner.addChild(bg);

        const txt = new PIXI.Text({
            text: `DESYNC\n${reason}\nClick to request fresh snapshot.`,
            style: {
                fontFamily: "Chivo Mono, JetBrains Mono, monospace",
                fontSize: 12,
                fill: 0xf7f2e9,
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

function getWorldBounds(spec?: RenderSpec): RoomBounds {
    const b = spec?.coord_system?.bounds;
    if (b) {
        return { min_x: b.min_x, min_y: b.min_y, max_x: b.max_x, max_y: b.max_y };
    }
    return { min_x: 0, min_y: 0, max_x: 500, max_y: 500 };
}

function roomBoundsFromRoom(r: KvpRoom): RoomBounds | null {
    if (!r.bounds) return null;
    return {
        min_x: r.bounds.min_x,
        min_y: r.bounds.min_y,
        max_x: r.bounds.max_x,
        max_y: r.bounds.max_y,
    };
}

function boundsFromCenter(c: RoomCenter, size: number): RoomBounds {
    return {
        min_x: c.x - size,
        min_y: c.y - size,
        max_x: c.x + size,
        max_y: c.y + size,
    };
}

function objectWorldCenter(obj: KvpObject, roomBounds: RoomBounds): RoomCenter {
    const turns = normalizeQuarterTurns(obj.orientation ?? 0);
    const footW = turns % 2 === 1 ? obj.size_h : obj.size_w;
    const footH = turns % 2 === 1 ? obj.size_w : obj.size_h;
    const cx = roomBounds.min_x + obj.tile_x + footW * 0.5;
    const cy = roomBounds.min_y + obj.tile_y + footH * 0.5;
    return { x: cx, y: cy };
}

function rotateOffset(dx: number, dy: number, turns: number): RoomCenter {
    const t = normalizeQuarterTurns(turns);
    if (t === 1) return { x: -dy, y: dx };
    if (t === 2) return { x: -dx, y: -dy };
    if (t === 3) return { x: dy, y: -dx };
    return { x: dx, y: dy };
}

function boundsCenter(b: RoomBounds): RoomCenter {
    return {
        x: (b.min_x + b.max_x) * 0.5,
        y: (b.min_y + b.max_y) * 0.5,
    };
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
    bounds: RoomBounds,
    centers: Map<number, RoomCenter>,
    rooms: Map<number, RoomBounds>,
    agents: RoomCenter[]
): { min_x: number; min_y: number; max_x: number; max_y: number } {
    const points: RoomCenter[] = [];

    if (rooms.size === 0 && centers.size === 0 && agents.length === 0) {
        points.push({ x: bounds.min_x, y: bounds.min_y });
        points.push({ x: bounds.min_x, y: bounds.max_y });
        points.push({ x: bounds.max_x, y: bounds.min_y });
        points.push({ x: bounds.max_x, y: bounds.max_y });
    }

    for (const rb of rooms.values()) {
        points.push({ x: rb.min_x, y: rb.min_y });
        points.push({ x: rb.min_x, y: rb.max_y });
        points.push({ x: rb.max_x, y: rb.min_y });
        points.push({ x: rb.max_x, y: rb.max_y });
    }

    for (const c of centers.values()) points.push(c);
    for (const a of agents) points.push(a);

    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    for (const p of points) {
        const iso = isoProjectWorld(p);
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

function roomHeightPx(r: KvpRoom, isoTileH: number): number {
    const raw = r.height;
    if (raw !== null && raw !== undefined && Number.isFinite(raw) && raw > 0) {
        return (raw / worldUnitsPerTile) * isoTileH;
    }
    const base = Math.max(isoTileH * 0.9, 16);
    const zoneBoost = r.zone === "core" ? isoTileH * 0.35 : r.zone === "control" ? isoTileH * 0.2 : 0;
    return base + zoneBoost;
}


function roomColors(
    r: KvpRoom
): { top: number; sideA: number; sideB: number; stroke: number; glow: number; floor: number } {
    const zone = (r.zone ?? "").toLowerCase();
    const base =
        zone === "core"
            ? PALETTE.mustard
            : zone === "work"
            ? PALETTE.sea
            : zone === "support"
            ? PALETTE.mint
            : zone === "control"
            ? PALETTE.lilac
            : zone === "residential"
            ? PALETTE.coral
            : zone === "perimeter"
            ? PALETTE.teal
            : PALETTE.mist;

    const tension = (r.tension_tier ?? "low").toLowerCase();
    const accent =
        tension === "high" ? mixColor(base, PALETTE.coral, 0.35) : tension === "medium" ? mixColor(base, PALETTE.mustard, 0.2) : base;

    return {
        top: accent,
        sideA: shadeColor(accent, -0.18),
        sideB: shadeColor(accent, -0.28),
        stroke: PALETTE.ink,
        glow: shadeColor(accent, 0.18),
        floor: mixColor(accent, PALETTE.paper, 0.55),
    };
}

function agentColor(a: KvpAgent): number {
    const colors = [PALETTE.sea, PALETTE.coral, PALETTE.mustard, PALETTE.mint, PALETTE.lilac];
    return colors[a.role_code % colors.length];
}

function agentMoodColor(a: KvpAgent): number {
    const palette = [PALETTE.mint, PALETTE.sea, PALETTE.mustard, PALETTE.coral, PALETTE.lilac];
    const idx = Math.abs(a.action_state_code ?? 0) % palette.length;
    return palette[idx];
}

function agentIsSpeaking(a: KvpAgent): boolean {
    return (a.action_state_code ?? 0) % 5 === 2;
}

function tensionPulse(r: KvpRoom): number {
    const tier = (r.tension_tier ?? "low").toLowerCase();
    const intensity = tier === "high" ? 0.9 : tier === "medium" ? 0.5 : 0.2;
    const t = performance.now() * 0.002 + r.room_id * 0.7;
    return intensity * (0.35 + 0.35 * Math.sin(t));
}

function tensionWeight(r: KvpRoom): number {
    const tier = (r.tension_tier ?? "low").toLowerCase();
    if (tier === "high") return 1.0;
    if (tier === "medium") return 0.6;
    return 0.2;
}

function computeLocalExtents(
    agents: KvpAgent[],
    rooms: Map<number, RoomBounds>
): Map<number, { maxX: number; maxY: number; useLocal: boolean }> {
    const extents = new Map<number, { maxX: number; maxY: number; useLocal: boolean }>();

    for (const a of agents) {
        const entry = extents.get(a.room_id) ?? { maxX: 0, maxY: 0, useLocal: false };
        entry.maxX = Math.max(entry.maxX, Math.abs(a.transform.x));
        entry.maxY = Math.max(entry.maxY, Math.abs(a.transform.y));
        extents.set(a.room_id, entry);
    }

    for (const [roomId, entry] of extents.entries()) {
        const rb = rooms.get(roomId);
        if (!rb) continue;
        const w = rb.max_x - rb.min_x;
        const h = rb.max_y - rb.min_y;
        const localish = entry.maxX <= 25 && entry.maxY <= 25;
        const largeRoom = w >= 40 && h >= 40;
        entry.useLocal = localish && largeRoom;
    }

    return extents;
}

function resolveAgentWorldPos(
    a: KvpAgent,
    rooms: Map<number, RoomBounds>,
    extents: Map<number, { maxX: number; maxY: number; useLocal: boolean }>
): RoomCenter {
    const rb = rooms.get(a.room_id) ?? null;
    if (!rb) return { x: a.transform.x, y: a.transform.y };

    if (withinBounds(rb, a.transform.x, a.transform.y)) {
        return { x: a.transform.x, y: a.transform.y };
    }

    const entry = extents.get(a.room_id);
    if (!entry || !entry.useLocal) {
        return clampPoint({ x: a.transform.x, y: a.transform.y }, rb);
    }

    const pad = Math.min((rb.max_x - rb.min_x) * 0.08, (rb.max_y - rb.min_y) * 0.08);
    const usableW = Math.max(1, rb.max_x - rb.min_x - pad * 2);
    const usableH = Math.max(1, rb.max_y - rb.min_y - pad * 2);
    const nx = entry.maxX > 0 ? clamp(a.transform.x / entry.maxX, 0, 1) : 0.5;
    const ny = entry.maxY > 0 ? clamp(a.transform.y / entry.maxY, 0, 1) : 0.5;
    return {
        x: rb.min_x + pad + nx * usableW,
        y: rb.min_y + pad + ny * usableH,
    };
}

function resolveItemWorldPos(
    item: KvpItem,
    rooms: Map<number, RoomBounds>,
    centers: Map<number, RoomCenter>
): RoomCenter {
    const rb = rooms.get(item.room_id) ?? null;
    if (!rb) {
        const center = centers.get(item.room_id) ?? { x: 0, y: 0 };
        const angle = (item.item_id * 2.3999632297) % (Math.PI * 2);
        const radius = 0.65;
        return { x: center.x + Math.cos(angle) * radius, y: center.y + Math.sin(angle) * radius };
    }

    const u = fract(Math.sin(item.item_id * 12.9898) * 43758.5453);
    const v = fract(Math.sin((item.item_id + 77) * 78.233) * 12345.678);
    const pad = Math.min((rb.max_x - rb.min_x) * 0.1, (rb.max_y - rb.min_y) * 0.1);
    return {
        x: lerp(rb.min_x + pad, rb.max_x - pad, u),
        y: lerp(rb.min_y + pad, rb.max_y - pad, v),
    };
}

function rectEdgePoint(bounds: RoomBounds, target: RoomCenter): RoomCenter {
    const cx = (bounds.min_x + bounds.max_x) * 0.5;
    const cy = (bounds.min_y + bounds.max_y) * 0.5;
    const dx = target.x - cx;
    const dy = target.y - cy;
    const w = Math.max(0.001, (bounds.max_x - bounds.min_x) * 0.5);
    const h = Math.max(0.001, (bounds.max_y - bounds.min_y) * 0.5);
    const t = Math.max(Math.abs(dx) / w, Math.abs(dy) / h);
    return { x: cx + dx / t, y: cy + dy / t };
}

function floorElevationPx(floor: number, isoTileH: number): number {
    if (floor <= 0) return 0;
    return Math.max(isoTileH * 1.6, 28) * floor;
}

function isRoomVisible(roomId: number, floors: Map<number, number>, filter: "all" | 0 | 1): boolean {
    if (filter === "all") return true;
    const roomFloor = floors.get(roomId) ?? 0;
    return roomFloor === filter;
}

type TileLayout = {
    boundsById: Map<number, RoomBounds>;
    floorById: Map<number, number>;
};

function buildTileLayout(rooms: KvpRoom[], world: RoomBounds): TileLayout {
    const boundsById = new Map<number, RoomBounds>();
    const floorById = new Map<number, number>();

    const indoors: KvpRoom[] = [];
    const outdoors: KvpRoom[] = [];
    for (const r of rooms) {
        if (isOutdoorRoom(r)) outdoors.push(r);
        else indoors.push(r);
    }

    const placed0 = new Set<string>();
    const placed1 = new Set<string>();

    const tileUnits = Math.max(1, worldUnitsPerTile);
    const originX = world.min_x + tileUnits;
    const originY = world.min_y + tileUnits;

    const grid0W = 10;
    const grid0H = 8;
    const grid1W = 8;
    const grid1H = 6;

    const placeAt = (
        r: KvpRoom,
        floor: number,
        x: number,
        y: number,
        w: number,
        h: number,
        offsetX: number,
        offsetY: number
    ): boolean => {
        const occupied = floor === 0 ? placed0 : placed1;
        for (let dy = 0; dy < h; dy += 1) {
            for (let dx = 0; dx < w; dx += 1) {
                const key = `${x + dx},${y + dy}`;
                if (occupied.has(key)) return false;
            }
        }
        for (let dy = 0; dy < h; dy += 1) {
            for (let dx = 0; dx < w; dx += 1) {
                occupied.add(`${x + dx},${y + dy}`);
            }
        }
        const min_x = originX + offsetX + x * tileUnits;
        const min_y = originY + offsetY + y * tileUnits;
        const max_x = min_x + w * tileUnits;
        const max_y = min_y + h * tileUnits;
        boundsById.set(r.room_id, { min_x, min_y, max_x, max_y });
        floorById.set(r.room_id, floor);
        return true;
    };

    const placeRoom = (r: KvpRoom, floor: number, gridW: number, gridH: number, offsetX: number, offsetY: number) => {
        const [w, h] = roomTileSize(r);
        const occupied = floor === 0 ? placed0 : placed1;
        for (let y = 0; y <= gridH - h; y += 1) {
            for (let x = 0; x <= gridW - w; x += 1) {
                let ok = true;
                for (let dy = 0; dy < h; dy += 1) {
                    for (let dx = 0; dx < w; dx += 1) {
                        const key = `${x + dx},${y + dy}`;
                        if (occupied.has(key)) ok = false;
                    }
                }
                if (!ok) continue;
                for (let dy = 0; dy < h; dy += 1) {
                    for (let dx = 0; dx < w; dx += 1) {
                        occupied.add(`${x + dx},${y + dy}`);
                    }
                }
                const min_x = originX + offsetX + x * tileUnits;
                const min_y = originY + offsetY + y * tileUnits;
                const max_x = min_x + w * tileUnits;
                const max_y = min_y + h * tileUnits;
                boundsById.set(r.room_id, { min_x, min_y, max_x, max_y });
                floorById.set(r.room_id, floor);
                return true;
            }
        }
        return false;
    };

    const lobby = pickLobbyRoom(indoors);
    const elevator = pickElevatorRoom(indoors, lobby);

    if (lobby) {
        const lobbyX = Math.floor(grid0W / 2);
        const lobbyY = grid0H - 2;
        placeAt(lobby, 0, lobbyX, lobbyY, 1, 2, 0, 0);
    }

    if (elevator) {
        const lobbyX = Math.floor(grid0W / 2);
        const lobbyY = grid0H - 2;
        placeAt(elevator, 0, lobbyX, Math.max(0, lobbyY - 1), 1, 1, 0, 0);
    }

    const floor1Rooms = indoors.filter((r) => isUpperFloorRoom(r) && r !== lobby && r !== elevator);
    if (floor1Rooms.length === 0 && indoors.length > 3) {
        const fallback = indoors.filter((r) => r !== lobby && r !== elevator);
        if (fallback.length > 0) floor1Rooms.push(fallback[fallback.length - 1]);
    }

    // Sort larger rooms first for better packing
    indoors.sort((a, b) => {
        const [aw, ah] = roomTileSize(a);
        const [bw, bh] = roomTileSize(b);
        return bw * bh - aw * ah;
    });
    outdoors.sort((a, b) => {
        const [aw, ah] = roomTileSize(a);
        const [bw, bh] = roomTileSize(b);
        return bw * bh - aw * ah;
    });

    for (const r of floor1Rooms) {
        if (boundsById.has(r.room_id)) continue;
        const ok = placeRoom(r, 1, grid1W, grid1H, 0, 0);
        if (!ok) placeRoom(r, 0, grid0W, grid0H, 0, 0);
    }

    for (const r of indoors) {
        if (boundsById.has(r.room_id)) continue;
        placeRoom(r, 0, grid0W, grid0H, 0, 0);
    }

    // Outdoor band on floor 0 (no second floor above)
    for (const r of outdoors) {
        if (!boundsById.has(r.room_id)) {
            placeRoom(r, 0, 8, 2, 0, tileUnits * 9);
        }
    }

    // Fallback for any unplaced rooms
    for (const r of rooms) {
        if (!boundsById.has(r.room_id)) {
            placeRoom(r, 0, grid0W, grid0H, 0, 0);
        }
    }

    return { boundsById, floorById };
}

function roomTileSize(r: KvpRoom): [number, number] {
    const label = (r.label ?? "").toLowerCase();
    if (label.includes("lobby") || label.includes("entry") || label.includes("reception")) return [1, 2];
    if (label.includes("elevator") || label.includes("lift")) return [1, 1];
    if (label.includes("brain") || label.includes("forge")) return [2, 2];
    if (label.includes("assembly") || label.includes("habitation") || label.includes("yard")) return [2, 2];
    if (label.includes("cooling") || label.includes("resonance")) return [2, 1];
    if (label.includes("maintenance") || label.includes("commons") || label.includes("supervisor")) return [1, 2];
    if (label.includes("outdoor") || label.includes("courtyard")) return [2, 2];
    return (r.room_id % 3) === 0 ? [2, 1] : (r.room_id % 4) === 0 ? [1, 2] : [1, 1];
}

function pickLobbyRoom(rooms: KvpRoom[]): KvpRoom | undefined {
    const labeled = rooms.find((r) => /lobby|entry|reception/.test((r.label ?? "").toLowerCase()));
    if (labeled) return labeled;
    return rooms.slice().sort((a, b) => a.room_id - b.room_id)[0];
}

function pickElevatorRoom(rooms: KvpRoom[], lobby?: KvpRoom): KvpRoom | undefined {
    const labeled = rooms.find((r) => /elevator|lift/.test((r.label ?? "").toLowerCase()));
    if (labeled) return labeled;
    const remaining = rooms.filter((r) => r !== lobby).sort((a, b) => a.room_id - b.room_id);
    return remaining[0];
}

function isUpperFloorRoom(r: KvpRoom): boolean {
    const label = (r.label ?? "").toLowerCase();
    return /deck|supervisor|control|loft|office|upper|lab/.test(label);
}

function isOutdoorRoom(r: KvpRoom): boolean {
    const label = (r.label ?? "").toLowerCase();
    if (label.includes("yard") || label.includes("outdoor") || label.includes("courtyard")) return true;
    const zone = (r.zone ?? "").toLowerCase();
    return zone === "perimeter";
}

function isElevatorRoom(r: KvpRoom | undefined): boolean {
    if (!r) return false;
    const label = (r.label ?? "").toLowerCase();
    return label.includes("elevator") || label.includes("lift");
}

function extractRoomIdFromEvent(ev: { payload?: Record<string, unknown> }): number | null {
    const payload = ev.payload ?? {};
    const roomId = toNumber(payload.room_id ?? payload.previous_room_id ?? payload.target_room_id);
    return roomId;
}

type OverlayBubbleType = "speech" | "thought" | "notice";
type OverlayBubble = { node: PIXI.Container; expiresAt: number };

function overlayBubbleType(kind: string): OverlayBubbleType {
    const k = (kind ?? "").toLowerCase();
    if (k.includes("thought") || k.includes("idea")) return "thought";
    if (k.includes("say") || k.includes("speak") || k.includes("announce")) return "speech";
    return "notice";
}

function overlayBubbleText(ev: UIOverlayEvent): string {
    const text = getRecordString(ev.data, "text");
    if (text) return text;
    const kind = ev.kind ?? "event";
    return kind.replace(/_/g, " ");
}

function makeOverlayBubble(text: string, type: OverlayBubbleType): PIXI.Container {
    const container = new PIXI.Container();
    const bg = new PIXI.Graphics();
    const label = new PIXI.Text({
        text,
        style: {
            fontFamily: "Bricolage Grotesque, Space Grotesk, sans-serif",
            fontSize: 10,
            fill: 0x1f242b,
        },
    });
    label.name = "label";
    const padX = 8;
    const padY = 4;
    const w = label.width + padX * 2;
    const h = label.height + padY * 2;
    bg.roundRect(0, 0, w, h, 6);
    const fill = type === "thought" ? PALETTE.lilac : type === "speech" ? PALETTE.paper : PALETTE.mint;
    bg.fill({ color: fill, alpha: 0.92 });
    bg.stroke({ width: 1, color: PALETTE.ink, alpha: 0.35 });
    container.addChild(bg);

    label.x = padX;
    label.y = padY;
    container.addChild(label);

    const tail = new PIXI.Graphics();
    tail.poly([6, h, 12, h + 6, 2, h + 6], true);
    tail.fill({ color: fill, alpha: 0.92 });
    container.addChild(tail);
    return container;
}

function roomTopCenter(bounds: RoomBounds, floor: number, height: number, isoTileH: number): RoomCenter {
    const elev = floorElevationPx(floor, isoTileH);
    const top = isoRectPoints(bounds, height, elev);
    return centerOfPoints(top);
}

function isoRect(bounds: RoomBounds): number[] {
    return pointsToArray(isoRectPoints(bounds, 0, 0));
}

function isoRectPoints(bounds: RoomBounds, heightPx: number, elevPx: number): RoomCenter[] {
    const corners = [
        { x: bounds.min_x, y: bounds.min_y },
        { x: bounds.max_x, y: bounds.min_y },
        { x: bounds.max_x, y: bounds.max_y },
        { x: bounds.min_x, y: bounds.max_y },
    ];
    return corners.map((c) => {
        const p = isoProjectWorld(c);
        return { x: p.x, y: p.y - heightPx - elevPx };
    });
}

function drawObjectPart(
    g: PIXI.Graphics,
    part: ObjectPartSpec,
    baseCenter: RoomCenter,
    turns: number,
    scaleX: number,
    scaleY: number,
    scaleZ: number,
    elevBase: number,
    isoTileH: number
): void {
    const offset = part.offset ?? { x: 0, y: 0, z: 0 };
    const roff = rotateOffset(offset.x, offset.y, turns);
    let w = part.size.w * scaleX;
    let h = part.size.h * scaleY;
    const z = part.size.z * scaleZ;
    if (turns % 2 === 1) {
        const tmp = w;
        w = h;
        h = tmp;
    }
    const cx = baseCenter.x + roff.x * scaleX;
    const cy = baseCenter.y + roff.y * scaleY;
    const bounds: RoomBounds = {
        min_x: cx - w * 0.5,
        min_y: cy - h * 0.5,
        max_x: cx + w * 0.5,
        max_y: cy + h * 0.5,
    };
    const heightPx = (z / worldUnitsPerTile) * isoTileH;
    const elevPx = elevBase + (offset.z * scaleZ / worldUnitsPerTile) * isoTileH;

    const base = isoRectPoints(bounds, 0, elevPx);
    const top = isoRectPoints(bounds, heightPx, elevPx);
    const opacity = part.opacity ?? 0.95;
    const baseColor = part.color ?? 0xb6c4c3;
    const sideA = shadeColor(baseColor, -0.12);
    const sideB = shadeColor(baseColor, -0.22);
    const topColor = shadeColor(baseColor, 0.02);

    // Right face (east)
    g.poly(pointsToArray([base[1], base[2], top[2], top[1]]), true);
    g.fill({ color: sideA, alpha: opacity });

    // Left face (south)
    g.poly(pointsToArray([base[2], base[3], top[3], top[2]]), true);
    g.fill({ color: sideB, alpha: opacity });

    // Top face
    g.poly(pointsToArray(top), true);
    g.fill({ color: topColor, alpha: opacity });

    if (part.emissive && part.emissive > 0) {
        g.poly(pointsToArray(top), true);
        g.fill({ color: shadeColor(baseColor, 0.25), alpha: Math.min(0.6, part.emissive) });
    }

    g.stroke({ width: 1, color: shadeColor(baseColor, -0.35), alpha: 0.65 });
}

function pointsToArray(points: RoomCenter[]): number[] {
    const out: number[] = [];
    for (const p of points) out.push(p.x, p.y);
    return out;
}

function centerOfPoints(points: RoomCenter[]): RoomCenter {
    const sum = points.reduce((acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }), { x: 0, y: 0 });
    return { x: sum.x / points.length, y: sum.y / points.length };
}

function withinBounds(bounds: RoomBounds, x: number, y: number): boolean {
    return x >= bounds.min_x && x <= bounds.max_x && y >= bounds.min_y && y <= bounds.max_y;
}

function isoProjectWorld(p: RoomCenter): RoomCenter {
    const turns = worldRotationQuarterTurns;
    let x = p.x;
    let y = p.y;
    if (turns !== 0) {
        const dx = p.x - worldCenter.x;
        const dy = p.y - worldCenter.y;
        if (turns === 1) {
            x = worldCenter.x - dy;
            y = worldCenter.y + dx;
        } else if (turns === 2) {
            x = worldCenter.x - dx;
            y = worldCenter.y - dy;
        } else {
            x = worldCenter.x + dy;
            y = worldCenter.y - dx;
        }
    }
    return isoProject({ x: x / worldUnitsPerTile, y: y / worldUnitsPerTile });
}

function drawIsoHatch(g: PIXI.Graphics, bounds: RoomBounds, step: number, color: number, alpha: number): void {
    for (let y = Math.floor(bounds.min_y); y <= Math.ceil(bounds.max_y); y += step) {
        const p0 = isoProjectWorld({ x: bounds.min_x, y });
        const p1 = isoProjectWorld({ x: bounds.max_x, y: y + step * 0.4 });
        g.moveTo(p0.x, p0.y);
        g.lineTo(p1.x, p1.y);
    }
    g.stroke({ width: 1, color, alpha });
}

function drawRoomHatch(g: PIXI.Graphics, top: RoomCenter[], color: number): void {
    if (top.length !== 4) return;
    for (let i = 1; i <= 3; i += 1) {
        const t = i / 4;
        const a = lerpPoint(top[0], top[3], t);
        const b = lerpPoint(top[1], top[2], t);
        g.moveTo(a.x, a.y);
        g.lineTo(b.x, b.y);
    }
    g.stroke({ width: 1, color, alpha: 0.12 });
}

function lerpPoint(a: RoomCenter, b: RoomCenter, t: number): RoomCenter {
    return { x: lerp(a.x, b.x, t), y: lerp(a.y, b.y, t) };
}

function shadeColor(hex: number, factor: number): number {
    const r = (hex >> 16) & 0xff;
    const g = (hex >> 8) & 0xff;
    const b = hex & 0xff;
    const nr = clamp(Math.round(r + 255 * factor), 0, 255);
    const ng = clamp(Math.round(g + 255 * factor), 0, 255);
    const nb = clamp(Math.round(b + 255 * factor), 0, 255);
    return (nr << 16) | (ng << 8) | nb;
}

function mixColor(a: number, b: number, t: number): number {
    const ar = (a >> 16) & 0xff;
    const ag = (a >> 8) & 0xff;
    const ab = a & 0xff;
    const br = (b >> 16) & 0xff;
    const bg = (b >> 8) & 0xff;
    const bb = b & 0xff;
    const nr = clamp(Math.round(ar + (br - ar) * t), 0, 255);
    const ng = clamp(Math.round(ag + (bg - ag) * t), 0, 255);
    const nb = clamp(Math.round(ab + (bb - ab) * t), 0, 255);
    return (nr << 16) | (ng << 8) | nb;
}

function toNumber(val: unknown): number | null {
    if (typeof val === "number" && Number.isFinite(val)) return val;
    if (typeof val === "string" && val.trim() !== "" && Number.isFinite(Number(val))) return Number(val);
    return null;
}

function getRecordNumber(data: Record<string, unknown>, key: string): number | null {
    if (!data) return null;
    return toNumber(data[key]);
}

function getRecordString(data: Record<string, unknown>, key: string): string | null {
    if (!data) return null;
    const val = data[key];
    return typeof val === "string" ? val : null;
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
