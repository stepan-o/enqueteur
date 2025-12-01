"""Social substrate components (Sprint 3.3).

Numeric social relationship substrate spanning L3/L4 (social beliefs +
emotional charge). All values are numeric/ID codes; no text labels.
Rust‑portable shapes only per SOT-SIM4-ECS-SUBSTRATE-COMPONENTS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..entity import EntityID


@dataclass
class SocialSubstrate:
    """
    Social relationship substrate (L3/L4).

    All values are numeric:
    - relationship_to: -1..+1 overall affinity.
    - trust_to: 0..1 trust.
    - respect_to: 0..1 admiration.
    - resentment_to: 0..1 grudges/resentment.
    """

    relationship_to: Dict[EntityID, float]
    trust_to: Dict[EntityID, float]
    respect_to: Dict[EntityID, float]
    resentment_to: Dict[EntityID, float]


@dataclass
class SocialImpressionState:
    """
    Social impression substrate (L3/L4).

    - impression_code_to: enum-coded impressions as ints.
    - misunderstanding_level_to: perceived misunderstanding level (0..1).
    """

    impression_code_to: Dict[EntityID, int]
    misunderstanding_level_to: Dict[EntityID, float]


@dataclass
class FactionAffinityState:
    """
    Faction affinity substrate (L3/L4).

    - faction_affinity: [-1, +1] affinity per faction ID.
    - faction_loyalty: [0, 1] loyalty per faction ID.
    """

    faction_affinity: Dict[int, float]
    faction_loyalty: Dict[int, float]
