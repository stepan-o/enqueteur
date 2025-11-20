# Deprecated shim — real implementation lives in loopforge.psych.emotion_model
from __future__ import annotations

from loopforge.psych.emotion_model import *  # pragma: no cover

from loopforge.psych import emotion_model as _emotion_model_mod

__all__ = getattr(
    _emotion_model_mod,
    "__all__",
    [n for n in dir(_emotion_model_mod) if not n.startswith("_")],
)
