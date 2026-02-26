# 🌐 WEBVIEW-0001 — LOOPFORGE WEB VIEWER
## _Debug Truth Machine → Isometric “Watch the City Evolve” Viewer_

**Status:** Draft v1.0  
**Applies to:** Sim5 → SimX  
**Protocol:** KVP-0001 (mandatory)  
**Audience:** Kernel, Web, QA, Replay, Tooling

---

## 0. Purpose

WEBVIEW-0001 defines the **reference web-based viewer** for Loopforge.

It serves two roles:
1. **Debug Truth Machine** (Phase 1)
2. **2.5D Isometric Observer Viewer** (Phase 2)

The Web Viewer is the **first canonical implementation**
of KVP-0001 and sets behavioral expectations
for all future viewers.

---

## 1. Non-Goals

The Web Viewer will NOT:
- simulate world state
- resolve conflicts
- advance time
- run LLMs
- invent narrative
- act as authoritative storage

All truth originates in the kernel.
The viewer only reflects it.

---

## 2. Architectural Position

```text
SimX Kernel (Rust)
        ⇄  KVP-0001 (WebSocket + HTTP)
        ⇄
Web Viewer (TypeScript)
```

Key constraints:
* no shared memory
* no kernel imports
* protocol-only interaction
* replay and live use identical code paths

---

## 3. Technology Stack (Recommended)

Mandatory:
- TypeScript
- WebSocket (live stream)
- HTTP (snapshot + replay fetch)

Rendering lanes (choose one):
- Canvas 2D (baseline)
- PixiJS (preferred for Phase 2)

Explicitly optional:
- Web Workers (diff apply off main thread)
- IndexedDB (replay caching)

---

## 4. Module Layout

```text
webview/
  kvp/
    client.ts
    codec.ts
    schema.ts
  state/
    worldStore.ts
    agentStore.ts
    eventStore.ts
  replay/
    timeline.ts
    scrubber.ts
    traceLoader.ts
  render/
    isometric.ts
    overlays.ts
    bubbles.ts
  ui/
    inspector/
    timeline/
    connection/
  debug/
    desync.ts
    hashVerifier.ts
```

Module boundaries are strict.
Rendering must never touch protocol code.

---

## 5. Connection & Handshake

On load:
1. Viewer opens WebSocket
2. Sends `VIEWER_HELLO`
3. Receives `KERNEL_HELLO`
4. Selects viewer plugin/store by `engine_name + schema_version` from `KERNEL_HELLO`
5. Subscribes to channels

Failure at any step must be surfaced
in the UI immediately.

Handshake + routing notes:
- `VIEWER_HELLO.supported_schema_versions` may include multiple schemas (for example `["1", "sim_sim_1"]`).
- `KERNEL_HELLO` selects one schema for the session and carries engine identity.
- LIVE WebSocket KVP envelopes are UTF-8 JSON text frames.

---

## 6. Subscription Policy

Default subscription (Phase 1):
- WORLD
- AGENTS
- EVENTS
- DEBUG

Optional:
- NARRATIVE (toggleable)

Viewer must allow dynamic resubscribe  
without full reload.

---

## 7. Phase 1 — Debug Truth Machine

Phase 1 is mandatory before Phase 2 begins.

Primary goal:
> **See exactly what the kernel believes is happening.**

Aesthetic quality is irrelevant here.
Correctness is everything.

---

## 8. Phase 1 Required Features

- connection status panel
- snapshot load indicator
- diff stream counter
- current tick display
- step_hash display
- replay/live mode toggle
- pause / resume / seek controls

No animation smoothing.
State changes must be immediate and explicit.

---

## 9. Inspector Panels

Inspector UI must support:
- agent inspection (components + values)
- room inspection (occupancy, tension, fields)
- event log per tick
- narrative fragment listing (if enabled)

Inspectors are read-only.
They must never mutate state.

---

## 10. Replay System (Phase 1)

Replay uses:
- the same snapshot/diff logic as live mode
- a pre-recorded command log

Replay must support:
- play
- pause
- seek
- scrub
- speed control

Replay and live execution paths
must be identical.

