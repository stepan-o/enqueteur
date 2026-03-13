from backend.runtime_messages import (
    command_rejected_message_contract,
    launch_error_message_contract,
    live_error_message_contract,
    live_warn_message_contract,
)


def test_command_rejected_contract_normalizes_reason_code_and_keeps_legacy_fields():
    key, params = command_rejected_message_contract(
        reason_code="INVALID_OBJECT",
        client_cmd_id="cmd-123",
    )

    assert key == "live.command_rejected.invalid_object"
    assert params == {
        "reason_code": "INVALID_OBJECT",
        "client_cmd_id": "cmd-123",
    }


def test_command_rejected_contract_uses_unknown_token_for_empty_reason_code():
    key, params = command_rejected_message_contract(reason_code="   ")

    assert key == "live.command_rejected.unknown"
    assert params == {"reason_code": "   "}


def test_live_warn_and_error_contracts_shape_message_keys_and_params():
    warn_key, warn_params = live_warn_message_contract(code="BASELINE_REQUIRED")
    error_key, error_params = live_error_message_contract(code="INTERNAL_RUNTIME_ERROR", fatal=True)

    assert warn_key == "live.warn.baseline_required"
    assert warn_params == {"code": "BASELINE_REQUIRED"}
    assert error_key == "live.error.internal_runtime_error"
    assert error_params == {"code": "INTERNAL_RUNTIME_ERROR", "fatal": True}


def test_launch_error_contract_includes_optional_metadata_when_present():
    key, params = launch_error_message_contract(
        code="INVALID_REQUEST",
        field="seed",
        phase_gate="CASE_START",
        status_code=400,
    )

    assert key == "launch.error.invalid_request"
    assert params == {
        "code": "INVALID_REQUEST",
        "field": "seed",
        "phase_gate": "CASE_START",
        "status_code": 400,
    }
