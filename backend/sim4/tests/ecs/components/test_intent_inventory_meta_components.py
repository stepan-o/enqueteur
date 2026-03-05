from __future__ import annotations

from backend.sim4.ecs.components.intent_action import (
    PrimitiveIntent,
    SanitizedIntent,
    MovementIntent,
    InteractionIntent,
    ActionState,
    RoomID,
    AssetID,
)
from backend.sim4.ecs.components.narrative_state import NarrativeState
from backend.sim4.ecs.components.inventory import (
    InventorySubstrate,
    ItemState,
    ItemID,
)
from backend.sim4.ecs.components.meta import DebugFlags, SystemMarkers
from backend.sim4.ecs.entity import EntityID


def test_primitive_and_sanitized_intent_instantiation():
    agent: EntityID = 1
    room: RoomID = 10
    asset: AssetID = 100

    prim = PrimitiveIntent(
        intent_code=42,
        target_agent_id=agent,
        target_room_id=room,
        target_asset_id=asset,
        priority=0.8,
    )
    san = SanitizedIntent(
        intent_code=42,
        target_agent_id=agent,
        target_room_id=room,
        target_asset_id=asset,
        priority=0.8,
        valid=True,
        reason_code=0,
    )

    assert prim.intent_code == 42
    assert prim.target_agent_id == agent
    assert san.valid is True
    assert san.reason_code == 0


def test_movement_and_interaction_intents():
    agent: EntityID = 2
    room: RoomID = 20

    move = MovementIntent(
        kind_code=1,
        target_room_id=room,
        target_position=(1.5, -3.0),
        follow_agent_id=agent,
        speed_scalar=1.2,
        active=True,
    )
    inter = InteractionIntent(
        kind_code=2,
        target_agent_id=agent,
        target_asset_id=None,
        strength_scalar=0.6,
        active=False,
    )

    assert move.active is True
    assert move.target_position == (1.5, -3.0)
    assert inter.kind_code == 2
    assert inter.active is False


def test_action_state_and_narrative_state():
    action = ActionState(
        mode_code=3,
        time_in_mode=1.25,
        last_mode_change_tick=100,
    )
    narrative = NarrativeState(
        narrative_id=7,
        last_reflection_tick=50,
        cached_summary_ref=None,
        tokens_used_recently=256,
    )

    assert action.mode_code == 3
    assert narrative.narrative_id == 7
    assert narrative.cached_summary_ref is None


def test_inventory_and_meta_components():
    inv = InventorySubstrate(
        items=[ItemID(1), ItemID(2)],
        equipped_item_ids=[ItemID(2)],
    )
    item = ItemState(
        item_id=ItemID(1),
        owner_agent_id=EntityID(10),
        location_room_id=None,
        status_code=0,
    )
    debug = DebugFlags(
        log_agent=True,
        highlight_in_snapshot=False,
        freeze_movement=True,
    )
    markers = SystemMarkers(
        archetype_code=5,
        debug_notes_id=None,
    )

    assert inv.items == [1, 2]
    assert inv.equipped_item_ids == [2]
    assert item.owner_agent_id == 10
    assert debug.freeze_movement is True
    assert markers.archetype_code == 5
