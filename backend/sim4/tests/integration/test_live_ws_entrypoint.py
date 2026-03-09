from __future__ import annotations

import asyncio
from dataclasses import replace
import json

from backend.api.cases_start import CaseRunRegistry, CaseStartRequest, CaseStartService
from backend.api.live_ws import (
    INTERNAL_RUNTIME_WS_CLOSE_CODE,
    INTERNAL_RUNTIME_WS_CLOSE_REASON,
    PROTOCOL_VIOLATION_WS_CLOSE_CODE,
    PROTOCOL_VIOLATION_WS_CLOSE_REASON,
    RUN_NOT_FOUND_WS_CLOSE_CODE,
    RUN_NOT_FOUND_WS_CLOSE_REASON,
    EnqueteurLiveSessionHost,
    RunLookupError,
    handle_enqueteur_live_disconnect,
    handle_enqueteur_live_incoming_message,
    open_enqueteur_live_websocket,
    stream_enqueteur_frame_diff_loop,
    stream_enqueteur_frame_diff_once,
)
from backend.sim4.integration.live_envelope import make_live_envelope


class FakeWebSocket:
    def __init__(self) -> None:
        self.accept_calls = 0
        self.close_calls: list[tuple[int, str]] = []
        self.sent_texts: list[str] = []

    async def accept(self) -> None:
        self.accept_calls += 1

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.close_calls.append((code, reason))

    async def send_text(self, data: str) -> None:
        self.sent_texts.append(data)


def _start_mbam_case(
    *,
    registry: CaseRunRegistry,
    seed: str = "A",
    difficulty_profile: str = "D0",
) -> tuple[CaseStartService, dict[str, object]]:
    service = CaseStartService(ws_base_url="ws://localhost:7777/live", registry=registry)
    response = service.start_case(
        CaseStartRequest.from_payload(
            {
                "case_id": "MBAM_01",
                "seed": seed,
                "difficulty_profile": difficulty_profile,
                "mode": "playtest",
            }
        )
    )
    return service, response.to_payload()


def _decode_sent_envelope(ws: FakeWebSocket, idx: int) -> dict[str, object]:
    return json.loads(ws.sent_texts[idx])


def _envelope(msg_type: str, payload: dict[str, object]) -> str:
    env = make_live_envelope(msg_type, payload, msg_id="00000000-0000-4000-8000-000000000001", sent_at_ms=0)
    return json.dumps(env)


def _open_attached_session(host: EnqueteurLiveSessionHost, ws: FakeWebSocket, connection_target: str):
    return asyncio.run(
        open_enqueteur_live_websocket(
            ws,
            connection_target=connection_target,
            host=host,
        )
    )


def _handshake_and_subscribe(
    *,
    host: EnqueteurLiveSessionHost,
    ws: FakeWebSocket,
    session: object,
    channels: list[str],
) -> None:
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": channels,
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()


def _prime_resolution_confrontation_gate(registry: CaseRunRegistry, payload: dict[str, object]) -> None:
    started = registry.get(str(payload["run_id"]))
    assert started is not None
    runner = started.runner
    case_state = runner.get_case_state()
    runtime = runner.get_dialogue_runtime_state()
    npc_states = runner.get_npc_states()
    assert case_state is not None
    assert runtime is not None
    assert "elodie" in npc_states

    completion = dict(runtime.scene_completion_states)
    completion["S5"] = "available"
    surfaced = tuple(sorted(set(runtime.surfaced_scene_ids).union({"S5"})))
    runner._dialogue_runtime_state = replace(  # type: ignore[attr-defined]
        runtime,
        scene_completion_states=tuple(
            (scene_id, completion[scene_id]) for scene_id, _ in runtime.scene_completion_states
        ),
        surfaced_scene_ids=surfaced,
    )

    threshold = case_state.scene_gates.S5.trust_threshold
    if threshold is not None:
        npc_states["elodie"] = replace(
            npc_states["elodie"],
            trust=max(float(npc_states["elodie"].trust), float(threshold) + 0.2),
        )
        runner._npc_states = npc_states  # type: ignore[attr-defined]


