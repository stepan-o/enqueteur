# Deprecated shim — canonical implementation lives in loopforge.narrative.explainer_context
from __future__ import annotations
from loopforge.narrative import explainer_context as _core  # pragma: no cover

# Mirror all non-dunder symbols
for _n, _v in vars(_core).items():  # pragma: no cover
    if not _n.startswith("__"):
        globals()[_n] = _v

# Export same surface
__all__ = list(
    getattr(
        _core,
        "__all__",
        [n for n in vars(_core).keys() if not n.startswith("__")]
    )
)
