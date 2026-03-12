from __future__ import annotations

import asyncio
import importlib
import json

import pytest

pytest.importorskip("fastapi")

from backend.api.cases_start import (
    ENQUETEUR_ENGINE_NAME,
    ENQUETEUR_SCHEMA_VERSION,
    CaseRunRegistry,
    CaseStartService,
)
from fastapi import FastAPI
from starlette.websockets import WebSocketDisconnect
from fastapi.routing import APIRoute
from starlette.routing import WebSocketRoute

from backend.api.live_ws import (
    PROTOCOL_VIOLATION_WS_CLOSE_CODE,
    PROTOCOL_VIOLATION_WS_CLOSE_REASON,
    RUN_NOT_FOUND_WS_CLOSE_CODE,
    RUN_NOT_FOUND_WS_CLOSE_REASON,
)
from backend.server.app import create_app
from backend.server.config import DEFAULT_UVICORN_APP_PATH
from backend.server.models import CaseStartTransportRequest
from backend.server.routes_http import (
    CASE_START_PATH,
    CASE_START_PHASE_GATE,
    HOST_NOT_READY_CODE,
    launch_case_from_transport,
)
from backend.server.run_registry import RunRegistry
from backend.server.session_controller import SessionController
from backend.server.routes_ws import (
    LIVE_WS_PATH,
    WS_POLICY_VIOLATION,
)
from backend.sim4.integration.live_envelope import make_live_envelope


class FakeWebSocket:
    def __init__(
        self,
        *,
        app: FastAPI,
        run_id: str | None = None,
        incoming_texts: tuple[str, ...] = (),
    ) -> None:
        self.app = app
        self.query_params = {} if run_id is None else {"run_id": run_id}
        path = LIVE_WS_PATH if run_id is None else f"{LIVE_WS_PATH}?run_id={run_id}"
        self.url = f"ws://localhost:7777{path}"
        self._incoming_texts = list(incoming_texts)
        self.accept_calls = 0
        self.sent_payloads: list[dict[str, object]] = []
        self.sent_texts: list[str] = []
        self.close_calls: list[tuple[int, str]] = []

    async def accept(self) -> None:
        self.accept_calls += 1

    async def send_json(self, payload: dict[str, object]) -> None:
        self.sent_payloads.append(payload)

    async def send_text(self, data: str) -> None:
        self.sent_texts.append(data)

    async def receive_text(self) -> str:
        if self._incoming_texts:
            return self._incoming_texts.pop(0)
        raise WebSocketDisconnect(code=1001)

    async def close(self, *, code: int = 1000, reason: str = "") -> None:
        self.close_calls.append((code, reason))


class FakeRequest:
    def __init__(self, *, app: FastAPI, payload: object, raise_json_error: bool = False) -> None:
        self.app = app
        self._payload = payload
        self._raise_json_error = raise_json_error

    async def json(self) -> object:
        if self._raise_json_error:
            raise ValueError("invalid json")
        return self._payload


def _find_http_route_endpoint(*, app: FastAPI, path: str, method: str):
    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route.endpoint
    raise AssertionError(f"HTTP route not found: {method} {path}")


def _find_ws_route_endpoint(*, app: FastAPI, path: str):
    for route in app.routes:
        if isinstance(route, WebSocketRoute) and route.path == path:
            return route.endpoint
    raise AssertionError(f"WebSocket route not found: {path}")


def _envelope(msg_type: str, payload: dict[str, object]) -> str:
    envelope = make_live_envelope(
        msg_type,
        payload,
        msg_id="00000000-0000-4000-8000-000000000001",
        sent_at_ms=0,
    )
    return json.dumps(envelope)


def _decode_sent_envelope(websocket: FakeWebSocket, idx: int) -> dict[str, object]:
    decoded = json.loads(websocket.sent_texts[idx])
    assert isinstance(decoded, dict)
    return decoded


def test_canonical_asgi_target_imports_app_object() -> None:
    module_path, app_attr = DEFAULT_UVICORN_APP_PATH.split(":", maxsplit=1)
    module = importlib.import_module(module_path)
    app = getattr(module, app_attr)

    assert isinstance(app, FastAPI)


