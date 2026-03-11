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
from fastapi.routing import APIRoute
from starlette.routing import WebSocketRoute

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
from backend.server.routes_ws import (
    LIVE_WS_PATH,
    LIVE_WS_PHASE_GATE,
    WS_POLICY_VIOLATION,
    WS_TRY_AGAIN_LATER,
)


class FakeWebSocket:
    def __init__(self, *, run_id: str | None = None) -> None:
        self.query_params = {} if run_id is None else {"run_id": run_id}
        self.accept_calls = 0
        self.sent_payloads: list[dict[str, object]] = []
        self.close_calls: list[tuple[int, str]] = []

    async def accept(self) -> None:
        self.accept_calls += 1

    async def send_json(self, payload: dict[str, object]) -> None:
        self.sent_payloads.append(payload)

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
    assert stored.world_id == body["world_id"]
    assert stored.case_id == body["case_id"]
    assert stored.ws_url == body["ws_url"]
    assert stored.started_run is not None
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


def test_live_ws_rejects_missing_run_id_with_explicit_close() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path=LIVE_WS_PATH)
    websocket = FakeWebSocket()
    asyncio.run(endpoint(websocket))

    assert websocket.accept_calls == 1
    assert websocket.sent_payloads[0]["error"]["code"] == "MISSING_RUN_ID"
    assert websocket.close_calls == [(WS_POLICY_VIOLATION, "MISSING_RUN_ID")]


def test_live_ws_rejects_unimplemented_session_flow() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path=LIVE_WS_PATH)
    websocket = FakeWebSocket(run_id="s1-placeholder")
    asyncio.run(endpoint(websocket))

    payload = websocket.sent_payloads[0]
    assert payload["error"]["code"] == "NOT_IMPLEMENTED"
    assert payload["error"]["details"]["run_id"] == "s1-placeholder"
    assert payload["error"]["details"]["phase_gate"] == LIVE_WS_PHASE_GATE
    assert websocket.close_calls == [(WS_TRY_AGAIN_LATER, "NOT_IMPLEMENTED")]


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
