from __future__ import annotations

"""Deterministic MBAM CaseState generator for shipped seeds A/B/C.

Phase 1B scope:
- provide canonical seed fixtures
- support explicit seed IDs and seed values
- generate deterministic role assignment + cast overlays + drop location

Non-goals in this chunk:
- full timeline/truth-graph generation
- object affordances / runtime integration
"""

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal, Final

from .models import (
    CaseState,
    CastOverlay,
    CharacterOverlay,
    DifficultyProfile,
    DropId,
    Helpfulness,
    MisdirectorId,
    RoleAssignment,
)
from .scaffold import (
    ShippedSeed,
    make_empty_case_state_shell,
    make_roles_assignment_from_seed_lock,
)


SeedInput = str | int

DEFAULT_RUNTIME_CLOCK_START: Final[str] = "2026-01-15T18:00:00-05:00"


@dataclass(frozen=True)
class MbamSeedFixture:
    seed_id: ShippedSeed
    misdirector: MisdirectorId
    drop: DropId
    default_difficulty_profile: DifficultyProfile = "D0"
    runtime_clock_start: str = DEFAULT_RUNTIME_CLOCK_START


# Canonical fixture table for Enqueteur v1.0 MBAM.
_SEED_FIXTURES: dict[ShippedSeed, MbamSeedFixture] = {
    "A": MbamSeedFixture(seed_id="A", misdirector="elodie", drop="corridor_bin"),
    "B": MbamSeedFixture(seed_id="B", misdirector="laurent", drop="cafe_bathroom_stash"),
    "C": MbamSeedFixture(seed_id="C", misdirector="samira", drop="coat_rack_pocket"),
}

_SEED_ORDER: tuple[ShippedSeed, ShippedSeed, ShippedSeed] = ("A", "B", "C")


def _normalize_seed_input(seed: SeedInput) -> str:
    if isinstance(seed, int):
        return str(seed)
    if not isinstance(seed, str):
        raise ValueError("seed must be str or int")
    normalized = seed.strip()
    if not normalized:
        raise ValueError("seed must be non-empty")
    return normalized


def resolve_seed_id(seed: SeedInput) -> ShippedSeed:
    """Resolve any explicit seed ID/value to canonical shipped seed A/B/C.

    Rules (deterministic):
    - explicit A/B/C (case-insensitive) maps directly
    - numeric values map by abs(value) % 3 over (A, B, C)
    - non-numeric strings map via sha256(byte[0]) % 3 over (A, B, C)
    """
    normalized = _normalize_seed_input(seed)
    upper = normalized.upper()
    if upper in _SEED_FIXTURES:
        return upper  # type: ignore[return-value]

    if normalized.lstrip("-").isdigit():
        idx = abs(int(normalized)) % len(_SEED_ORDER)
        return _SEED_ORDER[idx]

    idx = sha256(normalized.encode("utf-8")).digest()[0] % len(_SEED_ORDER)
    return _SEED_ORDER[idx]


def get_seed_fixture(seed: SeedInput) -> MbamSeedFixture:
    seed_id = resolve_seed_id(seed)
    return _SEED_FIXTURES[seed_id]


def _actor_slot_from_roles(
    *,
    actor_id: Literal["elodie", "marc", "samira", "laurent", "jo", "outsider"],
    roles: RoleAssignment,
) -> str:
    if actor_id == roles.ally:
        return "ALLY"
    if actor_id == roles.misdirector:
        return "MISDIRECTOR"
    if actor_id == roles.culprit:
        return "CULPRIT"

    baseline_slots: dict[str, str] = {
        "elodie": "CURATOR",
        "marc": "GUARD",
        "samira": "INTERN",
        "laurent": "DONOR",
        "jo": "BARISTA",
        "outsider": "OUTSIDER",
    }
    return baseline_slots[actor_id]


def _actor_helpfulness(
    *,
    actor_id: Literal["elodie", "marc", "samira", "laurent", "jo", "outsider"],
    roles: RoleAssignment,
) -> Helpfulness:
    if actor_id == "outsider":
        return "none"
    if actor_id == roles.ally:
        return "high"
    if actor_id == roles.culprit:
        return "low"
    if actor_id == roles.misdirector:
        return "low"
    return "medium"


