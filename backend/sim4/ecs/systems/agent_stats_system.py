from __future__ import annotations

"""
Phase D system — AgentStatsSystem.

Updates agent stats per tick, applying continuous drain/recovery and discrete
event-style changes (e.g., paydays). All stats except money are clamped to [0, 1].
"""

from .base import SystemContext
from ..query import QuerySignature
from ..components.agent_stats import AgentStats
from ..components.work import WorkAssignment


class AgentStatsSystem:
    """Phase D: updates agent stats (energy, durability, money, traits)."""

    energy_drain_work: float = 0.018
    energy_recovery_idle: float = 0.009
    durability_decay_work: float = 0.0025
    durability_decay_low_energy: float = 0.0015
    low_energy_threshold: float = 0.18

    pay_interval_ticks: int = 600
    pay_amount: float = 20.0

    def run(self, ctx: SystemContext) -> None:
        sig = QuerySignature(read=(AgentStats, WorkAssignment), write=(AgentStats,))
        for row in ctx.world.query(sig):
            stats, assignment = row.components
            working = assignment.object_id is not None
            load_band = max(0, int(assignment.load_band))

            energy = float(stats.energy)
            durability = float(stats.durability)
            money = float(stats.money)

            # --- Continuous per-tick changes ---
            if working:
                load_factor = 1.0 + 0.2 * max(0, load_band - 1)
                toughness_factor = max(0.6, 1.0 - 0.35 * float(stats.toughness))
                energy -= self.energy_drain_work * load_factor * toughness_factor * ctx.dt
                durability -= self.durability_decay_work * load_factor * ctx.dt
            else:
                energy += self.energy_recovery_idle * ctx.dt

            if energy <= self.low_energy_threshold:
                durability -= self.durability_decay_low_energy * ctx.dt

            energy = _clamp01(energy)
            durability = _clamp01(durability)

            # --- Discrete event: pay every N working ticks ---
            if working and self.pay_interval_ticks > 0:
                if assignment.ticks_working > 0 and assignment.ticks_working % self.pay_interval_ticks == 0:
                    pay_bonus = 1.0 + 0.1 * load_band
                    money += self.pay_amount * pay_bonus

            money = max(0.0, money)

            # Clamp traits (in case initialization drifted)
            smartness = _clamp01(float(stats.smartness))
            toughness = _clamp01(float(stats.toughness))
            obedience = _clamp01(float(stats.obedience))
            alignment = _clamp01(float(stats.factory_goal_alignment))

            _set_if_changed(ctx, row.entity, AgentStats, "energy", energy, stats.energy)
            _set_if_changed(ctx, row.entity, AgentStats, "durability", durability, stats.durability)
            _set_if_changed(ctx, row.entity, AgentStats, "money", money, stats.money)
            _set_if_changed(ctx, row.entity, AgentStats, "smartness", smartness, stats.smartness)
            _set_if_changed(ctx, row.entity, AgentStats, "toughness", toughness, stats.toughness)
            _set_if_changed(ctx, row.entity, AgentStats, "obedience", obedience, stats.obedience)
            _set_if_changed(ctx, row.entity, AgentStats, "factory_goal_alignment", alignment, stats.factory_goal_alignment)


def _clamp01(value: float) -> float:
    if value <= 0.0:
        return 0.0
    if value >= 1.0:
        return 1.0
    return value


def _set_if_changed(ctx: SystemContext, entity_id: int, component_type, field: str, value: float, prev: float) -> None:
    if abs(value - float(prev)) > 1e-6:
        ctx.commands.set_field(entity_id, component_type, field, value)


__all__ = ["AgentStatsSystem"]
