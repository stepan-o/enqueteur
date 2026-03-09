# 📡 KVP-ENQ-0001 — Kernel ↔ Viewer Protocol for Enquêteur LIVE Play

This document **does not replace** KVP-0001:
* **KVP-0001** is the **shared constitutional base**
* **KVP-ENQ-0001** is the **Enquêteur-specific binding/profile**
* this doc inherits KVP-0001
* it narrows/extends it for `engine_name="enqueteur"` and `schema_version="enqueteur_mbam_1"`

That gives us:

* one shared transport/session philosophy
* one Enquêteur-specific runtime contract

## Conflict Resolution Notes (Implementation-Locked)

For Enquêteur LIVE implementation, this document is the source of truth when it intentionally conflicts with KVP-0001.

The following conflicts are intentional and locked for `engine_name="enqueteur"` + `schema_version="enqueteur_mbam_1"`:

1. Channel taxonomy override
   * Enquêteur channel set is: `WORLD`, `NPCS`, `INVESTIGATION`, `DIALOGUE`, `LEARNING`, `EVENTS`, `DEBUG`.
   * If KVP-0001 v0.1 channel enums differ, Enquêteur runtime/viewer MUST follow the Enquêteur channel set above.

2. `COMMAND_REJECTED` payload override
   * Enquêteur `COMMAND_REJECTED` payload uses:
     * `client_cmd_id`
     * `reason_code`
     * `message`
   * If KVP-0001 examples/traits use a single `reason` field, Enquêteur implementations MUST use the Enquêteur shape here.

3. `KERNEL_HELLO.seed` typing override
   * Enquêteur allows `seed` as a canonical seed token string (for example `"A"`) or integer.
   * If KVP-0001 examples/traits assume numeric-only seed typing, Enquêteur implementations MUST follow this Enquêteur seed rule.

4. Spec hygiene note
   * Non-normative drafting/assistant scaffolding text is not part of this protocol contract and has been removed.

## *Enquêteur binding/profile on top of KVP-0001*

**Status:** Draft v0.1
**Audience:** Backend runtime, frontend webview, tooling, QA
**Scope:** Enquêteur live play over WebSocket, with offline artifacts as secondary replay/debug support
**Applies to:** Enquêteur frontend webview and backend session host

---

## 0. Relationship to KVP-0001

KVP-ENQ-0001 does **not** replace KVP-0001.

It is an **Enquêteur-specific profile** of KVP-0001.

### KVP-0001 remains authoritative for:

* envelope structure
* protocol versioning rules
* handshake sequencing
* subscribe lifecycle
* command vs state philosophy
* kernel sovereignty
* determinism rules
* snapshot/diff discipline
* desync/error philosophy

### KVP-ENQ-0001 defines:

* Enquêteur engine identity
* Enquêteur schema identity
* Enquêteur channels
* Enquêteur snapshot shape
* Enquêteur diff ops
* Enquêteur command types
* Enquêteur live-play assumptions
* Enquêteur-specific practical rules for MBAM v1

### Conflict rule

If KVP-ENQ-0001 explicitly narrows or specializes runtime behavior for Enquêteur, that rule governs Enquêteur. Otherwise KVP-0001 governs.

---

## 1. Purpose

Define the **live session protocol contract** between the Enquêteur deterministic runtime/kernel and the Enquêteur frontend viewer.

This protocol exists so that:

* the **standard player path is LIVE**
* the **frontend is a shell, not an authority**
* the **backend remains canonical for world truth, case truth, dialogue legality, learning progression, and outcomes**
* the game is playable through a real session, not artifact-only replay
* replay/debug remains possible without becoming the primary player flow

### Primary mode

* **Primary player mode:** LIVE WebSocket session
* **Secondary mode:** offline artifact replay for QA/debug/review

---

## 2. Core Principles (Non-Negotiable)

1. **Protocol, not code**

    * Viewer never imports kernel/runtime logic
    * Kernel never imports viewer logic
    * No shared runtime state
    * No hidden contracts outside the spec

2. **Kernel sovereignty**

    * Kernel is the only authority for:

        * world truth
        * case truth
        * investigation progression
        * dialogue legality
        * learning/minigame scoring
        * outcome evaluation

