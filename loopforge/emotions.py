# Deprecated shim — real implementation lives in loopforge.psych.emotions
from __future__ import annotations

from loopforge.psych.emotions import *  # pragma: no cover

# Explicit re-export for introspection & tools
from loopforge.psych import emotions as _emotions_mod

__all__ = getattr(_emotions_mod, "__all__", [n for n in dir(_emotions_mod) if not n.startswith("_")])