def _prime_resolution_progress_for_recovery(registry: CaseRunRegistry, payload: dict[str, object]) -> None:
    started = registry.get(str(payload["run_id"]))
    assert started is not None
    runner = started.runner
    case_state = runner.get_case_state()
    progress = runner.get_investigation_progress()
    assert case_state is not None
    assert progress is not None

    req = case_state.resolution_rules.recovery_success
    required_actions = tuple(action for action in req.required_actions if action != "action:recover_medallion")
    runner._investigation_progress = replace(  # type: ignore[attr-defined]
        progress,
        known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union(req.required_fact_ids))),
        discovered_evidence_ids=tuple(sorted(set(progress.discovered_evidence_ids).union(req.required_items))),
        collected_evidence_ids=tuple(sorted(set(progress.collected_evidence_ids).union(req.required_items))),
        satisfied_action_flags=tuple(sorted(set(progress.satisfied_action_flags).union(required_actions))),
    )


def _prime_resolution_progress_for_accusation(registry: CaseRunRegistry, payload: dict[str, object]) -> None:
    started = registry.get(str(payload["run_id"]))
    assert started is not None
    runner = started.runner
    case_state = runner.get_case_state()
    progress = runner.get_investigation_progress()
    assert case_state is not None
    assert progress is not None

    req = case_state.resolution_rules.accusation_success
    required_actions = tuple(
        action for action in req.required_actions if not action.startswith("action:accuse_")
    )
    runner._investigation_progress = replace(  # type: ignore[attr-defined]
        progress,
        known_fact_ids=tuple(sorted(set(progress.known_fact_ids).union(req.required_fact_ids))),
        discovered_evidence_ids=tuple(sorted(set(progress.discovered_evidence_ids).union(req.required_items))),
        collected_evidence_ids=tuple(sorted(set(progress.collected_evidence_ids).union(req.required_items))),
        satisfied_action_flags=tuple(sorted(set(progress.satisfied_action_flags).union(required_actions))),
    )


def test_live_websocket_entrypoint_attaches_to_started_run() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()

    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    assert ws.accept_calls == 1
    assert ws.close_calls == []
    assert session.phase == "HANDSHAKING"
    assert session.protocol_state == "AWAITING_VIEWER_HELLO"
    assert session.run.run_id == payload["run_id"]
    assert session.run.world_id == payload["world_id"]
    assert session.run.engine_name == "enqueteur"
    assert session.run.schema_version == "enqueteur_mbam_1"

    stored = host.get_session(session.connection_id)
    assert stored is not None
    assert stored.run.run_id == payload["run_id"]
    assert stored.phase == "HANDSHAKING"


def test_live_websocket_entrypoint_closes_on_missing_run() -> None:
    host = EnqueteurLiveSessionHost(run_registry=CaseRunRegistry())
    ws = FakeWebSocket()

    try:
        _open_attached_session(host, ws, "/live?run_id=missing-run-id")
    except RunLookupError as exc:
        assert exc.run_id_hint == "missing-run-id"
    else:
        raise AssertionError("RunLookupError was expected for unknown run_id.")

    assert ws.accept_calls == 1
    error_env = _decode_sent_envelope(ws, 0)
    assert error_env["msg_type"] == "ERROR"
    error_payload = error_env["payload"]
    assert error_payload["code"] == "RUN_NOT_FOUND"
    assert error_payload["fatal"] is True
    assert ws.close_calls == [(RUN_NOT_FOUND_WS_CLOSE_CODE, RUN_NOT_FOUND_WS_CLOSE_REASON)]


