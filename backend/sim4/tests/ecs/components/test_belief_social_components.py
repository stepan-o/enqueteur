from __future__ import annotations

from backend.sim4.ecs.components.belief import (
    BeliefGraphSubstrate,
    AgentInferenceState,
    SocialBeliefWeights,
)
from backend.sim4.ecs.components.social import (
    SocialSubstrate,
    SocialImpressionState,
    FactionAffinityState,
)
from backend.sim4.ecs.entity import EntityID


def test_belief_graph_substrate_instantiation():
    nodes = [10, 20, 30]
    edges = [(0, 1), (1, 2)]
    weights = [0.5, 0.8]
    source_tags = [1, 2]

    belief = BeliefGraphSubstrate(
        nodes=nodes,
        edges=edges,
        weights=weights,
        last_updated_tick=42,
        source_tags=source_tags,
    )

    assert belief.nodes == nodes
    assert belief.edges == edges
    assert belief.weights == weights
    assert belief.last_updated_tick == 42
    assert belief.source_tags == source_tags
    # basic sanity: edges and weights lengths align
    assert len(belief.edges) == len(belief.weights)


def test_agent_inference_state_instantiation():
    state = AgentInferenceState(
        pending_updates=3,
        last_inference_tick=7,
        uncertainty_score=0.4,
        epistemic_drift=0.1,
    )
    assert state.pending_updates == 3
    assert state.last_inference_tick == 7
    assert state.uncertainty_score == 0.4
    assert state.epistemic_drift == 0.1


def test_social_belief_weights_instantiation():
    e1: EntityID = 1
    e2: EntityID = 2

    weights = SocialBeliefWeights(
        perceived_reputation={e1: 0.9, e2: 0.3},
        perceived_status={e1: 0.7, e2: 0.5},
        perceived_alignment={e1: 1.0, e2: -0.5},
    )

    assert weights.perceived_reputation[e1] == 0.9
    assert weights.perceived_status[e2] == 0.5
    assert weights.perceived_alignment[e2] == -0.5


def test_social_substrate_and_impressions_instantiation():
    a: EntityID = 1
    b: EntityID = 2

    social = SocialSubstrate(
        relationship_to={a: 0.8, b: -0.2},
        trust_to={a: 0.9},
        respect_to={a: 0.6},
        resentment_to={b: 0.4},
    )
    assert social.relationship_to[a] == 0.8
    assert social.resentment_to[b] == 0.4

    impressions = SocialImpressionState(
        impression_code_to={a: 10, b: 20},
        misunderstanding_level_to={a: 0.2, b: 0.7},
    )
    assert impressions.impression_code_to[b] == 20
    assert impressions.misunderstanding_level_to[b] == 0.7


def test_faction_affinity_state_instantiation():
    factions_aff = {1: 0.5, 2: -0.3}
    factions_loyal = {1: 0.9, 2: 0.1}

    fas = FactionAffinityState(
        faction_affinity=factions_aff,
        faction_loyalty=factions_loyal,
    )
    assert fas.faction_affinity[1] == 0.5
    assert fas.faction_loyalty[2] == 0.1
