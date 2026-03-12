# Enqueteur Local Playtest Workflow

This is the canonical local developer workflow for live Enqueteur playtesting.

## Canonical Topology

- Backend: Python ASGI host (`backend/server`) on `127.0.0.1:7777`
- Frontend: Vite dev server (`frontend/enqueteur-webview`) on `127.0.0.1:5173`
- Canonical runtime ownership: backend host owns launch, live session, command handling, and diffs.

## One-Time Setup

Python dependencies:

```bash
uv sync --extra dev --extra server
```

Frontend dependencies:

```bash
make web-install
```

## Daily Run

Terminal A (backend):

```bash
make server-dev
```

Terminal B (frontend):

```bash
make web-dev-local
```

Open `http://127.0.0.1:5173`.

## Canonical UI Flow

1. Loading
2. Main Menu
3. Case Select
4. Connecting
5. Live Game

Recommended daily playtest profile:

- `MBAM_01`
- seed `A`
- difficulty `D0`
- mode `playtest`

## Runtime Verification

Check backend readiness:

```bash
curl http://127.0.0.1:7777/readyz
```

Expected while running:

- `status` is `ready`
- app launch from UI returns a `run_id`
- live connect reaches baseline and enters Live Game

## Endpoint/Protocol Path

The frontend local flow should execute:

1. `POST /api/cases/start` on backend host
2. connect to `WS /live?run_id=<run_id>`
3. handshake and baseline
4. interactive live session with command ACK/REJECT + frame diffs

## Local Config Knobs

Backend env vars (prefix `ENQ_SERVER_`):

- `HOST` (default `127.0.0.1`)
- `PORT` (default `7777`)
- `LOG_LEVEL` (default `info`)
- `RUN_TTL_SECONDS` (default `1800`)
- `VERBOSE_PROTOCOL_LOGGING` (default `false`)

Frontend env:

- `VITE_ENQUETEUR_API_BASE_URL` (optional override; local default resolves to `http://127.0.0.1:7777` in dev)

## Troubleshooting

- Launch error `BACKEND_UNREACHABLE`:
  - backend is not running on `127.0.0.1:7777`, or frontend base URL override is wrong.
- WS error `RUN_NOT_FOUND`:
  - run was removed/expired; relaunch from menu and reconnect.
- WS error `HOST_SHUTTING_DOWN`:
  - backend is stopping; restart backend and reconnect.
- Stuck in Connecting:
  - confirm backend `/readyz` is `ready`.
  - inspect backend logs for protocol rejection category.

## Useful Test Commands

Backend full:

```bash
make test
```

Backend host-focused:

```bash
uv run -m pytest backend/sim4/tests/integration/test_server_shell_s1.py backend/sim4/tests/integration/test_server_shell_s2_app_launch.py backend/sim4/tests/integration/test_server_shell_s4_live_ws_asgi.py -q
```

Frontend:

```bash
cd frontend/enqueteur-webview
npm test
```
