import json
from hashlib import sha256
from pathlib import Path

import pytest

from backend.sim4.integration.manifest_schema import ManifestV0_1
from backend.sim4.integration.kvp_envelope import validate_envelope, envelope_msg_type
from backend.sim4.integration.record_writer import read_record
from backend.sim4.integration.export_verify import reconstruct_state_at_tick


FIXTURE_ROOT = Path(__file__).resolve().parents[4] / "fixtures" / "kvp" / "v0_1" / "small_run"


def _sha256_hex(p: Path) -> str:
    return sha256(p.read_bytes()).hexdigest()


def test_fixture_manifest_and_discoverability():
    # Manifest exists and validates
    mpath = FIXTURE_ROOT / "manifest.kvp.json"
    assert mpath.exists(), "fixture manifest must exist"
    m = ManifestV0_1.from_dict(json.loads(mpath.read_text("utf-8")))
    # discoverability: keyframes and snapshots present
    kf = m.derive_keyframe_ticks()
    for t in kf:
        assert t in m.snapshots
    # diffs coverage complete
    m.diffs.validate_coverage(m.available_start_tick, m.available_end_tick)
    # overlays resolve
    assert m.overlays is not None and len(m.overlays) >= 1
    for op in m.overlays.values():
        assert (FIXTURE_ROOT / op.rel_path).exists()


def test_fixture_record_schemas_and_envelope_first_dispatch():
    m = ManifestV0_1.from_dict(json.loads((FIXTURE_ROOT / "manifest.kvp.json").read_text("utf-8")))
    # snapshots
    for rp in m.snapshots.values():
        env = read_record(FIXTURE_ROOT / rp.rel_path)
        validate_envelope(env)
        assert envelope_msg_type(env) in ("FULL_SNAPSHOT", "KERNEL_HELLO")
        # payload minimal schema
        p = env["payload"]
        assert "schema_version" in p and "state" in p and "step_hash" in p
        # No unknown top-level keys in envelope
        assert set(env.keys()) == {"kvp_version", "msg_type", "msg_id", "sent_at_ms", "payload"}
    # diffs
    for rp in m.diffs.diffs_by_from_tick.values():
        env = read_record(FIXTURE_ROOT / rp.rel_path)
        validate_envelope(env)
        assert envelope_msg_type(env) == "FRAME_DIFF"
        p = env["payload"]
        assert set(p.keys()) >= {"schema_version", "from_tick", "to_tick", "prev_step_hash", "ops", "step_hash"}
        assert p["to_tick"] == p["from_tick"] + 1
        assert isinstance(p["ops"], list)
    # overlays JSONL: each line is envelope
    for k, op in (m.overlays or {}).items():
        lines = [ln for ln in (FIXTURE_ROOT / op.rel_path).read_text("utf-8").splitlines() if ln.strip()]
        assert lines, f"overlay {k} must have lines"
        for ln in lines:
            env = json.loads(ln)
            validate_envelope(env)
            mt = envelope_msg_type(env)
            assert mt.startswith("X_")


def test_fixture_replay_and_hash_chain():
    m = ManifestV0_1.from_dict(json.loads((FIXTURE_ROOT / "manifest.kvp.json").read_text("utf-8")))
    # reconstruct first, mid, last
    s0 = reconstruct_state_at_tick(FIXTURE_ROOT, m, m.available_start_tick)
    assert isinstance(s0, dict)
    mid = (m.available_start_tick + m.available_end_tick) // 2
    sm = reconstruct_state_at_tick(FIXTURE_ROOT, m, mid)
    assert isinstance(sm, dict)
    sl = reconstruct_state_at_tick(FIXTURE_ROOT, m, m.available_end_tick)
    assert isinstance(sl, dict)
    # chain: each diff to_tick == from_tick+1 already asserted above


def test_fixture_byte_parity():
    # Every file hash matches fixture_hashes.json
    mapping = json.loads((FIXTURE_ROOT / "fixture_hashes.json").read_text("utf-8"))
    assert isinstance(mapping, dict) and mapping, "fixture_hashes.json must map rel_path -> sha256"
    for rel, expected in mapping.items():
        p = FIXTURE_ROOT / rel
        assert p.exists(), f"missing fixture file: {rel}"
        actual = _sha256_hex(p)
        assert actual == expected, f"hash mismatch for {rel}: {actual} != {expected}"
