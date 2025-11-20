# Deprecated shim — real implementation lives in loopforge.psych.attribution
from __future__ import annotations

from loopforge.psych import attribution as _core  # pragma: no cover

# Mirror all non-dunder names into this module to preserve full API (incl. single-underscore helpers)
for _name, _obj in vars(_core).items():  # pragma: no cover
    if not _name.startswith("__"):
        globals()[_name] = _obj

# Explicit __all__ from core if available; otherwise synthesize from mirrored names
__all__ = list(getattr(_core, "__all__", [n for n in vars(_core).keys() if not n.startswith("__")]))  # pragma: no cover