def test_handshake_then_subscribe_emits_kernel_hello_subscribed_and_baseline() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()

    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {
                        "diff_stream": True,
                        "full_snapshot": True,
                        "replay_seek": False,
                    },
                },
            ),
            host=host,
        )
    )

    kernel_hello = _decode_sent_envelope(ws, 0)
    assert kernel_hello["msg_type"] == "KERNEL_HELLO"
    kernel_payload = kernel_hello["payload"]
    assert kernel_payload["engine_name"] == "enqueteur"
    assert kernel_payload["schema_version"] == "enqueteur_mbam_1"
    assert kernel_payload["world_id"] == payload["world_id"]
    assert kernel_payload["run_id"] == payload["run_id"]
    assert kernel_payload["render_spec"]

    handshake_state = host.get_session(session.connection_id)
    assert handshake_state is not None
    assert handshake_state.protocol_state == "AWAITING_SUBSCRIBE"

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )

    subscribed = _decode_sent_envelope(ws, 1)
    assert subscribed["msg_type"] == "SUBSCRIBED"
    subscribed_payload = subscribed["payload"]
    assert subscribed_payload["effective_stream"] == "LIVE"
    assert subscribed_payload["effective_channels"] == [
        "WORLD",
        "NPCS",
        "INVESTIGATION",
        "DIALOGUE",
        "LEARNING",
        "EVENTS",
    ]
    assert subscribed_payload["effective_diff_policy"] == "DIFF_ONLY"
    assert subscribed_payload["effective_snapshot_policy"] == "ON_JOIN"
    assert host.can_deliver_state(session.connection_id) is True

    snapshot = _decode_sent_envelope(ws, 2)
    assert snapshot["msg_type"] == "FULL_SNAPSHOT"
    snapshot_payload = snapshot["payload"]
    assert snapshot_payload["schema_version"] == "enqueteur_mbam_1"
    assert isinstance(snapshot_payload["tick"], int)
    assert isinstance(snapshot_payload["step_hash"], str)
    state = snapshot_payload["state"]
    assert set(state.keys()) == {"world", "npcs", "investigation", "dialogue", "learning", "resolution"}

    subscribed_state = host.get_session(session.connection_id)
    assert subscribed_state is not None
    assert subscribed_state.baseline_sent is True
    assert subscribed_state.baseline_tick == snapshot_payload["tick"]


def test_subscribe_with_snapshot_never_does_not_emit_baseline() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "NEVER",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )

    assert len(ws.sent_texts) == 2
    assert _decode_sent_envelope(ws, 0)["msg_type"] == "KERNEL_HELLO"
    assert _decode_sent_envelope(ws, 1)["msg_type"] == "SUBSCRIBED"
    stored = host.get_session(session.connection_id)
    assert stored is not None
    assert stored.baseline_sent is False
    assert stored.baseline_tick is None


def test_full_snapshot_respects_subscribed_channel_scope() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )

    snapshot = _decode_sent_envelope(ws, 2)
    assert snapshot["msg_type"] == "FULL_SNAPSHOT"
    snapshot_state = snapshot["payload"]["state"]
    assert set(snapshot_state.keys()) == {"world", "resolution"}


def test_stream_frame_diff_once_emits_ordered_hash_chained_payload() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    baseline = _decode_sent_envelope(ws, 2)["payload"]

    payload_diff = asyncio.run(
        stream_enqueteur_frame_diff_once(
            ws,
            session=session,
            host=host,
        )
    )
    diff_env = _decode_sent_envelope(ws, 3)
    assert diff_env["msg_type"] == "FRAME_DIFF"
    diff_payload = diff_env["payload"]
    assert diff_payload == payload_diff
    assert diff_payload["schema_version"] == "enqueteur_mbam_1"
    assert diff_payload["from_tick"] == baseline["tick"]
    assert diff_payload["to_tick"] == baseline["tick"] + 1
    assert diff_payload["prev_step_hash"] == baseline["step_hash"]
    assert isinstance(diff_payload["step_hash"], str)
    assert isinstance(diff_payload["ops"], list)
    assert any(op["op"] == "SET_CLOCK" for op in diff_payload["ops"])

    stored = host.get_session(session.connection_id)
    assert stored is not None
    assert stored.last_tick == diff_payload["to_tick"]
    assert stored.last_step_hash == diff_payload["step_hash"]


def test_frame_diff_respects_subscribed_channel_scope() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )

    asyncio.run(
        stream_enqueteur_frame_diff_once(
            ws,
            session=session,
            host=host,
        )
    )

    diff_payload = _decode_sent_envelope(ws, 3)["payload"]
    op_names = {op["op"] for op in diff_payload["ops"]}
    allowed_world_resolution_ops = {
        "UPSERT_ROOM",
        "REMOVE_ROOM",
        "UPSERT_DOOR",
        "REMOVE_DOOR",
        "UPSERT_OBJECT",
        "REMOVE_OBJECT",
        "SET_CLOCK",
        "SET_RESOLUTION_STATUS",
        "SET_OUTCOME",
        "SET_RECAP",
    }
    assert op_names.issubset(allowed_world_resolution_ops)
    assert "UPSERT_NPC" not in op_names
    assert "REVEAL_FACT" not in op_names
    assert "SET_ACTIVE_SCENE" not in op_names
    assert "SET_HINT_LEVEL" not in op_names


