"""
Snapshot-layer output interfaces (Phase H).

Defines a protocol for deterministic per-tick outputs that can be consumed
by integration without importing runtime (SOP-100). Runtime importing this
module is explicitly allowed by the SOP-100 DAG (runtime → snapshot).
"""

from __future__ import annotations

from typing import Protocol, Sequence, Any, runtime_checkable

from .world_snapshot import WorldSnapshot


@runtime_checkable
class TickOutputSink(Protocol):
    """Interface for consuming deterministic per-tick outputs.

    Implementations must be side-effect-safe for the kernel:
    - no exceptions should escape to the runtime tick
    - no kernel state mutation (read-only consumption only)
    """

    def on_tick_output(
        self,
        *,
        tick_index: int,
        dt: float,
        world_snapshot: WorldSnapshot,
        runtime_events: Sequence[Any],
        narrative_fragments: Sequence[Any],
    ) -> None: ...


__all__ = ["TickOutputSink"]
