from __future__ import annotations

"""MBAM Case Truth canonical data models.

This module is the deterministic, non-physical truth layer for Enqueteur v1.0
Case 1 (MBAM). It intentionally does not import world/runtime/frontend modules.

Boundary:
- World Truth (rooms, objects, doors, positions, clock) stays in backend.sim4.world.
- Case Truth (culprit, overlays, evidence graph, scene gates, resolution rules)
  is defined here.
"""

from dataclasses import dataclass
from typing import Literal


DifficultyProfile = Literal["D0", "D1"]

Helpfulness = Literal["none", "low", "medium", "high"]

CulpritId = Literal["samira", "laurent", "outsider"]
AllyId = Literal["marc", "jo", "elodie"]
MisdirectorId = Literal["elodie", "samira", "laurent"]
MethodId = Literal["badge_borrow", "case_left_unlatched", "delivery_cart_swap"]
DropId = Literal["cafe_bathroom_stash", "corridor_bin", "coat_rack_pocket"]

TimelineBeatType = Literal[
    "npc_move",
    "availability_change",
    "evidence_shift",
    "access_change",
    "witness_window",
    "archive_event",
]

TruthNodeType = Literal["access", "time", "text", "contradiction", "location", "method"]
TruthVisibility = Literal["hidden", "discoverable", "public"]
TruthEdgeRelation = Literal["supports", "contradicts", "narrows", "unlocks"]

SceneId = Literal["S1", "S2", "S3", "S4", "S5"]

SceneCompletionState = Literal["locked", "available", "in_progress", "completed", "failed_soft"]

AlibiTruthValue = Literal["true", "false", "partial"]