def test_stream_frame_diff_loop_stops_at_max_frames() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )

    count = asyncio.run(
        stream_enqueteur_frame_diff_loop(
            ws,
            session=session,
            host=host,
            max_frames=3,
            tick_interval_seconds=0.0,
        )
    )
    assert count == 3
    frame_diff_types = [json.loads(text)["msg_type"] for text in ws.sent_texts if json.loads(text)["msg_type"] == "FRAME_DIFF"]
    assert len(frame_diff_types) == 3


def test_stream_loop_warns_when_baseline_cursor_is_missing() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "NEVER",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    count = asyncio.run(
        stream_enqueteur_frame_diff_loop(
            ws,
            session=session,
            host=host,
            max_frames=2,
            tick_interval_seconds=0.0,
        )
    )
    assert count == 0
    warn_env = _decode_sent_envelope(ws, 0)
    assert warn_env["msg_type"] == "WARN"
    assert warn_env["payload"]["code"] == "BASELINE_REQUIRED"
    assert ws.close_calls == []


def test_unsupported_allowed_message_emits_warn_nonfatal() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope("UNSUBSCRIBE", {"stream_id": "S1"}),
            host=host,
        )
    )

    warn_env = _decode_sent_envelope(ws, 0)
    assert warn_env["msg_type"] == "WARN"
    assert warn_env["payload"]["code"] == "UNSUPPORTED_MESSAGE"
    assert ws.close_calls == []


def test_viewer_hello_requires_enqueteur_schema_support() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()

    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["sim4_legacy"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )

    error_env = _decode_sent_envelope(ws, 0)
    assert error_env["msg_type"] == "ERROR"
    error_payload = error_env["payload"]
    assert error_payload["code"] == "SCHEMA_MISMATCH"
    assert error_payload["fatal"] is True
    assert ws.close_calls == [(PROTOCOL_VIOLATION_WS_CLOSE_CODE, PROTOCOL_VIOLATION_WS_CLOSE_REASON)]


def test_invalid_envelope_is_protocol_violation_and_closes() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message="{\"not\":\"an envelope\"}",
            host=host,
        )
    )

    error_env = _decode_sent_envelope(ws, 0)
    assert error_env["msg_type"] == "ERROR"
    assert error_env["payload"]["code"] == "PROTOCOL_VIOLATION"
    assert error_env["payload"]["fatal"] is True
    assert ws.close_calls == [(PROTOCOL_VIOLATION_WS_CLOSE_CODE, PROTOCOL_VIOLATION_WS_CLOSE_REASON)]


def test_subscribe_before_viewer_hello_is_bad_sequence() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()

    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )

    error_env = _decode_sent_envelope(ws, 0)
    assert error_env["msg_type"] == "ERROR"
    error_payload = error_env["payload"]
    assert error_payload["code"] == "BAD_SEQUENCE"
    assert error_payload["fatal"] is True
    assert ws.close_calls == [(PROTOCOL_VIOLATION_WS_CLOSE_CODE, PROTOCOL_VIOLATION_WS_CLOSE_REASON)]


def test_subscribe_rejects_duplicate_channels() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()

    session = _open_attached_session(host, ws, str(payload["ws_url"]))
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "WORLD"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )

    error_env = _decode_sent_envelope(ws, 0)
    assert error_env["msg_type"] == "ERROR"
    error_payload = error_env["payload"]
    assert error_payload["code"] == "INVALID_SUBSCRIPTION"
    assert error_payload["fatal"] is True


def test_ping_echoes_pong_nonce() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope("PING", {"nonce": "abc123"}),
            host=host,
        )
    )

    pong_env = _decode_sent_envelope(ws, 0)
    assert pong_env["msg_type"] == "PONG"
    assert pong_env["payload"] == {"nonce": "abc123"}
    assert ws.close_calls == []


