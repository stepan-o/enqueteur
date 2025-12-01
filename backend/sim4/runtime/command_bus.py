"""
Deterministic command bus helpers for Phase E/F (Sprint 6.4).

Scope:
- Provide thin batching utilities that take ECS/World commands collected during
  a tick and normalize them into a single globally sequenced list by assigning
  seq = 0..N-1 in the order provided.
- No randomness, no time; behavior is fully deterministic.

SOT alignment:
- SOT-SIM4-RUNTIME-TICK §4.5 (Phase E) and §4.6 (Phase F): runtime must apply
  commands in a stable, deterministic global order within a tick. These helpers
  implement the minimal sequencing policy used by runtime.tick.

Layering:
- This lives in runtime/ and may import ecs.* and world.* (SOP-100 compliant).
  Neither ecs/ nor world/ import runtime/.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, List

from backend.sim4.ecs.commands import ECSCommand
from backend.sim4.world.commands import WorldCommand


class ECSCommandBatch:
    """
    Aggregates ECSCommand instances for a single tick and produces a globally
    seq-ordered list suitable for ECSWorld.apply_commands().

    Policy:
    - Global application order is the order in which runtime aggregates commands
      (phase → system → per-buffer order from 6.3 wiring).
    - We rewrite seq to be 0..N-1 to provide a canonical global ordering.
    """

    def __init__(self, commands: Iterable[ECSCommand]):
        self._commands = list(commands)

    def to_global_sequence(self) -> List[ECSCommand]:
        """
        Return a new list of ECSCommand where 'seq' is reassigned to a global
        0..N-1 sequence in the order commands were provided.
        """
        result: List[ECSCommand] = []
        for idx, cmd in enumerate(self._commands):
            result.append(replace(cmd, seq=idx))
        return result


class WorldCommandBatch:
    """
    Aggregates WorldCommand instances for a single tick and produces a globally
    seq-ordered list suitable for apply_world_commands().
    """

    def __init__(self, commands: Iterable[WorldCommand]):
        self._commands = list(commands)

    def to_global_sequence(self) -> List[WorldCommand]:
        result: List[WorldCommand] = []
        for idx, cmd in enumerate(self._commands):
            result.append(replace(cmd, seq=idx))
        return result


__all__ = ["ECSCommandBatch", "WorldCommandBatch"]
