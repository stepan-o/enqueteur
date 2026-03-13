from __future__ import annotations

"""Locale-aware presentation text lookup for MBAM backend-authored copy.

This module is presentation-only. It must not be used for truth semantics.
"""

from typing import Literal

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

