from __future__ import annotations

import pytest

from backend.server.errors import RunNotFoundError
from backend.server.run_registry import RunRegistry


def _launch_payload(*, run_id: str = "run-123") -> dict[str, object]:
    return {
        "run_id": run_id,
        "world_id": "world-123",
        "case_id": "MBAM_01",
        "seed": "A",
        "resolved_seed_id": "A",
        "difficulty_profile": "D0",
        "mode": "playtest",
        "engine_name": "enqueteur",
        "schema_version": "enqueteur_mbam_1",
        "ws_url": f"ws://localhost:7777/live?run_id={run_id}",
        "started_at": "2026-03-11T12:00:00Z",
    }


def test_run_registry_registers_structured_launch_entry() -> None:
    registry = RunRegistry()
    runtime_ref = object()
    payload = _launch_payload()

    entry = registry.register_launched_run(launch_payload=payload, started_run=runtime_ref)

    assert entry.run_id == "run-123"
    assert entry.launch.case_id == "MBAM_01"
    assert entry.launch.world_id == "world-123"
    assert entry.launch.engine_name == "enqueteur"
    assert entry.launch.schema_version == "enqueteur_mbam_1"
    assert entry.runtime.started_run is runtime_ref
    assert entry.host.registered_at
    assert entry.host.last_activity_at

    assert registry.exists("run-123")
    assert registry.get_launch_metadata("run-123") is not None
    assert registry.get_runtime_reference("run-123") is runtime_ref
    assert registry.get_by_connection_target("ws://localhost:7777/live?run_id=run-123") is not None
    assert registry.resolve_connection_target("ws://localhost:7777/live?run_id=run-123") is not None


def test_run_registry_touch_activity_tracks_session_hint() -> None:
    registry = RunRegistry()
    payload = _launch_payload()
    entry = registry.register_launched_run(launch_payload=payload, started_run=object())
    assert entry.host.last_session_id is None

    touched = registry.touch_activity("run-123", session_id="session-1")
    assert touched.host.last_session_id == "session-1"


def test_run_registry_remove_and_require_behavior() -> None:
    registry = RunRegistry()
    payload = _launch_payload()
    registry.register_launched_run(launch_payload=payload, started_run=object())

    removed = registry.remove("run-123")
    assert removed is not None
    assert removed.run_id == "run-123"
    assert registry.exists("run-123") is False
    assert registry.get("run-123") is None

    with pytest.raises(RunNotFoundError):
        registry.require("run-123")


def test_run_registry_rejects_missing_run_id() -> None:
    registry = RunRegistry()

    with pytest.raises(ValueError):
        registry.register_launched_run(launch_payload={"case_id": "MBAM_01"}, started_run=object())


def test_run_registry_rejects_ws_url_run_id_mismatch() -> None:
    registry = RunRegistry()
    payload = _launch_payload(run_id="run-123")
    payload["ws_url"] = "ws://localhost:7777/live?run_id=run-999"

    with pytest.raises(ValueError):
        registry.register_launched_run(launch_payload=payload, started_run=object())


def test_run_registry_extract_run_id_supports_raw_id_and_ws_target() -> None:
    assert RunRegistry.extract_run_id("run-raw") == "run-raw"
    assert RunRegistry.extract_run_id("ws://localhost:7777/live?run_id=run-123") == "run-123"
    assert RunRegistry.extract_run_id("/live?run_id=run-456") == "run-456"
    assert RunRegistry.extract_run_id("ws://localhost:7777/live") is None
