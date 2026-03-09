from __future__ import annotations

import asyncio

from backend.api.cases_start import CaseRunRegistry, CaseStartRequest, CaseStartService
from backend.api.live_ws import (
    RUN_NOT_FOUND_WS_CLOSE_CODE,
    RUN_NOT_FOUND_WS_CLOSE_REASON,
    EnqueteurLiveSessionHost,
    RunLookupError,
    open_enqueteur_live_websocket,
)


class FakeWebSocket:
    def __init__(self) -> None:
        self.accept_calls = 0
        self.close_calls: list[tuple[int, str]] = []

    async def accept(self) -> None:
        self.accept_calls += 1

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.close_calls.append((code, reason))


def _start_mbam_case(*, registry: CaseRunRegistry) -> tuple[CaseStartService, dict[str, object]]:
    service = CaseStartService(ws_base_url="ws://localhost:7777/live", registry=registry)
    response = service.start_case(
        CaseStartRequest.from_payload(
            {
                "case_id": "MBAM_01",
                "seed": "A",
                "difficulty_profile": "D0",
                "mode": "playtest",
            }
        )
    )
    return service, response.to_payload()


def test_live_websocket_entrypoint_attaches_to_started_run() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()

    session = asyncio.run(
        open_enqueteur_live_websocket(
            ws,
            connection_target=str(payload["ws_url"]),
            host=host,
        )
    )

    assert ws.accept_calls == 1
    assert ws.close_calls == []
    assert session.phase == "HANDSHAKING"
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
        asyncio.run(
            open_enqueteur_live_websocket(
                ws,
                connection_target="/live?run_id=missing-run-id",
                host=host,
            )
        )
    except RunLookupError as exc:
        assert exc.run_id_hint == "missing-run-id"
    else:
        raise AssertionError("RunLookupError was expected for unknown run_id.")

    assert ws.accept_calls == 0
    assert ws.close_calls == [(RUN_NOT_FOUND_WS_CLOSE_CODE, RUN_NOT_FOUND_WS_CLOSE_REASON)]


def test_live_session_host_tracks_connection_lifecycle() -> None:
    registry = CaseRunRegistry()
    _service, payload = _start_mbam_case(registry=registry)
    host = EnqueteurLiveSessionHost(run_registry=registry)
    ws = FakeWebSocket()

    session = asyncio.run(
        open_enqueteur_live_websocket(
            ws,
            connection_target=str(payload["run_id"]),
            host=host,
        )
    )
    assert session.phase == "HANDSHAKING"

    subscribed = host.mark_subscribed(session.connection_id)
    assert subscribed.phase == "SUBSCRIBED"

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
