from pathlib import Path


def test_export_layout_doc_exists_and_has_required_statements():
    root = Path(__file__).resolve().parents[4]  # .../loopforge
    doc = root / "docs" / "kvp_export_layout_v0_1.md"
    assert doc.exists(), "docs/kvp_export_layout_v0_1.md must exist"
    text = doc.read_text(encoding="utf-8")
    assert "manifest.kvp.json is authoritative" in text
    assert "ARTIFACTS ONLY — NO REPLAY_* — NO LIVE SESSION" in text
