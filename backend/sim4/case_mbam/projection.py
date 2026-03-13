from __future__ import annotations

"""Projection helpers for exporting MBAM Case Truth.

These helpers provide explicit output surfaces:
- visible projection: safe to include in player-facing replay/snapshots
- debug projection: private case truth intended for DEBUG-channel artifacts only
"""

from dataclasses import asdict
from typing import Any, Mapping

from .cast_registry import FixedCastId, list_cast_ids
from .dialogue_runtime import DialogueSceneRuntimeState, DialogueTurnLogEntry
from .investigation_progress import (
    InvestigationProgressState,
    contradiction_required_for_accusation,
    contradiction_requirement_satisfied_for_accusation,
)
from .learning_state import (
    build_debug_learning_projection,
    build_visible_learning_projection,
)
from .models import CaseState
from .npc_state import NPCState
from .object_state import (
    MbamObjectId,
    MbamObjectStateBundle,
    get_affordances_for_object,
    get_object_state_by_id,
    list_mbam_object_ids,
)
from .presentation_localization import (
    localize_dialogue_support_text,
    localize_dialogue_utterance_text,
    localize_presentation_key,
    normalize_presentation_locale,
)


def _require_positive_epoch(truth_epoch: int) -> int:
    epoch = int(truth_epoch)
    if epoch <= 0:
        raise ValueError("truth_epoch must be >= 1")
    return epoch


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return value


def build_visible_case_projection(case_state: CaseState, *, truth_epoch: int = 1) -> dict[str, Any]:
    """Build the minimal visible case projection for snapshots/exports."""
    epoch = _require_positive_epoch(truth_epoch)
    visible_slice = case_state.visible_case_slice
    return {
        "case_id": case_state.case_id,
        "seed": case_state.seed,
        "truth_epoch": epoch,
        "visible_case_slice": {
            "public_room_ids": list(visible_slice.public_room_ids),
            "public_object_ids": list(visible_slice.public_object_ids),
            "starting_scene_id": visible_slice.starting_scene_id,
            "starting_known_fact_ids": list(visible_slice.starting_known_fact_ids),
        },
    }


def build_debug_case_projection(case_state: CaseState, *, truth_epoch: int = 1) -> dict[str, Any]:
    """Build private case-truth projection for DEBUG-only exports."""
    epoch = _require_positive_epoch(truth_epoch)
    return {
        "case_id": case_state.case_id,
        "seed": case_state.seed,
        "truth_epoch": epoch,
        "debug_scope": "case_truth_private",
        "roles_assignment": asdict(case_state.roles_assignment),
        "hidden_case_slice": {
            "private_fact_ids": list(case_state.hidden_case_slice.private_fact_ids),
            "private_overlay_flags": list(case_state.hidden_case_slice.private_overlay_flags),
        },
    }


def _sanitize_visible_behavior_flags(flags: tuple[str, ...]) -> tuple[str, ...]:
    # Keep visible behavior hints while preventing accidental leakage of
    # role/method/seed-private traces if future flags are added.
    hidden_prefixes = (
        "overlay_",
        "seed_",
        "slot_",
        "method_",
        "drop_",
        "culprit_",
        "misdirector_",
        "ally_",
    )
    return tuple(flag for flag in flags if not flag.startswith(hidden_prefixes))


def _label_title_for_seed(seed: str, *, locale: str = "fr") -> str:
    _ = seed
    key = _label_title_key_for_seed(seed)
    normalized_locale = normalize_presentation_locale(locale, default="fr")
    return (
        localize_presentation_key(
            key,
            locale=normalized_locale,
            fallback="Le Medaillon des Voyageurs",
        )
        or "Le Medaillon des Voyageurs"
    )


def _label_title_key_for_seed(seed: str) -> str:
    _ = seed
    return "mbam.clue.wall_label.title"


def _label_date_for_seed(seed: str) -> str:
    _ = seed
    return "1898"


