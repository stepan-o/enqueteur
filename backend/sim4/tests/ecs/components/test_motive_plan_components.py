from __future__ import annotations

from backend.sim4.ecs.components.motive_plan import (
    MotiveSubstrate,
    PlanStepSubstrate,
    PlanLayerSubstrate,
    RoomID,
    AssetID,
)
from backend.sim4.ecs.entity import EntityID


def test_motive_substrate_allows_uneven_lists():
    """Dataclass stores lists as-is; systems must enforce alignment."""
    motives = [101, 202, 303]
    strengths = [0.5, 0.9]  # intentionally shorter

    substrate = MotiveSubstrate(
        active_motives=motives,
        motive_strengths=strengths,
        last_update_tick=42,
    )

    assert substrate.active_motives == motives
    assert substrate.motive_strengths == strengths
    assert substrate.last_update_tick == 42
    # lengths may differ — alignment is a system concern, not enforced here
    assert len(substrate.active_motives) != len(substrate.motive_strengths)


def test_plan_step_and_layer_instantiation():
    agent: EntityID = 1
    room: RoomID = 10
    asset: AssetID = 100

    step1 = PlanStepSubstrate(
        step_id=1001,
        target_agent_id=agent,
        target_room_id=room,
        target_asset_id=None,
        status_code=0,  # e.g. PENDING
    )
    step2 = PlanStepSubstrate(
        step_id=1002,
        target_agent_id=None,
        target_room_id=None,
        target_asset_id=asset,
        status_code=1,  # e.g. IN_PROGRESS
    )

    layer = PlanLayerSubstrate(
        steps=[step1, step2],
        current_index=1,
        plan_confidence=0.75,
        revision_needed=False,
    )

    assert len(layer.steps) == 2
    assert layer.steps[0].step_id == 1001
    assert layer.steps[1].target_asset_id == asset
    assert layer.current_index == 1
    assert layer.plan_confidence == 0.75
    assert layer.revision_needed is False
