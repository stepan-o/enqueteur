import pytest

from backend.sim4.runtime.clock import TickClock
from backend.sim4.runtime.tick import tick
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.systems.base import SystemContext
from backend.sim4.world.context import WorldContext, RoomRecord
from backend.sim4.world.commands import make_set_agent_room
from backend.sim4.world.events import WorldEventKind


class DummyScheduler:
    def __init__(self, mapping):
        self._mapping = mapping

    def iter_phase_systems(self, phase: str):
        return self._mapping.get(phase, [])


def _mk_world_two_rooms_with_agent() -> tuple[WorldContext, int, int, int]:
    wc = WorldContext()
    room_a = 1
    room_b = 2
    wc.register_room(RoomRecord(id=room_a, label="A"))
    wc.register_room(RoomRecord(id=room_b, label="B"))
    agent_id = 100
    wc.register_agent(agent_id=agent_id, room_id=room_a)
    return wc, agent_id, room_a, room_b


def test_tick_result_contains_world_events_in_runtime_events():
    clock = TickClock()
    ecs_world = ECSWorld()
    world_ctx, agent_id, room_a, room_b = _mk_world_two_rooms_with_agent()

    # Move agent A -> B
    wcmd = make_set_agent_room(seq=999, agent_id=agent_id, room_id=room_b)
    scheduler = DummyScheduler({})

    result = tick(
        clock,
        ecs_world,
        world_ctx,
        rng_seed=0,
        system_scheduler=scheduler,
        world_commands_in=[wcmd],
    )

    # World events present and correct
    assert len(result.world_events) == 1
    ev = result.world_events[0]
    assert ev.kind is WorldEventKind.AGENT_MOVED_ROOM

    # Runtime events reflect world events with origin/world and seq 0
    assert len(result.runtime_events) == 1
    rev = result.runtime_events[0]
    assert rev.origin == "world"
    assert rev.tick_index == result.tick_index
    assert rev.seq == 0
    # runtime payload should be the same event instance or equal by value
    assert rev.payload == ev


def test_tick_result_command_counts_match_application():
    # System that enqueues one CREATE_ENTITY command
    class CreateEntitySystem:
        def run(self, ctx: SystemContext) -> None:  # type: ignore[override]
            ctx.commands.create_entity([])

    clock = TickClock()
    ecs_world = ECSWorld()
    world_ctx, agent_id, room_a, room_b = _mk_world_two_rooms_with_agent()

    wcmd = make_set_agent_room(seq=0, agent_id=agent_id, room_id=room_b)
    scheduler = DummyScheduler({"B": [CreateEntitySystem]})

    result = tick(
        clock,
        ecs_world,
        world_ctx,
        rng_seed=123,
        system_scheduler=scheduler,
        world_commands_in=[wcmd],
    )

    # Counts align
    assert result.ecs_commands_applied == len(result.ecs_commands) == 1
    assert result.world_commands_applied == 1

    # ECS state changed: one entity exists
    all_eids = list(ecs_world.iter_entity_ids())
    assert len(all_eids) == 1

    # World state changed: agent moved
    assert world_ctx.get_agent_room(agent_id) == room_b


def test_event_consolidation_determinism():
    # Setup identical worlds and schedulers
    world_ctx1, agent_id1, room_a1, room_b1 = _mk_world_two_rooms_with_agent()
    world_ctx2, agent_id2, room_a2, room_b2 = _mk_world_two_rooms_with_agent()

    wcmd1 = make_set_agent_room(seq=55, agent_id=agent_id1, room_id=room_b1)
    wcmd2 = make_set_agent_room(seq=55, agent_id=agent_id2, room_id=room_b2)

    sched = DummyScheduler({})

    r1 = tick(TickClock(), ECSWorld(), world_ctx1, rng_seed=1, system_scheduler=sched, world_commands_in=[wcmd1])
    r2 = tick(TickClock(), ECSWorld(), world_ctx2, rng_seed=1, system_scheduler=sched, world_commands_in=[wcmd2])

    sig1 = [(e.origin, getattr(e.payload, "kind", None)) for e in r1.runtime_events]
    sig2 = [(e.origin, getattr(e.payload, "kind", None)) for e in r2.runtime_events]
    assert sig1 == sig2