def _receipt_item_for_seed(seed: str, *, locale: str = "fr") -> str:
    key = _receipt_item_key_for_seed(seed)
    normalized_locale = normalize_presentation_locale(locale, default="fr")
    if seed == "A":
        fallback = "cafe filtre"
    elif seed == "B":
        fallback = "croissant"
    else:
        fallback = "espresso"
    return localize_presentation_key(key, locale=normalized_locale, fallback=fallback) or fallback


def _receipt_item_key_for_seed(seed: str) -> str:
    token = seed.strip().lower()
    if token not in {"a", "b", "c"}:
        token = "c"
    return f"mbam.clue.receipt.item.{token}"


def _torn_note_puzzle_for_seed(seed: str, *, locale: str = "fr") -> dict[str, Any]:
    normalized_locale = normalize_presentation_locale(locale, default="fr")

    if seed == "A":
        fallback_prompt = "___ de ___ vers ___"
        fallback_options = ["chariot", "livraison", "17h58", "badge", "vitrine"]
        option_keys = [
            "mbam.clue.torn_note.a.option.chariot",
            "mbam.clue.torn_note.a.option.livraison",
            "mbam.clue.torn_note.a.option.time_1758",
            "mbam.clue.torn_note.a.option.badge",
            "mbam.clue.torn_note.a.option.vitrine",
        ]
        prompt_key = "mbam.clue.torn_note.a.prompt"
        return {
            "variant_id": "torn_note_a",
            "prompt": localize_presentation_key(
                prompt_key,
                locale=normalized_locale,
                fallback=fallback_prompt,
            ) or fallback_prompt,
            "options": [
                localize_presentation_key(key, locale=normalized_locale, fallback=fallback) or fallback
                for key, fallback in zip(option_keys, fallback_options, strict=True)
            ],
            "prompt_key": prompt_key,
            "option_keys": option_keys,
        }
    if seed == "B":
        fallback_prompt = "___ de ___ avant ___ heures"
        fallback_options = ["pret", "badge", "dix-huit", "chariot", "vitrine"]
        option_keys = [
            "mbam.clue.torn_note.b.option.pret",
            "mbam.clue.torn_note.b.option.badge",
            "mbam.clue.torn_note.b.option.dix_huit",
            "mbam.clue.torn_note.b.option.chariot",
            "mbam.clue.torn_note.b.option.vitrine",
        ]
        prompt_key = "mbam.clue.torn_note.b.prompt"
        return {
            "variant_id": "torn_note_b",
            "prompt": localize_presentation_key(
                prompt_key,
                locale=normalized_locale,
                fallback=fallback_prompt,
            ) or fallback_prompt,
            "options": [
                localize_presentation_key(key, locale=normalized_locale, fallback=fallback) or fallback
                for key, fallback in zip(option_keys, fallback_options, strict=True)
            ],
            "prompt_key": prompt_key,
            "option_keys": option_keys,
        }
    fallback_prompt = "___ laissee ___ pres de ___"
    fallback_options = ["vitrine", "entre-ouverte", "17h58", "badge", "livraison"]
    option_keys = [
        "mbam.clue.torn_note.c.option.vitrine",
        "mbam.clue.torn_note.c.option.entre_ouverte",
        "mbam.clue.torn_note.c.option.time_1758",
        "mbam.clue.torn_note.c.option.badge",
        "mbam.clue.torn_note.c.option.livraison",
    ]
    prompt_key = "mbam.clue.torn_note.c.prompt"
    return {
        "variant_id": "torn_note_c",
        "prompt": localize_presentation_key(
            prompt_key,
            locale=normalized_locale,
            fallback=fallback_prompt,
        ) or fallback_prompt,
        "options": [
            localize_presentation_key(key, locale=normalized_locale, fallback=fallback) or fallback
            for key, fallback in zip(option_keys, fallback_options, strict=True)
        ],
        "prompt_key": prompt_key,
        "option_keys": option_keys,
    }


