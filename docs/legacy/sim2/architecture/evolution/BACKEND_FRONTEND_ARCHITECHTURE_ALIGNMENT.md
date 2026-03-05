# Backend–Frontend Alignment for Loopforge Stage

_**(Why we should nudge the backend now instead of only adding more frontend)**_
_(This doc was written at the end of Era II of the frontend by Helios)_

---

## 0. Purpose
This doc is a sanity check before we double-down on post-Era II frontend work.

We’re at a fork:
* Option A: “Backend is fine; keep layering UI on top.”
* Option B: “Backend is fine for analytics, but underspecified for a stage / board / game experience, so we should add a small, expressive layer now.”

My (Helios) conclusion:    
**We need a small, deliberate backend evolution if we actually want a game-like Stage, not just a pretty debugger.**  
The changes can be additive and conservative, but they should be explicit.

---

## 1. Reality check: what the backend currently gives us
Right now the frontend is built around:
* `StageEpisode` (in `_raw`)
* `EpisodeViewModel` (frontend wrapper)
* Per-day aggregates:
  * `day_index`
  * `tension_score`
  * `total_incidents`
  * `supervisor_activity`
  * `perception_mode`
  * `agents: { name → { avg_stress, guardrail_count, context_count, attribution_cause, narrative[] } }`
* Episode-level:
  * `tension_trend`
  * `agents` with start/end stress, totals, trait snapshots
  * `story_arc`, `narrative`, `long_memory` (often sparse/null)

This works well for:
* charts
* summaries
* belief text
* “what happened on Day N?” **debugging**

But critically, it **does not encode**:
* actual **rooms / locations** (we had to invent “Factory Floor” as a synthetic room)
* a **world graph** (how spaces connect)
* **who was where, when** (agent positions or movement)
* intra-day **beats** or events with structure (actor, target, location, type)
* any notion of **scene importance** vs background noise

So the current contract is perfect for a **simulation log / analytics console**, and underpowered for a **stage / board / game** UI.

---

## 2. What the frontend is now expected to become
From the revised vision:
* Phase 4+: **Stage + Story**
  * A visible Stage Map: rooms, tension, active agents.
  * A Story Mode surface: days as scenes, not rows.
* Later:
  * Agent portraits & emotional variants.
  * Micro-motion hooked to events (incidents, shifts, resolutions).
  * Eventually: visualized process (agents moving, interacting).

In visual terms, we’re drifting towards:
* A board-game-like map of the factory (nodes + edges).
* Agents as pieces moving on that board.
* Episodes as runs / scenarios played on that board.

If the backend doesn’t speak in terms compatible with a board, the frontend will have to guess the world from statistical leftovers. That’s doable, but brittle and misaligned with the actual sim.

---

## 3. Where the gaps are (backend vs “stage” frontend)
### 3.1 Spatial model
Current state:
* No explicit rooms.
* No room types (control room, hallway, storage).
* No adjacency graph.
* No room-level stats except those we infer by “everything happens in Factory Floor”.

For a meaningful Stage Map we need at least:
* A **canonical list of rooms** per stage version.
* Optional **layout hints** (“these rooms are adjacent / should sit near each other”).

Without that, the front-end either:
* Hardcodes a fake factory board that may drift from actual sim topology, or
* Stays in “single box with numbers” land.

### 3.2 Time & events
Current state:
* Time resolution is **per day**.
* No intra-day event list.
* Incidents are just a **count**.
* Agent “narrative” is text, not structured events.

For a process-feeling UI, we eventually want:
* A simple sequence of **beats**:
  * timestamp or step index within day
  * location id
  * actor agents
  * optional target agents
  * event type (check, fix, warn, escalate, fail, etc.)
  * severity / tension delta

Even a coarse list (5–20 beats per day) would let us:
* Pulse rooms when something happens.
* Jitter portraits on conflict.
* Make Story Mode cards about **events**, not just averaged mood.

Right now, the frontend has no reliable hook for **“something happened here”** beyond the scalar `total_incidents`.

### 3.3 Causality & belief overlays
Current state:
* Attribution cause is basically stringy (“system”, “random”, etc.).
* No structured mapping `event → believed cause → true cause`.

For the future “belief vs truth light layer” and more intelligent overlays, it would help to have:
* For at least some beats:
  * `true_cause` (system, human, environment, etc.)
  * `agent_belief` (what the agent thought caused it)
* Even if this is sparse, it anchors the visuals to real divergence, not generic labels.

This isn’t required for the next frontend cycle, but it’s worth keeping in mind when designing event structures.

---

## 4. Crucial adjustment: what I’d change in the backend (minimally)
I wouldn’t blow up existing contracts. I’d **add** a small, expressive layer with clear versioning.

