from __future__ import annotations

import pytest

from backend.sim4.case_mbam import (
    AlibiMatrix,
    BenchEvidence,
    BestOutcomeRule,
    CafeEvidence,
    CaseState,
    CastOverlay,
    CharacterOverlay,
    CorridorEvidence,
    DisplayCaseEvidence,
    DropLocationEvidence,
    EvidencePlacement,
    HiddenCaseSlice,
    ResolutionRequirement,
    ResolutionRules,
    RoleAssignment,
    SceneGate,
    SceneGates,
    SoftFailRule,
    TimelineBeat,
    TruthGraph,
    TruthGraphEdge,
    TruthGraphNode,
    VisibleCaseSlice,
    get_seed_role_lock,
    make_default_cast_overlay,
    make_empty_case_state_shell,
    make_roles_assignment_from_seed_lock,
)


def test_shipped_seed_role_locks_match_project_lock() -> None:
    lock_a = get_seed_role_lock("A")
    assert lock_a.culprit == "outsider"
    assert lock_a.method == "delivery_cart_swap"
    assert lock_a.ally == "marc"

    lock_b = get_seed_role_lock("B")
    assert lock_b.culprit == "samira"
    assert lock_b.method == "badge_borrow"
    assert lock_b.ally == "jo"

    lock_c = get_seed_role_lock("C")
    assert lock_c.culprit == "laurent"
    assert lock_c.method == "case_left_unlatched"
    assert lock_c.ally == "elodie"


def test_make_empty_case_state_shell_builds_deterministic_shell() -> None:
    roles = make_roles_assignment_from_seed_lock(
        "B",
        misdirector="laurent",
        drop="coat_rack_pocket",
    )
    state = make_empty_case_state_shell(
        seed="B",
        difficulty_profile="D0",
        runtime_clock_start="2026-03-06T18:00:00-05:00",
        roles_assignment=roles,
    )

    assert state.case_id == "MBAM_01"
    assert state.seed == "B"
    assert state.roles_assignment.culprit == "samira"
    assert state.roles_assignment.method == "badge_borrow"
    assert state.timeline_schedule == ()
    assert state.truth_graph.nodes == ()
    assert state.truth_graph.edges == ()
    assert state.visible_case_slice.starting_scene_id == "S1"


def test_cast_overlay_rejects_invalid_role_slot_for_actor() -> None:
    with pytest.raises(ValueError):
        CastOverlay(
            elodie=CharacterOverlay(role_slot="DONOR", helpfulness="medium"),
            marc=CharacterOverlay(role_slot="GUARD", helpfulness="medium"),
            samira=CharacterOverlay(role_slot="INTERN", helpfulness="medium"),
            laurent=CharacterOverlay(role_slot="DONOR", helpfulness="medium"),
            jo=CharacterOverlay(role_slot="BARISTA", helpfulness="medium"),
            outsider=CharacterOverlay(role_slot="OUTSIDER", helpfulness="none"),
        )


def test_truth_graph_rejects_edges_with_unknown_nodes() -> None:
    with pytest.raises(ValueError):
        TruthGraph(
            nodes=(
                TruthGraphNode(
                    fact_id="N1",
                    type="time",
                    text="Missing item discovered around 18h05",
                    visibility="discoverable",
                ),
            ),
            edges=(
                TruthGraphEdge(
                    edge_id="E_BAD",
                    from_fact_id="N1",
                    to_fact_id="N2",
                    relation="supports",
                ),
            ),
        )


def test_case_state_rejects_unsorted_timeline_schedule() -> None:
    roles = RoleAssignment(
        culprit="outsider",
        ally="marc",
        misdirector="elodie",
        method="delivery_cart_swap",
        drop="corridor_bin",
    )

    with pytest.raises(ValueError):
        CaseState(
            seed="A",
            difficulty_profile="D1",
            runtime_clock_start="2026-03-06T18:00:00-05:00",
            cast_overlay=make_default_cast_overlay(),
            roles_assignment=roles,
            timeline_schedule=(
                TimelineBeat(
                    beat_id="T_PLUS_05",
                    time_offset_sec=300,
                    type="npc_move",
                    actor_id="marc",
                    location_id="security_office",
                ),
                TimelineBeat(
                    beat_id="T_PLUS_02",
                    time_offset_sec=120,
                    type="availability_change",
                    actor_id="elodie",
                    location_id="mbam_lobby",
                ),
            ),
            evidence_placement=EvidencePlacement(
                display_case=DisplayCaseEvidence(tampered=True, latch_condition="scratched"),
                bench=BenchEvidence(contains="none"),
                corridor=CorridorEvidence(contains=("lanyard_fiber",)),
                cafe=CafeEvidence(receipt_id="R1"),
                drop_location=DropLocationEvidence(
                    location_id="corridor_bin",
                    contains_medallion=True,
                ),
            ),
            alibi_matrix=AlibiMatrix(),
            truth_graph=TruthGraph(),
            scene_gates=SceneGates(
                S1=SceneGate(),
                S2=SceneGate(),
                S3=SceneGate(),
                S4=SceneGate(),
                S5=SceneGate(),
            ),
            resolution_rules=ResolutionRules(
                recovery_success=ResolutionRequirement(),
                accusation_success=ResolutionRequirement(),
                soft_fail=SoftFailRule(),
                best_outcome=BestOutcomeRule(),
            ),
            visible_case_slice=VisibleCaseSlice(starting_scene_id="S1"),
            hidden_case_slice=HiddenCaseSlice(),
        )