def _tupleize(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    out = tuple(values)
    for v in out:
        if not isinstance(v, str) or not v:
            raise ValueError("String flag values must be non-empty strings")
    return out


@dataclass(frozen=True)
class CharacterOverlay:
    role_slot: str
    helpfulness: Helpfulness
    knowledge_flags: tuple[str, ...] = ()
    belief_flags: tuple[str, ...] = ()
    hidden_flags: tuple[str, ...] = ()
    misremember_flags: tuple[str, ...] = ()
    state_card_profile_id: str | None = None

    def __post_init__(self) -> None:
        if not self.role_slot:
            raise ValueError("CharacterOverlay.role_slot must be non-empty")
        object.__setattr__(self, "knowledge_flags", _tupleize(self.knowledge_flags))
        object.__setattr__(self, "belief_flags", _tupleize(self.belief_flags))
        object.__setattr__(self, "hidden_flags", _tupleize(self.hidden_flags))
        object.__setattr__(self, "misremember_flags", _tupleize(self.misremember_flags))


_ALLOWED_ROLE_SLOTS_BY_CHARACTER: dict[str, set[str]] = {
    "elodie": {"CURATOR", "MISDIRECTOR", "ALLY"},
    "marc": {"GUARD", "ALLY"},
    "samira": {"INTERN", "CULPRIT", "MISDIRECTOR"},
    "laurent": {"DONOR", "CULPRIT", "MISDIRECTOR"},
    "jo": {"BARISTA", "ALLY"},
    "outsider": {"OUTSIDER", "CULPRIT"},
}


@dataclass(frozen=True)
class CastOverlay:
    elodie: CharacterOverlay
    marc: CharacterOverlay
    samira: CharacterOverlay
    laurent: CharacterOverlay
    jo: CharacterOverlay
    outsider: CharacterOverlay

    def __post_init__(self) -> None:
        self._validate_actor("elodie", self.elodie)
        self._validate_actor("marc", self.marc)
        self._validate_actor("samira", self.samira)
        self._validate_actor("laurent", self.laurent)
        self._validate_actor("jo", self.jo)
        self._validate_actor("outsider", self.outsider)

        if self.outsider.helpfulness != "none":
            raise ValueError("outsider.helpfulness must be 'none'")

    @staticmethod
    def _validate_actor(actor_id: str, overlay: CharacterOverlay) -> None:
        allowed = _ALLOWED_ROLE_SLOTS_BY_CHARACTER[actor_id]
        if overlay.role_slot not in allowed:
            raise ValueError(
                f"Invalid role_slot '{overlay.role_slot}' for {actor_id}; expected one of {sorted(allowed)}"
            )


@dataclass(frozen=True)
class RoleAssignment:
    culprit: CulpritId
    ally: AllyId
    misdirector: MisdirectorId
    method: MethodId
    drop: DropId


@dataclass(frozen=True)
class TimelineBeat:
    beat_id: str
    time_offset_sec: int
    type: TimelineBeatType
    actor_id: str | None
    location_id: str | None
    preconditions: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.beat_id:
            raise ValueError("TimelineBeat.beat_id must be non-empty")
        if self.time_offset_sec < 0:
            raise ValueError("TimelineBeat.time_offset_sec must be >= 0")
        object.__setattr__(self, "preconditions", _tupleize(self.preconditions))
        object.__setattr__(self, "effects", _tupleize(self.effects))


@dataclass(frozen=True)
class DisplayCaseEvidence:
    tampered: bool
    latch_condition: Literal["intact", "scratched", "loose"]


@dataclass(frozen=True)
class BenchEvidence:
    contains: Literal["none", "torn_note_fragment", "receipt_fragment"]


@dataclass(frozen=True)
class CorridorEvidence:
    contains: tuple[Literal["none", "lanyard_fiber", "sticker", "cart_trace"], ...] = ()


@dataclass(frozen=True)
class CafeEvidence:
    receipt_id: str | None


@dataclass(frozen=True)
class DropLocationEvidence:
    location_id: DropId
    contains_medallion: bool


@dataclass(frozen=True)
class EvidencePlacement:
    display_case: DisplayCaseEvidence
    bench: BenchEvidence
    corridor: CorridorEvidence
    cafe: CafeEvidence
    drop_location: DropLocationEvidence


@dataclass(frozen=True)
class AlibiClaim:
    time_window: str
    location_claim: str
    truth_value: AlibiTruthValue
    evidence_support: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.time_window:
            raise ValueError("AlibiClaim.time_window must be non-empty")
        if not self.location_claim:
            raise ValueError("AlibiClaim.location_claim must be non-empty")
        object.__setattr__(self, "evidence_support", _tupleize(self.evidence_support))


@dataclass(frozen=True)
class AlibiMatrix:
    elodie: tuple[AlibiClaim, ...] = ()
    marc: tuple[AlibiClaim, ...] = ()
    samira: tuple[AlibiClaim, ...] = ()
    laurent: tuple[AlibiClaim, ...] = ()
    jo: tuple[AlibiClaim, ...] = ()


@dataclass(frozen=True)
class TruthGraphNode:
    fact_id: str
    type: TruthNodeType
    text: str
    visibility: TruthVisibility
    source_ids: tuple[str, ...] = ()
    unlock_conditions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.fact_id:
            raise ValueError("TruthGraphNode.fact_id must be non-empty")
        if not self.text:
            raise ValueError("TruthGraphNode.text must be non-empty")
        object.__setattr__(self, "source_ids", _tupleize(self.source_ids))
        object.__setattr__(self, "unlock_conditions", _tupleize(self.unlock_conditions))


@dataclass(frozen=True)
class TruthGraphEdge:
    edge_id: str
    from_fact_id: str
    to_fact_id: str
    relation: TruthEdgeRelation

    def __post_init__(self) -> None:
        if not self.edge_id:
            raise ValueError("TruthGraphEdge.edge_id must be non-empty")
        if not self.from_fact_id or not self.to_fact_id:
            raise ValueError("TruthGraphEdge fact ids must be non-empty")


@dataclass(frozen=True)
class TruthGraph:
    nodes: tuple[TruthGraphNode, ...] = ()
    edges: tuple[TruthGraphEdge, ...] = ()

    def __post_init__(self) -> None:
        node_ids = [n.fact_id for n in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("TruthGraph.nodes contains duplicate fact_id values")

        edge_ids = [e.edge_id for e in self.edges]
        if len(edge_ids) != len(set(edge_ids)):
            raise ValueError("TruthGraph.edges contains duplicate edge_id values")

        node_id_set = set(node_ids)
        for edge in self.edges:
            if edge.from_fact_id not in node_id_set:
                raise ValueError(f"TruthGraph edge references unknown from_fact_id: {edge.from_fact_id}")
            if edge.to_fact_id not in node_id_set:
                raise ValueError(f"TruthGraph edge references unknown to_fact_id: {edge.to_fact_id}")


@dataclass(frozen=True)
class SceneGate:
    required_fact_ids: tuple[str, ...] = ()
    required_items: tuple[str, ...] = ()
    trust_threshold: float | None = None
    time_window: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_fact_ids", _tupleize(self.required_fact_ids))
        object.__setattr__(self, "required_items", _tupleize(self.required_items))
        if self.trust_threshold is not None and self.trust_threshold < 0:
            raise ValueError("SceneGate.trust_threshold must be >= 0 when set")


@dataclass(frozen=True)
class SceneGates:
    S1: SceneGate
    S2: SceneGate
    S3: SceneGate
    S4: SceneGate
    S5: SceneGate


@dataclass(frozen=True)
class ResolutionRequirement:
    required_fact_ids: tuple[str, ...] = ()
    required_items: tuple[str, ...] = ()
    required_actions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_fact_ids", _tupleize(self.required_fact_ids))
        object.__setattr__(self, "required_items", _tupleize(self.required_items))
        object.__setattr__(self, "required_actions", _tupleize(self.required_actions))


@dataclass(frozen=True)
class SoftFailRule:
    trigger_conditions: tuple[str, ...] = ()
    outcome_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "trigger_conditions", _tupleize(self.trigger_conditions))
        object.__setattr__(self, "outcome_flags", _tupleize(self.outcome_flags))


@dataclass(frozen=True)
class BestOutcomeRule:
    required_fact_ids: tuple[str, ...] = ()
    required_items: tuple[str, ...] = ()
    required_actions: tuple[str, ...] = ()
    required_relationship_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_fact_ids", _tupleize(self.required_fact_ids))
        object.__setattr__(self, "required_items", _tupleize(self.required_items))
        object.__setattr__(self, "required_actions", _tupleize(self.required_actions))
        object.__setattr__(self, "required_relationship_flags", _tupleize(self.required_relationship_flags))


@dataclass(frozen=True)
class ResolutionRules:
    recovery_success: ResolutionRequirement
    accusation_success: ResolutionRequirement
    soft_fail: SoftFailRule
    best_outcome: BestOutcomeRule


@dataclass(frozen=True)
class VisibleCaseSlice:
    public_room_ids: tuple[str, ...] = ()
    public_object_ids: tuple[str, ...] = ()
    starting_scene_id: SceneId = "S1"
    starting_known_fact_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "public_room_ids", _tupleize(self.public_room_ids))
        object.__setattr__(self, "public_object_ids", _tupleize(self.public_object_ids))
        object.__setattr__(self, "starting_known_fact_ids", _tupleize(self.starting_known_fact_ids))