def _build_actor_overlay(
    *,
    actor_id: Literal["elodie", "marc", "samira", "laurent", "jo", "outsider"],
    seed_id: ShippedSeed,
    roles: RoleAssignment,
) -> CharacterOverlay:
    role_slot = _actor_slot_from_roles(actor_id=actor_id, roles=roles)
    helpfulness = _actor_helpfulness(actor_id=actor_id, roles=roles)

    hidden_flags: list[str] = [f"seed_{seed_id}", f"slot_{role_slot.lower()}"]
    if actor_id == roles.culprit:
        hidden_flags.append(f"method_{roles.method}")
        hidden_flags.append(f"drop_{roles.drop}")

    knowledge_flags: list[str] = []
    if actor_id == roles.ally:
        knowledge_flags.append("ally_knows_partial_path")
    if actor_id == roles.misdirector:
        knowledge_flags.append("misdirector_controls_narrative")

    belief_flags: list[str] = []
    if actor_id == roles.misdirector:
        belief_flags.append("pushes_safe_explanation")

    misremember_flags: list[str] = []
    if actor_id == roles.misdirector:
        misremember_flags.append("time_fuzz_1")

    state_card_profile_id = None if actor_id == "outsider" else f"{actor_id}_{seed_id.lower()}_{role_slot.lower()}"

    return CharacterOverlay(
        role_slot=role_slot,
        helpfulness=helpfulness,
        knowledge_flags=tuple(knowledge_flags),
        belief_flags=tuple(belief_flags),
        hidden_flags=tuple(hidden_flags),
        misremember_flags=tuple(misremember_flags),
        state_card_profile_id=state_card_profile_id,
    )


def build_cast_overlay_for_seed(seed: SeedInput) -> CastOverlay:
    fixture = get_seed_fixture(seed)
    roles = make_roles_assignment_from_seed_lock(
        fixture.seed_id,
        misdirector=fixture.misdirector,
        drop=fixture.drop,
    )
    return CastOverlay(
        elodie=_build_actor_overlay(actor_id="elodie", seed_id=fixture.seed_id, roles=roles),
        marc=_build_actor_overlay(actor_id="marc", seed_id=fixture.seed_id, roles=roles),
        samira=_build_actor_overlay(actor_id="samira", seed_id=fixture.seed_id, roles=roles),
        laurent=_build_actor_overlay(actor_id="laurent", seed_id=fixture.seed_id, roles=roles),
        jo=_build_actor_overlay(actor_id="jo", seed_id=fixture.seed_id, roles=roles),
        outsider=_build_actor_overlay(actor_id="outsider", seed_id=fixture.seed_id, roles=roles),
    )


def build_role_assignment_for_seed(seed: SeedInput) -> RoleAssignment:
    fixture = get_seed_fixture(seed)
    return make_roles_assignment_from_seed_lock(
        fixture.seed_id,
        misdirector=fixture.misdirector,
        drop=fixture.drop,
    )


def generate_case_state(
    seed: SeedInput,
    *,
    difficulty_profile: DifficultyProfile | None = None,
    runtime_clock_start: str | None = None,
) -> CaseState:
    """Generate deterministic MBAM CaseState for a seed ID/value."""
    fixture = get_seed_fixture(seed)
    roles = build_role_assignment_for_seed(fixture.seed_id)
    cast_overlay = build_cast_overlay_for_seed(fixture.seed_id)

    return make_empty_case_state_shell(
        seed=fixture.seed_id,
        difficulty_profile=difficulty_profile or fixture.default_difficulty_profile,
        runtime_clock_start=runtime_clock_start or fixture.runtime_clock_start,
        roles_assignment=roles,
        cast_overlay=cast_overlay,
        medallion_at_drop=True,
    )


def generate_case_state_for_seed_id(
    seed_id: ShippedSeed,
    *,
    difficulty_profile: DifficultyProfile | None = None,
    runtime_clock_start: str | None = None,
) -> CaseState:
    """Typed convenience wrapper for explicit canonical seed IDs A/B/C."""
    return generate_case_state(
        seed_id,
        difficulty_profile=difficulty_profile,
        runtime_clock_start=runtime_clock_start,
    )


__all__ = [
    "DEFAULT_RUNTIME_CLOCK_START",
    "MbamSeedFixture",
    "SeedInput",
    "build_cast_overlay_for_seed",
    "build_role_assignment_for_seed",
    "generate_case_state",
    "generate_case_state_for_seed_id",
    "get_seed_fixture",
    "resolve_seed_id",
]
