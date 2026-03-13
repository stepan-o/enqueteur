from __future__ import annotations

"""Enqueteur LIVE INPUT_COMMAND parsing and dispatch skeleton."""

from dataclasses import dataclass
from typing import Any, Callable, Literal
import uuid

from backend.runtime_messages import command_rejected_message_contract


EnqueteurCommandType = Literal[
    "INVESTIGATE_OBJECT",
    "DIALOGUE_TURN",
    "MINIGAME_SUBMIT",
    "ATTEMPT_RECOVERY",
    "ATTEMPT_ACCUSATION",
]

ENQUETEUR_INPUT_COMMAND_TYPES: tuple[EnqueteurCommandType, ...] = (
    "INVESTIGATE_OBJECT",
    "DIALOGUE_TURN",
    "MINIGAME_SUBMIT",
    "ATTEMPT_RECOVERY",
    "ATTEMPT_ACCUSATION",
)

UNKNOWN_CLIENT_CMD_ID = "00000000-0000-4000-8000-000000000000"


@dataclass(frozen=True)
class InvestigateObjectCommandPayload:
    object_id: str
    action_id: str


@dataclass(frozen=True)
class DialogueTurnCommandPayload:
    scene_id: str
    npc_id: str
    intent_id: str
    slots: dict[str, Any]


@dataclass(frozen=True)
class MinigameSubmitCommandPayload:
    minigame_id: str
    target_id: str
    answer: dict[str, Any]


@dataclass(frozen=True)
class AttemptRecoveryCommandPayload:
    target_id: str


@dataclass(frozen=True)
class AttemptAccusationCommandPayload:
    suspect_id: str
    supporting_fact_ids: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]


ParsedCommandPayload = (
    InvestigateObjectCommandPayload
    | DialogueTurnCommandPayload
    | MinigameSubmitCommandPayload
    | AttemptRecoveryCommandPayload
    | AttemptAccusationCommandPayload
)


@dataclass(frozen=True)
class ParsedInputCommand:
    client_cmd_id: str
    tick_target: int
    cmd_type: EnqueteurCommandType
    payload: ParsedCommandPayload


@dataclass(frozen=True)
class CommandDispatchResult:
    accepted: bool
    client_cmd_id: str
    reason_code: str | None = None
    message: str | None = None
    message_key: str | None = None
    message_params: dict[str, Any] | None = None

    @classmethod
    def accepted_result(cls, *, client_cmd_id: str) -> "CommandDispatchResult":
        return cls(accepted=True, client_cmd_id=client_cmd_id)

    @classmethod
    def rejected_result(
        cls,
        *,
        client_cmd_id: str,
        reason_code: str,
        message: str,
        message_key: str | None = None,
        message_params: dict[str, Any] | None = None,
    ) -> "CommandDispatchResult":
        if message_key is None or message_params is None:
            default_key, default_params = command_rejected_message_contract(
                reason_code=reason_code,
                client_cmd_id=client_cmd_id,
            )
            if message_key is None:
                message_key = default_key
            if message_params is None:
                message_params = default_params
        return cls(
            accepted=False,
            client_cmd_id=client_cmd_id,
            reason_code=reason_code,
            message=message,
            message_key=message_key,
            message_params=message_params,
        )


