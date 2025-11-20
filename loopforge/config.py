"""
Compatibility shim for configuration utilities.

Original implementation has moved to loopforge.core.config.
This module re-exports the public API for backward compatibility.

Note: We proactively reload the underlying core module on import so that
`importlib.reload(loopforge.config)` in tests re-reads environment variables
and recomputes module-level flags (e.g., USE_LLM_POLICY).
"""

import importlib as _importlib  # pragma: no cover
import loopforge.core.config as _core_config  # pragma: no cover
_importlib.reload(_core_config)  # pragma: no cover
from loopforge.core.config import *  # pragma: no cover