def test_server_shell_registers_s1_route_surface() -> None:
    app = create_app()
    route_paths = {route.path for route in app.routes}

    assert CASE_START_PATH in route_paths
    assert LIVE_WS_PATH in route_paths


def test_post_cases_start_launches_case_and_registers_run_in_server_registry() -> None:
    core_registry = CaseRunRegistry()
    case_start_service = CaseStartService(ws_base_url="ws://localhost:7777/live", registry=core_registry)
    run_registry = RunRegistry()

    status, body = launch_case_from_transport(
        CaseStartTransportRequest.from_payload(
            {
                "case_id": "MBAM_01",
                "seed": "A",
                "difficulty_profile": "D0",
                "mode": "playtest",
            }
        ),
        case_start_service=case_start_service,
        run_registry=run_registry,
    )

    assert status == 200
    assert body["run_id"]
    assert body["world_id"]
    assert body["engine_name"] == ENQUETEUR_ENGINE_NAME
    assert body["schema_version"] == ENQUETEUR_SCHEMA_VERSION
    assert body["ws_url"].startswith("ws://localhost:7777/live?run_id=")

    stored = run_registry.require(body["run_id"])
    assert stored.run_id == body["run_id"]
    assert stored.launch.world_id == body["world_id"]
    assert stored.launch.case_id == body["case_id"]
    assert stored.launch.ws_url == body["ws_url"]
    assert stored.runtime.started_run is not None
    assert run_registry.resolve_connection_target(body["ws_url"]) is not None


def test_post_cases_start_route_handler_uses_app_state_services() -> None:
    app = create_app()
    endpoint = _find_http_route_endpoint(app=app, path=CASE_START_PATH, method="POST")
    app.state.case_start_service = CaseStartService(
        ws_base_url="ws://localhost:7777/live",
        registry=CaseRunRegistry(),
    )
    app.state.run_registry = RunRegistry()

    response = asyncio.run(
        endpoint(
            FakeRequest(
                app=app,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
        )
    )
    body = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 200
    assert body["run_id"]
    assert app.state.run_registry.count() == 1
    assert app.state.run_registry.get(body["run_id"]) is not None


def test_post_cases_start_route_maps_invalid_json_payload() -> None:
    app = create_app()
    endpoint = _find_http_route_endpoint(app=app, path=CASE_START_PATH, method="POST")

    response = asyncio.run(
        endpoint(
            FakeRequest(
                app=app,
                payload=None,
                raise_json_error=True,
            )
        )
    )
    body = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 400
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert body["error"]["field"] == "payload"


def test_post_cases_start_route_maps_non_object_payload() -> None:
    app = create_app()
    endpoint = _find_http_route_endpoint(app=app, path=CASE_START_PATH, method="POST")

    response = asyncio.run(endpoint(FakeRequest(app=app, payload=["not", "an", "object"])))
    body = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 400
    assert body["error"]["code"] == "INVALID_REQUEST"
    assert body["error"]["field"] == "payload"


def test_post_cases_start_route_maps_host_not_ready() -> None:
    app = create_app()
    endpoint = _find_http_route_endpoint(app=app, path=CASE_START_PATH, method="POST")
    app.state.case_start_service = object()
    app.state.run_registry = RunRegistry()

    response = asyncio.run(
        endpoint(
            FakeRequest(
                app=app,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                },
            )
        )
    )
    body = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 503
    assert body["error"]["code"] == HOST_NOT_READY_CODE
    assert body["phase_gate"] == CASE_START_PHASE_GATE


def test_post_cases_start_preserves_core_validation_errors() -> None:
    core_registry = CaseRunRegistry()
    case_start_service = CaseStartService(ws_base_url="ws://localhost:7777/live", registry=core_registry)
    run_registry = RunRegistry()

    status, body = launch_case_from_transport(
        CaseStartTransportRequest.from_payload(
            {
                "case_id": "WRONG_CASE",
                "seed": "A",
                "difficulty_profile": "D0",
            }
        ),
        case_start_service=case_start_service,
        run_registry=run_registry,
    )

    assert status == 400
    assert body["error"]["code"] == "UNSUPPORTED_CASE"
    assert body["error"]["field"] == "case_id"
    assert run_registry.count() == 0