def test_investigate_object_command_is_accepted_and_diff_reflects_authoritative_state() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "INVESTIGATION", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-00000000000a"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "INVESTIGATE_OBJECT",
                        "payload": {"object_id": "O4_BENCH", "action_id": "inspect"},
                    },
                },
            ),
            host=host,
        )
    )

    accepted = _decode_sent_envelope(ws, 0)
    assert accepted["msg_type"] == "COMMAND_ACCEPTED"
    assert accepted["payload"] == {"client_cmd_id": client_cmd_id}
    assert ws.close_calls == []

    asyncio.run(
        stream_enqueteur_frame_diff_once(
            ws,
            session=session,
            host=host,
        )
    )
    diff_payload = _decode_sent_envelope(ws, 1)["payload"]
    reveal_ops = [op for op in diff_payload["ops"] if op["op"] == "REVEAL_EVIDENCE"]
    assert any(op.get("evidence_id") == "E1_TORN_NOTE" for op in reveal_ops)
    assert any(op["op"] == "SET_OBJECT_INVESTIGATION_STATE" for op in diff_payload["ops"])
    assert diff_payload["schema_version"] == "enqueteur_mbam_1"


def test_investigate_object_rejects_unknown_object_id() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "INVESTIGATION"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-00000000000b"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "INVESTIGATE_OBJECT",
                        "payload": {"object_id": "OX_UNKNOWN", "action_id": "inspect"},
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["client_cmd_id"] == client_cmd_id
    assert rejected["payload"]["reason_code"] == "INVALID_OBJECT"
    assert ws.close_calls == []


def test_investigate_object_rejects_action_not_allowed_for_object() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "INVESTIGATION"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-00000000000c"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "INVESTIGATE_OBJECT",
                        "payload": {"object_id": "O1_DISPLAY_CASE", "action_id": "read_receipt"},
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["client_cmd_id"] == client_cmd_id
    assert rejected["payload"]["reason_code"] == "OBJECT_ACTION_UNAVAILABLE"
    assert ws.close_calls == []


def test_investigate_object_rejects_blocked_prerequisites() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "INVESTIGATION"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-00000000000f"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "INVESTIGATE_OBJECT",
                        "payload": {"object_id": "O6_BADGE_TERMINAL", "action_id": "view_logs"},
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["client_cmd_id"] == client_cmd_id
    assert rejected["payload"]["reason_code"] == "OBJECT_ACTION_UNAVAILABLE"
    assert ws.close_calls == []


def test_invalid_input_command_payload_is_rejected_with_reason_code() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": "not-a-uuid",
                    "tick_target": 1,
                    "cmd": {"type": "INVESTIGATE_OBJECT", "payload": {}},
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["client_cmd_id"] == "not-a-uuid"
    assert rejected["payload"]["reason_code"] == "INVALID_COMMAND"
    assert ws.close_calls == []


def test_dialogue_turn_missing_slots_is_rejected_with_missing_required_slots() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "DIALOGUE"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-00000000000d"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "DIALOGUE_TURN",
                        "payload": {
                            "scene_id": "S1",
                            "npc_id": "marc",
                            "intent_id": "request_access",
                        },
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["client_cmd_id"] == client_cmd_id
    assert rejected["payload"]["reason_code"] == "MISSING_REQUIRED_SLOTS"
    assert ws.close_calls == []


def test_dialogue_turn_command_is_accepted_and_updates_dialogue_diff_state() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "DIALOGUE", "INVESTIGATION", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-000000000015"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "DIALOGUE_TURN",
                        "payload": {
                            "scene_id": "S1",
                            "npc_id": "elodie",
                            "intent_id": "ask_what_happened",
                            "slots": {},
                        },
                    },
                },
            ),
            host=host,
        )
    )

    accepted = _decode_sent_envelope(ws, 0)
    assert accepted["msg_type"] == "COMMAND_ACCEPTED"
    assert accepted["payload"] == {"client_cmd_id": client_cmd_id}

    asyncio.run(
        stream_enqueteur_frame_diff_once(
            ws,
            session=session,
            host=host,
        )
    )
    diff_payload = _decode_sent_envelope(ws, 1)["payload"]
    assert any(op["op"] == "APPEND_DIALOGUE_TURN" for op in diff_payload["ops"])


def test_dialogue_turn_rejects_invalid_npc_for_scene() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "DIALOGUE"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-000000000016"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "DIALOGUE_TURN",
                        "payload": {
                            "scene_id": "S1",
                            "npc_id": "marc",
                            "intent_id": "ask_what_happened",
                            "slots": {},
                        },
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["client_cmd_id"] == client_cmd_id
    assert rejected["payload"]["reason_code"] == "INVALID_NPC"


