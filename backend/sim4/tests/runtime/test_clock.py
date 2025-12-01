import pytest

from backend.sim4.runtime.clock import TickClock, TickIndex, DeltaTime


def test_default_construction_and_advance():
    clock = TickClock()
    assert isinstance(clock.tick_index, int)
    assert pytest.approx(clock.dt) == 1.0 / 60.0
    assert clock.tick == 0
    assert pytest.approx(clock.delta_time) == clock.dt

    # advance single step
    new_tick = clock.advance()
    assert new_tick == 1
    assert clock.tick_index == 1

    # advance multiple steps
    new_tick = clock.advance(steps=4)
    assert new_tick == 5
    assert clock.tick == 5


def test_custom_dt_and_start_index():
    clock = TickClock(tick_index=10, dt=0.5)
    assert clock.tick_index == 10
    assert clock.dt == 0.5

    clock.advance()
    assert clock.tick_index == 11


def test_invalid_advance_steps():
    clock = TickClock()
    with pytest.raises(ValueError):
        clock.advance(0)
    with pytest.raises(ValueError):
        clock.advance(-3)
