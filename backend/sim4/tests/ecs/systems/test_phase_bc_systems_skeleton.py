from __future__ import annotations

from dataclasses import dataclass

import pytest

from backend.sim4.ecs.world import ECSWorld
from backend.sim4.ecs.systems.base import SystemContext, SimulationRNG, ECSCommandBuffer, WorldViewsHandle
from backend.sim4.ecs.components import (
    Transform,
    RoomPresence,
    ProfileTraits,
    PerceptionSubstrate,
    AttentionSlots,
    SalienceState,
    BeliefGraphSubstrate,
    AgentInferenceState,
    SocialBeliefWeights,
    DriveState,
    MotiveSubstrate,
    PlanLayerSubstrate,
    PathState,
    SocialSubstrate,
    SocialImpressionState,
    FactionAffinityState,
    SelfModelSubstrate,
    EmotionFields,
)

from backend.sim4.ecs.systems.perception_system import PerceptionSystem
from backend.sim4.ecs.systems.cognitive_preprocessor import CognitivePreprocessor
from backend.sim4.ecs.systems.emotion_gradient_system import EmotionGradientSystem
from backend.sim4.ecs.systems.drive_update_system import DriveUpdateSystem
from backend.sim4.ecs.systems.motive_formation_system import MotiveFormationSystem
from backend.sim4.ecs.systems.plan_resolution_system import PlanResolutionSystem
from backend.sim4.ecs.systems.social_update_system import SocialUpdateSystem


@dataclass
class DummyWorldViews:
    """
    Minimal dummy implementation of WorldViewsHandle for tests.
    """

    def get_room_bounds(self, room_id: int):
        _ = room_id
        return None


def make_minimal_world() -> ECSWorld:
    world = ECSWorld()

    components = [
        Transform(room_id=0, x=0.0, y=0.0, orientation=0.0),
        RoomPresence(room_id=0, time_in_room=0.0),
        ProfileTraits(
            introversion=0.5,
            volatility=0.5,
            conscientiousness=0.5,
            agreeableness=0.5,
            openness=0.5,
            risk_tolerance=0.5,
        ),
        PerceptionSubstrate(
            visible_agents=[],
            visible_assets=[],
            visible_rooms=[],
            proximity_scores={},
        ),
        AttentionSlots(
            focused_agent=None,
            focused_asset=None,
            focused_room=None,
            secondary_targets=[],
            distraction_level=0.0,
        ),
        SalienceState(agent_salience={}, topic_salience={}, location_salience={}),
        BeliefGraphSubstrate(nodes=[], edges=[], weights=[], last_updated_tick=0, source_tags=None),
        AgentInferenceState(pending_updates=0, last_inference_tick=0, uncertainty_score=0.0, epistemic_drift=0.0),
        SocialBeliefWeights(perceived_reputation={}, perceived_status={}, perceived_alignment={}),
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
        EmotionFields(
            tension=0.0,
            mood_valence=0.0,
            arousal=0.0,
            social_stress=0.0,
            excitement=0.0,
            boredom=0.0,
        ),
        MotiveSubstrate(active_motives=[], motive_strengths=[], last_update_tick=0),
        PlanLayerSubstrate(steps=[], current_index=0, plan_confidence=0.0, revision_needed=False),
        PathState(active=False, waypoints=[], current_index=0, progress_along_segment=0.0, path_valid=True),
        SocialSubstrate(relationship_to={}, trust_to={}, respect_to={}, resentment_to={}),
        SocialImpressionState(impression_code_to={}, misunderstanding_level_to={}),
        FactionAffinityState(faction_affinity={}, faction_loyalty={}),
        SelfModelSubstrate(identity_vector=[], self_consistency_pressure=0.0, contradiction_count=0, drift_score=0.0),
    ]

    world.create_entity(initial_components=components)
    return world


def make_system_context(world: ECSWorld) -> SystemContext:
    rng = SimulationRNG(seed=123)
    views: WorldViewsHandle = DummyWorldViews()
    commands = ECSCommandBuffer()
    return SystemContext(world=world, dt=0.1, rng=rng, views=views, commands=commands, tick_index=0)


@pytest.mark.parametrize(
    "system_cls",
    [
        PerceptionSystem,
        CognitivePreprocessor,
        EmotionGradientSystem,
        DriveUpdateSystem,
        MotiveFormationSystem,
        PlanResolutionSystem,
        SocialUpdateSystem,
    ],
)
def test_phase_bc_system_skeletons_run_without_error(system_cls):
    world = make_minimal_world()
    ctx = make_system_context(world)

    system = system_cls()
    # Should not raise
    system.run(ctx)