@dataclass(frozen=True)
class HiddenCaseSlice:
    private_fact_ids: tuple[str, ...] = ()
    private_overlay_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "private_fact_ids", _tupleize(self.private_fact_ids))
        object.__setattr__(self, "private_overlay_flags", _tupleize(self.private_overlay_flags))


@dataclass(frozen=True)
class CaseState:
    seed: str
    difficulty_profile: DifficultyProfile
    runtime_clock_start: str
    cast_overlay: CastOverlay
    roles_assignment: RoleAssignment
    timeline_schedule: tuple[TimelineBeat, ...]
    evidence_placement: EvidencePlacement
    alibi_matrix: AlibiMatrix
    truth_graph: TruthGraph
    scene_gates: SceneGates
    resolution_rules: ResolutionRules
    visible_case_slice: VisibleCaseSlice
    hidden_case_slice: HiddenCaseSlice
    case_id: Literal["MBAM_01"] = "MBAM_01"

    def __post_init__(self) -> None:
        if self.case_id != "MBAM_01":
            raise ValueError("CaseState.case_id must be 'MBAM_01' for Enqueteur v1.0")
        if not self.seed:
            raise ValueError("CaseState.seed must be non-empty")
        if not self.runtime_clock_start:
            raise ValueError("CaseState.runtime_clock_start must be non-empty")

        beat_ids = [b.beat_id for b in self.timeline_schedule]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("CaseState.timeline_schedule contains duplicate beat_id values")

        offsets = [b.time_offset_sec for b in self.timeline_schedule]
        if offsets != sorted(offsets):
            raise ValueError("CaseState.timeline_schedule must be sorted by time_offset_sec")

        visible_known = set(self.visible_case_slice.starting_known_fact_ids)
        hidden_private = set(self.hidden_case_slice.private_fact_ids)
        overlap = visible_known.intersection(hidden_private)
        if overlap:
            raise ValueError(
                "A fact cannot be both starting-known and hidden-private: "
                + ", ".join(sorted(overlap))
            )


__all__ = [
    "AlibiClaim",
    "AlibiMatrix",
    "AlibiTruthValue",
    "AllyId",
    "BestOutcomeRule",
    "CafeEvidence",
    "CaseState",
    "CastOverlay",
    "CharacterOverlay",
    "CulpritId",
    "DifficultyProfile",
    "DisplayCaseEvidence",
    "DropId",
    "DropLocationEvidence",
    "EvidencePlacement",
    "Helpfulness",
    "HiddenCaseSlice",
    "MethodId",
    "MisdirectorId",
    "ResolutionRequirement",
    "ResolutionRules",
    "RoleAssignment",
    "SceneCompletionState",
    "SceneGate",
    "SceneGates",
    "SceneId",
    "SoftFailRule",
    "TimelineBeat",
    "TimelineBeatType",
    "TruthEdgeRelation",
    "TruthGraph",
    "TruthGraphEdge",
    "TruthGraphNode",
    "TruthNodeType",
    "TruthVisibility",
    "VisibleCaseSlice",
    "BenchEvidence",
    "CorridorEvidence",
]
