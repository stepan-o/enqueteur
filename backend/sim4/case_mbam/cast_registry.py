from __future__ import annotations

"""Canonical MBAM recurring cast registry for Enqueteur v1.0.

This module owns fixed cast identity truth for Case 1 (MBAM). It is static and
deterministic by design, and is separate from seed-specific cast overlays in
CaseState.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal


FixedCastId = Literal["elodie", "marc", "samira", "laurent", "jo"]
IdentityRole = Literal["curator", "guard", "intern", "donor", "barista"]


def _tupleize(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    out = tuple(values)
    for value in out:
        if not isinstance(value, str) or not value:
            raise ValueError("CastRegistry string lists must contain non-empty strings")
    return out


@dataclass(frozen=True)
class PortraitConfig:
    base_portrait_id: str
    state_variants: tuple[str, ...]
    card_theme_id: str

    def __post_init__(self) -> None:
        if not self.base_portrait_id:
            raise ValueError("PortraitConfig.base_portrait_id must be non-empty")
        if not self.card_theme_id:
            raise ValueError("PortraitConfig.card_theme_id must be non-empty")
        object.__setattr__(self, "state_variants", _tupleize(self.state_variants))


@dataclass(frozen=True)
class CastIdentityEntry:
    npc_id: FixedCastId
    display_name: str
    identity_role: IdentityRole
    baseline_traits: tuple[str, ...]
    baseline_register: str
    tell_profile: tuple[str, ...]
    trust_triggers: tuple[str, ...]
    anti_triggers: tuple[str, ...]
    portrait_config: PortraitConfig

    def __post_init__(self) -> None:
        if not self.display_name:
            raise ValueError("CastIdentityEntry.display_name must be non-empty")
        if not self.baseline_register:
            raise ValueError("CastIdentityEntry.baseline_register must be non-empty")
        object.__setattr__(self, "baseline_traits", _tupleize(self.baseline_traits))
        object.__setattr__(self, "tell_profile", _tupleize(self.tell_profile))
        object.__setattr__(self, "trust_triggers", _tupleize(self.trust_triggers))
        object.__setattr__(self, "anti_triggers", _tupleize(self.anti_triggers))


_CAST_REGISTRY = MappingProxyType(
    {
        "elodie": CastIdentityEntry(
            npc_id="elodie",
            display_name="Élodie Marchand",
            identity_role="curator",
            baseline_traits=("proud", "precise", "impatient_with_vagueness"),
            baseline_register="formal_fr",
            tell_profile=("exact_wording", "exact_times"),
            trust_triggers=("polite_register", "accurate_summary"),
            anti_triggers=("sloppy_accusation",),
            portrait_config=PortraitConfig(
                base_portrait_id="elodie_base",
                state_variants=("calm", "guarded", "annoyed", "stressed"),
                card_theme_id="museum_formal",
            ),
        ),
        "marc": CastIdentityEntry(
            npc_id="marc",
            display_name="Marc Dutil",
            identity_role="guard",
            baseline_traits=("procedural", "tired", "rule_bound"),
            baseline_register="direct_protocol_fr",
            tell_profile=("procedure_first", "access_gatekeeper"),
            trust_triggers=("respectful_tone", "competence"),
            anti_triggers=("bypass_process",),
            portrait_config=PortraitConfig(
                base_portrait_id="marc_base",
                state_variants=("neutral", "procedural", "annoyed", "helpful"),
                card_theme_id="security_plain",
            ),
        ),
        "samira": CastIdentityEntry(
            npc_id="samira",
            display_name="Samira B.",
            identity_role="intern",
            baseline_traits=("anxious", "eager", "oversharing"),
            baseline_register="simple_fr_with_anglicisms",
            tell_profile=("too_many_details_when_nervous",),
            trust_triggers=("calm_reassurance",),
            anti_triggers=("early_pressure",),
            portrait_config=PortraitConfig(
                base_portrait_id="samira_base",
                state_variants=("nervous", "helpful", "flustered", "guarded"),
                card_theme_id="intern_warm",
            ),
        ),
        "laurent": CastIdentityEntry(
            npc_id="laurent",
            display_name="Laurent Vachon",
            identity_role="donor",
            baseline_traits=("polished", "status_aware", "defensive"),
            baseline_register="polished_formal_fr",
            tell_profile=("avoids_exact_times",),
            trust_triggers=("tact", "formality"),
            anti_triggers=("disrespect",),
            portrait_config=PortraitConfig(
                base_portrait_id="laurent_base",
                state_variants=("amused", "guarded", "defensive", "cold"),
                card_theme_id="vip_refined",
            ),
        ),
        "jo": CastIdentityEntry(
            npc_id="jo",
            display_name="Jo Leclerc",
            identity_role="barista",
            baseline_traits=("observant", "casual", "social"),
            baseline_register="montreal_casual_fr",
            tell_profile=("remembers_clothes_and_vibes",),
            trust_triggers=("friendly_specificity",),
            anti_triggers=("stiff_interrogation",),
            portrait_config=PortraitConfig(
                base_portrait_id="jo_base",
                state_variants=("relaxed", "curious", "helpful", "uncertain"),
                card_theme_id="cafe_casual",
            ),
        ),
    }
)


def list_cast_ids() -> tuple[FixedCastId, ...]:
    """Return fixed MBAM cast ids in canonical deterministic order."""
    return tuple(_CAST_REGISTRY.keys())


def get_cast_entry(npc_id: str) -> CastIdentityEntry:
    """Return a cast identity entry by id."""
    if npc_id not in _CAST_REGISTRY:
        expected = ", ".join(list_cast_ids())
        raise KeyError(f"Unknown cast npc_id: {npc_id!r}; expected one of {expected}")
    return _CAST_REGISTRY[npc_id]  # type: ignore[return-value]


def get_cast_registry() -> dict[FixedCastId, CastIdentityEntry]:
    """Return a deterministic copy of the fixed MBAM cast registry."""
    return {npc_id: _CAST_REGISTRY[npc_id] for npc_id in list_cast_ids()}


__all__ = [
    "FixedCastId",
    "IdentityRole",
    "PortraitConfig",
    "CastIdentityEntry",
    "list_cast_ids",
    "get_cast_entry",
    "get_cast_registry",
]
