from __future__ import annotations

"""Locale-aware presentation text lookup for MBAM backend-authored copy.

This module is presentation-only. It must not be used for truth semantics.
"""

from typing import Literal
import re

PresentationLocale = Literal["en", "fr"]

DEFAULT_PRESENTATION_LOCALE: PresentationLocale = "en"

_PRESENTATION_TEXT_BY_KEY: dict[str, dict[PresentationLocale, str]] = {
    "mbam.room.MBAM_LOBBY.label": {"en": "MBAM Lobby", "fr": "Hall MBAM"},
    "mbam.room.GALLERY_AFFICHES.label": {
        "en": "Gallery 1 - Poster Hall",
        "fr": "Galerie 1 - Salle des Affiches",
    },
    "mbam.room.SECURITY_OFFICE.label": {"en": "Security Office", "fr": "Bureau de securite"},
    "mbam.room.SERVICE_CORRIDOR.label": {"en": "Service Corridor", "fr": "Couloir de service"},
    "mbam.room.CAFE_DE_LA_RUE.label": {"en": "Cafe de la Rue", "fr": "Cafe de la Rue"},
    "mbam.clue.wall_label.title": {"en": "The Traveler's Medallion", "fr": "Le Medaillon des Voyageurs"},
    "mbam.clue.receipt.item.a": {"en": "filter coffee", "fr": "cafe filtre"},
    "mbam.clue.receipt.item.b": {"en": "croissant", "fr": "croissant"},
    "mbam.clue.receipt.item.c": {"en": "espresso", "fr": "espresso"},
    "mbam.clue.torn_note.a.prompt": {"en": "___ of ___ around ___", "fr": "___ de ___ vers ___"},
    "mbam.clue.torn_note.a.option.chariot": {"en": "cart", "fr": "chariot"},
    "mbam.clue.torn_note.a.option.livraison": {"en": "delivery", "fr": "livraison"},
    "mbam.clue.torn_note.a.option.time_1758": {"en": "17:58", "fr": "17h58"},
    "mbam.clue.torn_note.a.option.badge": {"en": "badge", "fr": "badge"},
    "mbam.clue.torn_note.a.option.vitrine": {"en": "display case", "fr": "vitrine"},
    "mbam.clue.torn_note.b.prompt": {"en": "___ of ___ before ___ o'clock", "fr": "___ de ___ avant ___ heures"},
    "mbam.clue.torn_note.b.option.pret": {"en": "loan", "fr": "pret"},
    "mbam.clue.torn_note.b.option.badge": {"en": "badge", "fr": "badge"},
    "mbam.clue.torn_note.b.option.dix_huit": {"en": "eighteen", "fr": "dix-huit"},
    "mbam.clue.torn_note.b.option.chariot": {"en": "cart", "fr": "chariot"},
    "mbam.clue.torn_note.b.option.vitrine": {"en": "display case", "fr": "vitrine"},
    "mbam.clue.torn_note.c.prompt": {"en": "___ left ___ near ___", "fr": "___ laissee ___ pres de ___"},
    "mbam.clue.torn_note.c.option.vitrine": {"en": "display case", "fr": "vitrine"},
    "mbam.clue.torn_note.c.option.entre_ouverte": {"en": "ajar", "fr": "entre-ouverte"},
    "mbam.clue.torn_note.c.option.time_1758": {"en": "17:58", "fr": "17h58"},
    "mbam.clue.torn_note.c.option.badge": {"en": "badge", "fr": "badge"},
    "mbam.clue.torn_note.c.option.livraison": {"en": "delivery", "fr": "livraison"},
}

_DIALOGUE_REPHRASE_BY_FR: dict[str, str] = {
    "Essaie avec une phrase guide simple.": "Try a simple guided sentence.",
    "Reformule avec une option plus claire.": "Rephrase with a clearer option.",
    "Change le ton et reste concret.": "Adjust your tone and stay concrete.",
    "Prends une autre piste, puis reviens.": "Try another lead, then return.",
    "Reformule brièvement.": "Rephrase briefly.",
}

