# Deprecated shim — real implementation lives in loopforge.psych.emotions
from __future__ import annotations

# Import the canonical module and mirror its namespace so that callers depending
# on private helpers (single-underscore) can still access them during migration.
from loopforge.psych import emotions as _core  # pragma: no cover

# Mirror all attributes except dunders into this module's globals.
# This intentionally includes single-underscore names (e.g., _clamp).
for _name, _obj in vars(_core).items():  # pragma: no cover
    if not _name.startswith("__"):
        globals()[_name] = _obj

# Build an explicit __all__ to match the core module's intent when available.
if hasattr(_core, "__all__"):
    __all__ = list(_core.__all__)  # pragma: no cover
else:
    __all__ = [name for name in vars(_core).keys() if not name.startswith("__")]  # pragma: no cover