3. **Determinism is sacred**

    * Same seed + same commands = same run
    * Viewer must never alter truth or progression locally
    * Live play must remain replayable/debuggable

4. **Player path is LIVE**

    * Standard play does not begin from artifact replay
    * Menus exist outside the live session
    * Session begins only after case launch

5. **Primitives-only payloads**

    * JSON-friendly
    * portable
    * no engine objects
    * no pointers
    * no shared references

6. **Replay is secondary, not abandoned**

    * Offline artifacts remain valid for QA/debug/review
    * LIVE protocol remains the player-first contract

---

## 3. Transport Model

KVP-ENQ-0001 inherits KVP-0001 transport rules.

### Standard transport

* **WebSocket** is the default LIVE transport
* Protocol messages MUST be sent as UTF-8 JSON text frames

### Secondary transport

* HTTP is used for **pre-session case launch**
* HTTP may also be used later for offline artifacts/debug tools

### Important separation

The **case-launch API** is **outside** the WebSocket protocol.
It is a pre-session bootstrapping step.

### Transport requirements for LIVE

* in-order delivery
* bidirectional flow
* explicit recovery path on desync
* no unsolicited state before subscribe completes

---

## 4. Pre-Session Bootstrapping (Outside WebSocket Protocol)

Before a LIVE WebSocket session begins, the frontend launches a case via HTTP.

## 4.1 Case Start Endpoint

**Recommended endpoint:**
`POST /api/cases/start`

### Request

```json
{
  "case_id": "MBAM_01",
  "seed": "A",
  "difficulty_profile": "D0"
}
```

### Response

```json
{
  "run_id": "uuid",
  "world_id": "uuid",
  "engine_name": "enqueteur",
  "schema_version": "enqueteur_mbam_1",
  "seed": "A",
  "difficulty_profile": "D0",
  "ws_url": "ws://host/live?run_id=uuid",
  "started_at": "2026-03-08T12:00:00Z"
}
```

### Bootstrapping rules

* Case launch MUST happen before WebSocket connection
* The HTTP response MUST contain the connection target for the corresponding run
* The frontend MUST validate:

    * `engine_name == "enqueteur"`
    * `schema_version == "enqueteur_mbam_1"`

This launch step is **not** a replacement for the KVP session lifecycle. It only creates the run.

---

## 5. Message Envelope (Inherited, Mandatory)

All LIVE protocol messages MUST use the KVP envelope:

```json
{
  "kvp_version": "0.1",
  "msg_type": "FULL_SNAPSHOT",
  "msg_id": "uuid",
  "sent_at_ms": 0,
  "payload": {}
}
```

### Envelope rules

* `kvp_version` MUST equal `"0.1"`
* `msg_type` is the single authoritative discriminator
* `payload` is decoded strictly by `msg_type`
* no shape-based top-level dispatch
* messages without this envelope are invalid

---

## 6. Versioning & Identity

### Protocol

* `kvp_version = "0.1"`

### Engine

* `engine_name = "enqueteur"`

### Schema

* `schema_version = "enqueteur_mbam_1"`

### Required session anchors

* `engine_name`
* `engine_version`
* `schema_version`
* `world_id`
* `run_id`
* `seed`
* `tick_rate_hz`
* `time_origin_ms`

These are required for:

* deterministic validation
* replay/debug traceability
* session integrity

---

## 7. Session Lifecycle (LIVE)

No Enquêteur state payloads may be sent before handshake and subscribe complete.

### Required sequence

1. `VIEWER_HELLO`
2. `KERNEL_HELLO`
3. `SUBSCRIBE`
4. `SUBSCRIBED`
5. `FULL_SNAPSHOT`
6. `FRAME_DIFF` stream

If the viewer violates sequence, kernel MUST send `ERROR` and may close the session.

### Baseline guarantee

If `snapshot_policy = ON_JOIN`, kernel MUST send exactly one baseline `FULL_SNAPSHOT` immediately after `SUBSCRIBED` and before any `FRAME_DIFF`.

---

## 8. Handshake

## 8.1 Viewer → Kernel: `VIEWER_HELLO`