def test_dialogue_turn_rejects_invalid_intent_for_scene() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "DIALOGUE"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-000000000017"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "DIALOGUE_TURN",
                        "payload": {
                            "scene_id": "S1",
                            "npc_id": "elodie",
                            "intent_id": "request_access",
                            "slots": {},
                        },
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["client_cmd_id"] == client_cmd_id
    assert rejected["payload"]["reason_code"] == "INVALID_COMMAND"


def test_dialogue_turn_rejects_insufficient_trust_gate() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "DIALOGUE"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-000000000018"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "DIALOGUE_TURN",
                        "payload": {
                            "scene_id": "S2",
                            "npc_id": "marc",
                            "intent_id": "request_access",
                            "slots": {"reason": "voir le terminal"},
                        },
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["client_cmd_id"] == client_cmd_id
    assert rejected["payload"]["reason_code"] == "INSUFFICIENT_TRUST"


def test_unsupported_input_command_type_is_rejected() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-00000000000e"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "SET_PLAYER_HP",
                        "payload": {"value": 999},
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["client_cmd_id"] == client_cmd_id
    assert rejected["payload"]["reason_code"] == "INVALID_COMMAND"
    assert ws.close_calls == []


def test_minigame_submit_command_is_accepted_and_updates_learning_diff_state() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "INVESTIGATION", "LEARNING", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-000000000012"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "MINIGAME_SUBMIT",
                        "payload": {
                            "minigame_id": "MG1",
                            "target_id": "O3_WALL_LABEL",
                            "answer": {"label_guess": "Le Medaillon des Voyageurs"},
                        },
                    },
                },
            ),
            host=host,
        )
    )

    accepted = _decode_sent_envelope(ws, 0)
    assert accepted["msg_type"] == "COMMAND_ACCEPTED"
    assert accepted["payload"] == {"client_cmd_id": client_cmd_id}
    assert ws.close_calls == []

    asyncio.run(
        stream_enqueteur_frame_diff_once(
            ws,
            session=session,
            host=host,
        )
    )
    diff_payload = _decode_sent_envelope(ws, 1)["payload"]
    assert any(op["op"] == "SET_OBJECT_INVESTIGATION_STATE" for op in diff_payload["ops"])
    assert any(
        op["op"] == "UPSERT_MINIGAME_STATE"
        and op.get("minigame_state", {}).get("minigame_id") == "MG1_LABEL_READING"
        and op.get("minigame_state", {}).get("completed") is True
        for op in diff_payload["ops"]
    )


def test_minigame_submit_rejects_mismatched_target_id() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "INVESTIGATION", "LEARNING", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-000000000013"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "MINIGAME_SUBMIT",
                        "payload": {
                            "minigame_id": "MG1",
                            "target_id": "O6_BADGE_TERMINAL",
                            "answer": {"label_guess": "Le Medaillon des Voyageurs"},
                        },
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["client_cmd_id"] == client_cmd_id
    assert rejected["payload"]["reason_code"] == "MINIGAME_INVALID_STATE"


