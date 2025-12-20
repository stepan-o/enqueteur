Sprint 14 Scope Lock — Sim4 / Loopforge

Required statement:

ARTIFACTS ONLY — NO REPLAY_* — NO LIVE SESSION

Plain-language scope
- Sprint 14 is artifacts-only replay. Viewers load recorded artifacts from disk or static HTTP.
- There is no live kernel, no transport, no handshake, no SUBSCRIBE, no REPLAY_* control messages.
- All replay control (seek/scrub) happens locally in the viewer using manifests; there is no server involvement.

Explicitly forbidden in S14.0
- WebSockets or any bidirectional transport
- Handshake/subscribe lifecycle of any kind
- Any REPLAY_* control messages (e.g., REPLAY_BEGIN, REPLAY_SEEK, REPLAY_READY)
- Kernel-hosted or server-mediated replay
- “Offline simulation” of a protocol/session (mock handshakes, mock stream controllers, etc.)

Modes — know the boundary
- LIVE KVP PROTOCOL (future v0.2+): out of scope for Sprint 14. Do not implement, simulate, or scaffold.
- ARTIFACT REPLAY MODE (Sprint 14): manifests + KVP-enveloped artifacts written to disk; viewers read files and control time locally.

Reviewer guidance (copy/paste)
- Reject any PR introducing live/session behavior, transport code, or replay control messages.
- Reject any dependency or API that implies a server or bidirectional messaging during replay.
- If ambiguous, choose artifacts-only and remove the ambiguity in favor of files-on-disk.

Authority
- This document governs Sprint 14. If a file or comment contradicts this, this scope lock wins.

Reference for headers/templates
- All exporter/replay modules must include the Sprint 14 header comment template and link back to this file.

Short reminder for PR descriptions
- ARTIFACTS ONLY — NO REPLAY_* — NO LIVE SESSION
