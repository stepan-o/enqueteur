from __future__ import annotations

"""Deterministic MBAM affordance execution (Phase 3C).

This module executes MBAM investigation affordances over object-state while
remaining frontend-agnostic and dialogue-agnostic.
"""

from dataclasses import dataclass
from dataclasses import replace
from typing import Iterable, Literal, cast

from .investigation_commands import (
    InvestigationCommand,
    InvestigationCommandAck,
    command_action_key,
    validate_investigation_command,
)
from .models import CaseState
from .object_state import (
    MbamObjectId,
    MbamObjectStateBundle,
    CafeReceiptEntry,
    get_affordances_for_object,
)


ObservationEntry = tuple[str, object]

ExecutionKind = Literal["validated_only", "executed", "rejected"]


@dataclass(frozen=True)
class StateTransition:
    field_path: str
    before: object
    after: object


@dataclass(frozen=True)
class InvestigationExecutionResult:
    command: InvestigationCommand
    ack: InvestigationCommandAck
    execution_kind: ExecutionKind
    object_state_before: MbamObjectStateBundle
    object_state_after: MbamObjectStateBundle
    timeline_effects: tuple[str, ...]
    timeline_transitions: tuple[StateTransition, ...]
    interaction_transitions: tuple[StateTransition, ...]
    descriptive_observation: tuple[ObservationEntry, ...]
    revealed_evidence_ids: tuple[str, ...]
    fact_unlock_candidates: tuple[str, ...]
    consumed_action_key: str | None


def _replace_ack(
    ack: InvestigationCommandAck,
    *,
    kind: Literal["success", "no_op", "blocked_prerequisite", "invalid_action", "state_consumed"],
    code: str,
    missing_prerequisites: tuple[str, ...] | None = None,
) -> InvestigationCommandAck:
    return InvestigationCommandAck(
        kind=kind,
        code=code,
        command_action_key=ack.command_action_key,
        object_id=ack.object_id,
        affordance_id=ack.affordance_id,
        execution_intent=ack.execution_intent,
        expected_prerequisites=ack.expected_prerequisites,
        missing_prerequisites=missing_prerequisites if missing_prerequisites is not None else ack.missing_prerequisites,
        result_fields=ack.result_fields,
        reveal_fact_ids=ack.reveal_fact_ids,
        reveal_evidence_ids=ack.reveal_evidence_ids,
    )


def _apply_timeline_effects(
    object_state: MbamObjectStateBundle,
    *,
    elapsed_seconds: float,
) -> tuple[MbamObjectStateBundle, tuple[str, ...], tuple[StateTransition, ...]]:
    effects: list[str] = []
    transitions: list[StateTransition] = []
    state = object_state

    # T+15 anchor: terminal log archive and access friction.
    if elapsed_seconds >= 900.0 and not state.o6_badge_terminal.archived:
        before = state.o6_badge_terminal.archived
        state = replace(
            state,
            o6_badge_terminal=replace(state.o6_badge_terminal, archived=True),
        )
        effects.append("T_PLUS_15_TERMINAL_ARCHIVE")
        transitions.append(
            StateTransition(
                field_path="o6_badge_terminal.archived",
                before=before,
                after=True,
            )
        )

    return state, tuple(effects), tuple(transitions)


def _filter_legal_fact_candidates(
    case_state: CaseState,
    fact_ids: Iterable[str],
) -> tuple[str, ...]:
    nodes = {node.fact_id: node for node in case_state.truth_graph.nodes}
    out: list[str] = []
    for fact_id in fact_ids:
        node = nodes.get(fact_id)
        if node is None:
            continue
        if node.visibility == "hidden":
            continue
        out.append(fact_id)
    return tuple(sorted(set(out)))


def _surface_trace_for_case(case_state: CaseState) -> str:
    latch = case_state.evidence_placement.display_case.latch_condition
    if latch == "scratched":
        return "micro_trace_frottement"
    if latch == "loose":
        return "usure_loquet_visible"
    return "surface_propre"


def _label_title_for_seed(seed: str) -> str:
    if seed == "A":
        return "Le Medaillon des Voyageurs"
    if seed == "B":
        return "Le Medaillon des Voyageurs"
    return "Le Medaillon des Voyageurs"


def _label_date_for_seed(seed: str) -> str:
    if seed == "A":
        return "1898"
    if seed == "B":
        return "1898"
    return "1898"


def _protocol_note_for_binder(page_state: str) -> str:
    if page_state == "incident_tab_open":
        return "onglet incident marque"
    if page_state == "missing_page":
        return "une page semble retiree"
    return "procedure standard"


def _expected_keypad_code(case_state: CaseState) -> str:
    _ = case_state
    # Locked deterministic puzzle code aligned with critical badge time.
    return "1758"