_DIALOGUE_SUMMARY_PROMPT_BY_FR: dict[str, str] = {
    "Fais un court résumé en français avant de continuer.": "Give a short French summary before continuing.",
    "On continue après un résumé français bref et exact.": "Continue after a short, accurate French summary.",
    "Ajoute un fait vérifié de plus dans ton résumé.": "Add one more verified fact to your summary.",
    "Ajoute le fait clé manquant dans ton résumé.": "Add the missing key fact to your summary.",
    "Fais un court resume en francais: qui, ou, quand.": "Give a short French summary: who, where, when.",
}

_DIALOGUE_HINT_BY_FR: dict[str, str] = {
    "Indice: garde la structure qui, où, quand.": "Hint: keep the who, where, when structure.",
    "Indice: complète le modèle de phrase proposé.": "Hint: complete the suggested sentence model.",
    "Indice: choisis une reformulation plus précise.": "Hint: choose a more precise rephrase.",
    "Hint: plan your French line, then deliver it in French.": "Hint: plan your French line, then deliver it in French.",
    "Repère: garde la structure qui, où, quand.": "Guide: keep the who, where, when structure.",
    "Repère: complète le modèle de phrase proposé.": "Guide: complete the suggested sentence model.",
    "Repère: choisis une reformulation plus précise.": "Guide: choose a more precise rephrase.",
    "Guide: plan your French line, then deliver it in French.": "Guide: plan your French line, then deliver it in French.",
}

_DIALOGUE_UTTERANCE_BY_FR: dict[str, str] = {
    "Très bien. Restons précis.": "Alright. Let's stay precise.",
    "D'accord. On suit la procédure.": "Understood. We'll follow procedure.",
    "Oui, je peux clarifier ça.": "Yes, I can clarify that.",
    "Très bien, je réponds brièvement.": "Alright, I'll answer briefly.",
    "Oui, je me souviens de quelques détails.": "Yes, I remember a few details.",
    "Je ne peux pas valider ça sans base claire.": "I can't validate that without a clear basis.",
    "Refusé pour l'instant. Procédure incomplète.": "Denied for now. Procedure is incomplete.",
    "Je préfère ne pas confirmer ça maintenant.": "I prefer not to confirm that yet.",
    "Je ne répondrai pas à cette formulation.": "I won't answer that phrasing.",
    "J'peux pas confirmer ça comme ça.": "I can't confirm it like that.",
    "Pas encore. Il manque une condition d'accès.": "Not yet. An access condition is still missing.",
    "Je refuse cette demande.": "I refuse that request.",
    "Cette action ne correspond pas à la scène en cours.": "That action does not match the current scene.",
    "Cette scène n'est pas disponible pour ce tour.": "This scene is not available for this turn.",
    "Interaction enregistrée.": "Interaction recorded.",
    "Compris.": "Understood.",
    "Réponse enregistrée.": "Response recorded.",
    "Ce n'est pas possible pour le moment.": "That is not possible right now.",
    "Réessaie avec une formulation plus précise en français.": "Try again with a more precise French phrasing.",
    "Je ne peux pas répondre à cette demande.": "I can't answer that request.",
    "Cette action ne convient pas dans cette scène.": "That action does not fit this scene.",
    "Cette scène n'est pas disponible maintenant.": "This scene is not available right now.",
}

_DIALOGUE_UTTERANCE_SUFFIX_BY_FR: dict[str, str] = {
    " Reste factuel.": " Stay factual.",
    " On avance calmement.": " Let's proceed calmly.",
}

_MODE_LABELS_EN: dict[str, str] = {
    "sentence_stem": "sentence stem",
    "rephrase_choice": "rephrase choice",
    "meta_hint": "meta hint",
    "alternate_path": "alternate path",
}

_LEVEL_LABELS_EN: dict[str, str] = {
    "soft_hint": "soft hint",
    "sentence_stem": "sentence stem",
    "rephrase_choice": "rephrase choice",
    "english_meta_help": "English meta help",
}

