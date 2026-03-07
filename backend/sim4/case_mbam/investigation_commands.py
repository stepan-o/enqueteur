from __future__ import annotations

"""MBAM investigation command contract (Phase 3B).

This module defines a deterministic, MBAM-first command/ack layer for object
investigation interactions. It validates command shape and applicability but
does not execute affordances.
"""

from dataclasses import dataclass
from typing import Iterable, Literal, cast

from .object_state import (
    MbamObjectId,
    MbamObjectStateBundle,
    list_affordances,
    list_mbam_object_ids,
    get_affordances_for_object,
)


InvestigationExecutionIntent = Literal["execute", "validate_only"]
InvestigationAckKind = Literal[
    "success",
    "no_op",
    "blocked_prerequisite",
    "invalid_action",
    "state_consumed",
]


@dataclass(frozen=True)
class InvestigationCommand:
    """Deterministic player investigation command for MBAM affordance intent."""

    object_id: str
    affordance_id: str
    execution_intent: InvestigationExecutionIntent = "execute"
    item_context_id: str | None = None
    evidence_context_id: str | None = None
    npc_context_id: str | None = None


@dataclass(frozen=True)
class InvestigationCommandAck:
    """Validation/result acknowledgment for a command contract check."""

    kind: InvestigationAckKind
    code: str
    command_action_key: str
    object_id: str
    affordance_id: str
    execution_intent: InvestigationExecutionIntent
    expected_prerequisites: tuple[str, ...]
    missing_prerequisites: tuple[str, ...]
    result_fields: tuple[str, ...]
    reveal_fact_ids: tuple[str, ...]
    reveal_evidence_ids: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        return self.kind in {"success", "no_op"}


def make_investigation_command(
    *,
    object_id: str,
    affordance_id: str,
    execution_intent: InvestigationExecutionIntent = "execute",
    item_context_id: str | None = None,
    evidence_context_id: str | None = None,
    npc_context_id: str | None = None,
) -> InvestigationCommand:
    """Helper constructor for MBAM investigation command payloads."""
    return InvestigationCommand(
        object_id=object_id,
        affordance_id=affordance_id,
        execution_intent=execution_intent,
        item_context_id=item_context_id,
        evidence_context_id=evidence_context_id,
        npc_context_id=npc_context_id,
    )


def command_action_key(command: InvestigationCommand) -> str:
    """Return canonical deterministic key for one command intent payload."""
    item = command.item_context_id or "-"
    evidence = command.evidence_context_id or "-"
    npc = command.npc_context_id or "-"
    return (
        f"{command.object_id}|{command.affordance_id}|"
        f"{command.execution_intent}|{item}|{evidence}|{npc}"
    )


def _derive_state_prerequisites(object_state: MbamObjectStateBundle) -> tuple[str, ...]:
    tokens: set[str] = set()
    if object_state.o2_medallion.status in {"present", "recovered"}:
        tokens.add("require:medallion_present_or_recovered")
    if object_state.o6_badge_terminal.online:
        tokens.add("terminal:online")
    if not object_state.o6_badge_terminal.archived:
        tokens.add("terminal:not_archived")
    if object_state.o9_receipt_printer.recent_receipts:
        tokens.add("receipt:available")
    if not object_state.o8_keypad_door.locked:
        tokens.add("door:unlocked")
    return tuple(sorted(tokens))


def _is_noop_for_state(command: InvestigationCommand, object_state: MbamObjectStateBundle) -> bool:
    if command.object_id == "O4_BENCH" and command.affordance_id == "inspect":
        return not object_state.o4_bench.under_bench_item
    if command.object_id == "O6_BADGE_TERMINAL" and command.affordance_id == "view_logs":
        return len(object_state.o6_badge_terminal.log_entries) == 0
    if command.object_id == "O8_KEYPAD_DOOR" and command.affordance_id == "attempt_code":
        return not object_state.o8_keypad_door.locked
    if command.object_id == "O9_RECEIPT_PRINTER" and command.affordance_id == "ask_for_receipt":
        return len(object_state.o9_receipt_printer.recent_receipts) == 0
    return False


