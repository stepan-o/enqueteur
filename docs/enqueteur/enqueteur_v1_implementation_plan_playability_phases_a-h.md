Here’s the implementation plan I’d use.

# Goal

Make the game boot into a proper **front-end shell** before any live simulation starts:

1. **Loading screen**
2. **Main menu**
3. **Case select screen**
4. **Case launch**
5. **Live session connect**
6. **Gameplay shell**

And do it using a **KVP-style live protocol** so the viewer/kernel relationship stays clean and deterministic.

---

# High-level product flow

## Frontend flow

1. App loads
2. Show **loading screen** with logo
3. Transition to **main menu**
4. Main menu shows:

    * Start / Cases
    * maybe Settings later
5. Clicking **Cases** opens **case selection screen**
6. Case selection currently shows:

    * MBAM / Le Petit Vol du Musée
    * Back button
7. Clicking the case:

    * sends a request to backend to create/start a run
    * opens a WebSocket live session
    * performs KVP-style handshake
    * receives baseline snapshot
    * enters gameplay shell

## Backend flow

1. Receive “start case” request
2. Create deterministic run:

    * case id
    * seed
    * difficulty
    * run_id
    * world_id
3. Prepare live session
4. Accept WebSocket connection
5. Perform handshake/subscription
6. Send baseline `FULL_SNAPSHOT`
7. Stream `FRAME_DIFF`
8. Accept structured player commands
9. Reply with `COMMAND_ACCEPTED` / `COMMAND_REJECTED`
10. Continue authoritative tick/update flow

---

# Core implementation principle

The menu system should be **outside the live session**.

That means:

* main menu is frontend-only UI state
* case selection is frontend-only UI state
* live kernel session only begins when a case is actually launched

This avoids forcing the backend to exist just to render menus.

---

# Recommended implementation phases

## Phase A — Frontend boot flow and pre-game shell

Build the app-level state machine before touching session transport.

### Add app states

Create a top-level app flow like:

* `BOOT`
* `LOADING`
* `MAIN_MENU`
* `CASE_SELECT`
* `CONNECTING`
* `LIVE_GAME`
* `ERROR`

This should live above the current world/game shell.

### Add screens

Implement:

* loading screen
* main menu
* case selection screen

### Current menu content

Main menu:

* `Start` or `Cases`
* maybe `Quit`/`Settings` later

Case screen:

* MBAM case card/button
* Back button

### Important rule

Do not initialize the full live game shell until the user chooses a case.

---

## Phase B — Case launch API

Add the backend HTTP endpoint that creates a run before WebSocket connection starts.

### Add a route like

`POST /api/cases/start`

Request body:

```json
{
  "case_id": "MBAM_01",
  "seed": "A",
  "difficulty_profile": "D0"
}
```

Response:

```json
{
  "run_id": "uuid",
  "world_id": "uuid",
  "engine_name": "enqueteur",
  "schema_version": "enqueteur_mbam_1",
  "ws_url": "ws://.../live?run_id=..."
}
```

### Backend responsibility

This endpoint should:

* validate case id
* instantiate deterministic case + world runtime
* register the run/session
* return the information the frontend needs to connect

### Why this is useful

It cleanly separates:

* **run creation**
* from **live stream connection**

That will make debugging much easier.

---

## Phase C — Define KVP-ENQ-0001

Before wiring live play, lock the Enquêteur KVP contract.

### Keep from KVP-0001

* same envelope
* same handshake sequencing
* same transport philosophy
* same kernel/viewer authority split
* same snapshot/diff model
* same command/ACK/NACK model

### Add Enquêteur-specific schema

Use:

* `engine_name = "enqueteur"`
* `schema_version = "enqueteur_mbam_1"`

### Recommended channels

* `WORLD`
* `NPCS`
* `INVESTIGATION`
* `DIALOGUE`
* `LEARNING`
* `EVENTS`
* `DEBUG`

### Required live messages

At minimum:

Handshake/session:

* `VIEWER_HELLO`
* `KERNEL_HELLO`
* `SUBSCRIBE`
* `SUBSCRIBED`

State:

* `FULL_SNAPSHOT`
* `FRAME_DIFF`

Input:

* `INPUT_COMMAND`
* `COMMAND_ACCEPTED`
* `COMMAND_REJECTED`

Error:

* `WARN`
* `ERROR`

That is enough to make live play work.

---

## Phase D — Backend live session host

Add the actual WebSocket live session implementation.

### Session lifecycle

For each launched run:

1. Frontend connects to WebSocket
2. Frontend sends `VIEWER_HELLO`
3. Backend replies `KERNEL_HELLO`
4. Frontend sends `SUBSCRIBE`
5. Backend replies `SUBSCRIBED`
6. Backend sends `FULL_SNAPSHOT`
7. Backend begins `FRAME_DIFF` stream

### Backend responsibilities

The live host must:

