# 🌟 Era III Types — What They Must Capture & How They Are Used

Types in Sim3 are not decorative.  
They are the **backbone** of the backend because:
* every module will depend on them,
* they define the **shape of data** moving between **layers**,
* they anchor the contract with the **frontend** (`StageEpisodeV2`),
* and they establish the **abstractions** that keep Sim3 manageable.

To avoid another messy import hell later, we define types properly from the start.

---

## 📦 1. Types Must Capture 5 Major Domains
### 1.1 Identity Types
(What agents are.)

These types define:

#### A. AgentTypeDefinition
* base traits
* vibe
* archetype
* stress profile
* color theme
* narrative hooks

#### B. RoleIdentity
* role name
* stress multipliers
* room affinity
* narrative role tags

#### C. AgentInstanceConfig
Scenario-level definition:
```text
id
type
role
presets (optional overrides)
```

#### D. AgentCharacterSheet
UI-facing character sheet  
(For StageEpisodeV2 `cast[]`)

#### Where They Are Used
| Module                       | 	Uses identity types to…                |
|------------------------------|-----------------------------------------|
| `identity/resolver.py`       | 	merge type+role+instance → agent state |
| `state/agent_state.py`       | 	create runtime agent object            |
| `episode/episode_builder.py` | 	build cast[]                           |
| `sim/controller.py`          | 	access stress multipliers, traits      |
| `recorder/trace_recorder.py` | 	annotate events with agent info        |

Identity types are critical—they are the **DNA** of every agent.

---

### 1.2 World Types
(What the world is.)

These types define:

#### A. WorldIdentity
Static world definition from registry:
* id
* name
* zones
* adjacency
* traits
* size
* description

#### B. RoomIdentity
* id
* label
* kind
* hazards
* base tension
* adjacency

#### C. RoomSnapshot / WorldSnapshot
UI-ready world representation  
(Used in StageEpisodeV2 `world`)

#### Where They Are Used
| Module                       | 	Purpose                             |
|------------------------------|--------------------------------------|
| `world/world_registry.py`    | 	stores WorldIdentity                |
| `world/snapshot_builder.py`  | 	converts identity → snapshot        |
| `state/world_state.py`       | 	runtime tension, events, room state |
| `episode/episode_builder.py` | 	build world section of episode      |

World types describe the board of the simulation.

---

### 1.3 Event & Time Types
(What happens, and when.)

Sim3 must model:
* ticks → beats → scenes → days
* tension curves
* incidents
* room transitions
* supervisor activity
* narrative labels

They include:
#### A. TickEvent
Atomic event emitted at each tick.

#### B. BeatMetadata
Collected ticks that form a "moment".

#### C. SceneUnit
Derived from beats.

#### D. DaySummary
Aggregate for each day.

#### E. DayWithScenes
DaySummary + scenes list.

#### F. EpisodeMood
For episode header banner.

#### Where They Are Used
| Module                       | 	Purpose                             |
|------------------------------|--------------------------------------|
| `sim/event_emitter.py`       | 	creates TickEvent                   |
| `sim/beat_engine.py`         | 	groups ticks into beats             |
| `sim/scene_trigger.py`       | 	produces SceneUnit                  |
| `sim/day_engine.py`          | 	produces DaySummary                 |
| `recorder/trace_recorder.py` | 	stores beats/scenes/ticks           |
| `episode/episode_builder.py` | 	builds StageEpisodeV2 days/scenes   |

These types define the temporal architecture of storytelling.

---

### 1.4 Runtime State Types
(What the sim currently is.)

These include:
#### A. WorldState
* dynamic room tension
* hazards active
* room occupancy

#### B. AgentState
* current traits
* room
* stress
* status flags
* pending actions

#### C. SimState
* world state
* all agent states
* tick count
* day index
* rng seed
* scenario parameters

#### Where They Are Used
| Module                       | 	Purpose                             |
|------------------------------|--------------------------------------|
| `sim/controller.py`          | 	tick logic reads & writes state     |
| `state/world_state.py`       | 	holds dynamic world data            |
| `state/agent_state.py`       | 	holds dynamic agent data            |
| `recorder/trace_recorder.py` | 	snapshot of tick state              |
| `episode/episode_builder.py` | 	derive summaries & mood             |

