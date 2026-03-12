from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from typing import Any
from urllib.parse import urlsplit

import pytest

pytest.importorskip("fastapi")

from backend.api.live_ws import (
    PROTOCOL_VIOLATION_WS_CLOSE_CODE,
    PROTOCOL_VIOLATION_WS_CLOSE_REASON,
    RUN_NOT_FOUND_WS_CLOSE_CODE,
    RUN_NOT_FOUND_WS_CLOSE_REASON,
)
from backend.server.app import create_app
from backend.server.routes_http import CASE_START_PATH
from backend.server.routes_ws import HOST_SHUTTING_DOWN_CODE, WS_POLICY_VIOLATION, WS_TRY_AGAIN_LATER
from backend.sim4.integration.live_envelope import make_live_envelope


@dataclass(frozen=True)
class AsgiHttpResponse:
    status_code: int
    headers: tuple[tuple[bytes, bytes], ...]
    body: bytes

    def json(self) -> dict[str, Any]:
        parsed = json.loads(self.body.decode("utf-8"))
        assert isinstance(parsed, dict)
        return parsed


@dataclass(frozen=True)
class AsgiWsResult:
    accepted: bool
    sent_texts: tuple[str, ...]
    close_frames: tuple[tuple[int, str], ...]

    def decoded_envelopes(self) -> tuple[dict[str, Any], ...]:
        out: list[dict[str, Any]] = []
        for text in self.sent_texts:
            parsed = json.loads(text)
            assert isinstance(parsed, dict)
            out.append(parsed)
        return tuple(out)


async def _asgi_http_request(
    app: Any,
    *,
    method: str,
    path: str,
    body: bytes = b"",
    headers: tuple[tuple[bytes, bytes], ...] = (),
) -> AsgiHttpResponse:
    request_messages: list[dict[str, Any]] = [
        {"type": "http.request", "body": body, "more_body": False}
    ]
    sent_messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        if request_messages:
            return request_messages.pop(0)
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": list(headers),
        "client": ("127.0.0.1", 43210),
        "server": ("testserver", 80),
    }

    await app(scope, receive, send)

    start = next(message for message in sent_messages if message["type"] == "http.response.start")
    body_parts = [message.get("body", b"") for message in sent_messages if message["type"] == "http.response.body"]
    return AsgiHttpResponse(
        status_code=int(start["status"]),
        headers=tuple(start.get("headers", [])),
        body=b"".join(body_parts),
    )


async def _post_json(app: Any, *, path: str, payload: object) -> AsgiHttpResponse:
    return await _asgi_http_request(
        app,
        method="POST",
        path=path,
        body=json.dumps(payload).encode("utf-8"),
        headers=((b"content-type", b"application/json"),),
    )


def _path_and_query_target(path_or_url: str) -> tuple[str, bytes]:
    if "://" in path_or_url:
        parsed = urlsplit(path_or_url)
        path = parsed.path or "/"
        return path, parsed.query.encode("utf-8")

    if "?" in path_or_url:
        path, query = path_or_url.split("?", maxsplit=1)
        return path or "/", query.encode("utf-8")
    return path_or_url or "/", b""


async def _asgi_ws_session(
    app: Any,
    *,
    path_or_url: str,
    incoming_texts: tuple[str, ...] = (),
    disconnect_code: int = 1001,
) -> AsgiWsResult:
    path, query_string = _path_and_query_target(path_or_url)
    request_messages: list[dict[str, Any]] = [{"type": "websocket.connect"}]
    request_messages.extend({"type": "websocket.receive", "text": text} for text in incoming_texts)
    request_messages.append({"type": "websocket.disconnect", "code": disconnect_code})
    sent_messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        if request_messages:
            return request_messages.pop(0)
        return {"type": "websocket.disconnect", "code": disconnect_code}

    async def send(message: dict[str, Any]) -> None:
        sent_messages.append(message)

    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string,
        "headers": [],
        "client": ("127.0.0.1", 43210),
        "server": ("testserver", 80),
        "subprotocols": [],
    }

    await app(scope, receive, send)

    accepted = any(message["type"] == "websocket.accept" for message in sent_messages)
    sent_texts = tuple(
        message["text"]
        for message in sent_messages
        if message["type"] == "websocket.send" and isinstance(message.get("text"), str)
    )
    close_frames = tuple(
        (int(message.get("code", 1000)), str(message.get("reason", "")))
        for message in sent_messages
        if message["type"] == "websocket.close"
    )
    return AsgiWsResult(
        accepted=accepted,
        sent_texts=sent_texts,
        close_frames=close_frames,
    )