def test_minigame_submit_rejects_invalid_answer_shape() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "INVESTIGATION", "LEARNING", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            host=host,
        )
    )
    ws.sent_texts.clear()

    client_cmd_id = "00000000-0000-4000-8000-000000000014"
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": client_cmd_id,
                    "tick_target": 1,
                    "cmd": {
                        "type": "MINIGAME_SUBMIT",
                        "payload": {
                            "minigame_id": "MG1",
                            "target_id": "O3_WALL_LABEL",
                            "answer": {},
                        },
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["client_cmd_id"] == client_cmd_id
    assert rejected["payload"]["reason_code"] == "MINIGAME_INVALID_SUBMISSION"


def test_attempt_recovery_rejects_invalid_target_id() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    _handshake_and_subscribe(
        host=host,
        ws=ws,
        session=session,
        channels=["WORLD", "INVESTIGATION", "EVENTS"],
    )

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": "00000000-0000-4000-8000-000000000021",
                    "tick_target": 1,
                    "cmd": {
                        "type": "ATTEMPT_RECOVERY",
                        "payload": {"target_id": "O1_DISPLAY_CASE"},
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["reason_code"] == "INVALID_COMMAND"


def test_attempt_recovery_rejects_missing_prerequisites() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    _handshake_and_subscribe(
        host=host,
        ws=ws,
        session=session,
        channels=["WORLD", "INVESTIGATION", "EVENTS"],
    )

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": "00000000-0000-4000-8000-000000000022",
                    "tick_target": 1,
                    "cmd": {
                        "type": "ATTEMPT_RECOVERY",
                        "payload": {"target_id": "O2_MEDALLION"},
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["reason_code"] == "RECOVERY_PREREQS_MISSING"


def test_attempt_recovery_accepts_when_requirements_are_satisfied() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    _prime_resolution_confrontation_gate(registry, payload)
    _prime_resolution_progress_for_recovery(registry, payload)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    _handshake_and_subscribe(
        host=host,
        ws=ws,
        session=session,
        channels=["WORLD", "INVESTIGATION", "EVENTS"],
    )

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": "00000000-0000-4000-8000-000000000023",
                    "tick_target": 1,
                    "cmd": {
                        "type": "ATTEMPT_RECOVERY",
                        "payload": {"target_id": "O2_MEDALLION"},
                    },
                },
            ),
            host=host,
        )
    )

    accepted = _decode_sent_envelope(ws, 0)
    assert accepted["msg_type"] == "COMMAND_ACCEPTED"

    asyncio.run(stream_enqueteur_frame_diff_once(ws, session=session, host=host))
    diff_payload = _decode_sent_envelope(ws, 1)["payload"]
    assert any(op["op"] in {"SET_RESOLUTION_STATUS", "SET_OUTCOME", "SET_RECAP"} for op in diff_payload["ops"])


def test_attempt_accusation_rejects_invalid_suspect_id() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    _handshake_and_subscribe(
        host=host,
        ws=ws,
        session=session,
        channels=["WORLD", "INVESTIGATION", "EVENTS"],
    )

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": "00000000-0000-4000-8000-000000000024",
                    "tick_target": 1,
                    "cmd": {
                        "type": "ATTEMPT_ACCUSATION",
                        "payload": {
                            "suspect_id": "not_a_suspect",
                            "supporting_fact_ids": [],
                            "supporting_evidence_ids": [],
                        },
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["reason_code"] == "INVALID_COMMAND"


def test_attempt_accusation_rejects_unknown_supporting_refs() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    _handshake_and_subscribe(
        host=host,
        ws=ws,
        session=session,
        channels=["WORLD", "INVESTIGATION", "EVENTS"],
    )

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": "00000000-0000-4000-8000-000000000025",
                    "tick_target": 1,
                    "cmd": {
                        "type": "ATTEMPT_ACCUSATION",
                        "payload": {
                            "suspect_id": "laurent",
                            "supporting_fact_ids": ["N999"],
                            "supporting_evidence_ids": ["E999_UNKNOWN"],
                        },
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["reason_code"] == "INVALID_COMMAND"


def test_attempt_accusation_rejects_missing_supporting_refs_and_missing_prereqs() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    _handshake_and_subscribe(
        host=host,
        ws=ws,
        session=session,
        channels=["WORLD", "INVESTIGATION", "EVENTS"],
    )

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": "00000000-0000-4000-8000-000000000026",
                    "tick_target": 1,
                    "cmd": {
                        "type": "ATTEMPT_ACCUSATION",
                        "payload": {
                            "suspect_id": "laurent",
                            "supporting_fact_ids": ["N3"],
                            "supporting_evidence_ids": ["E2_CAFE_RECEIPT"],
                        },
                    },
                },
            ),
            host=host,
        )
    )

    rejected = _decode_sent_envelope(ws, 0)
    assert rejected["msg_type"] == "COMMAND_REJECTED"
    assert rejected["payload"]["reason_code"] == "ACCUSATION_PREREQS_MISSING"