```json
{
  "viewer_name": "enqueteur-webview",
  "viewer_version": "0.1.0",
  "supported_schema_versions": ["enqueteur_mbam_1"],
  "supports": {
    "diff_stream": true,
    "full_snapshot": true,
    "replay_seek": false
  }
}
```

### Rules

* `supported_schema_versions` MUST be non-empty
* Kernel MUST choose exactly one schema version
* For Enquêteur v1, the chosen schema MUST be `enqueteur_mbam_1`

---

## 8.2 Kernel → Viewer: `KERNEL_HELLO`

```json
{
  "engine_name": "enqueteur",
  "engine_version": "0.1.0",
  "schema_version": "enqueteur_mbam_1",
  "world_id": "uuid",
  "run_id": "uuid",
  "seed": "A",
  "tick_rate_hz": 30,
  "time_origin_ms": 0,
  "render_spec": {}
}
```

### Required render_spec

`render_spec` is REQUIRED and must remain stable for the run.

It should include enough for:

* initial camera fit
* map bounds
* coordinate interpretation
* draw ordering guidance
* primitive fallback behavior

### Recommended render_spec shape

```json
{
  "coord_system": {
    "units": "WORLD_UNITS",
    "units_per_tile": 1.0,
    "axis": { "x_positive": "EAST", "y_positive": "SOUTH" },
    "origin": { "x": 0.0, "y": 0.0 },
    "bounds": { "min_x": 0.0, "min_y": 0.0, "max_x": 40.0, "max_y": 30.0 }
  },
  "projection": {
    "kind": "ISOMETRIC_2_5D",
    "recommended_iso_tile_w": 64,
    "recommended_iso_tile_h": 32
  },
  "asset_resolution": {
    "policy": "MANIFEST_OR_PRIMITIVE_FALLBACK",
    "missing_ref_behavior": "DRAW_PRIMITIVE"
  }
}
```

---

## 9. Subscription Model

## 9.1 Viewer → Kernel: `SUBSCRIBE`

```json
{
  "stream": "LIVE",
  "channels": ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
  "diff_policy": "DIFF_ONLY",
  "snapshot_policy": "ON_JOIN",
  "compression": "NONE"
}
```

### Rules

* `stream` MUST be `LIVE`
* `channels` MUST be non-empty
* `channels` MUST contain no duplicates
* Kernel MUST NOT send state before `SUBSCRIBED`
* Kernel MAY narrow channels, but must say so in `SUBSCRIBED`

---

## 9.2 Kernel → Viewer: `SUBSCRIBED`

```json
{
  "stream_id": "uuid",
  "effective_stream": "LIVE",
  "effective_channels": ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
  "effective_diff_policy": "DIFF_ONLY",
  "effective_snapshot_policy": "ON_JOIN",
  "effective_compression": "NONE"
}
```

---

## 10. Enquêteur Channels

The Enquêteur runtime uses these channels:

### `WORLD`

Visible physical/playfield state:

* rooms
* doors
* world objects
* world clock
* visible physical object flags relevant to play

### `NPCS`

Visible NPC semantic state:

* npc identity
* room/location presence
* availability
* emotion
* stance
* trust/stress visible values or projected deltas
* state-card visible fields

### `INVESTIGATION`

Investigation-facing state:

* discovered evidence
* collected evidence
* observed-not-collected evidence
* visible facts
* contradiction availability
* investigation-visible object state

### `DIALOGUE`

Structured dialogue-facing state:

* active scene
* scene progression
* transcript entries
* allowed intent metadata
* repair/refusal state
* summary requirement state

### `LEARNING`

Language-learning state:

* difficulty profile
* hint level
* minigame state
* summary-check state
* recent learning outcomes

### `EVENTS`

Short event stream for UI-facing state changes:

* evidence revealed
* contradiction unlocked
* scene completed
* minigame completed
* outcome reached

### `DEBUG`

Optional diagnostics for dev mode only

---

## 11. Time Model

Kernel is the authority on time.

All state deliveries include:

* `tick` or `from_tick`/`to_tick`
* `step_hash`
* `schema_version`

Viewer MUST:

* apply diffs strictly in order
* never advance truth locally
* never fabricate state between ticks
* treat interpolation as visual-only

### Tick rate

