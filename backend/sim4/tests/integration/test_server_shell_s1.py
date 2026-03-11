from __future__ import annotations

import asyncio
import importlib
import json

import pytest

pytest.importorskip("fastapi")

from fastapi import FastAPI

from backend.server.app import create_app
from backend.server.config import DEFAULT_UVICORN_APP_PATH
from backend.server.routes_ws import WS_POLICY_VIOLATION, WS_TRY_AGAIN_LATER


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


def _find_http_route_endpoint(*, app: FastAPI, path: str, method: str):
    for route in app.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", None)
        if methods and method in methods:
            return route.endpoint
    raise AssertionError(f"HTTP route not found: {method} {path}")


def _find_ws_route_endpoint(*, app: FastAPI, path: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and hasattr(route, "endpoint") and not hasattr(route, "methods"):
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

    assert "/api/cases/start" in route_paths
    assert "/live" in route_paths


def test_post_cases_start_returns_explicit_s1_not_implemented() -> None:
    app = create_app()
    endpoint = _find_http_route_endpoint(app=app, path="/api/cases/start", method="POST")
    response = asyncio.run(endpoint())
    body = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 501
    assert body["error"]["code"] == "NOT_IMPLEMENTED"
    assert body["phase_gate"] == "S2"
    assert body["placeholder"]["status"] == "not_implemented"


def test_live_ws_rejects_missing_run_id_with_explicit_close() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path="/live")
    websocket = FakeWebSocket()
    asyncio.run(endpoint(websocket))

    assert websocket.accept_calls == 1
    assert websocket.sent_payloads[0]["error"]["code"] == "MISSING_RUN_ID"
    assert websocket.close_calls == [(WS_POLICY_VIOLATION, "MISSING_RUN_ID")]


def test_live_ws_rejects_unimplemented_session_flow() -> None:
    app = create_app()
    endpoint = _find_ws_route_endpoint(app=app, path="/live")
    websocket = FakeWebSocket(run_id="s1-placeholder")
    asyncio.run(endpoint(websocket))

    payload = websocket.sent_payloads[0]
    assert payload["error"]["code"] == "NOT_IMPLEMENTED"
    assert payload["error"]["details"]["run_id"] == "s1-placeholder"
    assert payload["error"]["details"]["phase_gate"] == "S4"
    assert websocket.close_calls == [(WS_TRY_AGAIN_LATER, "NOT_IMPLEMENTED")]
