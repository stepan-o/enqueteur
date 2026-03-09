from __future__ import annotations

from backend.api.cases_start import (
    CASE_START_PATH,
    ENQUETEUR_ENGINE_NAME,
    ENQUETEUR_SCHEMA_VERSION,
    MODE_CHANNELS,
    CaseRunRegistry,
    CaseStartRequest,
    CaseStartService,
    derive_rng_seed,
    extract_run_id_from_connection_target,
    get_default_case_run_registry,
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
    assert registered.channels == MODE_CHANNELS["dev"]
    assert registered.rng_seed == derive_rng_seed(case_id="MBAM_01", seed="42", difficulty_profile="D1")

    case_state = registered.runner.get_case_state()
    assert case_state is not None
    assert case_state.case_id == "MBAM_01"
    assert case_state.seed == payload["resolved_seed_id"]
    assert case_state.difficulty_profile == "D1"


def test_case_start_creates_deterministic_runner_for_same_inputs() -> None:
    registry = CaseRunRegistry()
    service = CaseStartService(registry=registry)

    status_a, payload_a = handle_post_cases_start(
        {
            "case_id": "MBAM_01",
            "seed": "A",
            "difficulty_profile": "D0",
            "mode": "playtest",
        },
        service=service,
    )
    status_b, payload_b = handle_post_cases_start(
        {
            "case_id": "MBAM_01",
            "seed": "A",
            "difficulty_profile": "D0",
            "mode": "playtest",
        },
        service=service,
    )

    assert status_a == 200
    assert status_b == 200
    assert payload_a["run_id"] != payload_b["run_id"]
    assert payload_a["world_id"] != payload_b["world_id"]

    record_a = registry.get(payload_a["run_id"])
    record_b = registry.get(payload_b["run_id"])
    assert record_a is not None and record_b is not None
    assert record_a.rng_seed == record_b.rng_seed
    assert record_a.channels == record_b.channels == MODE_CHANNELS["playtest"]

    case_a = record_a.runner.get_case_state()
    case_b = record_b.runner.get_case_state()
    assert case_a is not None and case_b is not None
    assert case_a.case_id == case_b.case_id == "MBAM_01"
    assert case_a.seed == case_b.seed == "A"
    assert case_a.difficulty_profile == case_b.difficulty_profile == "D0"


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


def test_case_start_route_rejects_boolean_seed_values() -> None:
    status, payload = handle_post_cases_start(
        {
            "case_id": "MBAM_01",
            "seed": True,
            "difficulty_profile": "D0",
        }
    )

    assert status == 400
    assert payload["error"]["code"] == "INVALID_REQUEST"
    assert payload["error"]["field"] == "seed"


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


def test_default_router_uses_shared_registry_for_future_attach() -> None:
    registry = get_default_case_run_registry()
    count_before = registry.count()
    router = build_default_router()

    response = router.dispatch(
        ApiRequest(
            method="POST",
            path=CASE_START_PATH,
            json={
                "case_id": "MBAM_01",
                "seed": "C",
                "difficulty_profile": "D0",
                "mode": "playtest",
            },
        )
    )

    assert response.status == 200
    assert registry.count() == count_before + 1
    assert registry.get(response.json["run_id"]) is not None


def test_default_handler_persists_run_for_future_connection_lookup() -> None:
    registry = get_default_case_run_registry()
    count_before = registry.count()

    status, payload = handle_post_cases_start(
        {
            "case_id": "MBAM_01",
            "seed": "B",
            "difficulty_profile": "D0",
            "mode": "playtest",
        }
    )

    assert status == 200
    assert registry.count() == count_before + 1
    assert extract_run_id_from_connection_target(payload["ws_url"]) == payload["run_id"]

    record = registry.resolve_connection_target(payload["ws_url"])
    assert record is not None
    assert record.run_id == payload["run_id"]
