# Loopforge Stage Viewer — Backend Dev Notes (Phase 1 Prep)

This document is for developers wiring a frontend Stage Viewer to the Loopforge backend during Phase 1. It describes how to run the API server, what endpoints are available, a sample `StageEpisode` JSON, and a few notes for local development.

## Run the API

Two ways to run the server locally:

1) Via CLI (recommended):

```
uv run loopforge-sim api-server
```

This starts a FastAPI app at:
- Base URL: http://localhost:8000
- Docs (Swagger): http://localhost:8000/docs

2) Direct uvicorn:

```
uv run uvicorn loopforge.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Notes:
- The app installs CORS for the Vite dev server origins:
  - http://localhost:5173
  - http://127.0.0.1:5173
- All methods and headers are allowed during Phase 1 for ease of development.

Health check:
- GET http://localhost:8000/health → `{ "status": "ok" }`

## Episode Endpoints

Base path: `http://localhost:8000`

- GET `/episodes` → List available episodes from the read-only registry
  - Response (example):
    ```json
    [
      { "episode_id": "ep-123", "run_id": "run-abc", "episode_index": 0, "days": 3, "created_at": "2025-01-01T00:00:00+00:00" }
    ]
    ```

- GET `/episodes/{episode_id}` → Full `StageEpisode` JSON
  - Built on-demand via: registry → analysis → stage builder
  - Returns fully populated stage JSON safe for UI consumption

- GET `/episodes/{episode_id}/raw` (optional) → Raw `EpisodeSummary` export for debugging

All endpoints are read-only and do not modify simulation or logs.

## StageEpisode JSON (example)

Important: the Stage schema includes a version field for UI compatibility checks.

```json
{
  "episode_id": "ep-123",
  "run_id": "run-abc",
  "episode_index": 0,
  "stage_version": 1,
  "tension_trend": [0.1, 0.2, 0.3],
  "days": [
    {
      "day_index": 0,
      "perception_mode": "accurate",
      "tension_score": 0.2,
      "agents": {
        "Alpha": {
          "name": "Alpha",
          "role": "scout",
          "avg_stress": 0.3,
          "guardrail_count": 1,
          "context_count": 2,
          "emotional_read": null,
          "attribution_cause": null,
          "narrative": []
        }
      },
      "total_incidents": 0,
      "supervisor_activity": 0.0,
      "narrative": []
    }
  ],
  "agents": {
    "Alpha": {
      "name": "Alpha",
      "role": "scout",
      "guardrail_total": 2,
      "context_total": 3,
      "stress_start": 0.2,
      "stress_end": 0.4,
      "trait_snapshot": null,
      "visual": "",
      "vibe": "",
      "tagline": ""
    }
  },
  "story_arc": null,
  "narrative": [],
  "long_memory": null,
  "character_defs": null
}
```

Notes:
- All nested objects are JSON-safe.
- Datetimes (when present) are ISO-8601 strings.
- Narrative text may contain newlines; the API preserves them.
- Optional fields may be `null` or empty containers; the UI should handle both.

## CLI Export (optional, useful for snapshots)

Export a StageEpisode JSON without running the server:

```
uv run loopforge-sim export-stage-episode \
  --run-id RUN123 \
  --episode-index 0 \
  --output logs/stage_episode.json
```

## Phase 1 Goals (short)

- Deliver a stable, read-only Stage backend with CORS enabled for local frontend work.
- Provide a fully populated `StageEpisode` JSON including `stage_version` for UI compatibility.
- Keep simulation, logs, and seam behavior unchanged (additive only).

– Junie