### 4.1 Stage world descriptor (per stage version)
New object, wired alongside `StageEpisode`:

```jsonc
StageWorld {
  stage_version: 1,
    rooms: [
      { "id": "control_room", "label": "Control Room", "kind": "control", "layout_hint": { "x": 0, "y": 0 } },
      { "id": "conveyor",    "label": "Conveyor",    "kind": "flow",    "layout_hint": { "x": 1, "y": 0 } },
      { "id": "storage",     "label": "Storage",     "kind": "buffer",  "layout_hint": { "x": 0, "y": 1 } }
    ],
   edges: [
    { "from": "control_room", "to": "conveyor" },
    { "from": "conveyor",     "to": "storage"  }
  ]
}
```
* `layout_hint` is **not** a pixel coordinate, just a small grid or semantic hint.
* Edges allow the frontend to:
  * draw lines between rooms
  * fake agent motion along edges.

Even 3–5 rooms here already gives StageView something real to render.

### 4.2 Stage snapshots per day
Extend `StageEpisode` with an **optional** field:
```jsonc
"stage_snapshots": [
  {
    "day_index": 0,
    "rooms": [
      {
        "room_id": "control_room",
        "tension_score": 0.3,
        "incident_count": 0,
        "active_agents": ["Delta"]
      },
      {
        "room_id": "conveyor",
        "tension_score": 0.6,
        "incident_count": 2,
        "active_agents": ["Nova", "Sprocket"]
      }
    ]
  },
  ...
]
```

* This is essentially the **backend version** of `StageMapViewModel`, but canonical.
* Frontend StageMap VM becomes a thin adapter:
  * “trust backend’s world & room stats; add tier mapping & ordering”.
* We keep `tension_score` & `total_incidents` at the day level for analytics, but now have a spatial decomposition.

This small addition massively reduces heuristics and opens the door to:
* per-room highlighting
* room-level narratives (“Conveyor was the hotspot on Day 1”)
* smarter Story Mode (“Scene in Storage with Sprocket…”)

### 4.3 Optional: intra-day event skeleton
If we can afford one more small schema now, I’d add:
```jsonc
"events": [
  {
    "day_index": 1,
    "step": 3,
    "room_id": "conveyor",
    "actors": ["Nova"],
    "targets": ["system"],
    "event_type": "check_failed",
    "severity": 0.8,
    "true_cause": "system",
    "agent_beliefs": {
      "Nova": "system"
    }
  }
]
```

This doesn’t need to be exhaustive or high-frequency. Even a handful of events per day unlock:
* micro-motion (shake Nova’s icon on this beat)
* timeline overlays in StageView
* seeds for future belief overlays

However, if we have to choose, I’d do **`StageWorld`** + **`stage_snapshots`** first, then events later.

---

## 5. Why not “just do it in the frontend”?
We _can_ fake a lot in the frontend:
* assume a fixed set of rooms
* split tension heuristically
* invent a layout
* infer “primary room” from maybe some keyword in narrative

But that has downsides:
**5.1 Drift**  
The “visual fiction” diverges from actual sim behavior. Over time, nobody knows whether the map is canonical or just vibes.
**5.2 Duplication**  
If other consumers (CLI tools, notebooks, future UIs) want a notion of rooms, they’ll have to re-invent the same heuristics.
**5.3 Lost opportunity**  
The simulation does have an internal notion of world and events. Not exposing a minimal version leaves visual power on the table.
**5.4 Harder future work**  
When we later decide to expose rooms/events anyway, we’ll have to un-hack the frontend, replace heuristics, and migrate tests.

Given you already see Loopforge as “at least a board game”, I’d rather align the backend now with **where we know the product is going**, instead of letting the frontend mythologize a world on top.

---

## 6. Recommendation

If we want Loopforge to remain “a pretty debugger for nerds”, the backend is fine. We can keep polishing, add Story Mode purely on day-level data, and stop there.

But if we actually want:
* a **visible world** (Stage),
* a **cast** that occupies that world,
* and **episodes as runs on that board**,

then my recommendation as Helios is:

> **Run a small, backend-expressive alignment sprint now.**

Scope:
1. Introduce `StageWorld` (rooms + simple layout + edges) per stage version.
2. Add optional `stage_snapshots[day_index].rooms` with `tension/incidents/active_agents`.
3. Keep everything additive and versioned; do not break existing consumers.
4. Optionally sketch a minimal `events` schema, even if we don’t populate it fully yet.

Once that is in place, the next frontend architect can:
* upgrade StageMap from “box with text” to an actual board,
* implement Story Mode that references real locations,
* and later wire micro-motion to real events instead of generic deltas.

In other words: this adjustment lets the **backend tell the truth in a form the stage can actually stage**, instead of asking the frontend to improvise a play from partial logs.