def build_visible_npc_semantic_projection(
    npc_states: Mapping[FixedCastId, NPCState],
) -> list[dict[str, Any]]:
    """Build safe NPC semantic projection for replay/frontend-visible paths."""
    out: list[dict[str, Any]] = []
    for npc_id in list_cast_ids():
        state = npc_states.get(npc_id)
        if state is None:
            continue
        out.append(
            {
                "npc_id": state.npc_id,
                "current_room_id": state.current_room_id,
                "availability": state.availability,
                "trust": state.trust,
                "stress": state.stress,
                "stance": state.stance,
                "emotion": state.emotion,
                "soft_alignment_hint": state.soft_alignment_hint,
                "visible_behavior_flags": list(_sanitize_visible_behavior_flags(state.visible_behavior_flags)),
                "current_scene_id": state.current_scene_id,
                "card_state": {
                    "portrait_variant": state.card_state.portrait_variant,
                    "tell_cue": state.card_state.tell_cue,
                    "suggested_interaction_mode": state.card_state.suggested_interaction_mode,
                    "trust_trend": state.card_state.trust_trend,
                },
            }
        )
    return out


def build_debug_npc_semantic_projection(
    npc_states: Mapping[FixedCastId, NPCState],
) -> list[dict[str, Any]]:
    """Build debug/private NPC semantic projection for developer replay artifacts."""
    out: list[dict[str, Any]] = []
    for npc_id in list_cast_ids():
        state = npc_states.get(npc_id)
        if state is None:
            continue
        out.append(
            {
                "npc_id": state.npc_id,
                "overlay_role_slot": state.overlay_role_slot,
                "overlay_helpfulness": state.overlay_helpfulness,
                "current_room_id": state.current_room_id,
                "availability": state.availability,
                "trust": state.trust,
                "stress": state.stress,
                "stance": state.stance,
                "emotion": state.emotion,
                "soft_alignment_hint": state.soft_alignment_hint,
                "visible_behavior_flags": list(state.visible_behavior_flags),
                "known_fact_flags": list(state.known_fact_flags),
                "belief_flags": list(state.belief_flags),
                "hidden_flags": list(state.hidden_flags),
                "misremember_flags": list(state.misremember_flags),
                "current_scene_id": state.current_scene_id,
                "schedule_state": asdict(state.schedule_state),
                "card_state": asdict(state.card_state),
            }
        )
    return out


def _observed_affordances_by_object(
    progress: InvestigationProgressState,
) -> dict[MbamObjectId, set[str]]:
    out: dict[MbamObjectId, set[str]] = {object_id: set() for object_id in list_mbam_object_ids()}
    for clue_id in progress.observed_clue_ids:
        if not clue_id.startswith("obs:"):
            continue
        parts = clue_id.split(":")
        if len(parts) != 3:
            continue
        _, object_id, affordance_id = parts
        if object_id not in out:
            continue
        out[object_id].add(affordance_id)
    return out