---

## 11. Golden Trace Support

The Web Viewer is the **golden trace verifier**.

It must:
- load known-good snapshot + diff fixtures
- replay deterministically
- flag mismatched step_hash values
- surface first divergence clearly

This UI is required for CI and QA.

---

## 12. Desync Detection & Recovery

On step_hash mismatch:
1. Freeze rendering
2. Display desync banner
3. Offer actions:
   - request fresh snapshot
   - continue (unsafe)
   - export trace

Desync handling behavior
must be consistent across viewers.

---

## 13. Phase 2 — Isometric Viewer Activation

Phase 2 may begin only when:
- Phase 1 correctness is stable
- snapshot/diff schemas are frozen
- replay parity tests pass

Phase 2 builds on Phase 1,
never replaces it.

---

## 14. Phase 2 Rendering Goals

- 2.5D isometric view
- rooms/zones as tiles or planes
- agents as sprites or markers
- smooth camera pan/zoom
- optional interpolation (visual only)

Visual interpolation must not affect state.

---

## 15. Narrative Presentation

Narrative fragments are:
- optional
- viewer-facing only
- replaceable

Presentation includes:
- speech bubbles
- inner monologue popovers
- event annotations

Narrative must be visually distinguished
from deterministic state.

---

## 16. Psycho-Topology Overlays

Phase 2 overlays include:
- tension heatmap
- gossip pressure
- curiosity density
- social clustering

Overlays must:
- be toggleable
- be derived directly from kernel fields
- never infer missing data

---

## 17. Input Commands

Web Viewer may emit:
- WORLD_NUDGE
- DEBUG_PROBE
- REPLAY_CONTROL

UI must make clear:
- which commands affect simulation
- which affect only viewing

All commands are logged and visible.

---

## 18. Performance Constraints

Targets:
- 60 FPS rendering (best effort)
- diff apply < 5ms per tick (Phase 1)
- graceful degradation on large worlds

Viewer may:
- batch renders
- throttle visual updates
- decimate overlays

Viewer may NOT drop diffs silently.

---

## 19. Accessibility & UX

Debug clarity > aesthetics.

Requirements:
- readable text at all zoom levels
- colorblind-safe palettes for overlays
- explicit legends for heatmaps
- clear separation of layers

Confusion is a bug.

---

## 20. Acceptance Criteria

WEBVIEW-0001 is complete when:

- live and replay produce identical visuals
- golden traces replay without divergence
- desync is detected and recoverable
- inspectors reflect kernel truth
- Phase 2 rendering adds no logic
- no viewer code affects determinism

At that point, Godot and Unreal adapters
can safely follow.

## Appendix A: Vite + PixiJS layout

```text
loopforge-webview/
  package.json
  tsconfig.json
  vite.config.ts
  index.html
  src/
    main.ts
    app/
      boot.ts
    kvp/
      client.ts
      codec.ts
      types.ts
    state/
      worldStore.ts
    render/
      pixiScene.ts
      iso.ts
      overlays.ts
      bubbles.ts
    ui/
      hud.ts
      panels/
        inspector.ts
        timeline.ts
    debug/
      desync.ts
      hashVerifier.ts
    styles/
      app.css
```

## Appendix B: PixiJS Reference Skeleton