For MBAM v1, `tick_rate_hz` should remain explicit in `KERNEL_HELLO`.

### step_hash

Enquêteur inherits KVP-0001 hash/canonicalization rules:

* SHA-256
* canonical JSON
* quantization before hashing
* subscribed-channel scope only

---

## 12. FULL_SNAPSHOT — `enqueteur_mbam_1`

### Kernel → Viewer: `FULL_SNAPSHOT`

```json
{
  "schema_version": "enqueteur_mbam_1",
  "tick": 0,
  "step_hash": "hash",
  "state": {
    "world": {},
    "npcs": {},
    "investigation": {},
    "dialogue": {},
    "learning": {},
    "resolution": {}
  }
}
```

## 12.1 Snapshot contract surface

### `state.world`

Contains only visible physical world state:

* `rooms[]`
* `doors[]`
* `objects[]`
* `clock`

Example:

```json
{
  "rooms": [],
  "doors": [],
  "objects": [],
  "clock": {
    "tick": 0,
    "time_label": "18:00"
  }
}
```

### `state.npcs`

Contains visible NPC semantic state:

```json
{
  "npcs": [
    {
      "npc_id": "marc",
      "name": "Marc Dutil",
      "current_room_id": "security_office",
      "availability": "available",
      "emotion": "guarded",
      "stance": "procedural",
      "trust": 0.0,
      "stress": 0.1,
      "card_state": {
        "trust_trend": "flat",
        "tell_cue": "procedure-first",
        "interaction_mode_hint": "be precise"
      }
    }
  ]
}
```

### `state.investigation`

```json
{
  "discovered_evidence_ids": [],
  "collected_evidence_ids": [],
  "observed_not_collected_ids": [],
  "visible_fact_ids": [],
  "available_contradiction_ids": [],
  "object_states": []
}
```

### `state.dialogue`

```json
{
  "active_scene_id": null,
  "scene_states": [],
  "recent_turns": []
}
```

### `state.learning`

```json
{
  "difficulty_profile": "D0",
  "hint_level": 0,
  "summary_state": null,
  "minigame_states": [],
  "recent_outcomes": []
}
```

### `state.resolution`

```json
{
  "status": "in_progress",
  "outcome": null,
  "recap": null
}
```

## 12.2 Snapshot rules

* Must be complete for subscribed channels
* Must not contain hidden truth
* Must be canonicalizable deterministically
* Must be enough to reconstruct the frontend play shell

---

## 13. FRAME_DIFF — `enqueteur_mbam_1`

### Kernel → Viewer: `FRAME_DIFF`

```json
{
  "schema_version": "enqueteur_mbam_1",
  "from_tick": 0,
  "to_tick": 1,
  "prev_step_hash": "hash0",
  "step_hash": "hash1",
  "ops": []
}
```

### Rules

* `to_tick = from_tick + 1` in LIVE mode
* `prev_step_hash` must match prior state
* `ops[]` must be applied in order
* ops order is canonical

---

## 13.1 Enquêteur diff ops

The Enquêteur schema uses domain-specific ops rather than generic sim-only ops.

### World ops

* `UPSERT_ROOM`
* `REMOVE_ROOM`
* `UPSERT_DOOR`
* `REMOVE_DOOR`
* `UPSERT_OBJECT`
* `REMOVE_OBJECT`
* `SET_CLOCK`

### NPC ops

* `UPSERT_NPC`
* `REMOVE_NPC`

### Investigation ops

* `REVEAL_EVIDENCE`
* `COLLECT_EVIDENCE`
* `SET_OBJECT_INVESTIGATION_STATE`
* `REVEAL_FACT`
* `MAKE_CONTRADICTION_AVAILABLE`
* `CLEAR_CONTRADICTION_AVAILABLE`

### Dialogue ops

* `SET_ACTIVE_SCENE`
* `UPSERT_SCENE_STATE`
* `APPEND_DIALOGUE_TURN`

### Learning ops

* `SET_HINT_LEVEL`
* `UPSERT_MINIGAME_STATE`
* `SET_SUMMARY_STATE`
* `APPEND_LEARNING_OUTCOME`

### Resolution ops

