# sim4/main.py

import time

from .world.world import WorldContext
from .world.spawn_initial_world.spawn_initial_world import spawn_initial_world

# Systems
from .ecs.systems.perception import perception_system
from .ecs.systems.cognition import cognition_system
from .ecs.systems.emotion import emotion_system
from .ecs.systems.intention import intention_system
from .ecs.systems.action import action_system
from .ecs.systems.movement import movement_system
from .ecs.systems.resolution import resolution_system

# Runtime
from .runtime.tick import SimulationClock
from .runtime.snapshots import build_world_snapshot, snapshot_json
from .runtime.diff import diff_snapshots
from .runtime.logger import RuntimeLogger
from .runtime.history import HistoryBuffer


def main():
    # ---------------------------------------------------------
    # WORLD INITIALIZATION (Era V wrapper)
    # ---------------------------------------------------------
    logger = RuntimeLogger(enabled=True)
    ctx = WorldContext(logger=logger)

    # Spawn rooms + robots + layout + assets
    spawn_initial_world(ctx, count=5)

    # ---------------------------------------------------------
    # TIME + HISTORY BUFFER
    # ---------------------------------------------------------
    clock = SimulationClock(dt=0.1)
    history = HistoryBuffer(use_diffs=True, limit=2000)

    # ---------------------------------------------------------
    # REGISTER SYSTEMS (run inside ctx.ecs.step)
    # ---------------------------------------------------------
    ecs = ctx.ecs
    ecs.add_system("perception", perception_system)
    ecs.add_system("cognition", cognition_system)
    ecs.add_system("emotion", emotion_system)
    ecs.add_system("intention", intention_system)
    ecs.add_system("action", action_system)
    ecs.add_system("movement", movement_system)
    ecs.add_system("resolution", resolution_system)

    print("Simulation started (Era V). Ctrl+C to stop.\n")

    prev_snapshot = None

    try:
        while True:
            # -------------------------------------------------
            # TICK
            # -------------------------------------------------
            dt = clock.step()
            ctx.step(dt)                     # increments ctx.tick, runs ECS

            # -------------------------------------------------
            # SNAPSHOT
            # -------------------------------------------------
            curr_snapshot = build_world_snapshot(ctx, ctx.tick)

            if prev_snapshot is None:
                # First tick = full snapshot
                print(snapshot_json(curr_snapshot))
                history.record_snapshot(ctx.tick, curr_snapshot)

            else:
                # Following ticks = diff patch
                patch = diff_snapshots(prev_snapshot, curr_snapshot)
                print(snapshot_json(patch))
                history.record_diff(ctx.tick, patch)

            prev_snapshot = curr_snapshot

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopped simulation.\n")

        # -----------------------------------------------------
        # EPISODE EXPORT
        # -----------------------------------------------------
        episode = history.export_episode()
        print("Episode exported with ticks:", episode["order"])


if __name__ == "__main__":
    main()
