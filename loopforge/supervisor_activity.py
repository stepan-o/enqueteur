# Deprecated shim — canonical implementation lives in loopforge.analytics.supervisor_activity
from __future__ import annotations
from loopforge.analytics import supervisor_activity as _core  # pragma: no cover

for _n, _v in vars(_core).items():  # pragma: no cover
    if not _n.startswith("__"):
        globals()[_n] = _v

__all__ = list(
    getattr(
        _core,
        "__all__",
        [n for n in vars(_core).keys() if not n.startswith("__")]
    )
)