def _visible_known_state_for_object(
    object_id: MbamObjectId,
    *,
    case_state: CaseState,
    object_state: MbamObjectStateBundle,
    progress: InvestigationProgressState,
    observed_affordances: set[str],
    locale: str = "fr",
) -> dict[str, Any]:
    state = get_object_state_by_id(object_state, object_id)
    out: dict[str, Any] = {}

    if object_id == "O1_DISPLAY_CASE":
        s = state  # type: ignore[assignment]
        if "inspect" in observed_affordances or "check_lock" in observed_affordances:
            out["locked"] = s.locked
            out["latch_condition"] = s.latch_condition
        if "inspect" in observed_affordances:
            out["contains_item"] = s.contains_item
            out["tampered"] = s.tampered
        if "examine_surface" in observed_affordances:
            out["surface_examined"] = True
    elif object_id == "O2_MEDALLION":
        s = state  # type: ignore[assignment]
        if "examine" in observed_affordances:
            out["status"] = s.status
            out["examined"] = s.examined
            if s.status != "missing":
                out["location"] = s.location
    elif object_id == "O3_WALL_LABEL":
        s = state  # type: ignore[assignment]
        if "read" in observed_affordances:
            out["text_variant_id"] = s.text_variant_id
            out["title"] = _label_title_for_seed(case_state.seed, locale=locale)
            out["title_key"] = _label_title_key_for_seed(case_state.seed)
            out["date"] = _label_date_for_seed(case_state.seed)
    elif object_id == "O4_BENCH":
        s = state  # type: ignore[assignment]
        if "inspect" in observed_affordances:
            out["under_bench_item"] = s.under_bench_item
            known_evidence = set(progress.discovered_evidence_ids).union(progress.collected_evidence_ids)
            if "E1_TORN_NOTE" in known_evidence:
                puzzle = _torn_note_puzzle_for_seed(case_state.seed, locale=locale)
                out["torn_note_variant_id"] = puzzle["variant_id"]
                out["torn_note_prompt"] = puzzle["prompt"]
                out["torn_note_options"] = puzzle["options"]
                out["torn_note_prompt_key"] = puzzle["prompt_key"]
                out["torn_note_option_keys"] = puzzle["option_keys"]
    elif object_id == "O5_VISITOR_LOGBOOK":
        s = state  # type: ignore[assignment]
        if "read" in observed_affordances:
            out["entries_count"] = len(s.entries)
            out["scribble_pattern"] = s.scribble_pattern
    elif object_id == "O6_BADGE_TERMINAL":
        s = state  # type: ignore[assignment]
        if "request_access" in observed_affordances or "view_logs" in observed_affordances:
            out["online"] = s.online
            out["archived"] = s.archived
        if "view_logs" in observed_affordances:
            out["log_entry_count"] = len(s.log_entries)
            out["log_entries"] = [
                {
                    "badge_id": entry.badge_id,
                    "time": entry.time,
                    "door": entry.door,
                }
                for entry in s.log_entries
            ]
    elif object_id == "O7_SECURITY_BINDER":
        s = state  # type: ignore[assignment]
        if "read" in observed_affordances:
            out["page_state"] = s.page_state
    elif object_id == "O8_KEYPAD_DOOR":
        s = state  # type: ignore[assignment]
        if "inspect" in observed_affordances or "attempt_code" in observed_affordances:
            out["locked"] = s.locked
        if "inspect" in observed_affordances:
            out["has_code_hint"] = True
    elif object_id == "O9_RECEIPT_PRINTER":
        s = state  # type: ignore[assignment]
        if "ask_for_receipt" in observed_affordances or "read_receipt" in observed_affordances:
            out["receipt_count"] = len(s.recent_receipts)
        if "read_receipt" in observed_affordances and s.recent_receipts:
            out["latest_receipt_id"] = s.recent_receipts[0].receipt_id
        if "read_receipt" in observed_affordances:
            out["time"] = "17:52"
            out["item"] = _receipt_item_for_seed(case_state.seed, locale=locale)
            out["item_key"] = _receipt_item_key_for_seed(case_state.seed)
            out.setdefault(
                "latest_receipt_id",
                case_state.evidence_placement.cafe.receipt_id or f"R-{case_state.seed}-1752",
            )
    elif object_id == "O10_BULLETIN_BOARD":
        if "read" in observed_affordances:
            out["read"] = True

    return out