def _envelope(msg_type: str, payload: dict[str, object]) -> str:
    envelope = make_live_envelope(
        msg_type,
        payload,
        msg_id="00000000-0000-4000-8000-000000000001",
        sent_at_ms=0,
    )
    return json.dumps(envelope)


def _viewer_hello(*, supported_schema_versions: list[str] | None = None) -> str:
    return _envelope(
        "VIEWER_HELLO",
        {
            "viewer_name": "enqueteur-webview",
            "viewer_version": "0.1.0",
            "supported_schema_versions": supported_schema_versions or ["enqueteur_mbam_1"],
            "supports": {},
        },
    )


def _subscribe(*, snapshot_policy: str = "ON_JOIN") -> str:
    return _envelope(
        "SUBSCRIBE",
        {
            "stream": "LIVE",
            "channels": ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
            "diff_policy": "DIFF_ONLY",
            "snapshot_policy": snapshot_policy,
            "compression": "NONE",
        },
    )


def test_s4_asgi_happy_path_launch_then_live_handshake_and_baseline() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            launch = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            launch_payload = launch.json()
            assert launch.status_code == 200

            ws_result = await _asgi_ws_session(
                app,
                path_or_url=str(launch_payload["ws_url"]),
                incoming_texts=(
                    _viewer_hello(),
                    _subscribe(),
                ),
            )

            assert ws_result.accepted is True
            envelopes = ws_result.decoded_envelopes()
            assert [env["msg_type"] for env in envelopes] == ["KERNEL_HELLO", "SUBSCRIBED", "FULL_SNAPSHOT"]
            kernel_payload = envelopes[0]["payload"]
            assert kernel_payload["run_id"] == launch_payload["run_id"]
            assert kernel_payload["world_id"] == launch_payload["world_id"]
            assert kernel_payload["engine_name"] == launch_payload["engine_name"]
            assert kernel_payload["schema_version"] == launch_payload["schema_version"]

            baseline = envelopes[2]["payload"]
            assert baseline["schema_version"] == launch_payload["schema_version"]
            assert isinstance(baseline["tick"], int)
            assert isinstance(baseline["step_hash"], str)
            assert isinstance(baseline["state"], dict)
            assert app.state.run_registry.get(str(launch_payload["run_id"])) is not None
            assert app.state.session_controller.list_sessions() == ()

    asyncio.run(_scenario())


def test_s4_asgi_live_rejects_missing_and_unknown_run() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            missing_run = await _asgi_ws_session(
                app,
                path_or_url="/live",
            )
            assert missing_run.accepted is True
            missing_env = missing_run.decoded_envelopes()
            assert [env["msg_type"] for env in missing_env] == ["ERROR"]
            assert missing_env[0]["payload"]["code"] == "MISSING_RUN_ID"
            assert missing_run.close_frames == ((WS_POLICY_VIOLATION, "MISSING_RUN_ID"),)

            unknown_run = await _asgi_ws_session(
                app,
                path_or_url="/live?run_id=missing-run",
            )
            assert unknown_run.accepted is True
            unknown_env = unknown_run.decoded_envelopes()
            assert [env["msg_type"] for env in unknown_env] == ["ERROR"]
            assert unknown_env[0]["payload"]["code"] == "RUN_NOT_FOUND"
            assert unknown_run.close_frames == ((RUN_NOT_FOUND_WS_CLOSE_CODE, RUN_NOT_FOUND_WS_CLOSE_REASON),)

    asyncio.run(_scenario())


def test_s7_asgi_live_rejects_expired_run_after_lazy_registry_eviction() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            launch = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            launch_payload = launch.json()
            assert launch.status_code == 200
            run_id = str(launch_payload["run_id"])

            entry = app.state.run_registry.require(run_id)
            entry.host.last_activity_at = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
            entry.host.active_session_id = None
            app.state.run_registry.put(entry)

            ws_result = await _asgi_ws_session(
                app,
                path_or_url=str(launch_payload["ws_url"]),
            )

            assert ws_result.accepted is True
            envelopes = ws_result.decoded_envelopes()
            assert [env["msg_type"] for env in envelopes] == ["ERROR"]
            assert envelopes[0]["payload"]["code"] == "RUN_NOT_FOUND"
            assert ws_result.close_frames == ((RUN_NOT_FOUND_WS_CLOSE_CODE, RUN_NOT_FOUND_WS_CLOSE_REASON),)
            assert app.state.run_registry.get(run_id) is None

            recovery_launch = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "B",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            recovery_payload = recovery_launch.json()
            assert recovery_launch.status_code == 200
            recovery_ws = await _asgi_ws_session(
                app,
                path_or_url=str(recovery_payload["ws_url"]),
                incoming_texts=(
                    _viewer_hello(),
                    _subscribe(),
                ),
            )
            assert recovery_ws.accepted is True
            assert [env["msg_type"] for env in recovery_ws.decoded_envelopes()] == [
                "KERNEL_HELLO",
                "SUBSCRIBED",
                "FULL_SNAPSHOT",
            ]
            assert recovery_ws.close_frames == ()

    asyncio.run(_scenario())


