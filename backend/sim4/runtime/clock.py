"""
Deterministic tick/clock primitives for Sim4 runtime (Sprint 6.1).

Scope & constraints (SOT-SIM4-RUNTIME-TICK):
- Provide a simple, deterministic TickClock with an integer tick_index and a
  fixed or configurable delta-time (dt) value.
- No reliance on system time or randomness. No hidden globals.
- Rust-portable shapes only: ints, floats, and simple dataclasses.

Notes:
- dt: Per SOT guidance, dt may be fixed for a given simulation run (commonly 1/60).
  We support supplying a custom dt at construction time; TickClock.advance()
  does not change dt — it remains stable unless the caller constructs a new
  clock with a different dt.
- Tick semantics: runtime.tick() advances the clock at the start of each tick,
  so TickResult.tick_index is the post-advance value observed by all phases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType


# Public aliases (kept simple and serializable)
TickIndex = NewType("TickIndex", int)
DeltaTime = NewType("DeltaTime", float)


@dataclass
class TickClock:
    """
    Minimal deterministic simulation clock.

    Fields:
    - tick_index: integer index of the current tick (starts at 0 by default).
    - dt: delta time per tick (fixed for the life of this clock instance).

    Behavior:
    - advance(steps=1) increments tick_index deterministically.
    - dt is not mutated by advance(); callers choose dt at construction time
      (commonly 1/60 for 60 Hz simulated time).
    """

    tick_index: int = 0
    dt: float = 1.0 / 60.0

    def advance(self, steps: int = 1) -> int:
        """
        Advance the clock by a number of ticks (default: 1).

        Args:
            steps: positive integer number of ticks to advance.

        Returns:
            The new tick_index after advancing.

        Raises:
            ValueError: if steps < 1.
        """
        if steps < 1:
            raise ValueError(f"steps must be >= 1; got {steps}")
        self.tick_index += int(steps)
        return self.tick_index

    @property
    def tick(self) -> int:
        """Alias for tick_index for ergonomic access in callers."""
        return self.tick_index

    @property
    def delta_time(self) -> float:
        """Alias for dt (delta time per tick)."""
        return self.dt