def build_visible_investigation_projection(
    *,
    case_state: CaseState,
    object_state: MbamObjectStateBundle,
    progress: InvestigationProgressState,
    truth_epoch: int = 1,
    locale: str = "fr",
) -> dict[str, Any]:
    """Build safe investigation-state projection for replay/player-visible paths."""
    epoch = _require_positive_epoch(truth_epoch)
    observed_by_object = _observed_affordances_by_object(progress)

    objects: list[dict[str, Any]] = []
    for object_id in list_mbam_object_ids():
        affordances = tuple(a.affordance_id for a in get_affordances_for_object(object_id))
        observed_affordances = tuple(sorted(observed_by_object.get(object_id, set())))
        known_state = _visible_known_state_for_object(
            object_id,
            case_state=case_state,
            object_state=object_state,
            progress=progress,
            observed_affordances=set(observed_affordances),
            locale=locale,
        )
        objects.append(
            {
                "object_id": object_id,
                "affordances": list(affordances),
                "observed_affordances": list(observed_affordances),
                "known_state": known_state,
            }
        )

    observed_not_collected = tuple(
        sorted(
            clue_id
            for clue_id in progress.observed_clue_ids
            if clue_id.startswith("clue:evidence:") and clue_id.endswith(":observed_not_collected")
        )
    )

    return {
        "truth_epoch": epoch,
        "objects": objects,
        "evidence": {
            "discovered_ids": list(progress.discovered_evidence_ids),
            "collected_ids": list(progress.collected_evidence_ids),
            "observed_not_collected_ids": list(observed_not_collected),
        },
        "facts": {
            "known_fact_ids": list(progress.known_fact_ids),
        },
        "contradictions": {
            "unlockable_edge_ids": list(progress.unlockable_contradiction_edge_ids),
            "known_edge_ids": list(progress.known_contradiction_edge_ids),
            "required_for_accusation": contradiction_required_for_accusation(case_state),
            "requirement_satisfied": contradiction_requirement_satisfied_for_accusation(case_state, progress),
        },
    }


def build_debug_investigation_projection(
    *,
    case_state: CaseState,
    object_state: MbamObjectStateBundle,
    progress: InvestigationProgressState,
    truth_epoch: int = 1,
) -> dict[str, Any]:
    """Build private investigation-state projection for DEBUG-channel artifacts."""
    epoch = _require_positive_epoch(truth_epoch)
    return {
        "debug_scope": "investigation_state_private",
        "case_id": case_state.case_id,
        "seed": case_state.seed,
        "truth_epoch": epoch,
        "object_state": _to_jsonable(asdict(object_state)),
        "progress": _to_jsonable(asdict(progress)),
        "contradiction_required_for_accusation": contradiction_required_for_accusation(case_state),
        "contradiction_requirement_satisfied": contradiction_requirement_satisfied_for_accusation(case_state, progress),
    }


def _visible_turn_log_row(
    entry: DialogueTurnLogEntry,
    *,
    visible_fact_ids: set[str],
    locale: str = "fr",
) -> dict[str, Any]:
    normalized_locale = normalize_presentation_locale(locale, default="fr")
    return {
        "turn_index": entry.turn_index,
        "scene_id": entry.scene_id,
        "npc_id": entry.npc_id,
        "intent_id": entry.intent_id,
        "status": entry.status,
        "code": entry.code,
        "outcome": entry.outcome,
        "response_mode": entry.response_mode,
        "revealed_fact_ids": [fact_id for fact_id in entry.revealed_fact_ids if fact_id in visible_fact_ids],
        "trust_delta": entry.trust_delta,
        "stress_delta": entry.stress_delta,
        "repair_response_mode": entry.repair_response_mode,
        "summary_check_code": entry.summary_check_code,
        "presentation_source": entry.presentation_source,
        "presentation_reason_code": entry.presentation_reason_code,
        "presentation_metadata": list(entry.presentation_metadata),
        "npc_utterance_text": localize_dialogue_utterance_text(
            entry.npc_utterance_text,
            locale=normalized_locale,
        ),
        "short_rephrase_line": localize_dialogue_support_text(
            entry.short_rephrase_line,
            locale=normalized_locale,
        ),
        "hint_line": localize_dialogue_support_text(
            entry.hint_line,
            locale=normalized_locale,
        ),
        "summary_prompt_line": localize_dialogue_support_text(
            entry.summary_prompt_line,
            locale=normalized_locale,
        ),
    }


def _debug_turn_log_row(entry: DialogueTurnLogEntry) -> dict[str, Any]:
    return _to_jsonable(asdict(entry))


