📘 PHASE 0 — STAGE API FOUNDATIONS (SPEC)

Status: Ready for implementation
Architect: Stagemaker (Design)
Engineer: Junie
Scope: 1–2 sprints (tight but feasible)

🎯 PHASE 0 PURPOSE

This phase establishes the canonical data contract for all future visualizations, cinematic tooling, and producer consoles.

This includes:

Defining StageEpisode, the single source of truth for what the Stage Viewer will receive.

Adding a Stage builder (loopforge.stage) that transforms existing summaries + narrative into StageEpisode objects.

Exposing StageEpisode(s) via a small FastAPI service layer under loopforge.api.

Ensuring run metadata is retrievable (via DB or file-based registry if DB not required).

Adding minimal CLI integration for local testing.

No frontend is built yet.
This phase is entirely backend and sets the foundation for all future Stage phases.

🧩 SCOPE & DELIVERABLES
1. Introduce the Stage Layer (loopforge.stage)
1.1 Create module structure
loopforge/
  stage/
    __init__.py
    stage_episode.py
    builder.py
    errors.py        # (optional)

1.2 Define StageEpisode data model

Placed in either:

loopforge.schema.stage_types (preferred for long-term stability)

or in loopforge.stage.stage_episode (if you want it closer to implementation)

Fields (finalized after internal discussion):

@dataclass
class StageEpisode:
    episode_id: str

    # Basic metadata
    created_at: datetime | None = None
    steps_per_day: int | None = None
    days: list[StageDay] = field(default_factory=list)

    # Episode-level metrics
    tension_trend: list[float] = field(default_factory=list)
    story_arc: StoryArc | None = None
    long_memory: dict[str, LongMemorySnapshot] = field(default_factory=dict)

    # Per-agent episode-level stats
    agents: dict[str, StageAgentSummary] = field(default_factory=dict)


And child types:

StageDay

StageAgentDayView

StageAgentSummary

StageAgentTraits (optional)

StageNarrativeBlock (for intro/outro/agent beats)

Goal:
Everything the UI might need in the next 12 months should be in this data model.
No UI-specific transformation logic here — just structured data.

1.3 Write Stage builder logic

Create:

loopforge/stage/builder.py


with function:

def build_stage_episode(
    episode_summary: EpisodeSummary,
    day_summaries: list[DaySummary],
    story_arc: StoryArc | None,
    long_memory: dict[str, LongMemorySnapshot] | None,
    character_defs: dict[str, Character] | None = None,
) -> StageEpisode:
    ...


This function:

Extracts:

per-day tension, incidents, avg agent stress

guardrail/context counts

daily emotional reads (already in day_summary)

Injects:

narrative lines from loopforge.narrative.*

agent arcs from EpisodeSummary

Assembles into the StageEpisode format.

Success Criteria:
StageEpisode must fully capture everything required for Phase 1 & Phase 2 UI without needing to re-call narrative/analytics after Phase 0.

2. Build or extend a Run Registry

You already have run/episode identifiers produced by the sim CLI.
Phase 0 only needs:

list episodes

get episode by ID

Two options:

Option A — Use existing DB registry (preferred if already present)

Add minimal read endpoints to retrieve:

run metadata

episode metadata

Option B — Minimal filesystem registry

Each run writes a JSON manifest to:

logs/run_registry.json
logs/<run_id>/episode_0.json


This is simpler and enough for Phase 0.

3. Introduce API layer (loopforge.api)
3.1 Module structure
loopforge/
  api/
    __init__.py
    app.py
    routers/
      episodes.py
      runs.py (optional)

3.2 Add core endpoints
GET /episodes

Returns a list of available episodes:

[
  { "episode_id": "run-2025-001-0", "created_at": "...", "days": 3 }
]

GET /episodes/{id}

Returns full StageEpisode JSON.

{
  "episode_id": "run-2025-001-0",
  "days": [...],
  "agents": {...},
  ...
}


Optionally:

GET /episodes/{id}/raw

Returns the raw export-episode output for debugging.

3.3 API Server

Provide a simple entrypoint:

uv run loopforge-sim api-server


Runs FastAPI with uvicorn inside Docker or natively.

Speed is unimportant: episodes are not huge.

4. CLI Integration

Add new CLI commands:

loopforge-sim export-stage-episode \
    --run-id ... --episode-index ... \
    --output stage_episode.json


and:

loopforge-sim api-server


This ensures Phase 0 is testable without a UI.

5. Documentation

Add two docs:

docs/stage_episode.md

Full JSON schema

Serialization rules

Field-level descriptions

docs/api_overview.md

Endpoints

Expected inputs/outputs

Example usages

Phase 0 Completion Definition

Phase 0 is complete when:

StageEpisode type is finalized and versioned.

loopforge.stage.builder produces StageEpisode from real episodes.

GET /episodes and GET /episodes/{id} return correct JSON.

CLI can export StageEpisodes.

Tests exist for StageEpisode correctness.

No frontend yet.

This phase establishes the structural backbone for everything else.

🗂️ SPRINT PLAN FOR PHASE 0

Below is a concrete breakdown of what Junie should focus on.

Sprint 0.1 — Stage Types + Builder Skeleton

Goal: Stand up the Stage layer with typed models & first builder logic.

Tasks

 Create loopforge.stage module.

 Define StageEpisode and related data classes.

 Decide whether Stage DTOs live in schema or stage.
(Preferred: schema.stage_types)

 Write builder skeleton:

input parameters

stub fields

mapping EpisodeSummary → StageEpisode structure

 Add unit tests with fixtures based on fake summaries.

Acceptance Criteria

StageEpisode and StageDay structures are importable and validated.

Builder returns a structurally correct StageEpisode (with dummy/fake values where needed).

No API yet, but build_stage_episode can be tested.

Estimated time: ~1 sprint
Sprint 0.2 — API Layer + Real Episode Assembly

Goal: Produce real StageEpisode objects and expose them via FastAPI.

Tasks

 Create loopforge.api with FastAPI app.

 Add /episodes and /episodes/{id} routes.

 Connect run registry:

Option A: DB integration

Option B: simple file-based registry

 Integrate with existing sim export logic:

analytics.analyze_episode

narrative pieces

 Write real builder code:

populate all StageEpisode fields

ensure correct placement of narrative + metrics

 Add CLI command to manually export StageEpisode JSON.

Acceptance Criteria

Calling GET /episodes/{id} returns a real StageEpisode assembled from:

EpisodeSummary

DaySummary

StoryArc

LongMemory

Narrative text blocks

The episode viewer can rely on this JSON format without future breaking changes.

API runs in Docker environment.

Estimated time: ~1 sprint
Optional Mini-Sprint: StageEpisode Polish

If time remains or if sprint 0.2 surfaces mismatches.

Tasks

 Add richer metadata (run configuration, seed, durations)

 Improve narrative mapping

 Normalize per-agent stats for UI friendliness

 Add field versioning (stage_version=1)

Estimated time: 0.5 sprint (optional)
📌 TOOLS CONFIRMATION

Everything in Phase 0 uses existing stack:

uv for running CLI/linters/tests

Python 3.11+

Postgres + Alembic (optional unless using DB registry)

Docker for local deployment

FastAPI (new dependency but trivial to add)

Uvicorn for local run

No additional tools, engines, or frontend frameworks needed.