def validate_investigation_command(
    command: InvestigationCommand,
    *,
    object_state: MbamObjectStateBundle,
    available_prerequisites: Iterable[str] = (),
    consumed_action_keys: Iterable[str] = (),
) -> InvestigationCommandAck:
    """Validate command applicability/prerequisites without executing affordance."""
    action_key = command_action_key(command)
    empty = ()

    if command.execution_intent not in {"execute", "validate_only"}:
        return InvestigationCommandAck(
            kind="invalid_action",
            code="invalid_execution_intent",
            command_action_key=action_key,
            object_id=command.object_id,
            affordance_id=command.affordance_id,
            execution_intent="validate_only",
            expected_prerequisites=empty,
            missing_prerequisites=empty,
            result_fields=empty,
            reveal_fact_ids=empty,
            reveal_evidence_ids=empty,
        )

    object_ids = set(list_mbam_object_ids())
    if command.object_id not in object_ids:
        return InvestigationCommandAck(
            kind="invalid_action",
            code="unknown_object_id",
            command_action_key=action_key,
            object_id=command.object_id,
            affordance_id=command.affordance_id,
            execution_intent=command.execution_intent,
            expected_prerequisites=empty,
            missing_prerequisites=empty,
            result_fields=empty,
            reveal_fact_ids=empty,
            reveal_evidence_ids=empty,
        )
    object_id = cast(MbamObjectId, command.object_id)

    affordances = list_affordances()
    by_affordance = {a.affordance_id for a in affordances}
    if command.affordance_id not in by_affordance:
        return InvestigationCommandAck(
            kind="invalid_action",
            code="unknown_affordance_id",
            command_action_key=action_key,
            object_id=command.object_id,
            affordance_id=command.affordance_id,
            execution_intent=command.execution_intent,
            expected_prerequisites=empty,
            missing_prerequisites=empty,
            result_fields=empty,
            reveal_fact_ids=empty,
            reveal_evidence_ids=empty,
        )

    object_affordances = {
        a.affordance_id: a
        for a in get_affordances_for_object(object_id)
    }
    if command.affordance_id not in object_affordances:
        return InvestigationCommandAck(
            kind="invalid_action",
            code="affordance_not_allowed_for_object",
            command_action_key=action_key,
            object_id=command.object_id,
            affordance_id=command.affordance_id,
            execution_intent=command.execution_intent,
            expected_prerequisites=empty,
            missing_prerequisites=empty,
            result_fields=empty,
            reveal_fact_ids=empty,
            reveal_evidence_ids=empty,
        )

    affordance = object_affordances[command.affordance_id]

    consumed = set(consumed_action_keys)
    if action_key in consumed:
        return InvestigationCommandAck(
            kind="state_consumed",
            code="action_state_already_consumed",
            command_action_key=action_key,
            object_id=command.object_id,
            affordance_id=command.affordance_id,
            execution_intent=command.execution_intent,
            expected_prerequisites=affordance.prerequisites,
            missing_prerequisites=empty,
            result_fields=affordance.result_fields,
            reveal_fact_ids=affordance.reveal_fact_ids,
            reveal_evidence_ids=affordance.reveal_evidence_ids,
        )

    available = set(available_prerequisites)
    available.update(_derive_state_prerequisites(object_state))
    missing = tuple(sorted(p for p in affordance.prerequisites if p not in available))
    if missing:
        return InvestigationCommandAck(
            kind="blocked_prerequisite",
            code="missing_prerequisites",
            command_action_key=action_key,
            object_id=command.object_id,
            affordance_id=command.affordance_id,
            execution_intent=command.execution_intent,
            expected_prerequisites=affordance.prerequisites,
            missing_prerequisites=missing,
            result_fields=affordance.result_fields,
            reveal_fact_ids=affordance.reveal_fact_ids,
            reveal_evidence_ids=affordance.reveal_evidence_ids,
        )

    if _is_noop_for_state(command, object_state):
        return InvestigationCommandAck(
            kind="no_op",
            code="state_no_effect",
            command_action_key=action_key,
            object_id=command.object_id,
            affordance_id=command.affordance_id,
            execution_intent=command.execution_intent,
            expected_prerequisites=affordance.prerequisites,
            missing_prerequisites=empty,
            result_fields=affordance.result_fields,
            reveal_fact_ids=affordance.reveal_fact_ids,
            reveal_evidence_ids=affordance.reveal_evidence_ids,
        )

    return InvestigationCommandAck(
        kind="success",
        code="validated",
        command_action_key=action_key,
        object_id=command.object_id,
        affordance_id=command.affordance_id,
        execution_intent=command.execution_intent,
        expected_prerequisites=affordance.prerequisites,
        missing_prerequisites=empty,
        result_fields=affordance.result_fields,
        reveal_fact_ids=affordance.reveal_fact_ids,
        reveal_evidence_ids=affordance.reveal_evidence_ids,
    )


def list_supported_command_forms() -> tuple[tuple[MbamObjectId, tuple[str, ...]], ...]:
    """Return deterministic object -> affordance form mapping for MBAM."""
    out: list[tuple[MbamObjectId, tuple[str, ...]]] = []
    for object_id in list_mbam_object_ids():
        affordances = tuple(a.affordance_id for a in get_affordances_for_object(object_id))
        out.append((object_id, affordances))
    return tuple(out)


__all__ = [
    "InvestigationAckKind",
    "InvestigationCommand",
    "InvestigationCommandAck",
    "InvestigationExecutionIntent",
    "command_action_key",
    "list_supported_command_forms",
    "make_investigation_command",
    "validate_investigation_command",
]