def build_visible_dialogue_projection(
    *,
    case_state: CaseState,
    runtime_state: DialogueSceneRuntimeState,
    progress: InvestigationProgressState,
    recent_turns: tuple[DialogueTurnLogEntry, ...] = (),
    truth_epoch: int = 1,
    max_recent_turns: int = 8,
    locale: str = "fr",
) -> dict[str, Any]:
    """Build safe dialogue-state projection for replay/player-visible paths."""
    epoch = _require_positive_epoch(truth_epoch)
    known_fact_ids = set(progress.known_fact_ids)

    scene_rows = [
        {"scene_id": scene_id, "completion_state": completion_state}
        for scene_id, completion_state in runtime_state.scene_completion_states
    ]

    max_turns = max(0, int(max_recent_turns))
    tail = tuple(recent_turns[-max_turns:]) if max_turns else ()

    return {
        "truth_epoch": epoch,
        "active_scene_id": runtime_state.active_scene_id,
        "scene_completion": scene_rows,
        "surfaced_scene_ids": list(runtime_state.surfaced_scene_ids),
        "revealed_fact_ids": [
            fact_id for fact_id in runtime_state.revealed_fact_ids if fact_id in known_fact_ids
        ],
        "recent_turns": [
            _visible_turn_log_row(
                entry,
                visible_fact_ids=known_fact_ids,
                locale=locale,
            )
            for entry in tail
        ],
        "summary_rules": {
            "required_scene_ids": [
                scene_id
                for scene_id, definition in (
                    ("S1", runtime_state.scene_definitions.S1),
                    ("S2", runtime_state.scene_definitions.S2),
                    ("S3", runtime_state.scene_definitions.S3),
                    ("S4", runtime_state.scene_definitions.S4),
                    ("S5", runtime_state.scene_definitions.S5),
                )
                if definition.scene_state.summary_requirement.required
            ],
            "current_scene_min_fact_count": (
                getattr(runtime_state.scene_definitions, runtime_state.active_scene_id).scene_state.summary_requirement.min_fact_count
                if runtime_state.active_scene_id is not None
                else None
            ),
        },
        "contradiction_requirement_satisfied": contradiction_requirement_satisfied_for_accusation(
            case_state,
            progress,
        ),
        "learning": build_visible_learning_projection(
            case_state=case_state,
            runtime_state=runtime_state,
            progress=progress,
            recent_turns=recent_turns,
        ),
    }


def build_debug_dialogue_projection(
    *,
    case_state: CaseState,
    runtime_state: DialogueSceneRuntimeState,
    progress: InvestigationProgressState,
    recent_turns: tuple[DialogueTurnLogEntry, ...] = (),
    truth_epoch: int = 1,
) -> dict[str, Any]:
    """Build private dialogue-state projection for DEBUG-channel artifacts."""
    epoch = _require_positive_epoch(truth_epoch)
    return {
        "debug_scope": "dialogue_state_private",
        "case_id": case_state.case_id,
        "seed": case_state.seed,
        "truth_epoch": epoch,
        "runtime_state": _to_jsonable(asdict(runtime_state)),
        "recent_turns": [_debug_turn_log_row(entry) for entry in recent_turns],
        "known_fact_ids": list(progress.known_fact_ids),
        "known_evidence_ids": list(
            sorted(set(progress.discovered_evidence_ids).union(progress.collected_evidence_ids))
        ),
        "learning_private": build_debug_learning_projection(
            case_state=case_state,
            runtime_state=runtime_state,
            progress=progress,
            recent_turns=recent_turns,
        ),
    }


__all__ = [
    "build_visible_case_projection",
    "build_debug_case_projection",
    "build_visible_npc_semantic_projection",
    "build_debug_npc_semantic_projection",
    "build_visible_investigation_projection",
    "build_debug_investigation_projection",
    "build_visible_dialogue_projection",
    "build_debug_dialogue_projection",
]