```ts
/* ============================================================================
 * Loopforge Web Viewer — PixiJS Reference Skeleton (WEBVIEW-0001)
 * ----------------------------------------------------------------------------
 * Goals:
 * - KVP-0001 client (WebSocket)
 * - WorldStore with baseline snapshot + diff apply
 * - Pixi renderer: isometric-ish scene graph + overlays + bubbles hooks
 * - Debug UI hooks: connection status, tick, step_hash, desync banner
 *
 * Non-goals:
 * - No simulation logic
 * - No authoritative state mutation beyond applying kernel messages
 * - No fancy styling (this is a skeleton)
 * ========================================================================== */

import * as PIXI from "pixi.js";

/** -----------------------------
 * Types (minimal subset for skeleton)
 * (In real build, import generated types from kvp/schema.ts)
 * ------------------------------ */

type Tick = number;

type MsgType =
  | "VIEWER_HELLO"
  | "KERNEL_HELLO"
  | "SUBSCRIBE"
  | "SUBSCRIBED"
  | "FULL_SNAPSHOT"
  | "FRAME_DIFF"
  | "WARN"
  | "ERROR";

type Envelope<TPayload = unknown> = {
  kvp_version: "0.1";
  msg_type: MsgType;
  msg_id: string;
  sent_at_ms: number;
  payload: TPayload;
};

type ViewerHello = {
  viewer_name: string;
  viewer_version: string;
  supported_schema_versions: string[];
  supports: { diff_stream: boolean; full_snapshot: boolean; replay_seek: boolean };
};

type KernelHello = {
  engine_name: string;
  engine_version: string;
  schema_version: string;
  world_id: string;
  run_id: string;
  seed: number;
  tick_rate_hz: number;
  time_origin_ms: number;
};

type Subscribe = {
  stream: "LIVE" | "REPLAY";
  channels: Array<"WORLD" | "AGENTS" | "ITEMS" | "EVENTS" | "NARRATIVE" | "DEBUG">;
  diff_policy: "DIFF_ONLY" | "PERIODIC_SNAPSHOT" | "SNAPSHOT_ON_DESYNC";
  snapshot_policy: "ON_JOIN" | "NEVER";
  compression: "NONE";
};

type Vec2 = { x: number; y: number };

type RoomSnapshot = {
  room_id: number;
  name: string;
  zone_id: number;
  bounds: { x: number; y: number; w: number; h: number };
  occupancy: number;
  tension: number;
};

type AgentSnapshot = {
  agent_id: number;
  room_id: number | null;
  pos: Vec2;
  facing_deg: number;
  public_state: { label: string; mood: number; energy: number; speaking: boolean; emote?: string | null };
};

type NarrativeFragment = {
  entity_id: number;
  kind: "DIALOGUE" | "INNER_MONOLOGUE" | "THOUGHT_TAG";
  text: string;
  ttl_ticks: number;
  nondeterministic: boolean;
};

type FullSnapshot = {
  schema_version: string;
  tick: Tick;
  step_hash: string;
  world: { rooms: RoomSnapshot[]; zones: any[]; static_assets: any[] };
  agents: AgentSnapshot[];
  items: any[];
  events: any[];
  narrative_fragments: NarrativeFragment[];
};

type AgentMove = {
  agent_id: number;
  from_room_id: number | null;
  to_room_id: number | null;
  from_pos: Vec2;
  to_pos: Vec2;
};

type FrameDiff = {
  schema_version: string;
  from_tick: Tick;
  to_tick: Tick;
  step_hash: string;
  diff: {
    agent_moves: AgentMove[];
    agent_spawns: AgentSnapshot[];
    agent_despawns: number[];
    room_replacements: RoomSnapshot[];
    event_replacements: any[];
    narrative_replacements: NarrativeFragment[];
  };
};

/** -----------------------------
 * Small utilities
 * ------------------------------ */

function uuid(): string {
  // Good enough for skeleton; replace with crypto.randomUUID() in modern browsers.
  return (globalThis.crypto?.randomUUID?.() ?? `msg_${Date.now()}_${Math.random()}`).toString();
}

function nowMs(): number {
  return Date.now();
}

/** Convert cartesian (kernel coords) to isometric-ish screen coords.
 * Replace with your canonical mapping later.
 */
function isoProject(p: Vec2): Vec2 {
  // Simple 2:1 iso projection (placeholder).
  return { x: p.x - p.y, y: (p.x + p.y) * 0.5 };
}

/** -----------------------------
 * World Store (authoritative viewer state mirror)
 * ------------------------------ */

type WorldState = {
  connected: boolean;
  kernelHello?: KernelHello;
  schemaVersion?: string;

  tick: Tick;
  stepHash: string;

  rooms: Map<number, RoomSnapshot>;
  agents: Map<number, AgentSnapshot>;
  narrative: Map<string, NarrativeFragment>; // key: `${entity_id}:${kind}:${text}`

  // For desync + diagnostics
  lastEnvelopeId?: string;
  desynced: boolean;
  desyncReason?: string;
};

class WorldStore {
  public state: WorldState;

  // Event listeners (simple pub/sub)
  private listeners = new Set<(s: WorldState) => void>();

  constructor() {
    this.state = {
      connected: false,
      tick: 0,
      stepHash: "",
      rooms: new Map(),
      agents: new Map(),
      narrative: new Map(),
      desynced: false,
    };
  }

  subscribe(fn: (s: WorldState) => void): () => void {
    this.listeners.add(fn);
    fn(this.state);
    return () => this.listeners.delete(fn);
  }

  private emit(): void {
    for (const fn of this.listeners) fn(this.state);
  }

  setConnected(connected: boolean): void {
    this.state.connected = connected;
    this.emit();
  }

  setKernelHello(hello: KernelHello): void {
    this.state.kernelHello = hello;
    this.state.schemaVersion = hello.schema_version;
    this.emit();
  }

  applySnapshot(s: FullSnapshot): void {
    // Canonicalize expectations: assume payload already canonicalized by kernel.
    this.state.tick = s.tick;
    this.state.stepHash = s.step_hash;
    this.state.desynced = false;
    this.state.desyncReason = undefined;

    this.state.rooms.clear();
    for (const r of s.world.rooms) this.state.rooms.set(r.room_id, r);

    this.state.agents.clear();
    for (const a of s.agents) this.state.agents.set(a.agent_id, a);

    this.state.narrative.clear();
    for (const n of s.narrative_fragments) {
      this.state.narrative.set(`${n.entity_id}:${n.kind}:${n.text}`, n);
    }

    this.emit();
  }

  applyDiff(d: FrameDiff): void {
    // Basic sanity checks
    if (this.state.desynced) return;

    // Tick monotonicity guard (viewer must not accept backwards diffs)
    if (d.from_tick !== this.state.tick) {
      this.state.desynced = true;
      this.state.desyncReason = `Diff baseline mismatch: expected from_tick=${this.state.tick}, got ${d.from_tick}`;
      this.emit();
      return;
    }

    // Apply room replacements (Phase 1 policy)
    for (const r of d.diff.room_replacements) {
      this.state.rooms.set(r.room_id, r);
    }

    // Apply agent despawns
    for (const id of d.diff.agent_despawns) {
      this.state.agents.delete(id);
    }

    // Apply agent spawns
    for (const a of d.diff.agent_spawns) {
      this.state.agents.set(a.agent_id, a);
    }

    // Apply agent moves
    for (const m of d.diff.agent_moves) {
      const a = this.state.agents.get(m.agent_id);
      if (!a) continue;
      a.room_id = m.to_room_id;
      a.pos = m.to_pos;
      this.state.agents.set(m.agent_id, a);
    }

    // Replace narrative fragments (Phase 1 policy)
    this.state.narrative.clear();
    for (const n of d.diff.narrative_replacements) {
      this.state.narrative.set(`${n.entity_id}:${n.kind}:${n.text}`, n);
    }

    // Advance tick + step hash
    this.state.tick = d.to_tick;
    this.state.stepHash = d.step_hash;

    this.emit();
  }

  markDesync(reason: string): void {
    this.state.desynced = true;
    this.state.desyncReason = reason;
    this.emit();
  }
}

/** -----------------------------
 * KVP Client (WebSocket)
 * ------------------------------ */

type KvpClientOpts = {
  url: string; // ws://...
  viewerName: string;
  viewerVersion: string;
  supportedSchemaVersions: string[];
  defaultSubscribe: Subscribe;
};

class KvpClient {
  private ws?: WebSocket;
  private store: WorldStore;
  private opts: KvpClientOpts;

  constructor(store: WorldStore, opts: KvpClientOpts) {
    this.store = store;
    this.opts = opts;
  }

  connect(): void {
    this.ws = new WebSocket(this.opts.url);
    this.ws.onopen = () => {
      this.store.setConnected(true);
      this.sendViewerHello();
    };
    this.ws.onclose = () => {
      this.store.setConnected(false);
    };
    this.ws.onerror = () => {
      // Keep it simple in skeleton
    };
    this.ws.onmessage = (ev) => this.onMessage(ev.data);
  }

  disconnect(): void {
    this.ws?.close();
  }

  private sendEnvelope<TPayload>(msg_type: MsgType, payload: TPayload): void {
    const env: Envelope<TPayload> = {
      kvp_version: "0.1",
      msg_type,
      msg_id: uuid(),
      sent_at_ms: nowMs(),
      payload,
    };
    this.ws?.send(JSON.stringify(env));
  }

  private sendViewerHello(): void {
    const hello: ViewerHello = {
      viewer_name: this.opts.viewerName,
      viewer_version: this.opts.viewerVersion,
      supported_schema_versions: this.opts.supportedSchemaVersions,
      supports: { diff_stream: true, full_snapshot: true, replay_seek: true },
    };
    this.sendEnvelope("VIEWER_HELLO", hello);
  }

  private sendSubscribe(): void {
    this.sendEnvelope("SUBSCRIBE", this.opts.defaultSubscribe);
  }

  requestFreshSnapshot(): void {
    // Protocol option: simplest is re-SUBSCRIBE with snapshot_policy ON_JOIN,
    // or add a dedicated REQUEST_SNAPSHOT msg type later.
    this.sendSubscribe();
  }

  private onMessage(raw: string): void {
    let env: Envelope;
    try {
      env = JSON.parse(raw) as Envelope;
    } catch {
      this.store.markDesync("Invalid JSON from kernel");
      return;
    }

    switch (env.msg_type) {
      case "KERNEL_HELLO": {
        const h = env.payload as KernelHello;
        this.store.setKernelHello(h);
        this.sendSubscribe();
        break;
      }

      case "FULL_SNAPSHOT": {
        const s = env.payload as FullSnapshot;
        this.store.applySnapshot(s);
        break;
      }

      case "FRAME_DIFF": {
        const d = env.payload as FrameDiff;
        this.store.applyDiff(d);
        break;
      }

      case "WARN":
      case "ERROR": {
        // Surface via UI in real implementation
        break;
      }

      default:
        // Ignore unknown message types for forward-compat
        break;
    }
  }
}

/** -----------------------------
 * Pixi Scene Graph
 * ------------------------------ */

class PixiScene {
  public app: PIXI.Application;

  private root = new PIXI.Container();
  private roomsLayer = new PIXI.Container();
  private agentsLayer = new PIXI.Container();
  private overlayLayer = new PIXI.Container();
  private uiLayer = new PIXI.Container();

  // Render objects keyed by IDs
  private roomGfx = new Map<number, PIXI.Graphics>();
  private agentGfx = new Map<number, PIXI.Container>();

  constructor(canvasParent: HTMLElement) {
    this.app = new PIXI.Application({
      resizeTo: canvasParent,
      antialias: true,
      backgroundAlpha: 1,
    });

    canvasParent.appendChild(this.app.canvas);

    this.root.addChild(this.roomsLayer, this.agentsLayer, this.overlayLayer, this.uiLayer);
    this.app.stage.addChild(this.root);

    // Basic camera defaults (later: pan/zoom)
    this.root.x = 400;
    this.root.y = 200;
  }

  renderFromState(s: WorldState): void {
    if (s.desynced) {
      this.renderDesyncBanner(s.desyncReason ?? "desync");
      return;
    } else {
      this.clearDesyncBanner();
    }

    this.renderRooms(s);
    this.renderAgents(s);
    this.renderNarrative(s);
  }

  private renderRooms(s: WorldState): void {
    // Ensure stable ordering (rooms are in Map; we sort by room_id)
    const rooms = Array.from(s.rooms.values()).sort((a, b) => a.room_id - b.room_id);

    for (const r of rooms) {
      let g = this.roomGfx.get(r.room_id);
      if (!g) {
        g = new PIXI.Graphics();
        this.roomGfx.set(r.room_id, g);
        this.roomsLayer.addChild(g);
      }

      g.clear();

      // Placeholder: draw bounds as iso-projected rectangle corners
      // Real: tile shapes, walls, zone grouping, etc.
      const p0 = isoProject({ x: r.bounds.x, y: r.bounds.y });
      const p1 = isoProject({ x: r.bounds.x + r.bounds.w, y: r.bounds.y });
      const p2 = isoProject({ x: r.bounds.x + r.bounds.w, y: r.bounds.y + r.bounds.h });
      const p3 = isoProject({ x: r.bounds.x, y: r.bounds.y + r.bounds.h });

      // Do not set explicit colors here to keep skeleton neutral; Pixi requires something,
      // so we use a minimal default stroke.
      g.moveTo(p0.x, p0.y);
      g.lineTo(p1.x, p1.y);
      g.lineTo(p2.x, p2.y);
      g.lineTo(p3.x, p3.y);
      g.lineTo(p0.x, p0.y);
      g.stroke({ width: 1, color: 0xffffff, alpha: 0.4 });
    }
  }

  private renderAgents(s: WorldState): void {
    const agents = Array.from(s.agents.values()).sort((a, b) => a.agent_id - b.agent_id);

    for (const a of agents) {
      let node = this.agentGfx.get(a.agent_id);
      if (!node) {
        node = this.makeAgentNode(a);
        this.agentGfx.set(a.agent_id, node);
        this.agentsLayer.addChild(node);
      }

      // Update position
      const p = isoProject(a.pos);
      node.x = p.x;
      node.y = p.y;

      // Update label
      const label = node.getChildByName("label") as PIXI.Text | undefined;
      if (label) label.text = a.public_state.label;
    }

    // Cleanup despawned agents
    for (const id of Array.from(this.agentGfx.keys())) {
      if (!s.agents.has(id)) {
        const node = this.agentGfx.get(id)!;
        node.destroy({ children: true });
        this.agentGfx.delete(id);
      }
    }
  }

  private makeAgentNode(a: AgentSnapshot): PIXI.Container {
    const c = new PIXI.Container();

    const dot = new PIXI.Graphics();
    dot.circle(0, 0, 4);
    dot.fill({ color: 0xffffff, alpha: 0.9 });
    c.addChild(dot);

    const label = new PIXI.Text({
      text: a.public_state.label,
      style: { fontFamily: "monospace", fontSize: 10, fill: 0xffffff },
    });
    label.name = "label";
    label.y = -18;
    label.x = 8;
    c.addChild(label);

    return c;
  }

  private renderNarrative(s: WorldState): void {
    // Skeleton: no bubbles yet. We keep a hook for it.
    // In Phase 2: attach bubble nodes to agents by entity_id mapping.
    // Example rule: entity_id == agent_id for v0.1.
  }

  private desyncBanner?: PIXI.Container;

  private renderDesyncBanner(reason: string): void {
    if (this.desyncBanner) return;

    const banner = new PIXI.Container();

    const bg = new PIXI.Graphics();
    bg.rect(0, 0, 520, 80);
    bg.fill({ color: 0x000000, alpha: 0.85 });
    banner.addChild(bg);

    const text = new PIXI.Text({
      text: `DESYNC\n${reason}\nClick to request fresh snapshot.`,
      style: { fontFamily: "monospace", fontSize: 12, fill: 0xffffff },
    });
    text.x = 12;
    text.y = 10;
    banner.addChild(text);

    banner.x = 20;
    banner.y = 20;
    banner.eventMode = "static";
    banner.cursor = "pointer";

    banner.name = "desyncBanner";
    this.uiLayer.addChild(banner);
    this.desyncBanner = banner;
  }

  private clearDesyncBanner(): void {
    if (!this.desyncBanner) return;
    this.desyncBanner.destroy({ children: true });
    this.desyncBanner = undefined;
  }

  onDesyncBannerClick(fn: () => void): void {
    // Hook: attach after banner exists
    this.app.ticker.add(() => {
      if (!this.desyncBanner) return;
      // one-time binding
      if ((this.desyncBanner as any).__bound) return;
      (this.desyncBanner as any).__bound = true;
      this.desyncBanner.on("pointertap", fn);
    });
  }
}

/** -----------------------------
 * Minimal UI glue (DOM)
 * ------------------------------ */

function mountHud(store: WorldStore): HTMLElement {
  const hud = document.createElement("div");
  hud.style.position = "absolute";
  hud.style.top = "10px";
  hud.style.right = "10px";
  hud.style.padding = "8px 10px";
  hud.style.background = "rgba(0,0,0,0.5)";
  hud.style.color = "white";
  hud.style.fontFamily = "monospace";
  hud.style.fontSize = "12px";
  hud.style.whiteSpace = "pre";
  hud.style.pointerEvents = "none";

  store.subscribe((s) => {
    const kh = s.kernelHello;
    hud.textContent = [
      `connected: ${s.connected}`,
      `tick: ${s.tick}`,
      `step_hash: ${s.stepHash || "-"}`,
      `kernel: ${kh ? `${kh.engine_name}@${kh.engine_version}` : "-"}`,
      `schema: ${kh ? kh.schema_version : "-"}`,
      `desync: ${s.desynced ? "YES" : "no"}`,
    ].join("\n");
  });

  return hud;
}

/** -----------------------------
 * Offline loader (skeleton)
 * ------------------------------ */

async function startOfflineRun(
  store: WorldStore,
  opts: { baseUrl: string; speed?: number }
): Promise<void> {
  // Minimal contract:
  // - fetch `${baseUrl}/manifest.kvp.json`
  // - load nearest FULL_SNAPSHOT
  // - apply per-tick FRAME_DIFF ops in order
  // - respect run_anchors.tick_rate_hz * speed
  void opts;
  void store;
}

/** -----------------------------
 * App bootstrap
 * ------------------------------ */

export type BootMode = "live" | "offline";
export type BootOpts = {
  mountEl: HTMLElement;
  wsUrl?: string;
  offlineBaseUrl?: string;
  mode?: BootMode;
};

export function bootWebView(opts: BootOpts): void {
  const store = new WorldStore();

  // Pixi
  const scene = new PixiScene(opts.mountEl);
  const hud = mountHud(store);
  opts.mountEl.style.position = "relative";
  opts.mountEl.appendChild(hud);

  // Render loop: redraw on store updates
  store.subscribe((s) => scene.renderFromState(s));

  const mode = (opts.mode ?? import.meta.env.VITE_WEBVIEW_MODE ?? "offline") as BootMode;

  if (mode === "offline") {
    const baseUrl =
      opts.offlineBaseUrl ?? import.meta.env.VITE_WEBVIEW_RUN_BASE ?? "/demo/kvp_demo_1min";
    const speed = parseFloat(import.meta.env.VITE_WEBVIEW_SPEED ?? "1");

    store.setMode("offline");
    store.setConnected(true);
    startOfflineRun(store, { baseUrl, speed });
    return;
  }

  store.setMode("live");

  // KVP client
  const client = new KvpClient(store, {
    url: opts.wsUrl ?? import.meta.env.VITE_KVP_WS_URL ?? "ws://localhost:7777/kvp",
    viewerName: "loopforge-webview-pixi",
    viewerVersion: "0.1.0",
    supportedSchemaVersions: ["1", "sim_sim_1"],
    defaultSubscribe: {
      stream: "LIVE",
      channels: ["WORLD", "AGENTS", "ITEMS", "EVENTS", "DEBUG"],
      diff_policy: "DIFF_ONLY",
      snapshot_policy: "ON_JOIN",
      compression: "NONE",
    },
  });

  // Desync banner action: request fresh snapshot
  scene.onDesyncBannerClick(() => client.requestFreshSnapshot());

  client.connect();
}

/* ============================================================================
 * Usage (example)
 * ----------------------------------------------------------------------------
 * In your main.ts:
 *
 *   import { bootWebView } from "./webview";
 *   bootWebView({
 *     mountEl: document.getElementById("app")!,
 *     mode: "offline",
 *     offlineBaseUrl: "/demo/kvp_demo_1min",
 *   });
 *
 * ========================================================================== */
```
