"""
Adapter skeletons bridging core outputs to integration schemas.

Read-only contracts only; no logic implemented here.
"""

from .snapshot_adapter import build_tick_frame

__all__ = [
    "build_tick_frame",
]
