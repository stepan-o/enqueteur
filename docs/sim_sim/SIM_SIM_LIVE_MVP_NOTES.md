# sim_sim LIVE MVP Plumbing + `sim_sim_1` Contract

## A) Current plumbing findings

### 1) Frontend schema routing (`engine_name`, `schema_version`)
- Registry and resolver:
  - `frontend/loopforge-webview/src/viewers/core/viewerPlugin.ts`
- Registration and activation (sim4 + sim_sim):
  - `frontend/loopforge-webview/src/app/boot.ts`
- KERNEL_HELLO-driven selection:
  - `frontend/loopforge-webview/src/kvp/client.ts`
  - `pluginRegistry.resolve(hello.engine_name, hello.schema_version)`

### 2) sim_sim viewer implementation files
- Plugin bridge:
  - `frontend/loopforge-webview/src/viewers/sim_sim/simSimPlugin.ts`
- State model + snapshot/diff apply:
  - `frontend/loopforge-webview/src/viewers/sim_sim/simSimStore.ts`
- Rendering (PIXI world + DOM HUD/cards/feed/debug panel):
  - `frontend/loopforge-webview/src/viewers/sim_sim/simSimScene.ts`

### 3) Envelope validation + msg_type dispatch + lifecycle
- Envelope decode/validation and dispatch:
  - `frontend/loopforge-webview/src/kvp/client.ts`
- Expected order in LIVE:
  1. `VIEWER_HELLO` (out)
  2. `KERNEL_HELLO` (in)
  3. `SUBSCRIBE` (out)
  4. `SUBSCRIBED` (in)
  5. `FULL_SNAPSHOT` (in)
  6. `FRAME_DIFF` (in, per tick)

### 4) sim_sim backend snapshot/diff builders and channels
- Session orchestration + HELLO/SUBSCRIBE/INPUT handling:
  - `backend/sim_sim/live/session_host.py`
- WebSocket transport (Text JSON frames only):
  - `backend/sim_sim/live/ws_server.py`
- `sim_sim_1` projection + payload builders:
  - `backend/sim_sim/projection/kvp_schema1.py`
- Deterministic day kernel/state evolution:
  - `backend/sim_sim/kernel/state.py`
- Channel mapping currently uses KVP v0.1 channels:
  - `WORLD`, `AGENTS`, `ITEMS`, `EVENTS`, `DEBUG`

## B) `sim_sim_1` minimal contract (MVP)

### FULL_SNAPSHOT payload (`msg_type = FULL_SNAPSHOT`)

| Field | Type | Notes |
|---|---|---|
| `schema_version` | string | MUST be `"sim_sim_1"` |
| `tick` | int | current day tick |
| `step_hash` | string | canonical hash over projected subscribed state |
| `state.world_meta` | object | `{day,phase,time,tick_hz,seed,run_id,world_id,security_lead}` |
| `state.rooms[]` | array | room metrics for room_id 1..6 |
| `state.supervisors[]` | array | `{code,assigned_room,loyalty,confidence,influence,cooldown_days}` |
| `state.inventory` | object | `{cash,inventories{raw/washed/substrate/ribbon}}` |
| `state.regime` | object | regime flags/modifiers |
| `state.events[]` | array | `{tick,event_id,kind,room_id?,supervisor?,details?}` |
| `state.debug` | object (optional) | debug-only info |

### Room shape (`state.rooms[]`)
- `room_id`, `name`, `locked`, `supervisor`
- `workers_assigned {dumb,smart}`
- `workers_present {dumb,smart}`
- `equipment_condition`, `stress`, `discipline`, `alignment` (0..1)
- `output_today {raw_brains_dumb,raw_brains_smart,washed_dumb,washed_smart,substrate_gallons,ribbon_yards}`
- `accidents_today {count,casualties}`

### FRAME_DIFF payload (`msg_type = FRAME_DIFF`) — chosen semantics: Option 2

Structured updates by collection (only changed parts emitted):

| Field | Type | Notes |
|---|---|---|
| `schema_version` | string | MUST be `"sim_sim_1"` |
| `from_tick` | int | previous tick |
| `to_tick` | int | MUST equal `from_tick + 1` |
| `prev_step_hash` | string | hash chain guard |
| `world_meta_update` | object (optional) | replace world_meta |
| `room_updates[]` | array (optional) | changed room objects (by `room_id`) |
| `supervisor_updates[]` | array (optional) | changed supervisors (by `code`) |
| `inventory_update` | object (optional) | replace inventory |
| `regime_update` | object (optional) | replace regime |
| `events_append[]` | array (optional) | append-only event rows |
| `step_hash` | string | resulting state hash at `to_tick` |

Determinism guarantees:
- Rooms sorted by `room_id`
- Supervisors sorted by `code`
- Events sorted by `(tick,event_id)` and append-only per tick transition

## Local verification

1. Start backend:
   - `python -m backend.sim_sim.app.main --mode interactive --live`
2. Start webview:
   - `cd frontend/loopforge-webview && npm run dev`
3. In UI:
   - `Go to factory` -> `LIVE (sim_sim)`
4. In Chrome DevTools (Network -> WS):
   - Confirm `ws://localhost:7777/kvp` opens (`101`)
   - Confirm all protocol frames are **Text**
   - Confirm sequence: `VIEWER_HELLO` -> `KERNEL_HELLO` -> `SUBSCRIBE` -> `SUBSCRIBED` -> `FULL_SNAPSHOT`
5. In sim_sim CLI:
   - type `next` (or Enter)
   - confirm incoming `FRAME_DIFF`
   - confirm HUD tick/day, at least one room metric/inventory number, and live feed update
6. Click `Exit to menu`:
   - confirm socket closes cleanly