def test_s7_asgi_live_rejects_removed_run_and_host_stays_usable() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            launch = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            launch_payload = launch.json()
            assert launch.status_code == 200
            run_id = str(launch_payload["run_id"])
            removed = app.state.run_registry.remove(run_id)
            assert removed is not None

            missing_ws = await _asgi_ws_session(
                app,
                path_or_url=str(launch_payload["ws_url"]),
            )
            assert missing_ws.accepted is True
            missing_envs = missing_ws.decoded_envelopes()
            assert [env["msg_type"] for env in missing_envs] == ["ERROR"]
            assert missing_envs[0]["payload"]["code"] == "RUN_NOT_FOUND"
            assert missing_ws.close_frames == ((RUN_NOT_FOUND_WS_CLOSE_CODE, RUN_NOT_FOUND_WS_CLOSE_REASON),)

            followup_launch = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "B",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            followup_payload = followup_launch.json()
            assert followup_launch.status_code == 200

            followup_ws = await _asgi_ws_session(
                app,
                path_or_url=str(followup_payload["ws_url"]),
                incoming_texts=(
                    _viewer_hello(),
                    _subscribe(),
                ),
            )
            assert followup_ws.accepted is True
            assert [env["msg_type"] for env in followup_ws.decoded_envelopes()] == [
                "KERNEL_HELLO",
                "SUBSCRIBED",
                "FULL_SNAPSHOT",
            ]
            assert followup_ws.close_frames == ()

    asyncio.run(_scenario())


def test_s7_asgi_live_rejects_new_connections_while_host_shutting_down() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            app.state.shutting_down = True
            ws_result = await _asgi_ws_session(
                app,
                path_or_url="/live?run_id=run-any",
            )
            assert ws_result.accepted is True
            assert len(ws_result.sent_texts) == 1
            payload = json.loads(ws_result.sent_texts[0])
            assert payload["error"]["code"] == HOST_SHUTTING_DOWN_CODE
            assert ws_result.close_frames == ((WS_TRY_AGAIN_LATER, HOST_SHUTTING_DOWN_CODE),)
            assert app.state.session_controller.list_sessions() == ()

    asyncio.run(_scenario())


def test_s7_asgi_live_protocol_failure_does_not_block_reconnect_same_run() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            launch = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            launch_payload = launch.json()
            assert launch.status_code == 200
            ws_target = str(launch_payload["ws_url"])

            failed_ws = await _asgi_ws_session(
                app,
                path_or_url=ws_target,
                incoming_texts=(
                    _subscribe(),
                ),
            )
            assert failed_ws.accepted is True
            failed_envs = failed_ws.decoded_envelopes()
            assert [env["msg_type"] for env in failed_envs] == ["ERROR"]
            assert failed_envs[0]["payload"]["code"] == "BAD_SEQUENCE"
            assert failed_ws.close_frames == ((PROTOCOL_VIOLATION_WS_CLOSE_CODE, PROTOCOL_VIOLATION_WS_CLOSE_REASON),)
            assert app.state.session_controller.list_sessions() == ()

            recovery_ws = await _asgi_ws_session(
                app,
                path_or_url=ws_target,
                incoming_texts=(
                    _viewer_hello(),
                    _subscribe(),
                ),
            )
            assert recovery_ws.accepted is True
            assert [env["msg_type"] for env in recovery_ws.decoded_envelopes()] == [
                "KERNEL_HELLO",
                "SUBSCRIBED",
                "FULL_SNAPSHOT",
            ]
            assert recovery_ws.close_frames == ()
            assert app.state.session_controller.list_sessions() == ()

    asyncio.run(_scenario())


def test_s4_asgi_live_rejects_invalid_message_order() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            launch = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            launch_payload = launch.json()
            assert launch.status_code == 200

            ws_result = await _asgi_ws_session(
                app,
                path_or_url=str(launch_payload["ws_url"]),
                incoming_texts=(
                    _subscribe(),
                ),
            )
            assert ws_result.accepted is True
            envelopes = ws_result.decoded_envelopes()
            assert [env["msg_type"] for env in envelopes] == ["ERROR"]
            assert envelopes[0]["payload"]["code"] == "BAD_SEQUENCE"
            assert ws_result.close_frames == ((PROTOCOL_VIOLATION_WS_CLOSE_CODE, PROTOCOL_VIOLATION_WS_CLOSE_REASON),)

    asyncio.run(_scenario())


