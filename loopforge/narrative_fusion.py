# Deprecated shim — canonical implementation lives in loopforge.narrative.narrative_fusion
from __future__ import annotations
from loopforge.narrative import narrative_fusion as _core  # pragma: no cover

# Mirror all non-dunder symbols
for _n, _v in vars(_core).items():  # pragma: no cover
    if not _n.startswith("__"):
        globals()[_n] = _v

# Export same surface
__all__ = list(
    getattr(_core, "__all__", [
        n for n in vars(_core).keys() if not n.startswith("__")
    ])
)
