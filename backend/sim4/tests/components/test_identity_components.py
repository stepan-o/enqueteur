from __future__ import annotations

from backend.sim4.ecs.components.identity import (
    AgentIdentity,
    ProfileTraits,
    SelfModelSubstrate,
    PersonaSubstrate,
)
from backend.sim4.ecs.entity import EntityID


def test_agent_identity_instantiation():
    eid: EntityID = 1
    identity = AgentIdentity(
        id=eid,
        canonical_name_id=123,
        role_code=2,
        generation=0,
        seed=999,
    )
    assert identity.id == eid
    assert identity.canonical_name_id == 123
    assert identity.role_code == 2
    assert identity.generation == 0
    assert identity.seed == 999


def test_profile_traits_instantiation():
    traits = ProfileTraits(
        introversion=0.2,
        volatility=0.3,
        conscientiousness=0.8,
        agreeableness=0.7,
        openness=0.9,
        risk_tolerance=0.4,
    )
    assert traits.openness == 0.9
    assert traits.risk_tolerance == 0.4


def test_self_model_and_persona_instantiation():
    identity_vec = [0.1, 0.2, 0.3]
    self_model = SelfModelSubstrate(
        identity_vector=identity_vec,
        self_consistency_pressure=0.5,
        contradiction_count=1,
        drift_score=0.05,
    )
    assert self_model.identity_vector is identity_vec
    assert self_model.contradiction_count == 1

    persona = PersonaSubstrate(
        style_vector=[1.0, 0.0],
        symbol_affinity_vector=[0.5, 0.5],
        expressiveness=0.7,
        voice_register=0.3,
    )
    assert persona.style_vector == [1.0, 0.0]
    assert persona.expressiveness == 0.7