def test_s4_asgi_live_rejects_schema_mismatch_in_viewer_hello() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            launch = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            launch_payload = launch.json()
            assert launch.status_code == 200

            ws_result = await _asgi_ws_session(
                app,
                path_or_url=str(launch_payload["ws_url"]),
                incoming_texts=(
                    _viewer_hello(supported_schema_versions=["sim4_legacy"]),
                ),
            )
            assert ws_result.accepted is True
            envelopes = ws_result.decoded_envelopes()
            assert [env["msg_type"] for env in envelopes] == ["ERROR"]
            assert envelopes[0]["payload"]["code"] == "SCHEMA_MISMATCH"
            assert ws_result.close_frames == ((PROTOCOL_VIOLATION_WS_CLOSE_CODE, PROTOCOL_VIOLATION_WS_CLOSE_REASON),)

    asyncio.run(_scenario())


def test_s5_asgi_live_post_baseline_accepts_input_command() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            launch = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            launch_payload = launch.json()
            assert launch.status_code == 200

            ws_result = await _asgi_ws_session(
                app,
                path_or_url=str(launch_payload["ws_url"]),
                incoming_texts=(
                    _viewer_hello(),
                    _subscribe(),
                    _envelope(
                        "INPUT_COMMAND",
                        {
                            "client_cmd_id": "00000000-0000-4000-8000-000000000001",
                            "tick_target": 1,
                            "cmd": {
                                "type": "INVESTIGATE_OBJECT",
                                "payload": {"object_id": "O4_BENCH", "action_id": "inspect"},
                            },
                        },
                    ),
                ),
            )
            assert ws_result.accepted is True
            envelopes = ws_result.decoded_envelopes()
            assert [env["msg_type"] for env in envelopes] == [
                "KERNEL_HELLO",
                "SUBSCRIBED",
                "FULL_SNAPSHOT",
                "COMMAND_ACCEPTED",
                "FRAME_DIFF",
            ]
            assert envelopes[3]["payload"]["client_cmd_id"] == "00000000-0000-4000-8000-000000000001"
            frame_diff = envelopes[4]["payload"]
            assert frame_diff["schema_version"] == launch_payload["schema_version"]
            assert frame_diff["from_tick"] == envelopes[2]["payload"]["tick"]
            assert frame_diff["to_tick"] == frame_diff["from_tick"] + 1
            assert isinstance(frame_diff["ops"], list)
            assert ws_result.close_frames == ()
            assert app.state.session_controller.list_sessions() == ()
            run_entry = app.state.run_registry.require(str(launch_payload["run_id"]))
            assert run_entry.host.last_session_id is not None

    asyncio.run(_scenario())


def test_s5_asgi_live_post_baseline_rejects_invalid_input_command() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            launch = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            launch_payload = launch.json()
            assert launch.status_code == 200

            ws_result = await _asgi_ws_session(
                app,
                path_or_url=str(launch_payload["ws_url"]),
                incoming_texts=(
                    _viewer_hello(),
                    _subscribe(),
                    _envelope(
                        "INPUT_COMMAND",
                        {
                            "client_cmd_id": "00000000-0000-4000-8000-000000000002",
                            "tick_target": 1,
                            "cmd": {
                                "type": "INVESTIGATE_OBJECT",
                                "payload": {"object_id": "UNKNOWN_OBJECT", "action_id": "inspect"},
                            },
                        },
                    ),
                ),
            )
            assert ws_result.accepted is True
            envelopes = ws_result.decoded_envelopes()
            assert [env["msg_type"] for env in envelopes] == [
                "KERNEL_HELLO",
                "SUBSCRIBED",
                "FULL_SNAPSHOT",
                "COMMAND_REJECTED",
            ]
            rejected = envelopes[3]["payload"]
            assert rejected["client_cmd_id"] == "00000000-0000-4000-8000-000000000002"
            assert isinstance(rejected["reason_code"], str) and rejected["reason_code"]
            assert isinstance(rejected["message"], str) and rejected["message"]
            assert "FRAME_DIFF" not in [env["msg_type"] for env in envelopes]
            assert ws_result.close_frames == ()
            assert app.state.session_controller.list_sessions() == ()
            run_entry = app.state.run_registry.require(str(launch_payload["run_id"]))
            assert run_entry.host.last_session_id is not None

    asyncio.run(_scenario())


