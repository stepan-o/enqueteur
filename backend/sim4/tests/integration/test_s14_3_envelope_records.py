import json
import uuid
from pathlib import Path
import pytest

from backend.sim4.integration.kvp_version import KVP_VERSION
from backend.sim4.integration.kvp_envelope import (
    make_envelope,
    validate_envelope,
    envelope_msg_type,
)
from backend.sim4.integration.record_writer import write_record, read_record


def _env(msg_type: str, payload: dict | None = None):
    return make_envelope(
        msg_type,
        payload if payload is not None else {"ok": True},
        msg_id=str(uuid.uuid4()),
        sent_at_ms=0,
    )


def test_make_envelope_success_and_required_keys(tmp_path: Path):
    env = _env("FULL_SNAPSHOT", {"state": {}})
    for k in ("kvp_version", "msg_type", "msg_id", "sent_at_ms", "payload"):
        assert k in env
    assert env["kvp_version"] == KVP_VERSION
    assert isinstance(env["payload"], dict)
    # Validate explicitly
    validate_envelope(env)


def test_reject_msg_type_not_allowed():
    with pytest.raises(ValueError):
        _env("SOMETHING_ELSE")


def test_reject_msg_type_with_forbidden_prefix():
    with pytest.raises(ValueError):
        _env("REPLAY_BEGIN")


def test_reject_msg_type_not_screaming_snake():
    with pytest.raises(ValueError):
        _env("Full_Snapshot")


def test_reject_payload_not_dict():
    with pytest.raises(ValueError):
        make_envelope("FULL_SNAPSHOT", [1, 2, 3], msg_id=str(uuid.uuid4()), sent_at_ms=0)


def test_reject_negative_sent_at():
    with pytest.raises(ValueError):
        make_envelope("FULL_SNAPSHOT", {}, msg_id=str(uuid.uuid4()), sent_at_ms=-1)


def test_validate_envelope_missing_keys():
    env = _env("FULL_SNAPSHOT")
    bad = dict(env)
    bad.pop("msg_id")
    with pytest.raises(ValueError):
        validate_envelope(bad)


def test_envelope_first_dispatch_helper():
    p = {"schema_version": "2"}
    e1 = _env("FULL_SNAPSHOT", p)
    e2 = _env("FRAME_DIFF", p)
    # Helper must inspect only msg_type
    assert envelope_msg_type(e1) != envelope_msg_type(e2)


def test_write_read_record_round_trip(tmp_path: Path):
    env = _env("FULL_SNAPSHOT", {"state": {"x": 1}})
    file_path = tmp_path / "record.json"
    write_record(file_path, env)

    # Ensure file has no BOM
    raw = file_path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")

    loaded = read_record(file_path)
    # Should parse into equivalent dict
    assert loaded == json.loads(json.dumps(env))