def test_post_cases_start_route_maps_core_launch_exception_without_leaking_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    endpoint = _find_http_route_endpoint(app=app, path=CASE_START_PATH, method="POST")
    app.state.case_start_service = CaseStartService(
        ws_base_url="ws://localhost:7777/live",
        registry=CaseRunRegistry(),
    )
    app.state.run_registry = RunRegistry()

    def _raise_launch_failure(*args, **kwargs):
        raise RuntimeError("internal stack trace detail")

    monkeypatch.setattr("backend.server.routes_http.handle_post_cases_start", _raise_launch_failure)

    response = asyncio.run(
        endpoint(
            FakeRequest(
                app=app,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                },
            )
        )
    )
    body = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 502
    assert body["error"]["code"] == "LAUNCH_FAILED"
    assert "internal stack trace detail" not in body["error"]["message"]


def test_post_cases_start_route_maps_invalid_success_contract_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    endpoint = _find_http_route_endpoint(app=app, path=CASE_START_PATH, method="POST")
    app.state.case_start_service = CaseStartService(
        ws_base_url="ws://localhost:7777/live",
        registry=CaseRunRegistry(),
    )
    app.state.run_registry = RunRegistry()

    monkeypatch.setattr("backend.server.routes_http.handle_post_cases_start", lambda *_args, **_kwargs: (200, {}))

    response = asyncio.run(
        endpoint(
            FakeRequest(
                app=app,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                },
            )
        )
    )
    body = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 502
    assert body["error"]["code"] == "INVALID_LAUNCH_RESPONSE"


def test_post_cases_start_route_maps_run_id_and_ws_url_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app()
    endpoint = _find_http_route_endpoint(app=app, path=CASE_START_PATH, method="POST")
    app.state.case_start_service = CaseStartService(
        ws_base_url="ws://localhost:7777/live",
        registry=CaseRunRegistry(),
    )
    app.state.run_registry = RunRegistry()

    monkeypatch.setattr(
        "backend.server.routes_http.handle_post_cases_start",
        lambda *_args, **_kwargs: (
            200,
            {
                "run_id": "run-123",
                "world_id": "world-123",
                "case_id": "MBAM_01",
                "seed": "A",
                "resolved_seed_id": "A",
                "difficulty_profile": "D0",
                "mode": "playtest",
                "engine_name": "enqueteur",
                "schema_version": "enqueteur_mbam_1",
                "ws_url": "ws://localhost:7777/live?run_id=run-999",
                "started_at": "2026-03-11T12:00:00Z",
            },
        ),
    )

    response = asyncio.run(
        endpoint(
            FakeRequest(
                app=app,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                },
            )
        )
    )
    body = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 502
    assert body["error"]["code"] == "INVALID_LAUNCH_RESPONSE"


def test_live_ws_rejects_missing_run_id_with_explicit_close() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path=LIVE_WS_PATH)
    run_registry = RunRegistry()
    app.state.run_registry = run_registry
    app.state.session_controller = SessionController(run_registry=run_registry)
    websocket = FakeWebSocket(app=app)
    asyncio.run(endpoint(websocket))

    assert websocket.accept_calls == 1
    error = _decode_sent_envelope(websocket, 0)
    assert error["msg_type"] == "ERROR"
    assert error["payload"]["code"] == "MISSING_RUN_ID"
    assert websocket.close_calls == [(WS_POLICY_VIOLATION, "MISSING_RUN_ID")]


def test_live_ws_rejects_unknown_run_id() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path=LIVE_WS_PATH)
    run_registry = RunRegistry()
    app.state.run_registry = run_registry
    app.state.session_controller = SessionController(run_registry=run_registry)
    websocket = FakeWebSocket(app=app, run_id="s4-missing")
    asyncio.run(endpoint(websocket))

    error = _decode_sent_envelope(websocket, 0)
    assert error["msg_type"] == "ERROR"
    assert error["payload"]["code"] == "RUN_NOT_FOUND"
    assert websocket.close_calls == [(RUN_NOT_FOUND_WS_CLOSE_CODE, RUN_NOT_FOUND_WS_CLOSE_REASON)]