def test_s5_asgi_live_reject_then_accepts_later_command_and_emits_diff() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            launch = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            launch_payload = launch.json()
            assert launch.status_code == 200

            ws_result = await _asgi_ws_session(
                app,
                path_or_url=str(launch_payload["ws_url"]),
                incoming_texts=(
                    _viewer_hello(),
                    _subscribe(),
                    _envelope(
                        "INPUT_COMMAND",
                        {
                            "client_cmd_id": "00000000-0000-4000-8000-000000000010",
                            "tick_target": 1,
                            "cmd": {
                                "type": "INVESTIGATE_OBJECT",
                                "payload": {"object_id": "UNKNOWN_OBJECT", "action_id": "inspect"},
                            },
                        },
                    ),
                    _envelope(
                        "INPUT_COMMAND",
                        {
                            "client_cmd_id": "00000000-0000-4000-8000-000000000011",
                            "tick_target": 1,
                            "cmd": {
                                "type": "INVESTIGATE_OBJECT",
                                "payload": {"object_id": "O4_BENCH", "action_id": "inspect"},
                            },
                        },
                    ),
                ),
            )
            assert ws_result.accepted is True
            envelopes = ws_result.decoded_envelopes()
            assert [env["msg_type"] for env in envelopes] == [
                "KERNEL_HELLO",
                "SUBSCRIBED",
                "FULL_SNAPSHOT",
                "COMMAND_REJECTED",
                "COMMAND_ACCEPTED",
                "FRAME_DIFF",
            ]
            assert envelopes[3]["payload"]["client_cmd_id"] == "00000000-0000-4000-8000-000000000010"
            assert envelopes[4]["payload"]["client_cmd_id"] == "00000000-0000-4000-8000-000000000011"
            frame_diff = envelopes[5]["payload"]
            assert frame_diff["from_tick"] == envelopes[2]["payload"]["tick"]
            assert frame_diff["to_tick"] == frame_diff["from_tick"] + 1
            assert ws_result.close_frames == ()
            assert app.state.session_controller.list_sessions() == ()

    asyncio.run(_scenario())


def test_s5_asgi_live_repeated_interactive_sessions_teardown_cleanly() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            launch_one = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            payload_one = launch_one.json()
            assert launch_one.status_code == 200
            session_one = await _asgi_ws_session(
                app,
                path_or_url=str(payload_one["ws_url"]),
                incoming_texts=(
                    _viewer_hello(),
                    _subscribe(),
                    _envelope(
                        "INPUT_COMMAND",
                        {
                            "client_cmd_id": "00000000-0000-4000-8000-000000000020",
                            "tick_target": 1,
                            "cmd": {
                                "type": "INVESTIGATE_OBJECT",
                                "payload": {"object_id": "O4_BENCH", "action_id": "inspect"},
                            },
                        },
                    ),
                ),
            )
            assert [env["msg_type"] for env in session_one.decoded_envelopes()] == [
                "KERNEL_HELLO",
                "SUBSCRIBED",
                "FULL_SNAPSHOT",
                "COMMAND_ACCEPTED",
                "FRAME_DIFF",
            ]
            assert session_one.close_frames == ()
            assert app.state.session_controller.list_sessions() == ()
            entry_one = app.state.run_registry.require(str(payload_one["run_id"]))
            session_id_one = entry_one.host.last_session_id
            assert session_id_one is not None

            launch_two = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "B",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            payload_two = launch_two.json()
            assert launch_two.status_code == 200
            session_two = await _asgi_ws_session(
                app,
                path_or_url=str(payload_two["ws_url"]),
                incoming_texts=(
                    _viewer_hello(),
                    _subscribe(),
                    _envelope(
                        "INPUT_COMMAND",
                        {
                            "client_cmd_id": "00000000-0000-4000-8000-000000000021",
                            "tick_target": 1,
                            "cmd": {
                                "type": "INVESTIGATE_OBJECT",
                                "payload": {"object_id": "O4_BENCH", "action_id": "inspect"},
                            },
                        },
                    ),
                ),
            )
            assert [env["msg_type"] for env in session_two.decoded_envelopes()] == [
                "KERNEL_HELLO",
                "SUBSCRIBED",
                "FULL_SNAPSHOT",
                "COMMAND_ACCEPTED",
                "FRAME_DIFF",
            ]
            assert session_two.close_frames == ()
            assert app.state.session_controller.list_sessions() == ()
            entry_two = app.state.run_registry.require(str(payload_two["run_id"]))
            assert entry_two.host.last_session_id is not None
            assert entry_two.host.last_session_id != session_id_one

    asyncio.run(_scenario())
