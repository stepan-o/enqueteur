from __future__ import annotations

from backend.api.cases_start import (
    CASE_START_PATH,
    ENQUETEUR_ENGINE_NAME,
    ENQUETEUR_SCHEMA_VERSION,
    CaseRunRegistry,
    CaseStartRequest,
    CaseStartService,
    handle_post_cases_start,
)
from backend.api.router import ApiRequest, build_default_router


def test_case_start_request_validates_mbam_contract() -> None:
    request = CaseStartRequest.from_payload(
        {
            "case_id": "MBAM_01",
            "seed": "A",
            "difficulty_profile": "D0",
            "mode": "playtest",
        }
    )

    assert request.case_id == "MBAM_01"
    assert request.seed == "A"
    assert request.difficulty_profile == "D0"
    assert request.mode == "playtest"


def test_handle_post_cases_start_returns_contract_payload() -> None:
    registry = CaseRunRegistry()
    service = CaseStartService(ws_base_url="ws://localhost:7777/live", registry=registry)

    status, payload = handle_post_cases_start(
        {
            "case_id": "MBAM_01",
            "seed": "42",
            "difficulty_profile": "D1",
            "mode": "dev",
        },
        service=service,
    )

    assert status == 200
    assert payload["run_id"]
    assert payload["world_id"]
    assert payload["case_id"] == "MBAM_01"
    assert payload["seed"] == "42"
    assert payload["resolved_seed_id"] in {"A", "B", "C"}
    assert payload["difficulty_profile"] == "D1"
    assert payload["mode"] == "dev"
    assert payload["engine_name"] == ENQUETEUR_ENGINE_NAME
    assert payload["schema_version"] == ENQUETEUR_SCHEMA_VERSION
    assert payload["ws_url"].startswith("ws://localhost:7777/live?run_id=")
    assert payload["started_at"]

    registered = service.registry.get(payload["run_id"])
    assert registered is not None
    assert registered.run_id == payload["run_id"]
    assert registered.world_id == payload["world_id"]


def test_case_start_route_rejects_unsupported_case_id() -> None:
    status, payload = handle_post_cases_start(
        {
            "case_id": "OTHER_CASE",
            "seed": "A",
            "difficulty_profile": "D0",
        }
    )

    assert status == 400
    assert payload["error"]["code"] == "UNSUPPORTED_CASE"
    assert payload["error"]["field"] == "case_id"


def test_default_router_dispatches_post_cases_start() -> None:
    router = build_default_router()
    response = router.dispatch(
        ApiRequest(
            method="POST",
            path=CASE_START_PATH,
            json={
                "case_id": "MBAM_01",
                "seed": "A",
                "difficulty_profile": "D0",
            },
        )
    )

    assert response.status == 200
    assert response.json["case_id"] == "MBAM_01"
    assert response.json["engine_name"] == ENQUETEUR_ENGINE_NAME
    assert response.json["schema_version"] == ENQUETEUR_SCHEMA_VERSION
