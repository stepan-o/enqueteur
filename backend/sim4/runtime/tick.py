# sim4/runtime/tick.py
import time


class SimulationClock:
    """
    AAA-grade fixed-step simulation clock for Era III–V.

    Features:
        - fixed dt for simulation (deterministic)
        - accumulator for real-time synchronization
        - speed multiplier (slow/fast motion)
        - pause support
        - exact tick counter for snapshots
        - wall clock timestamps for profiling
    """

    def __init__(self, dt=0.1, speed=1.0):
        self.dt = dt                     # simulation step duration (fixed)
        self.speed = speed               # global sim speed multiplier
        self.tick = 0                    # monotonic simulation tick index

        self._paused = False
        self._last_time = time.perf_counter()
        self._accum = 0.0                # wall-clock accumulated dt

    # ----------------------------------------------------------------------
    # CONTROL
    # ----------------------------------------------------------------------
    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False
        self._last_time = time.perf_counter()

    def set_speed(self, speed: float):
        self.speed = max(0.01, float(speed))

    # ----------------------------------------------------------------------
    # MAIN STEP
    # ----------------------------------------------------------------------
    def step(self):
        """
        Returns True if a sim step should occur this frame, else False.

        Usage:
            while True:
                if clock.step():
                    world.step(clock.dt)
                    push_snapshot()
        """
        if self._paused:
            return False

        # Measure elapsed wall time
        now = time.perf_counter()
        wall_dt = now - self._last_time
        self._last_time = now

        # Apply speed multiplier
        wall_dt *= self.speed

        # Deposit into accumulator
        self._accum += wall_dt

        # Not enough time for a sim step yet
        if self._accum < self.dt:
            return False

        # Remove one fixed step worth of time
        self._accum -= self.dt

        # Advance simulation tick
        self.tick += 1

        return True

    # ----------------------------------------------------------------------
    # UTILITY
    # ----------------------------------------------------------------------
    def next_tick(self):
        """Convenience: returns the next tick index the sim will execute."""
        return self.tick + 1