def test_live_ws_runs_handshake_then_baseline_from_canonical_run_registry() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path=LIVE_WS_PATH)
    core_registry = CaseRunRegistry()
    case_start_service = CaseStartService(ws_base_url="ws://localhost:7777/live", registry=core_registry)
    run_registry = RunRegistry()
    app.state.case_start_service = case_start_service
    app.state.run_registry = run_registry
    app.state.session_controller = SessionController(run_registry=run_registry)

    status, body = launch_case_from_transport(
        CaseStartTransportRequest.from_payload(
            {
                "case_id": "MBAM_01",
                "seed": "A",
                "difficulty_profile": "D0",
                "mode": "playtest",
            }
        ),
        case_start_service=case_start_service,
        run_registry=run_registry,
    )
    assert status == 200
    run_id = str(body["run_id"])
    world_id = str(body["world_id"])

    # Ensure /live attachment is driven by canonical server run_registry, not core launch registry lookups.
    core_registry._runs.clear()  # type: ignore[attr-defined]

    websocket = FakeWebSocket(
        app=app,
        run_id=run_id,
        incoming_texts=(
            _envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            _envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "NPCS", "INVESTIGATION", "DIALOGUE", "LEARNING", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
        ),
    )

    asyncio.run(endpoint(websocket))

    msg_types = [_decode_sent_envelope(websocket, i)["msg_type"] for i in range(len(websocket.sent_texts))]
    assert msg_types == ["KERNEL_HELLO", "SUBSCRIBED", "FULL_SNAPSHOT"]
    kernel_hello = _decode_sent_envelope(websocket, 0)["payload"]
    assert kernel_hello["run_id"] == run_id
    assert kernel_hello["world_id"] == world_id
    assert kernel_hello["engine_name"] == ENQUETEUR_ENGINE_NAME
    assert kernel_hello["schema_version"] == ENQUETEUR_SCHEMA_VERSION
    assert run_registry.get(run_id) is not None
    assert app.state.session_controller.list_sessions() == ()


def test_live_ws_rejects_subscribe_before_viewer_hello() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path=LIVE_WS_PATH)
    core_registry = CaseRunRegistry()
    case_start_service = CaseStartService(ws_base_url="ws://localhost:7777/live", registry=core_registry)
    run_registry = RunRegistry()
    app.state.case_start_service = case_start_service
    app.state.run_registry = run_registry
    app.state.session_controller = SessionController(run_registry=run_registry)

    status, body = launch_case_from_transport(
        CaseStartTransportRequest.from_payload(
            {
                "case_id": "MBAM_01",
                "seed": "A",
                "difficulty_profile": "D0",
                "mode": "playtest",
            }
        ),
        case_start_service=case_start_service,
        run_registry=run_registry,
    )
    assert status == 200
    run_id = str(body["run_id"])

    websocket = FakeWebSocket(
        app=app,
        run_id=run_id,
        incoming_texts=(
            _envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
        ),
    )
    asyncio.run(endpoint(websocket))

    error = _decode_sent_envelope(websocket, 0)
    assert error["msg_type"] == "ERROR"
    assert error["payload"]["code"] == "BAD_SEQUENCE"
    assert websocket.close_calls == [(PROTOCOL_VIOLATION_WS_CLOSE_CODE, PROTOCOL_VIOLATION_WS_CLOSE_REASON)]


