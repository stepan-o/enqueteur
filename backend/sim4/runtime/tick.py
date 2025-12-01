"""
Tick pipeline skeleton (Sprint 6.2) — deterministic, phases A–I, no systems yet.

Scope:
- Provide a minimal tick(clock, ecs_world, world_ctx, ...) entrypoint that wires
  the canonical phases A–I as per SOT-SIM4-RUNTIME-TICK, but does not execute
  real systems or collect commands yet.
- Uses ECSWorld.apply_commands([]) and world.apply_world_commands([]) as
  placeholders for Phases E and F.
- Returns a lightweight TickResult DTO.

SOT alignment (Sub‑Sprint 6.2a):
- Advance the clock at the start of the tick (after conceptually locking
  WorldContext) so that all phases A–I observe the current tick_index and dt.
- Phase comments map 1:1 to SOT-SIM4-RUNTIME-TICK (A through I).

Layering (SOP-100): runtime orchestrates and may import ecs/ and world/.
Determinism (SOP-200): no system time; RNG seed is accepted but not used yet.

Note on WorldContext naming:
- This tick currently takes the world-layer substrate WorldContext from
  backend.sim4.world.context. Per SOT-SIM4-RUNTIME-WORLD-CONTEXT, a runtime‑level
  WorldContext façade will be added later and this tick will depend on that
  instead.  # TODO[RT-WORLD-CONTEXT]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Any

from backend.sim4.runtime.clock import TickClock
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.world.context import WorldContext
from backend.sim4.world.apply_world_commands import apply_world_commands as apply_world_cmds
from backend.sim4.world.events import WorldEvent


@dataclass(frozen=True)
class TickResult:
    """
    Minimal runtime-facing outcome DTO for a single tick step (kernel result).

    Fields:
    - tick_index: the simulation tick index for this tick (after start-of-tick advance).
    - dt: delta time used for this tick.
    - world_events: WorldEvent list emitted by Phase F (currently empty list in skeleton).
    - notes: optional diagnostic placeholders for later phases.

    This DTO may be extended or wrapped by SimulationEngine.step() per
    SOT-SIM4-ENGINE in later sub-sprints.
    """

    tick_index: int
    dt: float
    world_events: List[WorldEvent] = field(default_factory=list)
    notes: dict[str, Any] = field(default_factory=dict)


def tick(
    clock: TickClock,
    ecs_world: ECSWorld,
    world_ctx: WorldContext,
    *,
    rng_seed: int,
    system_scheduler: Any,
    previous_events: Optional[list[Any]] = None,
) -> TickResult:
    """
    Execute a minimal deterministic tick skeleton with phases A–I wired.

    Canonical order (SOT-SIM4-RUNTIME-TICK §3/§4):
    1) Lock WorldContext   # TODO[RT-LOCK]
    2) Update Clock (advance at start so all phases observe current tick)
    A) Input & Pre-Processing
    B) System Phase B (ECS)
    C) System Phase C (ECS)
    D) System Phase D (ECS)
    E) Apply ECS Commands
    F) Apply World Commands
    G) Event Consolidation
    H) History/Diff Hook
    I) Narrative Trigger     # TODO[RT-I]
    12) Unlock WorldContext  # TODO[RT-LOCK]

    This function currently does not run any systems or collect/apply real
    commands; it only executes placeholders to validate the runtime scaffold.

    Args:
        clock: TickClock instance (dt is fixed per instance).
        ecs_world: ECS world state owner.
        world_ctx: WorldContext world-layer state owner (world substrate for now).
        rng_seed: Deterministic RNG seed (accepted but unused in 6.2).
        system_scheduler: Placeholder for system scheduling (unused in 6.2).
        previous_events: Optional prior global events buffer (unused in 6.2).

    Returns:
        TickResult with the tick_index, dt, and any world events collected
        during Phase F (empty in the skeleton path).
    """

    # Phase 1 — Lock WorldContext (conceptual; no-op for now)
    # TODO[RT-LOCK]: acquire world lock to ensure exclusive mutation in phases E/F

    # Phase 2 — Update Clock (advance at start so all phases see current tick)
    clock.advance(1)

    # Phase A — Input collection & pre-processing (stub)
    # TODO[RT-A]: integrate sanitized external inputs
    _ = previous_events  # explicitly unused in skeleton

    # Phase B, C, D — System phases (stubs, no execution yet)
    # TODO[RT-BCD]: run ECS systems via system_scheduler and collect ECS commands

    # Phase E — Apply ECS commands (placeholder: none yet)
    ecs_world.apply_commands([])  # no-op apply

    # Phase F — Apply World commands (placeholder: none yet)
    world_events: List[WorldEvent] = apply_world_cmds(world_ctx, [])

    # Phase G — Event consolidation (stub)
    # TODO[RT-G]: consolidate ECS + World + runtime events into a tick event stream

    # Phase H — History/diff hook (stub)
    # TODO[RT-H]: build and store diffs/history for replay

    # Phase I — Narrative trigger (stub)
    # TODO[RT-I]: call narrative sidecar after deterministic phases (sidecar)

    # Phase 12 — Unlock WorldContext (conceptual; no-op for now)
    # TODO[RT-LOCK]: release world lock

    return TickResult(tick_index=clock.tick_index, dt=clock.dt, world_events=world_events)
