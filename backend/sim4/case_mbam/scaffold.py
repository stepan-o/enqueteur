from __future__ import annotations

"""Minimal MBAM Case Truth scaffolding for Phase 1A.

Scope in this chunk:
- lock shipped seed role constraints (A/B/C)
- provide deterministic constructors for empty CaseState shells
- avoid full seed generation or runtime integration
"""

from dataclasses import dataclass
from typing import Literal

from .models import (
    AlibiMatrix,
    AllyId,
    BenchEvidence,
    BestOutcomeRule,
    CafeEvidence,
    CaseState,
    CastOverlay,
    CharacterOverlay,
    CorridorEvidence,
    CulpritId,
    DifficultyProfile,
    DisplayCaseEvidence,
    DropId,
    DropLocationEvidence,
    EvidencePlacement,
    HiddenCaseSlice,
    MethodId,
    MisdirectorId,
    ResolutionRequirement,
    ResolutionRules,
    RoleAssignment,
    SceneGate,
    SceneGates,
    SoftFailRule,
    TruthGraph,
    VisibleCaseSlice,
)


ShippedSeed = Literal["A", "B", "C"]


@dataclass(frozen=True)
class SeedRoleLock:
    culprit: CulpritId
    method: MethodId
    ally: AllyId


_SHIPPED_SEED_ROLE_LOCKS: dict[ShippedSeed, SeedRoleLock] = {
    "A": SeedRoleLock(culprit="outsider", method="delivery_cart_swap", ally="marc"),
    "B": SeedRoleLock(culprit="samira", method="badge_borrow", ally="jo"),
    "C": SeedRoleLock(culprit="laurent", method="case_left_unlatched", ally="elodie"),
}


def get_seed_role_lock(seed: str) -> SeedRoleLock:
    """Return the shipped locked role tuple for seed A/B/C."""
    if seed not in _SHIPPED_SEED_ROLE_LOCKS:
        raise ValueError(f"Unsupported MBAM shipped seed: {seed!r}; expected one of A/B/C")
    return _SHIPPED_SEED_ROLE_LOCKS[seed]  # type: ignore[index]


def make_roles_assignment_from_seed_lock(
    seed: str,
    *,
    misdirector: MisdirectorId,
    drop: DropId,
) -> RoleAssignment:
    """Construct a full RoleAssignment from locked seed values + explicit remaining slots."""
    lock = get_seed_role_lock(seed)
    return RoleAssignment(
        culprit=lock.culprit,
        ally=lock.ally,
        misdirector=misdirector,
        method=lock.method,
        drop=drop,
    )


def make_default_cast_overlay() -> CastOverlay:
    """Create MBAM baseline cast overlay shells.

    This helper provides deterministic role-slot defaults only. Knowledge/belief/
    hidden flags remain empty until full case generation is added.
    """
    return CastOverlay(
        elodie=CharacterOverlay(
            role_slot="CURATOR",
            helpfulness="medium",
            state_card_profile_id="elodie_default",
        ),
        marc=CharacterOverlay(
            role_slot="GUARD",
            helpfulness="medium",
            state_card_profile_id="marc_default",
        ),
        samira=CharacterOverlay(
            role_slot="INTERN",
            helpfulness="medium",
            state_card_profile_id="samira_default",
        ),
        laurent=CharacterOverlay(
            role_slot="DONOR",
            helpfulness="medium",
            state_card_profile_id="laurent_default",
        ),
        jo=CharacterOverlay(
            role_slot="BARISTA",
            helpfulness="medium",
            state_card_profile_id="jo_default",
        ),
        outsider=CharacterOverlay(
            role_slot="OUTSIDER",
            helpfulness="none",
            state_card_profile_id=None,
        ),
    )


def make_empty_case_state_shell(
    *,
    seed: str,
    difficulty_profile: DifficultyProfile,
    runtime_clock_start: str,
    roles_assignment: RoleAssignment,
) -> CaseState:
    """Build a deterministic MBAM CaseState shell without generation logic.

    This is intentionally narrow scaffolding for Phase 1A. It gives later seed
    generation code a stable target schema while keeping world/case boundaries
    explicit.
    """
    return CaseState(
        seed=seed,
        difficulty_profile=difficulty_profile,
        runtime_clock_start=runtime_clock_start,
        cast_overlay=make_default_cast_overlay(),
        roles_assignment=roles_assignment,
        timeline_schedule=(),
        evidence_placement=EvidencePlacement(
            display_case=DisplayCaseEvidence(tampered=False, latch_condition="intact"),
            bench=BenchEvidence(contains="none"),
            corridor=CorridorEvidence(contains=()),
            cafe=CafeEvidence(receipt_id=None),
            drop_location=DropLocationEvidence(
                location_id=roles_assignment.drop,
                contains_medallion=False,
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


__all__ = [
    "SeedRoleLock",
    "ShippedSeed",
    "get_seed_role_lock",
    "make_roles_assignment_from_seed_lock",
    "make_default_cast_overlay",
    "make_empty_case_state_shell",
]
