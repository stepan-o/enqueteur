import pytest

from backend.sim4.runtime.clock import TickClock
from backend.sim4.runtime.tick import tick
from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.systems.base import SystemContext
from backend.sim4.ecs.commands import ECSCommandKind
from backend.sim4.world.context import WorldContext, RoomRecord
from backend.sim4.world.commands import make_set_agent_room, WorldCommandKind
from backend.sim4.world.events import WorldEventKind


# --- Systems used for ECS application test ---
class CreateEntitySystem:
    def run(self, ctx: SystemContext) -> None:  # type: ignore[override]
        # enqueue a CREATE_ENTITY command
        ctx.commands.create_entity([])


class SetFieldSystem:
    def __init__(self, entity_id, component_type, field_name: str, value) -> None:
        self.entity_id = entity_id
        self.component_type = component_type
        self.field_name = field_name
        self.value = value

    def run(self, ctx: SystemContext) -> None:  # type: ignore[override]
        ctx.commands.set_field(self.entity_id, self.component_type, self.field_name, self.value)


class DummyScheduler:
    def __init__(self, mapping):
        self._mapping = mapping

    def iter_phase_systems(self, phase: str):
        return self._mapping.get(phase, [])


def _mk_world_with_rooms() -> WorldContext:
    wc = WorldContext()
    wc.register_room(RoomRecord(id=1, label="A"))
    wc.register_room(RoomRecord(id=2, label="B"))
    return wc


def test_phase_e_applies_ecs_commands_create_entity():
    clock = TickClock()
    ecs_world = ECSWorld()
    world_ctx = _mk_world_with_rooms()

    scheduler = DummyScheduler({"B": [CreateEntitySystem]})

    result = tick(
        clock,
        ecs_world,
        world_ctx,
        rng_seed=123,
        system_scheduler=scheduler,
    )

    # Ensure commands were applied: one entity created in ECSWorld
    all_eids = list(ecs_world.iter_entity_ids())
    assert len(all_eids) == 1
    # And result.ecs_commands reflect final global sequencing
    assert len(result.ecs_commands) == 1
    assert result.ecs_commands[0].seq == 0
    assert result.ecs_commands[0].kind is ECSCommandKind.CREATE_ENTITY


def test_phase_f_applies_world_commands_and_emits_events():
    clock = TickClock()
    ecs_world = ECSWorld()
    world_ctx = _mk_world_with_rooms()

    # Register an agent in room 1
    agent_id = 100
    world_ctx.register_agent(agent_id=agent_id, room_id=1)

    # Prepare a world command to move agent to room 2
    wc_cmd = make_set_agent_room(seq=999, agent_id=agent_id, room_id=2)

    # Scheduler runs no ECS systems; focus on Phase F
    scheduler = DummyScheduler({})

    result = tick(
        clock,
        ecs_world,
        world_ctx,
        rng_seed=0,
        system_scheduler=scheduler,
        world_commands_in=[wc_cmd],
    )

    # World state mutated: agent moved to room 2
    assert world_ctx.get_agent_room(agent_id) == 2

    # Event emitted includes AGENT_MOVED_ROOM
    kinds = {e.kind for e in result.world_events}
    assert WorldEventKind.AGENT_MOVED_ROOM in kinds
