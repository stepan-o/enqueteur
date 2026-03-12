from __future__ import annotations

"""Canonical /api/cases/start host-entrypoint checks (historical filename kept)."""

import asyncio
from dataclasses import dataclass
import json
from typing import Any

import pytest

pytest.importorskip("fastapi")

from backend.api.cases_start import ENQUETEUR_ENGINE_NAME, ENQUETEUR_SCHEMA_VERSION
from backend.server.app import create_app
from backend.server.routes_http import CASE_START_PATH, READINESS_PATH


@dataclass(frozen=True)
class AsgiHttpResponse:
    status_code: int
    headers: tuple[tuple[bytes, bytes], ...]
    body: bytes

    def json(self) -> dict[str, Any]:
        parsed = json.loads(self.body.decode("utf-8"))
        assert isinstance(parsed, dict)
        return parsed


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


async def _post_raw_json_body(app: Any, *, path: str, body: bytes) -> AsgiHttpResponse:
    return await _asgi_http_request(
        app,
        method="POST",
        path=path,
        body=body,
        headers=((b"content-type", b"application/json"),),
    )


def test_s2_launch_route_success_via_asgi_app_registers_run() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            response = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            payload = response.json()

            assert response.status_code == 200
            required_fields = {
                "run_id",
                "world_id",
                "case_id",
                "seed",
                "resolved_seed_id",
                "difficulty_profile",
                "mode",
                "engine_name",
                "schema_version",
                "ws_url",
                "started_at",
            }
            assert required_fields.issubset(payload.keys())
            assert payload["case_id"] == "MBAM_01"
            assert payload["engine_name"] == ENQUETEUR_ENGINE_NAME
            assert payload["schema_version"] == ENQUETEUR_SCHEMA_VERSION
            assert payload["ws_url"].startswith("ws://")
            assert payload["run_id"] in payload["ws_url"]

            run_registry = app.state.run_registry
            assert run_registry.count() == 1
            run_record = run_registry.get(payload["run_id"])
            assert run_record is not None
            assert run_record.run_id == payload["run_id"]
            assert run_record.launch.world_id == payload["world_id"]
            assert run_record.launch.case_id == payload["case_id"]
            assert run_record.launch.engine_name == payload["engine_name"]
            assert run_record.launch.schema_version == payload["schema_version"]
            assert run_record.runtime.started_run is not None
            assert run_registry.get_launch_metadata(payload["run_id"]) is not None
            assert run_registry.get_runtime_reference(payload["run_id"]) is run_record.runtime.started_run
            assert run_registry.get_by_connection_target(payload["ws_url"]) is not None

    asyncio.run(_scenario())


def test_s2_launch_route_rejects_malformed_transport_body_via_asgi_app() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            response = await _post_raw_json_body(
                app,
                path=CASE_START_PATH,
                body=b'{"case_id":"MBAM_01","seed":"A"',
            )
            payload = response.json()

            assert response.status_code == 400
            assert payload["error"]["code"] == "INVALID_REQUEST"
            assert payload["error"]["field"] == "payload"

    asyncio.run(_scenario())


def test_s2_launch_route_maps_core_validation_failure_via_asgi_app() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            response = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "NOT_A_SUPPORTED_CASE",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            payload = response.json()

            assert response.status_code == 400
            assert payload["error"]["code"] == "UNSUPPORTED_CASE"
            assert payload["error"]["field"] == "case_id"
            assert app.state.run_registry.count() == 0

    asyncio.run(_scenario())


def test_s2_launch_route_registry_remove_after_launch_is_consistent() -> None:
    app = create_app()

    async def _scenario() -> None:
        async with app.router.lifespan_context(app):
            response = await _post_json(
                app,
                path=CASE_START_PATH,
                payload={
                    "case_id": "MBAM_01",
                    "seed": "A",
                    "difficulty_profile": "D0",
                    "mode": "playtest",
                },
            )
            payload = response.json()
            assert response.status_code == 200

            run_registry = app.state.run_registry
            removed = run_registry.remove(payload["run_id"])
            assert removed is not None
            assert removed.run_id == payload["run_id"]
            assert run_registry.get(payload["run_id"]) is None
            assert run_registry.get_by_connection_target(payload["ws_url"]) is None
            assert run_registry.count() == 0

    asyncio.run(_scenario())


def test_s7_lifespan_sets_host_state_and_readiness_status() -> None:
    app = create_app()

    async def _scenario() -> None:
        assert bool(getattr(app.state, "started", False)) is False
        assert bool(getattr(app.state, "shutting_down", False)) is False

        async with app.router.lifespan_context(app):
            assert app.state.started is True
            assert app.state.shutting_down is False
            assert isinstance(app.state.startup_note, str) and app.state.startup_note

            ready = await _asgi_http_request(
                app,
                method="GET",
                path=READINESS_PATH,
            )
            ready_payload = ready.json()
            assert ready.status_code == 200
            assert ready_payload["status"] == "ready"

            app.state.shutting_down = True
            stopping = await _asgi_http_request(
                app,
                method="GET",
                path=READINESS_PATH,
            )
            stopping_payload = stopping.json()
            assert stopping.status_code == 200
            assert stopping_payload["status"] == "stopping"

            app.state.shutting_down = False

        assert app.state.started is False
        assert app.state.shutting_down is True
        assert app.state.shutdown_note == "runtime-host shutting down"
        assert app.state.session_controller.accepting_connections is False

    asyncio.run(_scenario())
