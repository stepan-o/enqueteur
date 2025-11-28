# sim4/main.py

import time

from .ecs.scheduler import World
from .runtime.tick import SimulationClock
from .runtime.snapshots import build_snapshot, snapshot_json
from .runtime.diff import diff_snapshots
from .runtime.logger import RuntimeLogger
from .runtime.history import HistoryBuffer

from .world.bootstrap import spawn_initial_robots

# Systems (Era IV/V implementations)
from .ecs.systems.perception import perception_system
from .ecs.systems.cognition import cognition_system
from .ecs.systems.emotion import emotion_system
from .ecs.systems.intention import intention_system
from .ecs.systems.action import action_system
from .ecs.systems.movement import movement_system
from .ecs.systems.resolution import resolution_system


def main():
    # ---------------------------------------------------------
    # WORLD INITIALIZATION
    # ---------------------------------------------------------
    logger = RuntimeLogger(enabled=True)
    world = World(logger=logger)

    # Spawn robots with full component sets
    spawn_initial_robots(world, count=5)

    # ---------------------------------------------------------
    # TIME + HISTORY LAYER
    # ---------------------------------------------------------
    clock = SimulationClock(dt=0.1)

    # store last 2000 ticks + use diffs
    history = HistoryBuffer(use_diffs=True, limit=2000)

    # ---------------------------------------------------------
    # REGISTER SYSTEMS
    # ---------------------------------------------------------
    world.add_system("perception", perception_system)
    world.add_system("cognition", cognition_system)
    world.add_system("emotion", emotion_system)
    world.add_system("intention", intention_system)
    world.add_system("action", action_system)
    world.add_system("movement", movement_system)
    world.add_system("resolution", resolution_system)

    print("Simulation started (Era IV/V). Ctrl+C to stop.")

    # ---------------------------------------------------------
    # SNAPSHOT PIPELINE (full snapshot on tick 1)
    # ---------------------------------------------------------
    prev_snapshot = None

    try:
        while True:
            dt = clock.step()
            world.step(dt)

            # Build new snapshot
            curr_snapshot = build_snapshot(world, world.tick)

            # Tick 1 → full snapshot
            if prev_snapshot is None:
                print(snapshot_json(curr_snapshot))
                history.record_snapshot(world.tick, curr_snapshot)

            # All following ticks → diff patches
            else:
                patch = diff_snapshots(prev_snapshot, curr_snapshot)
                print(snapshot_json(patch))
                history.record_diff(world.tick, patch)

            prev_snapshot = curr_snapshot

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopped simulation.")

        # -----------------------------------------------------
        # Optional: Export the entire episode on shutdown
        # -----------------------------------------------------
        episode = history.export_episode()
        print("Episode exported with ticks:", episode["order"])


if __name__ == "__main__":
    main()
