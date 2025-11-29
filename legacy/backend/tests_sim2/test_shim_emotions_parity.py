from __future__ import annotations

from loopforge.psych import emotions as new_emotions
from loopforge.psych import emotions as shim_emotions


def test_emotions_shim_exports_superset():
    core_names = {n for n in dir(new_emotions) if not n.startswith("__")}
    shim_names = {n for n in dir(shim_emotions) if not n.startswith("__")}
    missing = sorted(core_names - shim_names)
    assert not missing, f"Shim loopforge.emotions is missing: {missing}"
