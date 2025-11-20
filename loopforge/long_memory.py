# Deprecated shim — real implementation lives in loopforge.psych.long_memory
from __future__ import annotations

from loopforge.psych import long_memory as _core  # pragma: no cover

for _name, _obj in vars(_core).items():  # pragma: no cover
    if not _name.startswith("__"):
        globals()[_name] = _obj

__all__ = list(getattr(_core, "__all__", [n for n in vars(_core).keys() if not n.startswith("__")]))  # pragma: no cover