def test_attempt_accusation_accepts_when_requirements_are_satisfied() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    _prime_resolution_confrontation_gate(registry, payload)
    _prime_resolution_progress_for_accusation(registry, payload)
    started = registry.get(str(payload["run_id"]))
    assert started is not None
    case_state = started.runner.get_case_state()
    assert case_state is not None
    culprit_id = case_state.roles_assignment.culprit
    supporting_facts = list(case_state.resolution_rules.accusation_success.required_fact_ids)
    supporting_evidence = list(case_state.resolution_rules.accusation_success.required_items)

    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    _handshake_and_subscribe(
        host=host,
        ws=ws,
        session=session,
        channels=["WORLD", "INVESTIGATION", "EVENTS"],
    )

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": "00000000-0000-4000-8000-000000000027",
                    "tick_target": 1,
                    "cmd": {
                        "type": "ATTEMPT_ACCUSATION",
                        "payload": {
                            "suspect_id": culprit_id,
                            "supporting_fact_ids": supporting_facts,
                            "supporting_evidence_ids": supporting_evidence,
                        },
                    },
                },
            ),
            host=host,
        )
    )

    accepted = _decode_sent_envelope(ws, 0)
    assert accepted["msg_type"] == "COMMAND_ACCEPTED"

    asyncio.run(stream_enqueteur_frame_diff_once(ws, session=session, host=host))
    diff_payload = _decode_sent_envelope(ws, 1)["payload"]
    outcome_ops = [op for op in diff_payload["ops"] if op["op"] == "SET_OUTCOME"]
    assert outcome_ops
    latest_outcome = outcome_ops[-1].get("outcome")
    assert isinstance(latest_outcome, dict)
    assert latest_outcome.get("primary_outcome") == "accusation_success"


def test_internal_runtime_error_is_structured_and_fatal() -> None:
    class FailingHost(EnqueteurLiveSessionHost):
        def record_viewer_hello(self, connection_id: str, payload: dict[str, object]) -> dict[str, object]:
            raise RuntimeError("boom")

    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = FailingHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            host=host,
        )
    )

    error_env = _decode_sent_envelope(ws, 0)
    assert error_env["msg_type"] == "ERROR"
    assert error_env["payload"]["code"] == "INTERNAL_RUNTIME_ERROR"
    assert error_env["payload"]["fatal"] is True
    assert ws.close_calls == [(INTERNAL_RUNTIME_WS_CLOSE_CODE, INTERNAL_RUNTIME_WS_CLOSE_REASON)]


def test_live_session_host_tracks_connection_lifecycle() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()

    session = _open_attached_session(host, ws, str(payload["run_id"]))
    assert session.phase == "HANDSHAKING"

    handshake_payload = {
        "viewer_name": "enqueteur-webview",
        "viewer_version": "0.1.0",
        "supported_schema_versions": ["enqueteur_mbam_1"],
        "supports": {},
    }
    subscribe_payload = {
        "stream": "LIVE",
        "channels": ["WORLD"],
        "diff_policy": "DIFF_ONLY",
        "snapshot_policy": "ON_JOIN",
        "compression": "NONE",
    }
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope("VIEWER_HELLO", handshake_payload),
            host=host,
        )
    )
    asyncio.run(
        handle_enqueteur_live_incoming_message(
            ws,
            session=session,
            raw_message=_envelope("SUBSCRIBE", subscribe_payload),
            host=host,
        )
    )

    current = host.get_session(session.connection_id)
    assert current is not None
    assert current.phase == "SUBSCRIBED"
    assert current.protocol_state == "SUBSCRIBED"
    assert current.baseline_sent is True
    assert current.baseline_tick is not None

    closed = host.close_connection(
        session.connection_id,
        close_code=1001,
        close_reason="client_disconnect",
    )
    assert closed.phase == "CLOSED"
    assert closed.close_code == 1001
    assert closed.close_reason == "client_disconnect"
    assert closed.closed_at is not None

    sessions_for_run = host.list_sessions_for_run(str(payload["run_id"]))
    assert len(sessions_for_run) == 1
    assert sessions_for_run[0].phase == "CLOSED"


def test_handle_disconnect_marks_closed_and_cleans_up_session() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()
    session = _open_attached_session(host, ws, str(payload["ws_url"]))

    closed = handle_enqueteur_live_disconnect(
        session=session,
        close_code=1001,
        close_reason="CLIENT_DISCONNECT",
        host=host,
    )
    assert closed is not None
    assert closed.phase == "CLOSED"
    assert closed.close_code == 1001
    assert closed.close_reason == "CLIENT_DISCONNECT"
    assert host.get_session(session.connection_id) is None
    assert host.list_sessions_for_run(str(payload["run_id"])) == ()
