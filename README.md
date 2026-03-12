# Enqueteur

Enqueteur is a deterministic living-world investigation game runtime, currently scoped to MBAM Case 1.

## Canonical Local Runtime

- Canonical runtime host: Python ASGI backend (`backend/server`) on `127.0.0.1:7777`.
- Frontend: separate Vite dev server (`frontend/enqueteur-webview`) on `127.0.0.1:5173`.
- Canonical local launch/connect path:
  - `POST /api/cases/start`
  - `WS /live?run_id=...`
- Vite proxy is not required for local play. Backend remains the source of runtime truth.

## Local Setup

Install Python deps (including host + test extras):

```bash
uv sync --extra dev --extra server
```

Install frontend deps:

```bash
make web-install
```

## Run Local Live Playtest

Terminal A (backend):

```bash
make server-dev
```

Terminal B (frontend):

```bash
make web-dev-local
```

Open `http://127.0.0.1:5173` and follow the normal UI path:

1. Loading
2. Main Menu
3. Case Select
4. Connecting
5. Live Game

Blessed daily local playtest path:

- Case: `MBAM_01`
- Seed: `A`
- Difficulty: `D0`
- Mode: `playtest`

Shared playtest standard (daily smoke, canonical full manual, and B/C sweep) is defined in [Local Playtest Workflow](docs/enqueteur/local_playtest_workflow.md#locked-playtest-standard).

## Basic Verification

Backend readiness:

```bash
curl http://127.0.0.1:7777/readyz
```

Expected: JSON with `"status": "ready"` while server is running.

When local play is working:

- case launch from the UI succeeds (no backend unreachable error),
- Connecting screen advances through handshake,
- app reaches Live Game after baseline snapshot.

## Tests

Backend:

```bash
make test
```

Focused backend host checks:

```bash
uv run -m pytest backend/sim4/tests/integration/test_server_shell_s1.py backend/sim4/tests/integration/test_server_shell_s2_app_launch.py backend/sim4/tests/integration/test_server_shell_s4_live_ws_asgi.py -q
```

Frontend:

```bash
cd frontend/enqueteur-webview
npm test
```

## Troubleshooting

- `BACKEND_UNREACHABLE` in UI: backend is not running on `127.0.0.1:7777`, or frontend is targeting the wrong API base URL.
- `RUN_NOT_FOUND` on `/live`: run is missing/expired; relaunch from menu and reconnect.
- `HOST_SHUTTING_DOWN`: backend is stopping; restart backend and reconnect.

See [Local Playtest Workflow](docs/enqueteur/local_playtest_workflow.md) for the full local runbook and config notes.