* `SET_RESOLUTION_STATUS`
* `SET_OUTCOME`
* `SET_RECAP`

### Event ops

* `APPEND_EVENT`

---

## 13.2 Example diff

```json
{
  "schema_version": "enqueteur_mbam_1",
  "from_tick": 120,
  "to_tick": 121,
  "prev_step_hash": "abc",
  "step_hash": "def",
  "ops": [
    {
      "op": "REVEAL_EVIDENCE",
      "evidence_id": "E2_CAFE_RECEIPT"
    },
    {
      "op": "REVEAL_FACT",
      "fact_id": "N4"
    },
    {
      "op": "APPEND_EVENT",
      "event": {
        "kind": "EVIDENCE_REVEALED",
        "label": "Café receipt found"
      }
    }
  ]
}
```

---

## 14. Viewer → Kernel Input

The viewer sends only commands, never state mutations.

### Envelope msg_type

`INPUT_COMMAND`

### Payload shape

```json
{
  "client_cmd_id": "uuid",
  "tick_target": 121,
  "cmd": {
    "type": "INVESTIGATE_OBJECT",
    "payload": {}
  }
}
```

### Rules

* Commands are validated and sanitized by kernel
* Kernel applies deterministically or rejects
* Accepted commands become part of run history
* Viewer must not mutate progression locally

---

## 14.1 Enquêteur command types

### `INVESTIGATE_OBJECT`

For object interactions.

```json
{
  "type": "INVESTIGATE_OBJECT",
  "payload": {
    "object_id": "O6_BADGE_TERMINAL",
    "action_id": "view_logs"
  }
}
```

### `DIALOGUE_TURN`

For structured scene turns.

```json
{
  "type": "DIALOGUE_TURN",
  "payload": {
    "scene_id": "S2",
    "npc_id": "marc",
    "intent_id": "request_access",
    "slots": {
      "reason": "voir les entrées du badge"
    }
  }
}
```

### `MINIGAME_SUBMIT`

For MG1–MG4 submissions.

```json
{
  "type": "MINIGAME_SUBMIT",
  "payload": {
    "minigame_id": "MG2",
    "target_id": "O6_BADGE_TERMINAL",
    "answer": {
      "selected_entry_id": "entry_3",
      "time_value": "17:58"
    }
  }
}
```

### `ATTEMPT_RECOVERY`

For recovery path resolution attempt.

```json
{
  "type": "ATTEMPT_RECOVERY",
  "payload": {
    "target_id": "O2_MEDALLION"
  }
}
```

### `ATTEMPT_ACCUSATION`

For accusation path resolution attempt.

```json
{
  "type": "ATTEMPT_ACCUSATION",
  "payload": {
    "suspect_id": "laurent",
    "supporting_fact_ids": ["N3", "N4", "N8"],
    "supporting_evidence_ids": ["E2_CAFE_RECEIPT"]
  }
}
```

---

## 15. Command Responses

## 15.1 `COMMAND_ACCEPTED`

```json
{
  "client_cmd_id": "uuid"
}
```

This means the command was valid and entered deterministic processing.

It does **not** itself replace state updates.

### Rule

Frontend should still wait for authoritative state projection changes.

---

## 15.2 `COMMAND_REJECTED`

```json
{
  "client_cmd_id": "uuid",
  "reason_code": "SCENE_GATE_BLOCKED",
  "message": "Scene requirements not met."
}
```

### Recommended reason codes

* `OBJECT_ACTION_UNAVAILABLE`
* `SCENE_GATE_BLOCKED`
* `MISSING_REQUIRED_SLOTS`
* `INSUFFICIENT_TRUST`
* `INVALID_NPC`
* `INVALID_OBJECT`
* `MINIGAME_INVALID_STATE`
* `MINIGAME_INVALID_SUBMISSION`
* `RECOVERY_PREREQS_MISSING`
* `ACCUSATION_PREREQS_MISSING`
* `INVALID_COMMAND`
* `RUNTIME_NOT_READY`

This is strongly recommended for Enquêteur because the live shell benefits from explicit rejection reasons.

---

## 16. Live Session Semantics

### Command/state relationship

The frontend may show:

* pending button state
* waiting spinner
* disabled control while command is outstanding

But it MUST NOT:

