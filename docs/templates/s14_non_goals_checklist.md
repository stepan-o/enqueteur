Sprint 14 Non-Goals Checklist (Paste into PRs / Reviews)

Required statement: ARTIFACTS ONLY — NO REPLAY_* — NO LIVE SESSION

❌ NOT ALLOWED — references or code paths
- WebSocket (any client/server, any library)
- Handshake or subscribe lifecycle (CONNECT/HELLO/SUBSCRIBE, etc.)
- REFERENCE to SUBSCRIBE in any form (strings, enums, comments)
- REPLAY_* control messages (REPLAY_BEGIN, REPLAY_SEEK, REPLAY_READY, etc.)
- Kernel-hosted replay or server-mediated replay

❌ NOT ALLOWED — attempts or assumptions
- Simulating a session offline (mock transport, mock handshakes, stream controllers)
- Requiring kernel/server presence to replay artifacts
- Assuming a server exists during replay or any bidirectional messaging

✅ REQUIRED — Sprint 14 behavior
- Artifacts-only replay: viewers load from disk/static HTTP
- Local-only replay control (seek/scrub) using manifest discovery
- Clear separation: ARTIFACT REPLAY MODE (S14) vs LIVE KVP PROTOCOL (future v0.2+)

Reviewer Gate
- Search diff and code for: WebSocket, socket, ws, handshake, subscribe, SUBSCRIBE, REPLAY_, REPLAY_BEGIN, REPLAY_SEEK, REPLAY_READY.
- Remove or block anything that implies transport, session state, or bidirectional messaging.
- If ambiguous, resolve in favor of artifacts-only and request edits to make it explicit.

Final affirmation (must be checked)
- [ ] This PR complies with Sprint 14 artifacts-only replay and introduces no live/session behavior.
