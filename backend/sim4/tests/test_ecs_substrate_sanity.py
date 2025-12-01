from __future__ import annotations

from backend.sim4.ecs import ECSWorld
from backend.sim4.ecs.systems.base import ECSCommandBuffer
from backend.sim4.ecs.components import (
    AgentIdentity,
    Transform,
    EmotionFields,
    DriveState,
)
from backend.sim4.ecs.entity import EntityID


def test_single_entity_identity_transform_emotion_bundle():
    world = ECSWorld()

    e = world.create_entity(
        initial_components=[
            AgentIdentity(
                id=EntityID(1),
                canonical_name_id=123,
                role_code=10,
                generation=0,
                seed=999,
            ),
            Transform(
                room_id=1,
                x=1.0,
                y=2.0,
                orientation=0.5,
            ),
            EmotionFields(
                tension=0.1,
                mood_valence=0.2,
                arousal=0.3,
                social_stress=0.0,
                excitement=0.4,
                boredom=0.0,
            ),
        ]
    )

    result = world.query((AgentIdentity, Transform, EmotionFields)).to_list()

    assert len(result) == 1
    (eid, (identity, transform, emotion)) = result[0]

    assert eid == e
    assert isinstance(identity, AgentIdentity)
    assert isinstance(transform, Transform)
    assert isinstance(emotion, EmotionFields)

    assert identity.canonical_name_id == 123
    assert transform.x == 1.0 and transform.y == 2.0
    assert emotion.tension == 0.1


def test_query_returns_only_entities_with_drive_state():
    world = ECSWorld()

    # e0: AgentIdentity + Transform (no DriveState)
    e0 = world.create_entity(
        initial_components=[
            AgentIdentity(id=EntityID(10), canonical_name_id=1, role_code=1, generation=0, seed=1),
            Transform(room_id=1, x=0.0, y=0.0, orientation=0.0),
        ]
    )

    # e1: AgentIdentity + DriveState
    e1 = world.create_entity(
        initial_components=[
            AgentIdentity(id=EntityID(11), canonical_name_id=2, role_code=2, generation=0, seed=2),
            DriveState(
                curiosity=0.5,
                safety_drive=0.8,
                dominance_drive=0.1,
                meaning_drive=0.3,
                attachment_drive=0.7,
                novelty_drive=0.4,
                fatigue=0.0,
                comfort=0.0,
            ),
        ]
    )

    # e2: AgentIdentity + Transform + DriveState
    e2 = world.create_entity(
        initial_components=[
            AgentIdentity(id=EntityID(12), canonical_name_id=3, role_code=3, generation=0, seed=3),
            Transform(room_id=2, x=1.0, y=1.0, orientation=1.0),
            DriveState(
                curiosity=0.2,
                safety_drive=0.9,
                dominance_drive=0.0,
                meaning_drive=0.6,
                attachment_drive=0.5,
                novelty_drive=0.1,
                fatigue=0.0,
                comfort=0.0,
            ),
        ]
    )

    rows = world.query((DriveState,)).to_list()

    entity_ids = [eid for eid, (_drive,) in rows]
    assert e0 not in entity_ids
    assert e1 in entity_ids
    assert e2 in entity_ids

    for eid, (drive,) in rows:
        assert isinstance(drive, DriveState)
        # Spot check one value deterministically
        if eid == e1:
            assert drive.safety_drive == 0.8


def test_commands_can_modify_substrate_components():
    world = ECSWorld()
    e = world.create_entity(
        initial_components=[
            DriveState(
                curiosity=0.1,
                safety_drive=0.5,
                dominance_drive=0.0,
                meaning_drive=0.2,
                attachment_drive=0.3,
                novelty_drive=0.4,
                fatigue=0.0,
                comfort=0.0,
            )
        ]
    )

    buf = ECSCommandBuffer()
    buf.set_field(
        entity_id=e,
        component_type=DriveState,
        field_name="curiosity",
        value=0.9,
    )

    world.apply_commands(buf.commands)

    drive = world.get_component(e, DriveState)
    assert drive is not None
    assert drive.curiosity == 0.9

    rows = world.query((DriveState,)).to_list()
    assert len(rows) == 1
    (eid, (drive2,)) = rows[0]
    assert eid == e
    assert drive2.curiosity == 0.9