def test_live_ws_rejects_ping_before_viewer_hello() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path=LIVE_WS_PATH)
    core_registry = CaseRunRegistry()
    case_start_service = CaseStartService(ws_base_url="ws://localhost:7777/live", registry=core_registry)
    run_registry = RunRegistry()
    app.state.case_start_service = case_start_service
    app.state.run_registry = run_registry
    app.state.session_controller = SessionController(run_registry=run_registry)

    status, body = launch_case_from_transport(
        CaseStartTransportRequest.from_payload(
            {
                "case_id": "MBAM_01",
                "seed": "A",
                "difficulty_profile": "D0",
                "mode": "playtest",
            }
        ),
        case_start_service=case_start_service,
        run_registry=run_registry,
    )
    assert status == 200
    run_id = str(body["run_id"])

    websocket = FakeWebSocket(
        app=app,
        run_id=run_id,
        incoming_texts=(
            _envelope("PING", {"nonce": 1}),
        ),
    )
    asyncio.run(endpoint(websocket))

    error = _decode_sent_envelope(websocket, 0)
    assert error["msg_type"] == "ERROR"
    assert error["payload"]["code"] == "BAD_SEQUENCE"
    assert websocket.close_calls == [(PROTOCOL_VIOLATION_WS_CLOSE_CODE, PROTOCOL_VIOLATION_WS_CLOSE_REASON)]


def test_live_ws_rejects_non_subscribe_second_message() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path=LIVE_WS_PATH)
    core_registry = CaseRunRegistry()
    case_start_service = CaseStartService(ws_base_url="ws://localhost:7777/live", registry=core_registry)
    run_registry = RunRegistry()
    app.state.case_start_service = case_start_service
    app.state.run_registry = run_registry
    app.state.session_controller = SessionController(run_registry=run_registry)

    status, body = launch_case_from_transport(
        CaseStartTransportRequest.from_payload(
            {
                "case_id": "MBAM_01",
                "seed": "A",
                "difficulty_profile": "D0",
                "mode": "playtest",
            }
        ),
        case_start_service=case_start_service,
        run_registry=run_registry,
    )
    assert status == 200
    run_id = str(body["run_id"])

    websocket = FakeWebSocket(
        app=app,
        run_id=run_id,
        incoming_texts=(
            _envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            _envelope("PING", {"nonce": "x"}),
        ),
    )
    asyncio.run(endpoint(websocket))

    msg_types = [_decode_sent_envelope(websocket, i)["msg_type"] for i in range(len(websocket.sent_texts))]
    assert msg_types == ["KERNEL_HELLO", "ERROR"]
    assert _decode_sent_envelope(websocket, 1)["payload"]["code"] == "BAD_SEQUENCE"
    assert websocket.close_calls == [(PROTOCOL_VIOLATION_WS_CLOSE_CODE, PROTOCOL_VIOLATION_WS_CLOSE_REASON)]


def test_live_ws_requires_on_join_baseline_in_s4() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path=LIVE_WS_PATH)
    core_registry = CaseRunRegistry()
    case_start_service = CaseStartService(ws_base_url="ws://localhost:7777/live", registry=core_registry)
    run_registry = RunRegistry()
    app.state.case_start_service = case_start_service
    app.state.run_registry = run_registry
    app.state.session_controller = SessionController(run_registry=run_registry)

    status, body = launch_case_from_transport(
        CaseStartTransportRequest.from_payload(
            {
                "case_id": "MBAM_01",
                "seed": "A",
                "difficulty_profile": "D0",
                "mode": "playtest",
            }
        ),
        case_start_service=case_start_service,
        run_registry=run_registry,
    )
    assert status == 200
    run_id = str(body["run_id"])

    websocket = FakeWebSocket(
        app=app,
        run_id=run_id,
        incoming_texts=(
            _envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            _envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "NEVER",
                    "compression": "NONE",
                },
            ),
        ),
    )
    asyncio.run(endpoint(websocket))

    msg_types = [_decode_sent_envelope(websocket, i)["msg_type"] for i in range(len(websocket.sent_texts))]
    assert msg_types == ["KERNEL_HELLO", "SUBSCRIBED", "ERROR"]
    assert _decode_sent_envelope(websocket, 2)["payload"]["code"] == "BASELINE_REQUIRED"
    assert websocket.close_calls == [(PROTOCOL_VIOLATION_WS_CLOSE_CODE, PROTOCOL_VIOLATION_WS_CLOSE_REASON)]


