"""
Tick pipeline (Sprint 6) — deterministic A–I phases with systems, command application, and event consolidation.

Overview (SOT-SIM4-RUNTIME-TICK):
- Phases A–I are wired in order and execute deterministically per tick.
- Phases B–D: runtime schedules and runs ECS systems via
  `system_scheduler.iter_phase_systems("B"/"C"/"D")`, injecting a per‑system
  `SimulationRNG` seed derived from (rng_seed, tick_index, system_index) and a
  per‑tick WorldViews façade (read‑only) over the world substrate.
- Phase E: runtime uses `ECSCommandBatch` to globally sequence ECS commands
  (seq 0..N-1 in aggregated order) and applies them with `ECSWorld.apply_commands(...)`.
- Phase F: runtime uses `WorldCommandBatch` to globally sequence WorldCommands
  and applies them with `apply_world_commands(...)` from world/, emitting
  `WorldEvent` instances.
- Phase G: runtime consolidates events via `runtime.events.consolidate_events(...)`
  into a list of `RuntimeEvent` values (origin, seq, payload) for the tick.
- Phases A, H, I are present as stubs: no real input bundle, diff/history, or
  narrative trigger yet.

Clock semantics:
- The TickClock is advanced at the start of tick (after conceptual world lock),
  so all phases observe the same tick_index and dt for this step.

Layering (SOP-100) and determinism (SOP-200):
- runtime orchestrates ECS and world; no wall‑clock or OS randomness is used.
- Command/event ordering is explicitly defined and test‑covered.

Note on WorldContext naming:
- This tick currently consumes the world‑layer substrate WorldContext from
  backend.sim4.world.context. Per SOT‑SIM4‑RUNTIME‑WORLD‑CONTEXT, a runtime‑level
  WorldContext façade will be introduced later; tick() will depend on that
  façade instead.  # TODO[RT-WORLD-CONTEXT]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Any

from backend.sim4.runtime.clock import TickClock
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.world.context import WorldContext
from backend.sim4.world.apply_world_commands import apply_world_commands as apply_world_cmds
from backend.sim4.world.events import WorldEvent
from backend.sim4.world.views import WorldViews
from backend.sim4.ecs.commands import ECSCommand
from backend.sim4.ecs.systems.base import (
    SystemContext,
    SimulationRNG,
    ECSCommandBuffer,
)
from backend.sim4.runtime.command_bus import ECSCommandBatch, WorldCommandBatch
from backend.sim4.world.commands import WorldCommand
from backend.sim4.runtime.events import RuntimeEvent, consolidate_events
from backend.sim4.snapshot.world_snapshot_builder import build_world_snapshot
from backend.sim4.snapshot.output import TickOutputSink


@dataclass(frozen=True)
class TickResult:
    """
    Minimal runtime-facing outcome DTO for a single tick step (kernel result).

    Fields (Sprint 6):
    - tick_index: simulation tick index for this tick (post start‑of‑tick advance).
    - dt: delta time for this tick.
    - world_events: WorldEvent list emitted by Phase F (application order).
    - ecs_commands: ECSCommand list applied in Phase E (globally seq‑ordered).
    - runtime_events: consolidated RuntimeEvent list from Phase G
      (world → ecs → runtime, per‑tick seq 0..N-1).
    - ecs_commands_applied: number applied in Phase E.
    - world_commands_applied: number applied in Phase F.
    - notes: diagnostic bag reserved for later phases.

    This DTO may be extended or wrapped by SimulationEngine.step() per
    SOT-SIM4-ENGINE in later sub-sprints.
    """

    tick_index: int
    dt: float
    world_events: List[WorldEvent] = field(default_factory=list)
    ecs_commands: List[ECSCommand] = field(default_factory=list)
    runtime_events: List[RuntimeEvent] = field(default_factory=list)
    ecs_commands_applied: int = 0
    world_commands_applied: int = 0
    notes: dict[str, Any] = field(default_factory=dict)


def tick(
    clock: TickClock,
    ecs_world: ECSWorld,
    world_ctx: WorldContext,
    *,
    rng_seed: int,
    system_scheduler: Any,
    previous_events: Optional[list[Any]] = None,
    world_commands_in: Optional[Iterable[WorldCommand]] = None,
    episode_id: int = 0,
    narrative_ctx: "NarrativeRuntimeContext | None" = None,
    tick_output_sink: TickOutputSink | None = None,
    run_id: int | None = None,
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
    I) Narrative Trigger     # optional; wired in Sub‑sprint 8.3
    12) Unlock WorldContext  # TODO[RT-LOCK]

    This function currently does not run any systems or collect/apply real
    commands; it only executes placeholders to validate the runtime scaffold.

    Args:
        clock: TickClock instance (dt is fixed per instance).
        ecs_world: ECS world state owner.
        world_ctx: WorldContext world-layer state owner (world substrate for now).
        rng_seed: Deterministic RNG seed used to derive per-system seeds.
        system_scheduler: Object that may expose iter_phase_systems(phase) to
            enumerate system classes for phases "B"/"C"/"D"; tolerated if None.
        previous_events: Optional prior global events buffer consumed during
            Phase A input collection (currently unused; accepted for API stability).
        world_commands_in: Iterable of WorldCommand objects to apply in Phase F.
            Commands are globally sequenced via WorldCommandBatch before apply.
        episode_id: Episode identifier propagated to Phase H snapshot/export and
            to optional narrative sidecar in Phase I.
        narrative_ctx: Optional NarrativeRuntimeContext providing a
            run_tick_narrative(...) hook; if provided, called in Phase I and any
            exceptions are swallowed to preserve kernel determinism.
        tick_output_sink: Optional TickOutputSink implementation to receive a
            snapshot-first runtime output in Phase H (on_tick_output(...)).
        run_id: Optional run identifier (reserved for future wiring).

    Returns:
        TickResult capturing tick_index, dt, Phase F world_events, globally
        sequenced ECS commands applied in Phase E, consolidated runtime_events
        from Phase G, and counters of applied commands.
    """

    # Phase 1 — Lock WorldContext (conceptual; no-op for now)
    # TODO[RT-LOCK]: acquire world lock to ensure exclusive mutation in phases E/F

    # Phase 2 — Update Clock (advance at start so all phases see current tick)
    clock.advance(1)

    # Phase A — Input collection & pre-processing (stub)
    # TODO[RT-A]: integrate sanitized external inputs
    _ = previous_events  # explicitly unused in skeleton

    # Prepare per-tick read-only world views and base RNG seed
    views = WorldViews(world_ctx)  # single per-tick instance reused across systems
    base_seed = rng_seed * 1_000_003 + int(clock.tick_index)

    # Phase B, C, D — System phases (generic today; specialization into
    # Perception / Cognition / Intention is planned in later sprints per SOT)
    aggregated_ecs_commands: List[ECSCommand] = []
    # Deterministic per-system seeding: combine base_seed with an increasing index
    local_index = 0
    for phase in ("B", "C", "D"):
        # system_scheduler is expected to expose iter_phase_systems(phase);
        # tolerate None or missing attribute (legacy tests pass object()/None)
        iter_phase = getattr(system_scheduler, "iter_phase_systems", None)
        systems_for_phase = iter_phase(phase) if callable(iter_phase) else ()
        for system_type in (systems_for_phase or ()):  # type: ignore[assignment]
            system_seed = base_seed * 1_000_003 + local_index
            local_index += 1
            rng = SimulationRNG(system_seed)
            cmd_buffer = ECSCommandBuffer()
            ctx = SystemContext(
                world=ecs_world,
                dt=clock.dt,
                rng=rng,
                views=views,
                commands=cmd_buffer,
                tick_index=clock.tick_index,
            )
            system = system_type()
            # Systems are expected to be deterministic and side-effect only via ctx.commands
            system.run(ctx)
            aggregated_ecs_commands.extend(cmd_buffer.commands)

    # Phase E — Apply ECS commands using the command bus (global sequencing)
    ecs_batch = ECSCommandBatch(aggregated_ecs_commands)
    final_ecs_commands = ecs_batch.to_global_sequence()
    ecs_world.apply_commands(final_ecs_commands)
    ecs_commands_applied = len(final_ecs_commands)

    # Phase F — Apply World commands via command bus and emit world events
    raw_world_commands = list(world_commands_in or [])
    world_commands_applied = 0
    if raw_world_commands:
        world_batch = WorldCommandBatch(raw_world_commands)
        final_world_commands = world_batch.to_global_sequence()
        world_commands_applied = len(final_world_commands)
        world_events: List[WorldEvent] = apply_world_cmds(world_ctx, final_world_commands)
    else:
        world_events = apply_world_cmds(world_ctx, [])
        world_commands_applied = 0

    # Phase G — Event consolidation
    runtime_events = consolidate_events(
        tick_index=clock.tick_index,
        dt=clock.dt,
        world_events=world_events,
        ecs_events=(),        # TODO[RT-G]: wire ECS-origin events when available
        runtime_events=(),    # TODO[RT-G]: internal runtime events when available
    )

    # Phase H — History/diff hook (snapshot emission; no persistence yet)
    world_snapshot = None
    try:
        world_snapshot = build_world_snapshot(
            tick_index=clock.tick_index,
            episode_id=episode_id,
            world_ctx=world_ctx,
            ecs_world=ecs_world,
        )
    except Exception:
        # Phase H must not break deterministic kernel; swallow snapshot errors
        world_snapshot = None

    if world_snapshot is not None and tick_output_sink is not None:
        try:
            tick_output_sink.on_tick_output(
                tick_index=clock.tick_index,
                dt=clock.dt,
                world_snapshot=world_snapshot,
                runtime_events=runtime_events,
                narrative_fragments=(),
            )
        except Exception:
            # Sink must never break deterministic kernel tick
            pass

    # Phase I — Narrative trigger (optional)
    if narrative_ctx is not None:
        try:
            narrative_ctx.run_tick_narrative(
                tick_index=clock.tick_index,
                dt=clock.dt,
                episode_id=episode_id,
                world_ctx=world_ctx,
                ecs_world=ecs_world,
            )
        except Exception:
            # Narrative sidecar must never break deterministic kernel tick
            pass

    # Phase 12 — Unlock WorldContext (conceptual; no-op for now)
    # TODO[RT-LOCK]: release world lock

    return TickResult(
        tick_index=clock.tick_index,
        dt=clock.dt,
        world_events=world_events,
        ecs_commands=final_ecs_commands,
        runtime_events=runtime_events,
        ecs_commands_applied=ecs_commands_applied,
        world_commands_applied=world_commands_applied,
        notes={},
    )