* look up the created run by `run_id`
* bind to the deterministic runtime
* maintain session state
* stream diffs in order
* accept commands
* emit accept/reject responses
* recover cleanly on disconnect

### Important

Do not make the WebSocket own truth.
It is only the transport around the already-authoritative runtime.

---

## Phase E — Enquêteur command handling

Make the live backend understand player actions.

### Required `INPUT_COMMAND` types

At minimum:

* `INVESTIGATE_OBJECT`
* `DIALOGUE_TURN`
* `MINIGAME_SUBMIT`
* `ATTEMPT_RECOVERY`
* `ATTEMPT_ACCUSATION`

### Backend handling

Each command should:

1. validate
2. either reject immediately
3. or accept and apply deterministically through existing runtime/case logic

### Rejections should be explicit

Examples:

* `OBJECT_ACTION_UNAVAILABLE`
* `SCENE_GATE_BLOCKED`
* `MISSING_REQUIRED_SLOTS`
* `INSUFFICIENT_TRUST`
* `MINIGAME_INVALID_STATE`
* `ACCUSATION_PREREQS_MISSING`

That will make the frontend much easier to reason about.

---

## Phase F — Frontend live connector

Replace the current default offline-first assumption with live-first case launch.

### Frontend case launch flow

When user clicks MBAM:

1. show `CONNECTING` screen
2. call `POST /api/cases/start`
3. get `run_id` + `ws_url`
4. open WebSocket
5. perform KVP handshake
6. on `FULL_SNAPSHOT`, initialize world/game store
7. transition to `LIVE_GAME`

### Failure handling

If anything fails:

* show error screen/state
* offer retry
* offer return to case select
* do not dump user into desynced shell

---

## Phase G — Integrate current game shell into app flow

Your current shell becomes the `LIVE_GAME` state.

That means:

* Pixi scene
* interaction panel
* dialogue panel
* notebook/evidence tray
* contradiction/timeline view
* resolution panel

all load only after successful session start.

### Keep replay as separate mode later

Do not mix replay startup into the normal player boot path.

Later you can add:

* Main Menu → Replay / Debug
  if needed.

But for now:

* player path = live game only

---

## Phase H — Playtest mode and dev mode split

This is important because your shell is still partly dev-oriented.

### Add two presentation modes

* `PLAYTEST_MODE`
* `DEV_MODE`

### In playtest mode

Hide or demote:

* transport diagnostics
* low-level dev controls
* extra debug overlays

### In dev mode

Keep:

* session info
* replay tools
* transport logs
* extra inspection surfaces

This will make the same build usable both for development and actual testing.

---

# Suggested technical structure

## Frontend

### New top-level app modules

* `appState.ts`
* `menu/LoadingScreen.ts`
* `menu/MainMenu.ts`
* `menu/CaseSelectScreen.ts`
* `menu/ConnectingScreen.ts`
* `menu/ErrorScreen.ts`
* `live/liveSessionClient.ts`
* `live/kvpRouter.ts`

### Existing shell reused under

* `LIVE_GAME`

## Backend

### New layers

* case launch API
* live session manager
* websocket session handler
* KVP message router for Enquêteur
* command dispatch bridge into existing runner/runtime

---

# Recommended sequencing

## Step 1

Build frontend boot/menu/case select flow.

## Step 2

Add backend `start case` endpoint.

## Step 3

Write and lock `KVP-ENQ-0001`.

## Step 4

Implement backend live session host.

## Step 5

Implement Enquêteur `INPUT_COMMAND` handling over live session.

## Step 6

Wire frontend live connector and connecting flow.

## Step 7

Attach current gameplay shell as the live session destination.

## Step 8

Add playtest/dev split and polish startup/failure UX.

---

# What I would explicitly not do yet

* do not make menus backend-driven
* do not make offline replay the default path
* do not add voice here
* do not redesign the whole UI skin first
* do not expand the protocol beyond what MBAM needs
* do not add generalized account/save/profile systems

---

# Practical acceptance criteria

This plan is done when:

1. Opening the app shows loading screen then main menu
2. Main menu leads to case select
3. Case select shows MBAM and Back
4. Clicking MBAM starts a backend run
5. Frontend opens WebSocket and completes KVP handshake
6. Baseline snapshot loads correctly
7. Gameplay shell becomes active
8. Player can:

    * investigate objects
    * talk to NPCs
    * submit minigames
    * attempt recovery/accusation
9. Backend responds authoritatively
10. No offline artifacts are required for standard play

---

# My recommendation

The right next milestone is:

## “Live MBAM Launch Path”

Not “protocol perfection,” not “UI polish,” not “Case 2.”

Just:

* proper frontend boot/menu flow
* real backend run creation
* real WebSocket live session
* real KVP-style command/state loop
* real player path into MBAM

If you want, I can next turn this into:

1. a **Codex execution brief** for the full live-session/menu implementation, or
2. a formal **KVP-ENQ-0001 spec draft** adapted from KVP-0001.