class InputCommandValidationError(ValueError):
    """Raised when INPUT_COMMAND payload fails Enqueteur command-shape validation."""

    def __init__(
        self,
        *,
        reason_code: str,
        message: str,
        client_cmd_id: str,
        message_key: str | None = None,
        message_params: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        if message_key is None or message_params is None:
            default_key, default_params = command_rejected_message_contract(
                reason_code=reason_code,
                client_cmd_id=client_cmd_id,
            )
            if message_key is None:
                message_key = default_key
            if message_params is None:
                message_params = default_params
        self.reason_code = reason_code
        self.message = message
        self.client_cmd_id = client_cmd_id
        self.message_key = message_key
        self.message_params = message_params


def parse_enqueteur_input_command(payload: Any) -> ParsedInputCommand:
    """Parse and validate INPUT_COMMAND against KVP-ENQ-0001 command shapes."""

    client_cmd_id = _coerce_client_cmd_id(payload)
    if not isinstance(payload, dict):
        raise InputCommandValidationError(
            reason_code="INVALID_COMMAND",
            message="INPUT_COMMAND payload must be an object.",
            client_cmd_id=client_cmd_id,
        )

    tick_target = payload.get("tick_target")
    if not isinstance(tick_target, int) or tick_target < 0:
        raise InputCommandValidationError(
            reason_code="INVALID_COMMAND",
            message="INPUT_COMMAND.tick_target must be a non-negative integer.",
            client_cmd_id=client_cmd_id,
        )

    cmd = payload.get("cmd")
    if not isinstance(cmd, dict):
        raise InputCommandValidationError(
            reason_code="INVALID_COMMAND",
            message="INPUT_COMMAND.cmd must be an object.",
            client_cmd_id=client_cmd_id,
        )

    cmd_type = cmd.get("type")
    if not isinstance(cmd_type, str) or not cmd_type.strip():
        raise InputCommandValidationError(
            reason_code="INVALID_COMMAND",
            message="INPUT_COMMAND.cmd.type must be a non-empty string.",
            client_cmd_id=client_cmd_id,
        )
    normalized_type = cmd_type.strip()
    if normalized_type not in ENQUETEUR_INPUT_COMMAND_TYPES:
        raise InputCommandValidationError(
            reason_code="INVALID_COMMAND",
            message=f"Unsupported INPUT_COMMAND type '{normalized_type}'.",
            client_cmd_id=client_cmd_id,
        )

    raw_cmd_payload = cmd.get("payload")
    if not isinstance(raw_cmd_payload, dict):
        raise InputCommandValidationError(
            reason_code="INVALID_COMMAND",
            message="INPUT_COMMAND.cmd.payload must be an object.",
            client_cmd_id=client_cmd_id,
        )

    parser = _PAYLOAD_PARSERS[normalized_type]
    parsed_payload = parser(raw_cmd_payload, client_cmd_id)
    return ParsedInputCommand(
        client_cmd_id=client_cmd_id,
        tick_target=tick_target,
        cmd_type=normalized_type,
        payload=parsed_payload,
    )


PayloadParser = Callable[[dict[str, Any], str], ParsedCommandPayload]


def _coerce_client_cmd_id(payload: Any) -> str:
    if not isinstance(payload, dict):
        return UNKNOWN_CLIENT_CMD_ID

    value = payload.get("client_cmd_id")
    if not isinstance(value, str) or not value.strip():
        return UNKNOWN_CLIENT_CMD_ID

    client_cmd_id = value.strip()
    try:
        uuid.UUID(client_cmd_id)
    except ValueError as exc:
        raise InputCommandValidationError(
            reason_code="INVALID_COMMAND",
            message="INPUT_COMMAND.client_cmd_id must be a valid UUID string.",
            client_cmd_id=client_cmd_id,
        ) from exc
    return client_cmd_id


def _require_non_empty_str(
    payload: dict[str, Any],
    *,
    field: str,
    client_cmd_id: str,
    reason_code: str = "INVALID_COMMAND",
) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise InputCommandValidationError(
            reason_code=reason_code,
            message=f"{field} must be a non-empty string.",
            client_cmd_id=client_cmd_id,
        )
    return value.strip()


def _require_string_list(
    payload: dict[str, Any],
    *,
    field: str,
    client_cmd_id: str,
) -> tuple[str, ...]:
    value = payload.get(field)
    if not isinstance(value, list):
        raise InputCommandValidationError(
            reason_code="INVALID_COMMAND",
            message=f"{field} must be a list of non-empty strings.",
            client_cmd_id=client_cmd_id,
        )

    out: list[str] = []
    for entry in value:
        if not isinstance(entry, str) or not entry.strip():
            raise InputCommandValidationError(
                reason_code="INVALID_COMMAND",
                message=f"{field} must contain non-empty strings.",
                client_cmd_id=client_cmd_id,
            )
        out.append(entry.strip())
    return tuple(out)


def _parse_investigate_object(payload: dict[str, Any], client_cmd_id: str) -> ParsedCommandPayload:
    return InvestigateObjectCommandPayload(
        object_id=_require_non_empty_str(payload, field="object_id", client_cmd_id=client_cmd_id),
        action_id=_require_non_empty_str(payload, field="action_id", client_cmd_id=client_cmd_id),
    )


def _parse_dialogue_turn(payload: dict[str, Any], client_cmd_id: str) -> ParsedCommandPayload:
    scene_id = _require_non_empty_str(payload, field="scene_id", client_cmd_id=client_cmd_id)
    npc_id = _require_non_empty_str(payload, field="npc_id", client_cmd_id=client_cmd_id)
    intent_id = _require_non_empty_str(payload, field="intent_id", client_cmd_id=client_cmd_id)
    slots = payload.get("slots")
    if slots is None:
        raise InputCommandValidationError(
            reason_code="MISSING_REQUIRED_SLOTS",
            message="slots must be provided for DIALOGUE_TURN.",
            client_cmd_id=client_cmd_id,
        )
    if not isinstance(slots, dict):
        raise InputCommandValidationError(
            reason_code="INVALID_COMMAND",
            message="slots must be an object.",
            client_cmd_id=client_cmd_id,
        )

    return DialogueTurnCommandPayload(
        scene_id=scene_id,
        npc_id=npc_id,
        intent_id=intent_id,
        slots=dict(slots),
    )


def _parse_minigame_submit(payload: dict[str, Any], client_cmd_id: str) -> ParsedCommandPayload:
    minigame_id = _require_non_empty_str(payload, field="minigame_id", client_cmd_id=client_cmd_id)
    target_id = _require_non_empty_str(payload, field="target_id", client_cmd_id=client_cmd_id)
    answer = payload.get("answer")
    if not isinstance(answer, dict):
        raise InputCommandValidationError(
            reason_code="INVALID_COMMAND",
            message="answer must be an object.",
            client_cmd_id=client_cmd_id,
        )
    return MinigameSubmitCommandPayload(
        minigame_id=minigame_id,
        target_id=target_id,
        answer=dict(answer),
    )


def _parse_attempt_recovery(payload: dict[str, Any], client_cmd_id: str) -> ParsedCommandPayload:
    return AttemptRecoveryCommandPayload(
        target_id=_require_non_empty_str(payload, field="target_id", client_cmd_id=client_cmd_id)
    )


def _parse_attempt_accusation(payload: dict[str, Any], client_cmd_id: str) -> ParsedCommandPayload:
    suspect_id = _require_non_empty_str(payload, field="suspect_id", client_cmd_id=client_cmd_id)
    supporting_fact_ids = _require_string_list(
        payload,
        field="supporting_fact_ids",
        client_cmd_id=client_cmd_id,
    )
    supporting_evidence_ids = _require_string_list(
        payload,
        field="supporting_evidence_ids",
        client_cmd_id=client_cmd_id,
    )
    return AttemptAccusationCommandPayload(
        suspect_id=suspect_id,
        supporting_fact_ids=supporting_fact_ids,
        supporting_evidence_ids=supporting_evidence_ids,
    )


_PAYLOAD_PARSERS: dict[EnqueteurCommandType, PayloadParser] = {
    "INVESTIGATE_OBJECT": _parse_investigate_object,
    "DIALOGUE_TURN": _parse_dialogue_turn,
    "MINIGAME_SUBMIT": _parse_minigame_submit,
    "ATTEMPT_RECOVERY": _parse_attempt_recovery,
    "ATTEMPT_ACCUSATION": _parse_attempt_accusation,
}


__all__ = [
    "ENQUETEUR_INPUT_COMMAND_TYPES",
    "UNKNOWN_CLIENT_CMD_ID",
    "EnqueteurCommandType",
    "InvestigateObjectCommandPayload",
    "DialogueTurnCommandPayload",
    "MinigameSubmitCommandPayload",
    "AttemptRecoveryCommandPayload",
    "AttemptAccusationCommandPayload",
    "ParsedCommandPayload",
    "ParsedInputCommand",
    "CommandDispatchResult",
    "InputCommandValidationError",
    "parse_enqueteur_input_command",
]
