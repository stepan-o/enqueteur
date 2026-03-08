from __future__ import annotations

"""Deterministic fallback + adapter-output normalization layer (Phase 8C).

This module keeps optional adapter output presentation-only and fail-safe:
- adapter responses are normalized and validated against legal truth boundaries
- invalid/unsafe responses are rejected
- deterministic fallback output is always available
"""

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from .dialogue_adapter import (
    DialogueAdapterInput,
    DialogueAdapterOutput,
    OptionalDialoguePresentationAdapter,
    validate_dialogue_adapter_output,
)


AdapterOutputSource = Literal["adapter", "fallback"]
AdapterFallbackReason = Literal[
    "adapter_ok",
    "adapter_disabled",
    "adapter_unavailable",
    "adapter_exception",
    "adapter_invalid_type",
    "adapter_invalid_structure",
    "adapter_invalid_value",
    "adapter_illegal_fact_reference",
    "adapter_turn_conflict",
]

_SUMMARY_REQUIRED_CODES = {
    "summary_required",
    "summary_needed",
    "summary_insufficient_facts",
    "summary_missing_key_fact",
}
_ALLOWED_METADATA_PREFIXES = (
    "mode:",
    "outcome:",
    "source:",
    "reason:",
    "status:",
    "npc:",
)
_MAX_PRESENTATION_TEXT_LEN = 220
_OUTPUT_ALLOWED_KEYS = {
    "npc_utterance_text",
    "short_rephrase_line",
    "hint_line",
    "summary_prompt_line",
    "response_mode_metadata",
    "referenced_fact_ids",
}


@dataclass(frozen=True)
class DialogueAdapterResolution:
    output: DialogueAdapterOutput
    source: AdapterOutputSource
    reason_code: AdapterFallbackReason
    normalized_from_mapping: bool


def _coerce_optional_string(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    text = value.strip()
    return text or None


def _coerce_string_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"{field_name} must be an array of strings")
    out: list[str] = []
    for row in value:
        if not isinstance(row, str):
            raise ValueError(f"{field_name} must contain only strings")
        cleaned = row.strip()
        if cleaned:
            out.append(cleaned)
    return tuple(sorted(set(out)))


def _normalize_line(value: str | None) -> str | None:
    if value is None:
        return None
    compact = " ".join(value.split()).strip()
    if not compact:
        return None
    if len(compact) <= _MAX_PRESENTATION_TEXT_LEN:
        return compact
    return compact[: _MAX_PRESENTATION_TEXT_LEN - 1].rstrip() + "…"


def _normalize_metadata(values: tuple[str, ...]) -> tuple[str, ...]:
    if len(values) > 8:
        raise ValueError("response_mode_metadata has too many entries")
    invalid = [row for row in values if not row.startswith(_ALLOWED_METADATA_PREFIXES)]
    if invalid:
        raise ValueError("response_mode_metadata contains unsupported tokens")
    return values


def _canonicalize_output(output: DialogueAdapterOutput) -> DialogueAdapterOutput:
    utterance = _normalize_line(output.npc_utterance_text)
    if utterance is None:
        raise ValueError("npc_utterance_text must be non-empty")
    return DialogueAdapterOutput(
        npc_utterance_text=utterance,
        short_rephrase_line=_normalize_line(output.short_rephrase_line),
        hint_line=_normalize_line(output.hint_line),
        summary_prompt_line=_normalize_line(output.summary_prompt_line),
        response_mode_metadata=_normalize_metadata(output.response_mode_metadata),
        referenced_fact_ids=output.referenced_fact_ids,
    )


def _normalize_output_from_mapping(raw_output: Mapping[str, Any]) -> DialogueAdapterOutput:
    extra = sorted(set(raw_output.keys()).difference(_OUTPUT_ALLOWED_KEYS))
    if extra:
        raise ValueError(f"unknown output keys: {', '.join(extra)}")

    if "npc_utterance_text" not in raw_output:
        raise ValueError("npc_utterance_text is required")
    utterance = raw_output.get("npc_utterance_text")
    if not isinstance(utterance, str):
        raise ValueError("npc_utterance_text must be a string")
    utterance = utterance.strip()
    if not utterance:
        raise ValueError("npc_utterance_text must be non-empty")

    return DialogueAdapterOutput(
        npc_utterance_text=utterance,
        short_rephrase_line=_coerce_optional_string(raw_output.get("short_rephrase_line"), field_name="short_rephrase_line"),
        hint_line=_coerce_optional_string(raw_output.get("hint_line"), field_name="hint_line"),
        summary_prompt_line=_coerce_optional_string(raw_output.get("summary_prompt_line"), field_name="summary_prompt_line"),
        response_mode_metadata=_coerce_string_tuple(raw_output.get("response_mode_metadata"), field_name="response_mode_metadata"),
        referenced_fact_ids=_coerce_string_tuple(raw_output.get("referenced_fact_ids"), field_name="referenced_fact_ids"),
    )


def _validate_turn_compatibility(output: DialogueAdapterOutput, payload: DialogueAdapterInput) -> None:
    if payload.turn_status == "repair" and not output.short_rephrase_line:
        raise ValueError("repair turn output requires short_rephrase_line")
    if payload.summary_check_code in _SUMMARY_REQUIRED_CODES and not output.summary_prompt_line:
        raise ValueError("summary-required turn output requires summary_prompt_line")


