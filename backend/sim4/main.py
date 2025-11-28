# sim4/main.py

import time

from .world.world import WorldContext
from .world.spawn_initial_world.spawn_initial_robots import spawn_initial_robots

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
from .runtime.snapshots import build_snapshot, snapshot_json
from .runtime.diff import diff_snapshots
from .runtime.logger import RuntimeLogger
from .runtime.history import HistoryBuffer


def main():
    # ---------------------------------------------------------
    # WORLD INITIALIZATION (Era V wrapper)
    # ---------------------------------------------------------
    logger = RuntimeLogger(enabled=True)
    ctx = WorldContext(logger=logger)

    # spawn robots into ctx.ecs + into a room (A)
    spawn_initial_robots(ctx, count=5)

    # ---------------------------------------------------------
    # TIME + HISTORY BUFFER
    # ---------------------------------------------------------
    clock = SimulationClock(dt=0.1)
    history = HistoryBuffer(use_diffs=True, limit=2000)

    # ---------------------------------------------------------
    # REGISTER SYSTEMS (Era V phases)
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
            # ---- Tick ----
            dt = clock.step()
            ctx.step(dt)

            # ---- Build snapshot ----
            curr_snapshot = build_snapshot(ctx, ctx.tick)

            if prev_snapshot is None:
                # First tick = full snapshot
                print(snapshot_json(curr_snapshot))
                history.record_snapshot(ctx.tick, curr_snapshot)

            else:
                # Following ticks = patch/diff
                patch = diff_snapshots(prev_snapshot, curr_snapshot)
                print(snapshot_json(patch))
                history.record_diff(ctx.tick, patch)

            prev_snapshot = curr_snapshot

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopped simulation.\n")

        # -----------------------------------------------------
        # Episode export
        # -----------------------------------------------------
        episode = history.export_episode()
        print("Episode exported with ticks:", episode["order"])


if __name__ == "__main__":
    main()
