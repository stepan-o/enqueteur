"""
Versioned, viewer-facing integration schemas.

These dataclasses are frozen, deterministic, and contain no logic.
They are safe for Rust portability and offline replay.
"""

from .version import IntegrationSchemaVersion
from .run_manifest import RunManifest
from .tick_frame import TickFrame

__all__ = [
    "IntegrationSchemaVersion",
    "RunManifest",
    "TickFrame",
]
