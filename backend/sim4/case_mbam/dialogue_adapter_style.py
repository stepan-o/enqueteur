from __future__ import annotations

"""MBAM-focused optional style adapter for dialogue phrasing (Phase 8D).

This adapter improves presentation text only. It must not alter truth,
progression, gates, or outcomes.
"""

from .cast_registry import get_cast_entry
from .dialogue_adapter import DialogueAdapterInput, DialogueAdapterOutput, OptionalDialoguePresentationAdapter


_ACCEPTED_LINE_BY_NPC: dict[str, str] = {
    "elodie": "Très bien. Restons précis.",
    "marc": "D'accord. On suit la procédure.",
    "samira": "Oui, je peux clarifier ça.",
    "laurent": "Très bien, je réponds brièvement.",
    "jo": "Oui, je me souviens de quelques détails.",
}

_REFUSED_LINE_BY_NPC: dict[str, str] = {
    "elodie": "Je ne peux pas valider ça sans base claire.",
    "marc": "Refusé pour l'instant. Procédure incomplète.",
    "samira": "Je préfère ne pas confirmer ça maintenant.",
    "laurent": "Je ne répondrai pas à cette formulation.",
    "jo": "J'peux pas confirmer ça comme ça.",
}

_REPAIR_LINE_BY_MODE: dict[str, str] = {
    "sentence_stem": "Essaie avec une phrase guide simple.",
    "rephrase_choice": "Reformule avec une option plus claire.",
    "meta_hint": "Change le ton et reste concret.",
    "alternate_path": "Prends une autre piste, puis reviens.",
}

_SUMMARY_PROMPT_BY_CODE: dict[str, str] = {
    "summary_required": "Fais un court résumé en français avant de continuer.",
    "summary_needed": "On continue après un résumé français bref et exact.",
    "summary_insufficient_facts": "Ajoute un fait vérifié de plus dans ton résumé.",
    "summary_missing_key_fact": "Ajoute le fait clé manquant dans ton résumé.",
}

_HINT_BY_LEVEL: dict[str, str] = {
    "soft_hint": "Indice: garde la structure qui, où, quand.",
    "sentence_stem": "Indice: complète le modèle de phrase proposé.",
    "rephrase_choice": "Indice: choisis une reformulation plus précise.",
    "english_meta_help": "Hint: plan your French line, then deliver it in French.",
}


def _clip(text: str, *, limit: int = 180) -> str:
    out = text.strip()
    if len(out) <= limit:
        return out
    return out[: limit - 1].rstrip() + "…"


def _accepted_line(payload: DialogueAdapterInput) -> str:
    base = _ACCEPTED_LINE_BY_NPC.get(payload.npc_id, "Compris.")
    if payload.visible_npc_state is None:
        return base
    if payload.visible_npc_state.emotion in {"guarded", "annoyed"}:
        return f"{base} Reste factuel."
    if payload.visible_npc_state.emotion in {"nervous", "stressed"}:
        return f"{base} On avance calmement."
    return base


def _repair_line(payload: DialogueAdapterInput) -> str:
    mode = payload.repair_response_mode or "sentence_stem"
    return _REPAIR_LINE_BY_MODE.get(mode, "Reformule brièvement.")


def _hint_line(payload: DialogueAdapterInput) -> str | None:
    if payload.learning_view is None:
        return None
    level = payload.learning_view.current_hint_level
    line = _HINT_BY_LEVEL.get(level)
    if line is None:
        return None
    if payload.learning_view.difficulty_profile == "D1":
        return line.replace("Indice:", "Repère:").replace("Hint:", "Guide:")
    return line


def _status_line(payload: DialogueAdapterInput) -> str:
    if payload.turn_status == "accepted":
        return _accepted_line(payload)
    if payload.turn_status == "repair":
        return _repair_line(payload)
    if payload.turn_status == "blocked_gate":
        return "Pas encore. Il manque une condition d'accès."
    if payload.turn_status == "refused":
        return _REFUSED_LINE_BY_NPC.get(payload.npc_id, "Je refuse cette demande.")
    if payload.turn_status == "invalid_intent":
        return "Cette action ne correspond pas à la scène en cours."
    if payload.turn_status == "invalid_scene_state":
        return "Cette scène n'est pas disponible pour ce tour."
    return "Interaction enregistrée."


class MbamStyleDialoguePresentationAdapter(OptionalDialoguePresentationAdapter):
    """Optional style adapter with deterministic MBAM phrasing templates."""

    def render_turn(self, payload: DialogueAdapterInput) -> DialogueAdapterOutput:
        cast_entry = get_cast_entry(payload.npc_id)
        npc_line = _status_line(payload)
        if payload.turn_status == "accepted" and payload.intent_id in {"ask_when", "ask_where", "ask_who"}:
            npc_line = f"{npc_line} ({cast_entry.display_name})"

        short_rephrase_line = None
        if payload.turn_status == "repair":
            short_rephrase_line = _repair_line(payload)

        summary_prompt_line = None
        if payload.summary_check_code in _SUMMARY_PROMPT_BY_CODE:
            summary_prompt_line = _SUMMARY_PROMPT_BY_CODE[payload.summary_check_code]
        hint_line = _hint_line(payload)

        output = DialogueAdapterOutput(
            npc_utterance_text=_clip(npc_line),
            short_rephrase_line=_clip(short_rephrase_line) if short_rephrase_line else None,
            hint_line=_clip(hint_line) if hint_line else None,
            summary_prompt_line=_clip(summary_prompt_line) if summary_prompt_line else None,
            response_mode_metadata=(
                "source:style_mbam_v1",
                f"status:{payload.turn_status}",
                f"mode:{payload.runtime_response_mode}",
                f"npc:{payload.npc_id}",
            ),
            referenced_fact_ids=tuple(payload.turn_revealed_fact_ids),
        )
        return output


__all__ = ["MbamStyleDialoguePresentationAdapter"]