* fabricate evidence discovery
* fabricate dialogue progression
* fabricate contradiction availability
* fabricate outcomes

Only kernel diffs make truth visible.

---

## 17. Error Handling

Inherited from KVP-0001.

### `WARN`

Non-fatal issues.

### `ERROR`

Fatal or non-fatal with explicit `fatal` flag.

Recommended Enquêteur error codes:

* `SCHEMA_MISMATCH`
* `PROTOCOL_VIOLATION`
* `RUN_NOT_FOUND`
* `RUN_ALREADY_CLOSED`
* `INVALID_SUBSCRIPTION`
* `DESYNC_RECOVERY_REQUIRED`
* `INTERNAL_RUNTIME_ERROR`

---

## 18. Desync Recovery

Enquêteur inherits KVP-0001 desync philosophy.

### Viewer may report

* `TICK_GAP`
* `FROM_TICK_MISMATCH`
* `INVALID_PAYLOAD`
* `EXTERNAL_HASH_MISMATCH`

### Kernel must respond with

* `DESYNC_CONFIRMED` + `recovery_tick`
  or
* `DESYNC_DENIED`

### LIVE recovery rule

Kernel MUST provide a new baseline `FULL_SNAPSHOT(recovery_tick)` and resume diffs only after recovery.

---

## 19. Replay and Offline Artifacts

Replay is supported, but not primary.

### Rules

* Offline artifacts MAY reuse `FULL_SNAPSHOT` and `FRAME_DIFF` schemas from `enqueteur_mbam_1`
* Offline artifacts remain for:

    * QA
    * replay/debug
    * validation
    * seed review
* Replay control is not central to the Enquêteur player path

### Player-path rule

The normal menu → case launch → play flow does not depend on artifacts.

---

## 20. Viewer UI State Mapping (Non-Normative)

Recommended viewer states:

* `LOADING`
* `MAIN_MENU`
* `CASE_SELECT`
* `CONNECTING`
* `HANDSHAKING`
* `SUBSCRIBING`
* `LOADING_BASELINE`
* `LIVE_GAME`
* `DESYNC_RECOVERY`
* `ERROR`

### Important

The menu states exist outside the WebSocket session.
The protocol begins only after case launch and socket connection.

---

## 21. Testability Requirements

KVP-ENQ-0001 inherits KVP-0001 testability rules.

Additionally, Enquêteur should validate:

* one-command case launch + live attach
* handshake sequencing
* baseline-before-diff guarantee
* command accept/reject correctness
* same seed + same command stream = same outcome
* full run reconstruction from snapshot + diff chain
* no hidden-truth leakage in visible channels

---

## 22. Final Authority

For Enquêteur:

* KVP-0001 is the shared constitutional base
* KVP-ENQ-0001 is the Enquêteur-specific live binding

No Enquêteur viewer or backend session host may bypass this contract.

---

## Appendix A — Enquêteur Minimal Supported Message Set

### Required for MBAM live play

* `VIEWER_HELLO`
* `KERNEL_HELLO`
* `SUBSCRIBE`
* `SUBSCRIBED`
* `FULL_SNAPSHOT`
* `FRAME_DIFF`
* `INPUT_COMMAND`
* `COMMAND_ACCEPTED`
* `COMMAND_REJECTED`
* `WARN`
* `ERROR`

### Optional later

* `PING`
* `PONG`
* `DESYNC_REPORT`
* `DESYNC_CONFIRMED`
* `DESYNC_DENIED`
* replay control messages

---

## Appendix B — Recommended Initial Implementation Priority

Implement in this order:

1. backend WebSocket live host
2. KVP handshake/subscription
3. baseline `FULL_SNAPSHOT`
4. `FRAME_DIFF` streaming
5. `INPUT_COMMAND` handling for:

    * `INVESTIGATE_OBJECT`
    * `DIALOGUE_TURN`
    * `MINIGAME_SUBMIT`
    * `ATTEMPT_RECOVERY`
    * `ATTEMPT_ACCUSATION`
6. `COMMAND_ACCEPTED` / `COMMAND_REJECTED`
7. frontend live connector
8. menu → launch → connect → baseline → `LIVE_GAME` path

---