def test_live_ws_post_baseline_processes_input_command() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path=LIVE_WS_PATH)
    core_registry = CaseRunRegistry()
    case_start_service = CaseStartService(ws_base_url="ws://localhost:7777/live", registry=core_registry)
    run_registry = RunRegistry()
    app.state.case_start_service = case_start_service
    app.state.run_registry = run_registry
    app.state.session_controller = SessionController(run_registry=run_registry)

    status, body = launch_case_from_transport(
        CaseStartTransportRequest.from_payload(
            {
                "case_id": "MBAM_01",
                "seed": "A",
                "difficulty_profile": "D0",
                "mode": "playtest",
            }
        ),
        case_start_service=case_start_service,
        run_registry=run_registry,
    )
    assert status == 200
    run_id = str(body["run_id"])

    websocket = FakeWebSocket(
        app=app,
        run_id=run_id,
        incoming_texts=(
            _envelope(
                "VIEWER_HELLO",
                {
                    "viewer_name": "enqueteur-webview",
                    "viewer_version": "0.1.0",
                    "supported_schema_versions": ["enqueteur_mbam_1"],
                    "supports": {},
                },
            ),
            _envelope(
                "SUBSCRIBE",
                {
                    "stream": "LIVE",
                    "channels": ["WORLD", "INVESTIGATION", "EVENTS"],
                    "diff_policy": "DIFF_ONLY",
                    "snapshot_policy": "ON_JOIN",
                    "compression": "NONE",
                },
            ),
            _envelope(
                "INPUT_COMMAND",
                {
                    "client_cmd_id": "00000000-0000-4000-8000-000000000001",
                    "tick_target": 1,
                    "cmd": {"type": "INVESTIGATE_OBJECT", "payload": {"object_id": "O4_BENCH", "action_id": "inspect"}},
                },
            ),
        ),
    )
    asyncio.run(endpoint(websocket))

    msg_types = [_decode_sent_envelope(websocket, i)["msg_type"] for i in range(len(websocket.sent_texts))]
    assert msg_types == ["KERNEL_HELLO", "SUBSCRIBED", "FULL_SNAPSHOT", "COMMAND_ACCEPTED", "FRAME_DIFF"]
    assert _decode_sent_envelope(websocket, 3)["payload"]["client_cmd_id"] == "00000000-0000-4000-8000-000000000001"
    frame_diff = _decode_sent_envelope(websocket, 4)["payload"]
    assert frame_diff["from_tick"] == _decode_sent_envelope(websocket, 2)["payload"]["tick"]
    assert frame_diff["to_tick"] == frame_diff["from_tick"] + 1
    assert websocket.close_calls == []


def test_live_ws_rejects_run_without_runtime_binding() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path=LIVE_WS_PATH)
    run_registry = RunRegistry()
    app.state.run_registry = run_registry
    app.state.session_controller = SessionController(run_registry=run_registry)

    run_id = "orphan-run"
    run_registry.register_launched_run(
        launch_payload={
            "run_id": run_id,
            "world_id": "world-orphan",
            "case_id": "MBAM_01",
            "seed": "A",
            "resolved_seed_id": "A",
            "difficulty_profile": "D0",
            "mode": "playtest",
            "engine_name": "enqueteur",
            "schema_version": "enqueteur_mbam_1",
            "ws_url": f"ws://localhost:7777/live?run_id={run_id}",
            "started_at": "2026-03-11T12:00:00Z",
        },
        started_run=None,
    )

    websocket = FakeWebSocket(app=app, run_id=run_id)
    asyncio.run(endpoint(websocket))

    error = _decode_sent_envelope(websocket, 0)
    assert error["msg_type"] == "ERROR"
    assert error["payload"]["code"] == "RUN_NOT_FOUND"
    assert websocket.close_calls == [(RUN_NOT_FOUND_WS_CLOSE_CODE, RUN_NOT_FOUND_WS_CLOSE_REASON)]


def test_case_start_transport_request_omits_mode_when_missing() -> None:
    request = CaseStartTransportRequest.from_payload(
        {
            "case_id": "MBAM_01",
            "seed": "A",
            "difficulty_profile": "D0",
        }
    )

    assert request.to_core_payload() == {
        "case_id": "MBAM_01",
        "seed": "A",
        "difficulty_profile": "D0",
    }
