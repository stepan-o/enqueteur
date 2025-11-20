# Deprecated shim — real implementation lives in loopforge.psych.beliefs
from __future__ import annotations

from loopforge.psych.beliefs import *  # pragma: no cover

from loopforge.psych import beliefs as _beliefs_mod

__all__ = getattr(_beliefs_mod, "__all__", [n for n in dir(_beliefs_mod) if not n.startswith("_")])
