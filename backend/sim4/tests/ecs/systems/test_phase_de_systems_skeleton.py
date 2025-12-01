from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.systems.base import SystemContext, SimulationRNG, ECSCommandBuffer, WorldViewsHandle
from backend.sim4.ecs.components import (
    Transform,
    RoomPresence,
    PathState,
    MovementIntent,
    InteractionIntent,
    ActionState,
    PrimitiveIntent,
    SanitizedIntent,
    MotiveSubstrate,
    PlanLayerSubstrate,
    DriveState,
    InventorySubstrate,
    ItemState,
    ProfileTraits,
)

from backend.sim4.ecs.systems.intent_resolver_system import IntentResolverSystem
from backend.sim4.ecs.systems.movement_resolution_system import MovementResolutionSystem
from backend.sim4.ecs.systems.interaction_resolution_system import InteractionResolutionSystem
from backend.sim4.ecs.systems.inventory_system import InventorySystem
from backend.sim4.ecs.systems.action_execution_system import ActionExecutionSystem


@dataclass
class DummyWorldViews:
    """
    Minimal dummy implementation of WorldViewsHandle for Phase D/E tests.
    """

    # Protocol has no concrete methods yet for this sprint.
    pass


def make_minimal_world() -> ECSWorld:
    world = ECSWorld()

    components = [
        # Embodiment & path
        Transform(room_id=0, x=0.0, y=0.0, orientation=0.0),
        RoomPresence(room_id=0, time_in_room=0.0),
        PathState(active=False, waypoints=[], current_index=0, progress_along_segment=0.0, path_valid=True),

        # Traits / drives
        ProfileTraits(
            introversion=0.5,
            volatility=0.5,
            conscientiousness=0.5,
            agreeableness=0.5,
            openness=0.5,
            risk_tolerance=0.5,
        ),
        DriveState(
            curiosity=0.5,
            safety_drive=0.5,
            dominance_drive=0.5,
            meaning_drive=0.5,
            attachment_drive=0.5,
            novelty_drive=0.5,
            fatigue=0.0,
            comfort=1.0,
        ),

        # Intent pipeline
        PrimitiveIntent(
            intent_code=1,
            target_agent_id=None,
            target_room_id=0,
            target_asset_id=None,
            priority=1.0,
        ),
        SanitizedIntent(
            intent_code=1,
            target_agent_id=None,
            target_room_id=0,
            target_asset_id=None,
            priority=1.0,
            valid=True,
            reason_code=0,
        ),
        MotiveSubstrate(active_motives=[], motive_strengths=[], last_update_tick=0),
        PlanLayerSubstrate(steps=[], current_index=0, plan_confidence=0.0, revision_needed=False),

        # Movement / interaction / action
        MovementIntent(
            kind_code=0,
            target_room_id=0,
            target_position=None,
            follow_agent_id=None,
            speed_scalar=1.0,
            active=False,
        ),
        InteractionIntent(
            kind_code=0,
            target_agent_id=None,
            target_asset_id=None,
            strength_scalar=0.0,
            active=False,
        ),
        ActionState(mode_code=0, time_in_mode=0.0, last_mode_change_tick=0),

        # Inventory
        InventorySubstrate(items=[], equipped_item_ids=[]),
        ItemState(item_id=1, owner_agent_id=None, location_room_id=0, status_code=0),
    ]

    world.create_entity(initial_components=components)
    return world


def make_system_context(world: ECSWorld) -> SystemContext:
    rng = SimulationRNG(seed=42)
    views: WorldViewsHandle = DummyWorldViews()
    commands = ECSCommandBuffer()
    return SystemContext(world=world, dt=0.1, rng=rng, views=views, commands=commands, tick_index=0)


@pytest.mark.parametrize(
    "system_cls",
    [
        IntentResolverSystem,
        MovementResolutionSystem,
        InteractionResolutionSystem,
        InventorySystem,
        ActionExecutionSystem,
    ],
)
def test_phase_de_system_skeletons_run_without_error(system_cls):
    world = make_minimal_world()
    ctx = make_system_context(world)

    system = system_cls()
    # Should not raise any exceptions during skeleton run
    system.run(ctx)