def _receipt_entry_for_read(
    case_state: CaseState,
    object_state: MbamObjectStateBundle,
    command: InvestigationCommand,
) -> CafeReceiptEntry:
    receipt_id = command.item_context_id or case_state.evidence_placement.cafe.receipt_id or f"R-{case_state.seed}-1752"
    for entry in object_state.o9_receipt_printer.recent_receipts:
        if entry.receipt_id == receipt_id:
            return entry
    # Fall back to canonical case receipt details.
    if case_state.seed == "A":
        item = "cafe filtre"
    elif case_state.seed == "B":
        item = "croissant"
    else:
        item = "espresso"
    return CafeReceiptEntry(
        receipt_id=receipt_id,
        time="17:52",
        item=item,
    )


def _noop_result(
    *,
    command: InvestigationCommand,
    ack: InvestigationCommandAck,
    base_before: MbamObjectStateBundle,
    base_after: MbamObjectStateBundle,
    timeline_effects: tuple[str, ...],
    timeline_transitions: tuple[StateTransition, ...],
) -> InvestigationExecutionResult:
    return InvestigationExecutionResult(
        command=command,
        ack=ack,
        execution_kind="rejected" if not ack.accepted else "validated_only",
        object_state_before=base_before,
        object_state_after=base_after,
        timeline_effects=timeline_effects,
        timeline_transitions=timeline_transitions,
        interaction_transitions=(),
        descriptive_observation=(),
        revealed_evidence_ids=(),
        fact_unlock_candidates=(),
        consumed_action_key=None,
    )


