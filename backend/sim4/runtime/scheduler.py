"""
Phase scheduler for ECS systems (Sprint 6.3).

This module provides a minimal runtime-facing wrapper around the canonical
phase → systems mapping declared in backend.sim4.ecs.systems.scheduler_order.

Contract relied on by runtime.tick.tick():

    systems_for_phase = scheduler.iter_phase_systems(phase: str) -> Iterable[type]

The scheduler itself contains no simulation logic; it simply exposes ordered
lists of system classes for phases "B", "C", and "D" (and optionally "E"
for completeness), preserving the deterministic order defined by ECS.

SOT alignment:
- SOT-SIM4-RUNTIME-TICK: runtime owns orchestration and system scheduling.
- Layer purity (SOP-100): runtime may import ecs.*, but ecs does not import
  runtime.
"""

from __future__ import annotations

from typing import Iterable, List, Type

from backend.sim4.ecs.systems import scheduler_order as _sched


class PhaseScheduler:
    """Default scheduler that exposes ECS systems per phase in deterministic order."""

    _MAP: dict[str, List[Type]] = {
        "B": list(_sched.PHASE_B_SYSTEMS),
        "C": list(_sched.PHASE_C_SYSTEMS),
        "D": list(_sched.PHASE_D_SYSTEMS),
        # Provided for completeness; Phase E is driven by apply step, not run here
        "E": list(_sched.PHASE_E_SYSTEMS),
    }

    def iter_phase_systems(self, phase: str) -> Iterable[Type]:
        """
        Return the ordered collection of system classes for the given phase key.

        Args:
            phase: One of "B", "C", "D" ("E" available for completeness).

        Returns:
            Iterable of system classes in deterministic order.
        """
        return self._MAP.get(phase, ())


__all__ = ["PhaseScheduler"]
