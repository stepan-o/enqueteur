from pathlib import Path


def test_export_layout_doc_exists_and_has_required_statements():
    root = Path(__file__).resolve().parents[4]  # .../repo root
    doc = root / "docs" / "enqueteur" / "case_1_implementation_spec.md"
    assert doc.exists(), "docs/enqueteur/case_1_implementation_spec.md must exist"
    text = doc.read_text(encoding="utf-8")
    assert "Le Petit Vol du Musée" in text
    assert "deterministic" in text.lower()