Runtime types represent the live evolving simulation.

### 1.5 Episode Output Types
(The **only thing** the UI receives.)

These include:
#### A. EpisodeMeta
scenario → episode identity

#### B. StageEpisodeV2
Full output payload (see more details in section 4):
```text
version
episode
world
cast
days
episodeMood
tensionTrend
```

#### Where They Are Used
| Module                       | 	Purpose          |
|------------------------------|-------------------|
| `episode/episode_builder.py` | 	final assembly   |
| frontend                     | 	reads everything |

These types are the contract with the frontend.

## 🧩 2. How Types Are Organized

Recommended structure:
```text
loopforge_sim3/types/
  identity_types.py
  world_types.py
  event_types.py
  runtime_types.py      ← top-level Episode output types
```

`runtime_types.py` only includes:
* RoomSnapshot
* WorldSnapshot
* AgentCharacterSheet
* SceneUnit
* DaySummary
* DayWithScenes
* EpisodeMeta
* EpisodeMood
* StageEpisodeV2

Identity/world/time/runtime state types live in separate files to avoid circular imports.

## 🔗 3. How Types Are Used Across the Backend
**Identity types**
→ feed into AgentState and Cast Snapshot

**World types**
→ feed into WorldState and WorldSnapshot

**Simulation State types**
→ used by controller, event emitter, recorder

**Event/Time types**
→ used by beat/scenes/days engines + recorder

**Episode output types**
→ final output for UI

The flow is:
```text
Identity + World + Scenario → SimState → Ticks → Beats → Scenes → Days
→ EpisodeBuilder → StageEpisodeV2 (UI)
```

Types are the schema that ensures this flow works.

## 4. Frontend-backend contract - StageEpisode v2 – Schema

### 4.1 Design goals for frontend Era III
What this spec is trying to unlock **visually**:
* **A board-like Stage map**:
  * 4–7 canonical rooms with a stable layout.
  * Tension / activity highlighting per day.
* **A Day strip + storyboard**:
  * Each day is a scene “tile”, not just a row in a table.
* **Character presence**:
  * Each agent has a “sheet” (name, role, vibe, color, archetype) for avatars and story beats.
* **A Story surface**:
  * Per-day scenes with short narrative summaries tied to rooms + agents.
* **A top-level mood banner**:
  * Episode arc (calm/escalating/volatile/decompression) with a 1–2 line summary.

This is the minimum for the next frontend architect to make StageView feel like a world with a cast and scenes — not an analytics console.

---

### 4.2 StageEpisode v2 – Schema
This is the expected format of the final output from the backend.

#### Top-level
```ts
export type StageEpisodeV2 = {
  version: "stage-episode-v2";

  episode: EpisodeMeta;          // episode id, run id, scenario, timing
  world: WorldSnapshot;          // room layout + base properties for Stage map
  cast: AgentCharacterSheet[];   // character sheets (for avatars, chips, cameos)
  days: DayWithScenes[];         // ordered day list with tension + scenes
  episodeMood: EpisodeMood;      // banner-level arc + summary
  tensionTrend: number[];        // 0–1 per day (aligned with days[index])
};
```

---

#### Episode meta
```ts
export type EpisodeMeta = {
  id: string;                  // "ep-123"
  runId: string;               // "run-123"
  index: number;               // 0-based, within run
  stageVersion: number;        // to keep in sync with Stage config
  scenarioId: string;          // "factory-baseline", "night-shift", etc.
  scenarioName: string;        // human label: "Baseline Day Shift"
  startedAt?: string;          // ISO timestamp
  totalTicks?: number;         // total sim ticks (optional, debug/graphs)
};
```

---

