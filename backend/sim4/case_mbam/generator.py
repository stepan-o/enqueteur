from __future__ import annotations

"""Deterministic MBAM CaseState generator for shipped seeds A/B/C.

Phase 1B/1C scope:
- provide canonical seed fixtures
- support explicit seed IDs and seed values
- generate deterministic role assignment + cast overlays
- generate deterministic timeline, alibi matrix, evidence placement, and truth graph

Non-goals in this chunk:
- object affordances execution
- dialogue/runtime integration
"""

from dataclasses import dataclass
from dataclasses import replace
from hashlib import sha256
from typing import Literal, Final

from .models import (
    AlibiClaim,
    AlibiMatrix,
    BenchEvidence,
    CafeEvidence,
    CaseState,
    CastOverlay,
    CharacterOverlay,
    CorridorEvidence,
    DifficultyProfile,
    DisplayCaseEvidence,
    DropId,
    DropLocationEvidence,
    EvidencePlacement,
    Helpfulness,
    MisdirectorId,
    RoleAssignment,
    TimelineBeat,
    TruthGraph,
    TruthGraphEdge,
    TruthGraphNode,
    VisibleCaseSlice,
    HiddenCaseSlice,
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
    donor_event_mode: Literal["appears", "calls"]
    vitrine_latch_condition: Literal["intact", "scratched", "loose"]
    bench_contains: Literal["none", "torn_note_fragment", "receipt_fragment"]
    corridor_contains: tuple[Literal["none", "lanyard_fiber", "sticker", "cart_trace"], ...]
    cafe_receipt_id: str
    witness_clothing: str
    torn_note_hint: str
    default_difficulty_profile: DifficultyProfile = "D0"
    runtime_clock_start: str = DEFAULT_RUNTIME_CLOCK_START


# Canonical fixture table for Enqueteur v1.0 MBAM.
_SEED_FIXTURES: dict[ShippedSeed, MbamSeedFixture] = {
    "A": MbamSeedFixture(
        seed_id="A",
        misdirector="elodie",
        drop="corridor_bin",
        donor_event_mode="calls",
        vitrine_latch_condition="scratched",
        bench_contains="torn_note_fragment",
        corridor_contains=("cart_trace", "sticker"),
        cafe_receipt_id="R-A-1752",
        witness_clothing="manteau beige, casquette sombre",
        torn_note_hint="chariot de livraison vers 17h58",
    ),
    "B": MbamSeedFixture(
        seed_id="B",
        misdirector="laurent",
        drop="cafe_bathroom_stash",
        donor_event_mode="appears",
        vitrine_latch_condition="intact",
        bench_contains="receipt_fragment",
        corridor_contains=("lanyard_fiber",),
        cafe_receipt_id="R-B-1752",
        witness_clothing="hoodie bleu et badge visiteur",
        torn_note_hint="prêt de badge avant dix-huit heures",
    ),
    "C": MbamSeedFixture(
        seed_id="C",
        misdirector="samira",
        drop="coat_rack_pocket",
        donor_event_mode="appears",
        vitrine_latch_condition="loose",
        bench_contains="torn_note_fragment",
        corridor_contains=("sticker",),
        cafe_receipt_id="R-C-1752",
        witness_clothing="écharpe bordeaux, manteau charbon",
        torn_note_hint="vitrine laissée entre-ouverte près de 17h58",
    ),
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


def _build_timeline_schedule(fixture: MbamSeedFixture, roles: RoleAssignment) -> tuple[TimelineBeat, ...]:
    donor_location = "MBAM_LOBBY" if fixture.donor_event_mode == "appears" else "PHONE_REMOTE"
    donor_effect = "donor_arrives_on_site" if fixture.donor_event_mode == "appears" else "donor_calls_front_desk"

    intern_location = "SERVICE_CORRIDOR" if roles.culprit == "samira" else "GALLERY_AFFICHES"
    intern_effect = "intern_nervous_movement" if roles.culprit == "samira" else "intern_restock_pass"

    archive_effect = f"terminal_archived_access_friction_{fixture.seed_id.lower()}"

    return (
        TimelineBeat(
            beat_id="T_PLUS_00_ARRIVAL",
            time_offset_sec=0,
            type="availability_change",
            actor_id="player",
            location_id="MBAM_LOBBY",
            effects=("medallion_already_missing",),
        ),
        TimelineBeat(
            beat_id="T_PLUS_02_CURATOR_CONTAINMENT",
            time_offset_sec=120,
            type="availability_change",
            actor_id="elodie",
            location_id="MBAM_LOBBY",
            effects=("curator_containment_mode",),
        ),
        TimelineBeat(
            beat_id="T_PLUS_05_GUARD_PATROL_SHIFT",
            time_offset_sec=300,
            type="npc_move",
            actor_id="marc",
            location_id="SECURITY_OFFICE",
            effects=("guard_patrol_position_change",),
        ),
        TimelineBeat(
            beat_id="T_PLUS_08_INTERN_MOVEMENT",
            time_offset_sec=480,
            type="npc_move",
            actor_id="samira",
            location_id=intern_location,
            effects=(intern_effect,),
        ),
        TimelineBeat(
            beat_id="T_PLUS_10_DONOR_EVENT",
            time_offset_sec=600,
            type="availability_change",
            actor_id="laurent",
            location_id=donor_location,
            effects=(donor_effect,),
        ),
        TimelineBeat(
            beat_id="T_PLUS_12_BARISTA_WITNESS_WINDOW",
            time_offset_sec=720,
            type="witness_window",
            actor_id="jo",
            location_id="CAFE_DE_LA_RUE",
            effects=("witness_signal_strongest",),
        ),
        TimelineBeat(
            beat_id="T_PLUS_15_TERMINAL_ARCHIVE",
            time_offset_sec=900,
            type="archive_event",
            actor_id="marc",
            location_id="SECURITY_OFFICE",
            effects=("terminal_log_archival", "access_friction_increased", archive_effect),
        ),
    )


def _build_alibi_matrix(roles: RoleAssignment) -> AlibiMatrix:
    elodie_truth: Literal["true", "false", "partial"] = "partial" if roles.ally == "elodie" else "true"
    samira_truth: Literal["true", "false", "partial"] = "false" if roles.culprit == "samira" else "partial"
    laurent_truth: Literal["true", "false", "partial"] = "false" if roles.culprit == "laurent" else "partial"
    marc_truth: Literal["true", "false", "partial"] = "partial" if roles.ally == "marc" else "true"
    jo_truth: Literal["true", "false", "partial"] = "partial" if roles.ally == "jo" else "true"

    return AlibiMatrix(
        elodie=(
            AlibiClaim(
                time_window="17h56-18h06",
                location_claim="MBAM Lobby",
                truth_value=elodie_truth,
                evidence_support=("N1", "N7"),
            ),
        ),
        marc=(
            AlibiClaim(
                time_window="17h57-18h07",
                location_claim="Security Office",
                truth_value=marc_truth,
                evidence_support=("N2", "N3"),
            ),
        ),
        samira=(
            AlibiClaim(
                time_window="17h54-18h02",
                location_claim="Service Corridor",
                truth_value=samira_truth,
                evidence_support=("N3", "N6"),
            ),
        ),
        laurent=(
            AlibiClaim(
                time_window="17h50-18h01",
                location_claim="Café de la Rue / MBAM Lobby",
                truth_value=laurent_truth,
                evidence_support=("N4", "N5"),
            ),
        ),
        jo=(
            AlibiClaim(
                time_window="17h50-18h00",
                location_claim="Café de la Rue",
                truth_value=jo_truth,
                evidence_support=("N4", "N5"),
            ),
        ),
    )


def _build_evidence_placement(fixture: MbamSeedFixture, roles: RoleAssignment) -> EvidencePlacement:
    return EvidencePlacement(
        display_case=DisplayCaseEvidence(
            tampered=True,
            latch_condition=fixture.vitrine_latch_condition,
        ),
        bench=BenchEvidence(contains=fixture.bench_contains),
        corridor=CorridorEvidence(contains=fixture.corridor_contains),
        cafe=CafeEvidence(receipt_id=fixture.cafe_receipt_id),
        drop_location=DropLocationEvidence(
            location_id=roles.drop,
            contains_medallion=True,
        ),
    )


def _build_truth_graph(fixture: MbamSeedFixture, roles: RoleAssignment) -> TruthGraph:
    nodes = (
        TruthGraphNode(
            fact_id="N1",
            type="time",
            text="Objet manquant constaté vers 18h05.",
            visibility="public",
            source_ids=("S1",),
            unlock_conditions=("scene:S1",),
        ),
        TruthGraphNode(
            fact_id="N2",
            type="access",
            text="Un badge du personnel est requis pour le corridor.",
            visibility="discoverable",
            source_ids=("O6", "S2"),
            unlock_conditions=("scene:S2",),
        ),
        TruthGraphNode(
            fact_id="N3",
            type="time",
            text="Un passage badge est journalisé à 17h58.",
            visibility="discoverable",
            source_ids=("O6",),
            unlock_conditions=("action:view_badge_logs",),
        ),
        TruthGraphNode(
            fact_id="N4",
            type="time",
            text="Un reçu café est horodaté à 17h52.",
            visibility="discoverable",
            source_ids=("O9",),
            unlock_conditions=("action:read_receipt",),
        ),
        TruthGraphNode(
            fact_id="N5",
            type="text",
            text=f"Témoin: tenue observée '{fixture.witness_clothing}'.",
            visibility="discoverable",
            source_ids=("S4",),
            unlock_conditions=("scene:S4",),
        ),
        TruthGraphNode(
            fact_id="N6",
            type="text",
            text=f"Note déchirée: indice direction/temps '{fixture.torn_note_hint}'.",
            visibility="discoverable",
            source_ids=("E1",),
            unlock_conditions=("action:reconstruct_torn_note",),
        ),
        TruthGraphNode(
            fact_id="N7",
            type="method",
            text="Indice vitrine: état de loquet compatible avec une extraction rapide.",
            visibility="discoverable",
            source_ids=("O1",),
            unlock_conditions=("action:check_vitrine_lock",),
        ),
        TruthGraphNode(
            fact_id="N8",
            type="location",
            text=f"Indice dépôt: piste vers '{roles.drop}'.",
            visibility="hidden",
            source_ids=("N3", "N4", "N5", "N6", "N7"),
            unlock_conditions=("need:N3", "need:N4", "need:contradiction_time_path"),
        ),
    )

    edges = (
        TruthGraphEdge(edge_id="E1", from_fact_id="N1", to_fact_id="N7", relation="supports"),
        TruthGraphEdge(edge_id="E2", from_fact_id="N2", to_fact_id="N3", relation="narrows"),
        TruthGraphEdge(edge_id="E3", from_fact_id="N3", to_fact_id="N4", relation="contradicts"),
        TruthGraphEdge(edge_id="E4", from_fact_id="N4", to_fact_id="N8", relation="unlocks"),
        TruthGraphEdge(edge_id="E5", from_fact_id="N5", to_fact_id="N8", relation="narrows"),
        TruthGraphEdge(edge_id="E6", from_fact_id="N6", to_fact_id="N8", relation="supports"),
        TruthGraphEdge(edge_id="E7", from_fact_id="N7", to_fact_id="N8", relation="narrows"),
    )
    return TruthGraph(nodes=nodes, edges=edges)


def _build_visible_case_slice() -> VisibleCaseSlice:
    return VisibleCaseSlice(
        public_room_ids=("MBAM_LOBBY", "GALLERY_AFFICHES", "CAFE_DE_LA_RUE"),
        public_object_ids=("O1_DISPLAY_CASE", "O3_WALL_LABEL", "O5_VISITOR_LOGBOOK", "O9_RECEIPT_PRINTER"),
        starting_scene_id="S1",
        starting_known_fact_ids=("N1",),
    )


def _build_hidden_case_slice(seed_id: ShippedSeed, roles: RoleAssignment) -> HiddenCaseSlice:
    return HiddenCaseSlice(
        private_fact_ids=("N8",),
        private_overlay_flags=(
            f"seed_{seed_id}",
            f"culprit_{roles.culprit}",
            f"drop_{roles.drop}",
            f"method_{roles.method}",
        ),
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

    base = make_empty_case_state_shell(
        seed=fixture.seed_id,
        difficulty_profile=difficulty_profile or fixture.default_difficulty_profile,
        runtime_clock_start=runtime_clock_start or fixture.runtime_clock_start,
        roles_assignment=roles,
        cast_overlay=cast_overlay,
        medallion_at_drop=True,
    )
    return replace(
        base,
        timeline_schedule=_build_timeline_schedule(fixture, roles),
        evidence_placement=_build_evidence_placement(fixture, roles),
        alibi_matrix=_build_alibi_matrix(roles),
        truth_graph=_build_truth_graph(fixture, roles),
        visible_case_slice=_build_visible_case_slice(),
        hidden_case_slice=_build_hidden_case_slice(fixture.seed_id, roles),
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
