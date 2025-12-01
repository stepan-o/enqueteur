import pytest

from backend.sim4.runtime.clock import TickClock
from backend.sim4.runtime.tick import tick, TickResult

from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.commands import cmd_create_entity
from backend.sim4.ecs.components.embodiment import Transform, RoomPresence
from backend.sim4.ecs.query import QuerySignature
from backend.sim4.ecs.systems.base import SystemContext

from backend.sim4.world.context import WorldContext, RoomRecord
from backend.sim4.world.commands import make_set_agent_room
from backend.sim4.world.events import WorldEventKind


class DummyScheduler:
    def __init__(self, mapping):
        self._mapping = mapping

    def iter_phase_systems(self, phase: str):
        return self._mapping.get(phase, [])


def _mk_world_with_agent_two_rooms() -> tuple[WorldContext, int, int, int]:
    wc = WorldContext()
    room_a = 1
    room_b = 2
    wc.register_room(RoomRecord(id=room_a, label="A"))
    wc.register_room(RoomRecord(id=room_b, label="B"))
    agent_id = 100
    wc.register_agent(agent_id=agent_id, room_id=room_a)
    return wc, agent_id, room_a, room_b


def _mk_ecs_with_agent(room_id: int) -> tuple[ECSWorld, int]:
    ecs_world = ECSWorld()
    cmd = cmd_create_entity(
        seq=0,
        components=[
            Transform(room_id=room_id, x=0.0, y=0.0, orientation=0.0),
            RoomPresence(room_id=room_id, time_in_room=0.0),
        ],
    )
    ecs_world.apply_commands([cmd])
    entity_ids = list(ecs_world.iter_entity_ids())
    assert len(entity_ids) == 1
    return ecs_world, entity_ids[0]


class TimeInRoomIncrementSystem:
    def __init__(self, delta: float = 1.0):
        self._delta = delta

    def run(self, ctx: SystemContext) -> None:  # type: ignore[override]
        sig = QuerySignature(
            read=(Transform,),
            write=(RoomPresence,),
        )
        for row in ctx.world.query(sig):
            entity = row.entity
            transform, room_presence = row.components  # read + write order
            _ = transform  # unused, but validates unpacking
            new_time = room_presence.time_in_room + self._delta
            ctx.commands.set_field(
                entity_id=entity,
                component_type=RoomPresence,
                field_name="time_in_room",
                value=new_time,
            )


def test_toy_simulation_tick_end_to_end():
    # --- Setup world + ECS ---
    world_ctx, agent_id, room_a, room_b = _mk_world_with_agent_two_rooms()
    ecs_world, eid = _mk_ecs_with_agent(room_a)

    # Sanity: initial ECS state
    rp_before = ecs_world.get_component(eid, RoomPresence)
    assert rp_before is not None
    assert rp_before.time_in_room == 0.0
    assert world_ctx.get_agent_room(agent_id) == room_a

    # --- Scheduler with our test system in Phase B ---
    class ToyScheduler(DummyScheduler):
        pass

    scheduler = ToyScheduler({"B": [TimeInRoomIncrementSystem]})

    # World command: move agent room_a -> room_b
    wcmd = make_set_agent_room(seq=10, agent_id=agent_id, room_id=room_b)

    # --- Run one tick ---
    clock = TickClock()
    result = tick(
        clock=clock,
        ecs_world=ecs_world,
        world_ctx=world_ctx,
        rng_seed=123,
        system_scheduler=scheduler,
        previous_events=None,
        world_commands_in=[wcmd],
    )

    # --- Assertions: core behavior ---

    # 1) TickResult sanity
    assert isinstance(result, TickResult)
    assert result.tick_index == 1  # clock advanced once at start-of-tick
    assert result.ecs_commands_applied == len(result.ecs_commands) > 0
    assert result.world_commands_applied == 1

    # 2) ECS state mutated via Phase E
    rp_after = ecs_world.get_component(eid, RoomPresence)
    assert rp_after is not None
    assert rp_after.time_in_room == pytest.approx(1.0)

    # 3) World state mutated via Phase F
    assert world_ctx.get_agent_room(agent_id) == room_b

    # 4) World events surfaced
    assert len(result.world_events) == 1
    ev = result.world_events[0]
    assert ev.kind is WorldEventKind.AGENT_MOVED_ROOM

    # 5) Runtime events reflect world events with deterministic ordering
    assert len(result.runtime_events) == 1
    rev = result.runtime_events[0]
    assert rev.origin == "world"
    assert rev.tick_index == result.tick_index
    assert rev.seq == 0
    assert rev.payload == ev


def test_toy_simulation_tick_determinism():
    world_ctx1, agent_id1, room_a1, room_b1 = _mk_world_with_agent_two_rooms()
    world_ctx2, agent_id2, room_a2, room_b2 = _mk_world_with_agent_two_rooms()

    ecs_world1, eid1 = _mk_ecs_with_agent(room_a1)
    ecs_world2, eid2 = _mk_ecs_with_agent(room_a2)

    scheduler = DummyScheduler({"B": [TimeInRoomIncrementSystem]})

    wcmd1 = make_set_agent_room(seq=10, agent_id=agent_id1, room_id=room_b1)
    wcmd2 = make_set_agent_room(seq=10, agent_id=agent_id2, room_id=room_b2)

    r1 = tick(TickClock(), ecs_world1, world_ctx1, rng_seed=999, system_scheduler=scheduler, world_commands_in=[wcmd1])
    r2 = tick(TickClock(), ecs_world2, world_ctx2, rng_seed=999, system_scheduler=scheduler, world_commands_in=[wcmd2])

    # Compare simplified event signatures
    sig1 = [(e.origin, getattr(e.payload, "kind", None)) for e in r1.runtime_events]
    sig2 = [(e.origin, getattr(e.payload, "kind", None)) for e in r2.runtime_events]
    assert sig1 == sig2

    # ECS numeric field should match too
    rp1 = ecs_world1.get_component(eid1, RoomPresence)
    rp2 = ecs_world2.get_component(eid2, RoomPresence)
    assert rp1 is not None and rp2 is not None
    assert rp1.time_in_room == pytest.approx(rp2.time_in_room)