#### World (Stage board)
```ts
export type WorldSnapshot = {
  id: string;                     // "factory-v1"
  name: string;                   // "Main Factory Floor"
  layoutKind: string;             // e.g. "factory-board-v1"
  rooms: WorldRoom[];
};

export type WorldRoom = {
  id: string;                     // "control-room"
  label: string;                  // "Control Room"
  kind: string;                   // "control" | "floor" | "storage" | ...
  // Board layout — interpreted as a normalized board coordinate system.
  position: { x: number; y: number };  // 0–1 or small integer grid
  size?: { w: number; h: number };     // optional, for larger rooms
  adjacency: string[];                 // neighbor room ids

  baseTensionTier: TensionTier;        // default mood of this room
  visualTags?: string[];               // e.g. ["industrial", "bright", "noisy"]
};
```

The **frontend can**:
* Render rooms as tiles on a fixed board using `position`/`size`.
* Use `kind` + `visualTags` to choose icons/styles.
* Show adjacency as subtle connectors (optional).

---

#### Agents (cast)
```ts
export type AgentCharacterSheet = {
  id: string;                 // internal stable id, maps to logs
  displayName: string;        // "Sprocket"
  shortName?: string;         // "Spr." for tiny chips

  role: string;               // "Line Worker", "Supervisor"
  type: string;               // "WorkerBot", "SupervisorBot"

  vibe: string;               // "earnest tinkerer", "tense overseer"
  archetype: string;          // semantic visual hook, e.g. "tired_supervisor"

  colorTheme: string;         // token, e.g. "blue", "amber" (frontend maps to palette)
  iconKey?: string;           // semantic key, e.g. "qa-bot", "optimizer"

  // Optional, but useful for Story/avatars
  stressProfile?: {
  baseline: number;         // 0–1
  volatility: number;       // 0–1
  };

  narrativeHooks?: string[];  // 1–3 short phrases for tooltips/story, e.g.
  // ["worries about throughput", "hates surprise faults"]
};
```

Frontend uses this to render:
* Agent chips on Stage map / DayStory.
* Agent avatar panels.
* Names + colors in Story scenes.

Backend doesn’t need to deal with actual portrait URLs; `colorTheme` + `iconKey` + `archetype` is enough for UI to pick visuals.

---

#### Days + Scenes
```ts
export type DayWithScenes = DaySummary & {
  scenes: SceneUnit[];        // ordered list of key beats for this day
};

export type DaySummary = {
  index: number;              // 0-based
  label: string;              // "Day 1", "Ramp-up", "Night Shift"

  tensionScore: number;       // 0–1
  tensionTier: TensionTier;   // "low" | "medium" | "high" | "critical"

  primaryRoomId: string;      // main location for this day on the Stage
  totalIncidents: number;     // count of notable events
  supervisorActivity: number; // normalized 0–1 (messages/actions)

  dominantAgents: string[];   // agent ids who “define” the day (1–3)
  summary: string;            // 1–2 sentences: “Quiet start, minor jams in Line A…”
};
```

`DaySummary` drives:
* Day storyboard tiles.
* Tension strip (the existing graph).
* Day detail header.

---

#### Scenes (for Story view and “beats” in StageView)
```ts
export type SceneUnit = {
  id: string;                 // "d1-s0", "d1-s1", etc.
  dayIndex: number;           // redundant but convenient
  index: number;              // order within the day

  timeCode: number;           // tick/beat index in the sim (monotonic)
  mainRoomId: string;         // room where this scene “happens”
  involvedAgents: string[];   // agent ids, 1–4 typical

  tensionTier: TensionTier;   // scene-level tier (can differ from day average)
  tensionDelta?: number;      // optional, signed change vs previous scene/day

  summary: string;            // short line: “Nova arrives late, line tension rises.”
  narrativeTags?: string[];   // ["arrival", "fault", "calm-down"]
};
```

Frontend can:
* Render a **Story strip**: card per scene, grouped by day.
* Use `mainRoomId` to highlight the room when hovering the scene.
* Use `involvedAgents` to show avatars on each scene card.
* Use `tensionTier` to color the scene border/glow.

---

#### Episode mood
```ts
export type EpisodeMood = {
  tier: "calm" | "rising" | "volatile" | "decompression";
  summary: string;            // “Behavior remains relatively steady.”
  dominantColor?: string;     // optional token, e.g. "green", "amber", "red"
};
```

Drives the banner you already have (`Steady State`, `Escalating`, etc.).

