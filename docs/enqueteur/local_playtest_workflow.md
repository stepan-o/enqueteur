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

## Locked Playtest Standard

Locked defaults for canonical playtesting:

- case: `MBAM_01` (MBAM)
- seed: `A`
- difficulty: `D0`
- launch mode/profile: `playtest`

### Tier 1: Daily Smoke Path

Use the locked defaults above.

Minimum finite checks:

1. Launch MBAM from Case Select and confirm transition to Connecting.
2. Confirm live handshake/baseline completes and app reaches Live Game.
3. Perform at least one in-game interaction and confirm the game state updates (no stuck UI/desync/error screen).
4. Return to menu and relaunch once to confirm repeated local use still works.

### Tier 2: Canonical Full Manual Path

Use the same locked defaults (Seed `A`, `D0`, `playtest`).

This is the shared reference run for meaningful feature work:

1. Launch MBAM and play through the normal investigation loop.
2. Exercise clue gathering + dialogue progression (not just first interaction).
3. Drive the run to a real case-end path (recovery or accusation flow).

Run this path when behavior-level changes are made to runtime, protocol/session flow, or core app flow.

### Tier 3: Secondary Coverage Sweep (B/C)

Use the same settings except seed:

- seed `B`
- seed `C`

Purpose:

- broaden seeded branch coverage,
- catch seed-specific regressions not visible in Seed A.

Run this sweep for larger gameplay/runtime/protocol changes; it is not the daily default gate.

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

## Automated Tests vs Manual Live Play

Automated backend/frontend tests are required, but they do not replace live manual play.

- Use automated tests for contract/regression confidence.
- Use the three-tier playtest standard above to verify real user-flow behavior through the canonical host.

## Terminology

- `playtest` is the canonical daily launch mode/profile.
- `demo` presentation/profile is secondary and should not replace the canonical playtest standard.

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
