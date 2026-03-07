from __future__ import annotations

"""Canonical MBAM investigation object state + affordance definitions.

This module is MBAM-specific by design for Enqueteur v1.0. It defines:
- case-side investigation object instance state (non-physical mystery layer)
- deterministic affordance contracts for O1..O10
- explicit bindings to world placement ids when they exist

It does not execute affordances. Runtime execution belongs to later phases.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from .models import CaseState, DropId


MbamObjectId = Literal[
    "O1_DISPLAY_CASE",
    "O2_MEDALLION",
    "O3_WALL_LABEL",
    "O4_BENCH",
    "O5_VISITOR_LOGBOOK",
    "O6_BADGE_TERMINAL",
    "O7_SECURITY_BINDER",
    "O8_KEYPAD_DOOR",
    "O9_RECEIPT_PRINTER",
    "O10_BULLETIN_BOARD",
]

AffordanceId = Literal[
    "inspect",
    "read",
    "check_lock",
    "examine_surface",
    "request_access",
    "view_logs",
    "ask_for_receipt",
    "read_receipt",
    "attempt_code",
    "examine",
]

AffordanceRepeatPolicy = Literal["one_shot", "repeatable", "state_dependent"]
DisplayCaseLockState = Literal["locked", "unlocked"]
MedallionPresence = Literal["present", "missing", "recovered"]
BinderPageState = Literal["intact", "incident_tab_open", "missing_page"]


def _tupleize(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    out = tuple(values)
    for value in out:
        if not isinstance(value, str) or not value:
            raise ValueError("Values must be non-empty strings")
    return out


@dataclass(frozen=True)
class ObjectWorldBinding:
    object_id: MbamObjectId
    room_token: str
    world_object_id: int | None = None
    world_class_code: str | None = None
    world_door_id: int | None = None

    def __post_init__(self) -> None:
        if not self.room_token:
            raise ValueError("ObjectWorldBinding.room_token must be non-empty")
        if self.world_object_id is None and self.world_door_id is None:
            # Case object may still be valid as investigation-only (non-placed).
            return
        if self.world_object_id is not None and self.world_object_id <= 0:
            raise ValueError("ObjectWorldBinding.world_object_id must be > 0 when set")
        if self.world_door_id is not None and self.world_door_id <= 0:
            raise ValueError("ObjectWorldBinding.world_door_id must be > 0 when set")


@dataclass(frozen=True)
class BadgeLogEntry:
    badge_id: str
    time: str
    door: str

    def __post_init__(self) -> None:
        if not self.badge_id:
            raise ValueError("BadgeLogEntry.badge_id must be non-empty")
        if not self.time:
            raise ValueError("BadgeLogEntry.time must be non-empty")
        if not self.door:
            raise ValueError("BadgeLogEntry.door must be non-empty")


@dataclass(frozen=True)
class CafeReceiptEntry:
    receipt_id: str
    time: str
    item: str

    def __post_init__(self) -> None:
        if not self.receipt_id:
            raise ValueError("CafeReceiptEntry.receipt_id must be non-empty")
        if not self.time:
            raise ValueError("CafeReceiptEntry.time must be non-empty")
        if not self.item:
            raise ValueError("CafeReceiptEntry.item must be non-empty")


@dataclass(frozen=True)
class VisitorLogEntry:
    visitor_name: str
    time_in: str
    note: str

    def __post_init__(self) -> None:
        if not self.visitor_name:
            raise ValueError("VisitorLogEntry.visitor_name must be non-empty")
        if not self.time_in:
            raise ValueError("VisitorLogEntry.time_in must be non-empty")
        if not self.note:
            raise ValueError("VisitorLogEntry.note must be non-empty")


@dataclass(frozen=True)
class DisplayCaseState:
    locked: DisplayCaseLockState
    contains_item: bool
    tampered: bool
    latch_condition: Literal["intact", "scratched", "loose"]


@dataclass(frozen=True)
class MedallionState:
    status: MedallionPresence
    location: Literal[
        "display_case",
        "cafe_bathroom_stash",
        "corridor_bin",
        "coat_rack_pocket",
        "player_inventory",
        "unknown",
    ]
    examined: bool


@dataclass(frozen=True)
class WallLabelState:
    text_variant_id: str

    def __post_init__(self) -> None:
        if not self.text_variant_id:
            raise ValueError("WallLabelState.text_variant_id must be non-empty")


@dataclass(frozen=True)
class BenchState:
    under_bench_item: bool


@dataclass(frozen=True)
class VisitorLogbookState:
    entries: tuple[VisitorLogEntry, ...]
    scribble_pattern: str

    def __post_init__(self) -> None:
        if not self.scribble_pattern:
            raise ValueError("VisitorLogbookState.scribble_pattern must be non-empty")


@dataclass(frozen=True)
class BadgeAccessTerminalState:
    online: bool
    log_entries: tuple[BadgeLogEntry, ...]
    archived: bool


@dataclass(frozen=True)
class SecurityBinderState:
    page_state: BinderPageState


@dataclass(frozen=True)
class KeypadDoorState:
    locked: bool
    code_hint: str

    def __post_init__(self) -> None:
        if not self.code_hint:
            raise ValueError("KeypadDoorState.code_hint must be non-empty")


@dataclass(frozen=True)
class ReceiptPrinterState:
    recent_receipts: tuple[CafeReceiptEntry, ...]


@dataclass(frozen=True)
class BulletinBoardState:
    flyer_text: str

    def __post_init__(self) -> None:
        if not self.flyer_text:
            raise ValueError("BulletinBoardState.flyer_text must be non-empty")


@dataclass(frozen=True)
class MbamObjectStateBundle:
    o1_display_case: DisplayCaseState
    o2_medallion: MedallionState
    o3_wall_label: WallLabelState
    o4_bench: BenchState
    o5_visitor_logbook: VisitorLogbookState
    o6_badge_terminal: BadgeAccessTerminalState
    o7_security_binder: SecurityBinderState
    o8_keypad_door: KeypadDoorState
    o9_receipt_printer: ReceiptPrinterState
    o10_bulletin_board: BulletinBoardState


@dataclass(frozen=True)
class AffordanceDefinition:
    affordance_id: AffordanceId
    object_id: MbamObjectId
    prerequisites: tuple[str, ...] = ()
    result_fields: tuple[str, ...] = ()
    can_reveal_facts: bool = False
    reveal_fact_ids: tuple[str, ...] = ()
    can_reveal_evidence: bool = False
    reveal_evidence_ids: tuple[str, ...] = ()
    repeat_policy: AffordanceRepeatPolicy = "repeatable"
    state_dependencies: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "prerequisites", _tupleize(self.prerequisites))
        object.__setattr__(self, "result_fields", _tupleize(self.result_fields))
        object.__setattr__(self, "reveal_fact_ids", _tupleize(self.reveal_fact_ids))
        object.__setattr__(self, "reveal_evidence_ids", _tupleize(self.reveal_evidence_ids))
        object.__setattr__(self, "state_dependencies", _tupleize(self.state_dependencies))

        if not self.result_fields:
            raise ValueError("AffordanceDefinition.result_fields must be non-empty")
        if self.can_reveal_facts != bool(self.reveal_fact_ids):
            raise ValueError("AffordanceDefinition.can_reveal_facts mismatch with reveal_fact_ids")
        if self.can_reveal_evidence != bool(self.reveal_evidence_ids):
            raise ValueError("AffordanceDefinition.can_reveal_evidence mismatch with reveal_evidence_ids")


_OBJECT_WORLD_BINDINGS = MappingProxyType(
    {
        "O1_DISPLAY_CASE": ObjectWorldBinding(
            object_id="O1_DISPLAY_CASE",
            room_token="GALLERY_AFFICHES",
            world_object_id=3002,
            world_class_code="DISPLAY_CASE",
        ),
        "O2_MEDALLION": ObjectWorldBinding(
            object_id="O2_MEDALLION",
            room_token="GALLERY_AFFICHES",
        ),
        "O3_WALL_LABEL": ObjectWorldBinding(
            object_id="O3_WALL_LABEL",
            room_token="GALLERY_AFFICHES",
        ),
        "O4_BENCH": ObjectWorldBinding(
            object_id="O4_BENCH",
            room_token="GALLERY_AFFICHES",
            world_object_id=3003,
            world_class_code="BENCH",
        ),
        "O5_VISITOR_LOGBOOK": ObjectWorldBinding(
            object_id="O5_VISITOR_LOGBOOK",
            room_token="MBAM_LOBBY",
        ),
        "O6_BADGE_TERMINAL": ObjectWorldBinding(
            object_id="O6_BADGE_TERMINAL",
            room_token="SECURITY_OFFICE",
            world_object_id=3004,
            world_class_code="SECURITY_TERMINAL",
        ),
        "O7_SECURITY_BINDER": ObjectWorldBinding(
            object_id="O7_SECURITY_BINDER",
            room_token="SECURITY_OFFICE",
        ),
        "O8_KEYPAD_DOOR": ObjectWorldBinding(
            object_id="O8_KEYPAD_DOOR",
            room_token="SERVICE_CORRIDOR",
            world_door_id=1002,
        ),
        "O9_RECEIPT_PRINTER": ObjectWorldBinding(
            object_id="O9_RECEIPT_PRINTER",
            room_token="CAFE_DE_LA_RUE",
            world_object_id=3007,
            world_class_code="RECEIPT_PRINTER",
        ),
        "O10_BULLETIN_BOARD": ObjectWorldBinding(
            object_id="O10_BULLETIN_BOARD",
            room_token="CAFE_DE_LA_RUE",
            world_object_id=3008,
            world_class_code="BULLETIN_BOARD",
        ),
    }
)

MBAM_OBJECT_ID_ORDER: tuple[MbamObjectId, ...] = tuple(_OBJECT_WORLD_BINDINGS.keys())

_AFFORDANCE_DEFINITIONS: tuple[AffordanceDefinition, ...] = (
    AffordanceDefinition(
        affordance_id="inspect",
        object_id="O1_DISPLAY_CASE",
        result_fields=("locked", "contains_item", "tampered", "latch_condition"),
        repeat_policy="state_dependent",
        state_dependencies=("o1_display_case.locked", "o1_display_case.contains_item"),
    ),
    AffordanceDefinition(
        affordance_id="check_lock",
        object_id="O1_DISPLAY_CASE",
        result_fields=("locked", "latch_condition"),
        can_reveal_facts=True,
        reveal_fact_ids=("N7",),
        repeat_policy="state_dependent",
        state_dependencies=("o1_display_case.locked", "o1_display_case.latch_condition"),
    ),
    AffordanceDefinition(
        affordance_id="examine_surface",
        object_id="O1_DISPLAY_CASE",
        result_fields=("tampered", "latch_condition", "surface_trace"),
        can_reveal_facts=True,
        reveal_fact_ids=("N7",),
        can_reveal_evidence=True,
        reveal_evidence_ids=("E3_METHOD_TRACE",),
        repeat_policy="state_dependent",
        state_dependencies=("o1_display_case.tampered", "o1_display_case.latch_condition"),
    ),
    AffordanceDefinition(
        affordance_id="examine",
        object_id="O2_MEDALLION",
        prerequisites=("require:medallion_present_or_recovered",),
        result_fields=("status", "location", "examined"),
        repeat_policy="state_dependent",
        state_dependencies=("o2_medallion.status", "o2_medallion.examined"),
    ),
    AffordanceDefinition(
        affordance_id="read",
        object_id="O3_WALL_LABEL",
        result_fields=("text_variant_id", "title", "date"),
        can_reveal_facts=True,
        reveal_fact_ids=("N1",),
        repeat_policy="state_dependent",
        state_dependencies=("o3_wall_label.text_variant_id",),
    ),
    AffordanceDefinition(
        affordance_id="inspect",
        object_id="O4_BENCH",
        result_fields=("under_bench_item", "found_item"),
        can_reveal_evidence=True,
        reveal_evidence_ids=("E1_TORN_NOTE", "E2_CAFE_RECEIPT"),
        repeat_policy="state_dependent",
        state_dependencies=("o4_bench.under_bench_item",),
    ),
    AffordanceDefinition(
        affordance_id="read",
        object_id="O5_VISITOR_LOGBOOK",
        result_fields=("entries", "scribble_pattern"),
        repeat_policy="state_dependent",
        state_dependencies=("o5_visitor_logbook.entries", "o5_visitor_logbook.scribble_pattern"),
    ),
    AffordanceDefinition(
        affordance_id="request_access",
        object_id="O6_BADGE_TERMINAL",
        prerequisites=("scene:S2", "trust:marc>=gate"),
        result_fields=("access_granted", "terminal_online", "terminal_archived"),
        can_reveal_facts=True,
        reveal_fact_ids=("N2",),
        repeat_policy="state_dependent",
        state_dependencies=("o6_badge_terminal.online", "o6_badge_terminal.archived"),
    ),
    AffordanceDefinition(
        affordance_id="view_logs",
        object_id="O6_BADGE_TERMINAL",
        prerequisites=("access:terminal_granted",),
        result_fields=("log_entries", "important_time"),
        can_reveal_facts=True,
        reveal_fact_ids=("N3",),
        repeat_policy="state_dependent",
        state_dependencies=("o6_badge_terminal.log_entries", "o6_badge_terminal.archived"),
    ),
    AffordanceDefinition(
        affordance_id="read",
        object_id="O7_SECURITY_BINDER",
        result_fields=("page_state", "protocol_notes"),
        repeat_policy="state_dependent",
        state_dependencies=("o7_security_binder.page_state",),
    ),
    AffordanceDefinition(
        affordance_id="inspect",
        object_id="O8_KEYPAD_DOOR",
        result_fields=("locked", "code_hint"),
        can_reveal_facts=True,
        reveal_fact_ids=("N2",),
        repeat_policy="repeatable",
        state_dependencies=("o8_keypad_door.locked",),
    ),
    AffordanceDefinition(
        affordance_id="attempt_code",
        object_id="O8_KEYPAD_DOOR",
        prerequisites=("input:code_4_digit",),
        result_fields=("attempt_result", "locked"),
        repeat_policy="state_dependent",
        state_dependencies=("o8_keypad_door.locked",),
    ),
    AffordanceDefinition(
        affordance_id="ask_for_receipt",
        object_id="O9_RECEIPT_PRINTER",
        prerequisites=("scene:S4",),
        result_fields=("receipt_available", "receipt_id"),
        can_reveal_evidence=True,
        reveal_evidence_ids=("E2_CAFE_RECEIPT",),
        repeat_policy="state_dependent",
        state_dependencies=("o9_receipt_printer.recent_receipts",),
    ),
    AffordanceDefinition(
        affordance_id="read_receipt",
        object_id="O9_RECEIPT_PRINTER",
        prerequisites=("inventory:E2_CAFE_RECEIPT",),
        result_fields=("receipt_id", "time", "item"),
        can_reveal_facts=True,
        reveal_fact_ids=("N4",),
        can_reveal_evidence=True,
        reveal_evidence_ids=("E2_CAFE_RECEIPT",),
        repeat_policy="repeatable",
        state_dependencies=("o9_receipt_printer.recent_receipts",),
    ),
    AffordanceDefinition(
        affordance_id="read",
        object_id="O10_BULLETIN_BOARD",
        result_fields=("flyer_text",),
        repeat_policy="repeatable",
        state_dependencies=("o10_bulletin_board.flyer_text",),
    ),
)


def _medallion_location_from_drop(drop_id: DropId) -> Literal["cafe_bathroom_stash", "corridor_bin", "coat_rack_pocket"]:
    if drop_id == "cafe_bathroom_stash":
        return "cafe_bathroom_stash"
    if drop_id == "corridor_bin":
        return "corridor_bin"
    return "coat_rack_pocket"


def _receipt_item_for_seed(seed: str) -> str:
    # Deterministic MBAM seed flavor for MG3 text, without changing truth nodes.
    if seed == "A":
        return "cafe filtre"
    if seed == "B":
        return "croissant"
    return "espresso"


def _label_variant_for_seed(seed: str) -> str:
    return f"label_variant_{seed.lower()}"


def _binder_state_for_seed(seed: str) -> BinderPageState:
    if seed == "A":
        return "incident_tab_open"
    if seed == "B":
        return "intact"
    return "incident_tab_open"


def build_initial_mbam_object_state(case_state: CaseState) -> MbamObjectStateBundle:
    """Build deterministic MBAM object-instance state from canonical CaseState."""
    evidence = case_state.evidence_placement
    roles = case_state.roles_assignment
    lock_state: DisplayCaseLockState = "unlocked" if roles.method == "case_left_unlatched" else "locked"
    drop_from_evidence = evidence.drop_location.location_id
    if drop_from_evidence != roles.drop:
        raise ValueError(
            "CaseState inconsistency: evidence.drop_location.location_id must match roles_assignment.drop"
        )
    medallion_location = _medallion_location_from_drop(drop_from_evidence)
    recent_receipt_id = evidence.cafe.receipt_id or f"R-{case_state.seed}-1752"

    return MbamObjectStateBundle(
        o1_display_case=DisplayCaseState(
            locked=lock_state,
            contains_item=False,
            tampered=evidence.display_case.tampered,
            latch_condition=evidence.display_case.latch_condition,
        ),
        o2_medallion=MedallionState(
            status="missing",
            location=medallion_location,
            examined=False,
        ),
        o3_wall_label=WallLabelState(
            text_variant_id=_label_variant_for_seed(case_state.seed),
        ),
        o4_bench=BenchState(
            under_bench_item=evidence.bench.contains in {"torn_note_fragment", "receipt_fragment"},
        ),
        o5_visitor_logbook=VisitorLogbookState(
            entries=(
                VisitorLogEntry(visitor_name="Vachon, Laurent", time_in="17:50", note="VIP"),
                VisitorLogEntry(visitor_name="Samira B.", time_in="17:46", note="stagiaire"),
            ),
            scribble_pattern="double_stroke_correction",
        ),
        o6_badge_terminal=BadgeAccessTerminalState(
            online=True,
            log_entries=(
                BadgeLogEntry(badge_id="MBAM-STF-04", time="17:58", door="SERVICE_CORRIDOR"),
                BadgeLogEntry(badge_id="MBAM-STF-01", time="17:43", door="SECURITY_OFFICE"),
            ),
            archived=False,
        ),
        o7_security_binder=SecurityBinderState(
            page_state=_binder_state_for_seed(case_state.seed),
        ),
        o8_keypad_door=KeypadDoorState(
            locked=True,
            code_hint="Indice: les chiffres de l'heure critique.",
        ),
        o9_receipt_printer=ReceiptPrinterState(
            recent_receipts=(
                CafeReceiptEntry(
                    receipt_id=recent_receipt_id,
                    time="17:52",
                    item=_receipt_item_for_seed(case_state.seed),
                ),
            ),
        ),
        o10_bulletin_board=BulletinBoardState(
            flyer_text="Exposition temporaire: objets de poche (jusqu'au 30 mars).",
        ),
    )


def list_mbam_object_ids() -> tuple[MbamObjectId, ...]:
    return MBAM_OBJECT_ID_ORDER


def get_object_world_binding(object_id: MbamObjectId) -> ObjectWorldBinding:
    return _OBJECT_WORLD_BINDINGS[object_id]


def get_all_object_world_bindings() -> dict[MbamObjectId, ObjectWorldBinding]:
    return {object_id: _OBJECT_WORLD_BINDINGS[object_id] for object_id in MBAM_OBJECT_ID_ORDER}


def list_affordances() -> tuple[AffordanceDefinition, ...]:
    return _AFFORDANCE_DEFINITIONS


def get_affordances_for_object(object_id: MbamObjectId) -> tuple[AffordanceDefinition, ...]:
    return tuple(a for a in _AFFORDANCE_DEFINITIONS if a.object_id == object_id)


def get_object_state_by_id(
    bundle: MbamObjectStateBundle,
    object_id: MbamObjectId,
) -> object:
    if object_id == "O1_DISPLAY_CASE":
        return bundle.o1_display_case
    if object_id == "O2_MEDALLION":
        return bundle.o2_medallion
    if object_id == "O3_WALL_LABEL":
        return bundle.o3_wall_label
    if object_id == "O4_BENCH":
        return bundle.o4_bench
    if object_id == "O5_VISITOR_LOGBOOK":
        return bundle.o5_visitor_logbook
    if object_id == "O6_BADGE_TERMINAL":
        return bundle.o6_badge_terminal
    if object_id == "O7_SECURITY_BINDER":
        return bundle.o7_security_binder
    if object_id == "O8_KEYPAD_DOOR":
        return bundle.o8_keypad_door
    if object_id == "O9_RECEIPT_PRINTER":
        return bundle.o9_receipt_printer
    if object_id == "O10_BULLETIN_BOARD":
        return bundle.o10_bulletin_board
    raise KeyError(f"Unknown MBAM object_id: {object_id!r}")


__all__ = [
    "AffordanceDefinition",
    "AffordanceId",
    "AffordanceRepeatPolicy",
    "BadgeAccessTerminalState",
    "BadgeLogEntry",
    "BenchState",
    "BinderPageState",
    "BulletinBoardState",
    "CafeReceiptEntry",
    "DisplayCaseLockState",
    "DisplayCaseState",
    "KeypadDoorState",
    "MBAM_OBJECT_ID_ORDER",
    "MbamObjectId",
    "MbamObjectStateBundle",
    "MedallionPresence",
    "MedallionState",
    "ObjectWorldBinding",
    "ReceiptPrinterState",
    "SecurityBinderState",
    "VisitorLogEntry",
    "VisitorLogbookState",
    "WallLabelState",
    "build_initial_mbam_object_state",
    "get_affordances_for_object",
    "get_all_object_world_bindings",
    "get_object_state_by_id",
    "get_object_world_binding",
    "list_affordances",
    "list_mbam_object_ids",
]