_TRAILING_NAME_PATTERN = re.compile(r"^(.*)\s+\(([^()]*)\)$")
_FALLBACK_CODE_PATTERN = re.compile(r"^(.*)\s+\(([^()]*)\)$")
_MODE_REPARATION_PATTERN = re.compile(r"^mode_reparation:([a-z_]+)$")
_REPAIR_MODE_PATTERN = re.compile(r"^repair_mode:([a-z_]+)$")
_NIVEAU_INDICE_PATTERN = re.compile(r"^niveau_indice:([a-z_]+)$")
_HINT_LEVEL_PATTERN = re.compile(r"^hint_level:([a-z_]+)$")


def normalize_presentation_locale(
    value: object,
    *,
    default: PresentationLocale = DEFAULT_PRESENTATION_LOCALE,
) -> PresentationLocale:
    if not isinstance(value, str):
        return default
    token = value.strip().lower()
    if token.startswith("fr"):
        return "fr"
    if token.startswith("en"):
        return "en"
    return default


def localize_presentation_key(
    key: object,
    *,
    locale: PresentationLocale,
    fallback: str | None = None,
) -> str | None:
    if not isinstance(key, str) or not key:
        return fallback
    locale_text = _PRESENTATION_TEXT_BY_KEY.get(key)
    if locale_text is None:
        return fallback
    return (
        locale_text.get(locale)
        or locale_text.get(DEFAULT_PRESENTATION_LOCALE)
        or fallback
    )


def localize_dialogue_support_text(
    value: str | None,
    *,
    locale: PresentationLocale,
) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split()).strip()
    if not text:
        return None
    if locale == "fr":
        return text

    exact = _DIALOGUE_REPHRASE_BY_FR.get(text)
    if exact is not None:
        return exact
    exact = _DIALOGUE_HINT_BY_FR.get(text)
    if exact is not None:
        return exact
    exact = _DIALOGUE_SUMMARY_PROMPT_BY_FR.get(text)
    if exact is not None:
        return exact

    mode_reparation = _MODE_REPARATION_PATTERN.match(text)
    if mode_reparation is not None:
        mode = mode_reparation.group(1)
        return f"repair mode: {_MODE_LABELS_EN.get(mode, mode)}"

    repair_mode = _REPAIR_MODE_PATTERN.match(text)
    if repair_mode is not None:
        mode = repair_mode.group(1)
        return f"repair mode: {_MODE_LABELS_EN.get(mode, mode)}"

    niveau_indice = _NIVEAU_INDICE_PATTERN.match(text)
    if niveau_indice is not None:
        level = niveau_indice.group(1)
        return f"hint level: {_LEVEL_LABELS_EN.get(level, level)}"

    hint_level = _HINT_LEVEL_PATTERN.match(text)
    if hint_level is not None:
        level = hint_level.group(1)
        return f"hint level: {_LEVEL_LABELS_EN.get(level, level)}"

    if text == "resume_en_francais":
        return "Give a short French summary."

    return text


def localize_dialogue_utterance_text(
    value: str | None,
    *,
    locale: PresentationLocale,
) -> str | None:
    if value is None:
        return None
    text = " ".join(value.split()).strip()
    if not text:
        return None
    if locale == "fr":
        return text

    direct = _DIALOGUE_UTTERANCE_BY_FR.get(text)
    if direct is not None:
        return direct

    for suffix_fr, suffix_en in _DIALOGUE_UTTERANCE_SUFFIX_BY_FR.items():
        if text.endswith(suffix_fr):
            stem = text[: -len(suffix_fr)]
            localized_stem = localize_dialogue_utterance_text(stem, locale=locale) or stem
            return f"{localized_stem}{suffix_en}"

    trailing_name = _TRAILING_NAME_PATTERN.match(text)
    if trailing_name is not None:
        stem = trailing_name.group(1).strip()
        name = trailing_name.group(2).strip()
        localized_stem = localize_dialogue_utterance_text(stem, locale=locale) or stem
        if name:
            return f"{localized_stem} ({name})"
        return localized_stem

    fallback_code = _FALLBACK_CODE_PATTERN.match(text)
    if fallback_code is not None:
        stem = fallback_code.group(1).strip()
        code = fallback_code.group(2).strip()
        localized_stem = _DIALOGUE_UTTERANCE_BY_FR.get(stem, stem)
        if code:
            return f"{localized_stem} ({code})"
        return localized_stem

    return text