---

#### Shared helpers
```ts
export type TensionTier = "low" | "medium" | "high" | "critical";
```

### 4.3. How this maps to the Era III UI
#### StageView (main surface)
* Uses `world.rooms` for the board.
* Uses `days[currentDay].primaryRoomId` to:
  * highlight the “focus” room,
  * maybe draw a subtle pulse.
* Uses `days[currentDay].dominantAgents` and `cast[]` to show avatars.
* Uses `scenes` to:
  * show a few key beats alongside the board,
  * hover a scene → jump highlight to `scene.mainRoomId`.

#### Day strip / storyboard
* Uses `days[].tensionScore` + `tensionTrend[]` to render:
  * the existing tension graph,
  * plus more expressive per-day tiles (size/glow by tier).
* `days[].summary` becomes the textual caption under each card.

#### Story “panel” / StoryMode v0
* Renders `DayWithScenes.scenes` as cards:
  * each with `summary`, `involvedAgents` avatars, room pill, small tension bar.
* Moving selection in Story strips updates Stage highlight via `mainRoomId`.

#### Character presence
* `cast[]` powers:
  * Agent sidebar,
  * Cameos in scenes,
  * Chips on Stage rooms (e.g. “who’s usually here?” if you choose).

---

### 4.4. Tiny example payload (trimmed)

Just to see it in one piece (highly abbreviated):
```json
{
  "version": "stage-episode-v2",
  "episode": {
    "id": "ep-123",
    "runId": "run-123",
    "index": 1,
    "stageVersion": 2,
    "scenarioId": "factory-baseline",
    "scenarioName": "Baseline Day Shift",
    "startedAt": "2025-11-25T09:00:00Z",
    "totalTicks": 480
  },
  "world": {
    "id": "factory-v1",
    "name": "Main Factory Floor",
    "layoutKind": "factory-board-v1",
    "rooms": [
      {
        "id": "control-room",
        "label": "Control Room",
        "kind": "control",
        "position": { "x": 0.1, "y": 0.1 },
        "size": { "w": 0.2, "h": 0.2 },
        "adjacency": ["line-a", "charging-bay"],
        "baseTensionTier": "medium",
        "visualTags": ["screens", "overlook"]
      },
      {
        "id": "line-a",
        "label": "Line A",
        "kind": "floor",
        "position": { "x": 0.4, "y": 0.3 },
        "size": { "w": 0.4, "h": 0.2 },
        "adjacency": ["control-room", "storage"],
        "baseTensionTier": "high",
        "visualTags": ["noisy", "conveyor"]
      }
    ]
  },
  "cast": [
    {
      "id": "sprocket",
      "displayName": "Sprocket",
      "role": "Line Worker",
      "type": "WorkerBot",
      "vibe": "earnest tinkerer",
      "archetype": "overloaded_worker",
      "colorTheme": "blue",
      "iconKey": "worker-bot",
      "stressProfile": { "baseline": 0.4, "volatility": 0.7 },
      "narrativeHooks": [
        "takes pride in smooth runs",
        "gets anxious when faults pile up"
      ]
    }
  ],
  "days": [
    {
      "index": 0,
      "label": "Day 1",
      "tensionScore": 0.3,
      "tensionTier": "low",
      "primaryRoomId": "line-a",
      "totalIncidents": 1,
      "supervisorActivity": 0.2,
      "dominantAgents": ["sprocket"],
      "summary": "Quiet shift with a single minor jam on Line A.",
      "scenes": [
        {
          "id": "d0-s0",
          "dayIndex": 0,
          "index": 0,
          "timeCode": 45,
          "mainRoomId": "line-a",
          "involvedAgents": ["sprocket"],
          "tensionTier": "medium",
          "tensionDelta": 0.2,
          "summary": "A minor jam on Line A makes Sprocket visibly tense.",
          "narrativeTags": ["fault", "jam"]
        }
      ]
    }
  ],
  "episodeMood": {
    "tier": "rising",
    "summary": "A calm start with hints of mounting pressure on the line.",
    "dominantColor": "amber"
  },
  "tensionTrend": [0.3]
}
```