def normalize_and_validate_adapter_output(
    raw_output: Any,
    payload: DialogueAdapterInput,
) -> tuple[DialogueAdapterOutput, bool]:
    """Normalize adapter output object and validate legal/safe compatibility."""

    normalized_from_mapping = False
    if isinstance(raw_output, DialogueAdapterOutput):
        output = raw_output
    elif isinstance(raw_output, Mapping):
        output = _normalize_output_from_mapping(raw_output)
        normalized_from_mapping = True
    else:
        raise TypeError("adapter output must be DialogueAdapterOutput or mapping")

    output = _canonicalize_output(output)
    validate_dialogue_adapter_output(output, payload)
    _validate_turn_compatibility(output, payload)
    return output, normalized_from_mapping


def build_deterministic_fallback_output(
    payload: DialogueAdapterInput,
    *,
    reason_code: AdapterFallbackReason,
) -> DialogueAdapterOutput:
    """Deterministic fallback phrasing for all dialogue turn categories."""

    status_line_by_status = {
        "accepted": "Réponse enregistrée.",
        "blocked_gate": "Ce n'est pas possible pour le moment.",
        "repair": "Réessaie avec une formulation plus précise en français.",
        "refused": "Je ne peux pas répondre à cette demande.",
        "invalid_intent": "Cette action ne convient pas dans cette scène.",
        "invalid_scene_state": "Cette scène n'est pas disponible maintenant.",
    }
    base = status_line_by_status.get(payload.turn_status, "Interaction enregistrée.")
    utterance = f"{base} ({payload.turn_code})"

    rephrase = None
    if payload.turn_status == "repair":
        mode = payload.repair_response_mode or "sentence_stem"
        rephrase = f"mode_reparation:{mode}"

    hint = None
    if payload.turn_status in {"repair", "blocked_gate"} and payload.learning_view is not None:
        hint = f"niveau_indice:{payload.learning_view.current_hint_level}"

    summary_prompt = None
    if payload.summary_check_code in _SUMMARY_REQUIRED_CODES:
        summary_prompt = "Fais un court resume en francais: qui, ou, quand."

    referenced = tuple(payload.turn_revealed_fact_ids)
    if payload.turn_status != "accepted":
        referenced = ()

    return DialogueAdapterOutput(
        npc_utterance_text=utterance,
        short_rephrase_line=rephrase,
        hint_line=hint,
        summary_prompt_line=summary_prompt,
        response_mode_metadata=(
            f"source:fallback",
            f"reason:{reason_code}",
            f"status:{payload.turn_status}",
            f"mode:{payload.runtime_response_mode}",
        ),
        referenced_fact_ids=referenced,
    )


def resolve_dialogue_adapter_output(
    payload: DialogueAdapterInput,
    *,
    adapter: OptionalDialoguePresentationAdapter | None,
    adapter_enabled: bool = True,
) -> DialogueAdapterResolution:
    """Resolve adapter output safely; always fall back deterministically."""

    if not adapter_enabled:
        return DialogueAdapterResolution(
            output=build_deterministic_fallback_output(payload, reason_code="adapter_disabled"),
            source="fallback",
            reason_code="adapter_disabled",
            normalized_from_mapping=False,
        )

    if adapter is None:
        return DialogueAdapterResolution(
            output=build_deterministic_fallback_output(payload, reason_code="adapter_unavailable"),
            source="fallback",
            reason_code="adapter_unavailable",
            normalized_from_mapping=False,
        )

    try:
        raw_output = adapter.render_turn(payload)
    except Exception:
        return DialogueAdapterResolution(
            output=build_deterministic_fallback_output(payload, reason_code="adapter_exception"),
            source="fallback",
            reason_code="adapter_exception",
            normalized_from_mapping=False,
        )

    try:
        output, normalized_from_mapping = normalize_and_validate_adapter_output(raw_output, payload)
    except TypeError:
        return DialogueAdapterResolution(
            output=build_deterministic_fallback_output(payload, reason_code="adapter_invalid_type"),
            source="fallback",
            reason_code="adapter_invalid_type",
            normalized_from_mapping=False,
        )
    except ValueError as exc:
        message = str(exc)
        if "outside legal visible slice" in message:
            reason: AdapterFallbackReason = "adapter_illegal_fact_reference"
        elif "requires" in message:
            reason = "adapter_turn_conflict"
        elif "unknown output keys" in message or "required" in message:
            reason = "adapter_invalid_structure"
        else:
            reason = "adapter_invalid_value"
        return DialogueAdapterResolution(
            output=build_deterministic_fallback_output(payload, reason_code=reason),
            source="fallback",
            reason_code=reason,
            normalized_from_mapping=False,
        )

    return DialogueAdapterResolution(
        output=output,
        source="adapter",
        reason_code="adapter_ok",
        normalized_from_mapping=normalized_from_mapping,
    )


__all__ = [
    "AdapterFallbackReason",
    "AdapterOutputSource",
    "DialogueAdapterResolution",
    "build_deterministic_fallback_output",
    "normalize_and_validate_adapter_output",
    "resolve_dialogue_adapter_output",
]
