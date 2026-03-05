from __future__ import annotations

"""
Phase C system — WorkDesireSystem.

Updates per-agent desire-to-work scalars deterministically.
"""

from .base import SystemContext
from ..query import QuerySignature
from ..components.work import WorkDesire


class WorkDesireSystem:
    """Phase C: monotonic desire growth + decay while working."""

    def run(self, ctx: SystemContext) -> None:
        sig = QuerySignature(read=(WorkDesire,), write=(WorkDesire,))
        for row in ctx.world.query(sig):
            desire = row.components[0]
            next_value = desire.value + desire.increase_rate * ctx.dt

            next_value = max(0.0, min(1.0, next_value))

            if next_value != desire.value:
                ctx.commands.set_field(row.entity, WorkDesire, "value", float(next_value))
            if desire.last_tick != ctx.tick_index:
                ctx.commands.set_field(row.entity, WorkDesire, "last_tick", int(ctx.tick_index))


__all__ = ["WorkDesireSystem"]