def execute_investigation_command(
    command: InvestigationCommand,
    *,
    case_state: CaseState,
    object_state: MbamObjectStateBundle,
    elapsed_seconds: float = 0.0,
    available_prerequisites: Iterable[str] = (),
    consumed_action_keys: Iterable[str] = (),
) -> InvestigationExecutionResult:
    """Execute MBAM affordance deterministically against object-state + case truth."""
    state_after_timeline, timeline_effects, timeline_transitions = _apply_timeline_effects(
        object_state,
        elapsed_seconds=float(elapsed_seconds),
    )
    ack = validate_investigation_command(
        command,
        object_state=state_after_timeline,
        available_prerequisites=available_prerequisites,
        consumed_action_keys=consumed_action_keys,
    )
    if ack.kind in {"invalid_action", "blocked_prerequisite", "state_consumed"}:
        return _noop_result(
            command=command,
            ack=ack,
            base_before=object_state,
            base_after=state_after_timeline,
            timeline_effects=timeline_effects,
            timeline_transitions=timeline_transitions,
        )

    if command.execution_intent == "validate_only":
        return InvestigationExecutionResult(
            command=command,
            ack=ack,
            execution_kind="validated_only",
            object_state_before=object_state,
            object_state_after=state_after_timeline,
            timeline_effects=timeline_effects,
            timeline_transitions=timeline_transitions,
            interaction_transitions=(),
            descriptive_observation=(),
            revealed_evidence_ids=(),
            fact_unlock_candidates=_filter_legal_fact_candidates(case_state, ack.reveal_fact_ids),
            consumed_action_key=None,
        )

    state = state_after_timeline
    interaction_transitions: list[StateTransition] = []
    observation: list[ObservationEntry] = []
    revealed_evidence: tuple[str, ...] = ()
    fact_candidates: tuple[str, ...] = _filter_legal_fact_candidates(case_state, ack.reveal_fact_ids)

    key = (command.object_id, command.affordance_id)

    if key == ("O1_DISPLAY_CASE", "inspect"):
        observation = [
            ("locked", state.o1_display_case.locked),
            ("contains_item", state.o1_display_case.contains_item),
            ("tampered", state.o1_display_case.tampered),
            ("latch_condition", state.o1_display_case.latch_condition),
        ]
    elif key == ("O1_DISPLAY_CASE", "check_lock"):
        observation = [
            ("locked", state.o1_display_case.locked),
            ("latch_condition", state.o1_display_case.latch_condition),
        ]
    elif key == ("O1_DISPLAY_CASE", "examine_surface"):
        observation = [
            ("tampered", state.o1_display_case.tampered),
            ("latch_condition", state.o1_display_case.latch_condition),
            ("surface_trace", _surface_trace_for_case(case_state)),
        ]
        revealed_evidence = ("E3_METHOD_TRACE",)
    elif key == ("O2_MEDALLION", "examine"):
        if state.o2_medallion.status == "missing":
            ack = _replace_ack(
                ack,
                kind="blocked_prerequisite",
                code="medallion_not_accessible",
                missing_prerequisites=("require:medallion_present_or_recovered",),
            )
            observation = [("status", state.o2_medallion.status)]
        elif state.o2_medallion.examined:
            ack = _replace_ack(ack, kind="no_op", code="medallion_already_examined")
            observation = [
                ("status", state.o2_medallion.status),
                ("location", state.o2_medallion.location),
                ("examined", state.o2_medallion.examined),
            ]
        else:
            before = state.o2_medallion.examined
            state = replace(
                state,
                o2_medallion=replace(state.o2_medallion, examined=True),
            )
            interaction_transitions.append(
                StateTransition(
                    field_path="o2_medallion.examined",
                    before=before,
                    after=True,
                )
            )
            observation = [
                ("status", state.o2_medallion.status),
                ("location", state.o2_medallion.location),
                ("examined", state.o2_medallion.examined),
            ]
    elif key == ("O3_WALL_LABEL", "read"):
        observation = [
            ("text_variant_id", state.o3_wall_label.text_variant_id),
            ("title", _label_title_for_seed(case_state.seed)),
            ("date", _label_date_for_seed(case_state.seed)),
        ]
    elif key == ("O4_BENCH", "inspect"):
        if not state.o4_bench.under_bench_item:
            ack = _replace_ack(ack, kind="no_op", code="bench_empty")
            observation = [
                ("under_bench_item", False),
                ("found_item", "none"),
            ]
        else:
            bench_contains = case_state.evidence_placement.bench.contains
            before = state.o4_bench.under_bench_item
            state = replace(
                state,
                o4_bench=replace(state.o4_bench, under_bench_item=False),
            )
            interaction_transitions.append(
                StateTransition(
                    field_path="o4_bench.under_bench_item",
                    before=before,
                    after=False,
                )
            )
            if bench_contains == "torn_note_fragment":
                revealed_evidence = ("E1_TORN_NOTE",)
            elif bench_contains == "receipt_fragment":
                revealed_evidence = ("E2_CAFE_RECEIPT",)
            else:
                revealed_evidence = ()
            observation = [
                ("under_bench_item", state.o4_bench.under_bench_item),
                ("found_item", bench_contains),
            ]
    elif key == ("O5_VISITOR_LOGBOOK", "read"):
        entries = tuple(
            f"{entry.visitor_name}@{entry.time_in}:{entry.note}"
            for entry in state.o5_visitor_logbook.entries
        )
        observation = [
            ("entries_count", len(entries)),
            ("entries", entries),
            ("scribble_pattern", state.o5_visitor_logbook.scribble_pattern),
        ]
    elif key == ("O6_BADGE_TERMINAL", "request_access"):
        if not state.o6_badge_terminal.online:
            ack = _replace_ack(
                ack,
                kind="blocked_prerequisite",
                code="terminal_offline",
                missing_prerequisites=("terminal:online",),
            )
            observation = [("access_granted", False)]
        elif state.o6_badge_terminal.archived and "override:terminal_archive" not in set(available_prerequisites):
            ack = _replace_ack(ack, kind="no_op", code="terminal_archived_access_friction")
            observation = [
                ("access_granted", False),
                ("terminal_online", state.o6_badge_terminal.online),
                ("terminal_archived", state.o6_badge_terminal.archived),
            ]
        else:
            observation = [
                ("access_granted", True),
                ("terminal_online", state.o6_badge_terminal.online),
                ("terminal_archived", state.o6_badge_terminal.archived),
            ]
    elif key == ("O6_BADGE_TERMINAL", "view_logs"):
        logs = state.o6_badge_terminal.log_entries
        if not logs:
            ack = _replace_ack(ack, kind="no_op", code="terminal_logs_empty")
            observation = [("log_entries", ())]
        elif state.o6_badge_terminal.archived and "override:terminal_archive" not in set(available_prerequisites):
            ack = _replace_ack(ack, kind="no_op", code="terminal_archived_access_friction")
            observation = [
                ("log_entries", ()),
                ("important_time", None),
                ("archived", True),
            ]
        else:
            important = next((entry for entry in logs if entry.time == "17:58"), logs[0])
            compact = tuple(f"{entry.badge_id}@{entry.time}/{entry.door}" for entry in logs)
            observation = [
                ("log_entries", compact),
                ("important_badge_id", important.badge_id),
                ("important_time", important.time),
                ("important_door", important.door),
                ("archived", state.o6_badge_terminal.archived),
            ]
    elif key == ("O7_SECURITY_BINDER", "read"):
        observation = [
            ("page_state", state.o7_security_binder.page_state),
            ("protocol_notes", _protocol_note_for_binder(state.o7_security_binder.page_state)),
        ]
    elif key == ("O8_KEYPAD_DOOR", "inspect"):
        observation = [
            ("locked", state.o8_keypad_door.locked),
            ("code_hint", state.o8_keypad_door.code_hint),
        ]
    elif key == ("O8_KEYPAD_DOOR", "attempt_code"):
        if not state.o8_keypad_door.locked:
            ack = _replace_ack(ack, kind="no_op", code="door_already_unlocked")
            observation = [
                ("attempt_result", "already_unlocked"),
                ("locked", state.o8_keypad_door.locked),
            ]
        else:
            supplied = (command.item_context_id or command.evidence_context_id or "").strip()
            if len(supplied) != 4 or not supplied.isdigit():
                ack = _replace_ack(
                    ack,
                    kind="blocked_prerequisite",
                    code="invalid_code_shape",
                    missing_prerequisites=("input:code_4_digit",),
                )
                observation = [
                    ("attempt_result", "invalid_format"),
                    ("locked", state.o8_keypad_door.locked),
                ]
            elif supplied != _expected_keypad_code(case_state):
                ack = _replace_ack(ack, kind="no_op", code="incorrect_code")
                observation = [
                    ("attempt_result", "incorrect"),
                    ("locked", state.o8_keypad_door.locked),
                ]
            else:
                before = state.o8_keypad_door.locked
                state = replace(
                    state,
                    o8_keypad_door=replace(state.o8_keypad_door, locked=False),
                )
                interaction_transitions.append(
                    StateTransition(
                        field_path="o8_keypad_door.locked",
                        before=before,
                        after=False,
                    )
                )
                observation = [
                    ("attempt_result", "success"),
                    ("locked", state.o8_keypad_door.locked),
                ]
    elif key == ("O9_RECEIPT_PRINTER", "ask_for_receipt"):
        receipts = state.o9_receipt_printer.recent_receipts
        if not receipts:
            ack = _replace_ack(ack, kind="no_op", code="receipt_unavailable")
            observation = [
                ("receipt_available", False),
                ("receipt_id", None),
            ]
        else:
            current = receipts[0]
            before = receipts
            after = tuple(receipts[1:])
            state = replace(
                state,
                o9_receipt_printer=replace(state.o9_receipt_printer, recent_receipts=after),
            )
            interaction_transitions.append(
                StateTransition(
                    field_path="o9_receipt_printer.recent_receipts",
                    before=before,
                    after=after,
                )
            )
            revealed_evidence = ("E2_CAFE_RECEIPT",)
            observation = [
                ("receipt_available", True),
                ("receipt_id", current.receipt_id),
            ]
    elif key == ("O9_RECEIPT_PRINTER", "read_receipt"):
        entry = _receipt_entry_for_read(case_state, state, command)
        observation = [
            ("receipt_id", entry.receipt_id),
            ("time", entry.time),
            ("item", entry.item),
        ]
        revealed_evidence = ("E2_CAFE_RECEIPT",)
    elif key == ("O10_BULLETIN_BOARD", "read"):
        observation = [("flyer_text", state.o10_bulletin_board.flyer_text)]
    else:
        # Defensive fallback: should never happen after validator passes.
        ack = _replace_ack(ack, kind="invalid_action", code="unsupported_affordance_handler")

    if ack.kind in {"blocked_prerequisite", "invalid_action", "state_consumed"}:
        exec_kind: ExecutionKind = "rejected"
    elif ack.kind == "no_op":
        exec_kind = "executed"
    else:
        exec_kind = "executed"

    result_facts = _filter_legal_fact_candidates(case_state, fact_candidates)
    if ack.kind != "success":
        if ack.kind == "no_op":
            result_facts = _filter_legal_fact_candidates(case_state, ack.reveal_fact_ids)
        else:
            result_facts = ()
            revealed_evidence = ()

    consumed_key: str | None = None
    if ack.kind == "success":
        object_id = cast(MbamObjectId, command.object_id)
        affordance_defs = {a.affordance_id: a for a in get_affordances_for_object(object_id)}
        affordance = affordance_defs.get(command.affordance_id)
        if affordance is not None and affordance.repeat_policy == "one_shot":
            consumed_key = command_action_key(command)

    return InvestigationExecutionResult(
        command=command,
        ack=ack,
        execution_kind=exec_kind,
        object_state_before=object_state,
        object_state_after=state,
        timeline_effects=timeline_effects,
        timeline_transitions=timeline_transitions,
        interaction_transitions=tuple(interaction_transitions),
        descriptive_observation=tuple(observation),
        revealed_evidence_ids=tuple(sorted(set(revealed_evidence))),
        fact_unlock_candidates=result_facts,
        consumed_action_key=consumed_key,
    )


__all__ = [
    "ExecutionKind",
    "InvestigationExecutionResult",
    "ObservationEntry",
    "StateTransition",
    "execute_investigation_command",
]
