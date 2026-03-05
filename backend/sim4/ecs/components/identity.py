"""Identity and persona substrate components (Sprint 3.1).

These components live primarily in mind layers L3/L4 (identity, traits,
self-model) and L7 (persona aesthetic vectors). Shapes are strictly
numeric/structural and Rust-portable per SOT-SIM4-ECS-SUBSTRATE-COMPONENTS.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..entity import EntityID


@dataclass
class AgentIdentity:
    """
    Agent identity substrate (L3).

    Numeric-only handle for an agent's stable identity and role.
    All fields are Rust-portable primitives or IDs.
    """

    id: EntityID
    canonical_name_id: int
    role_code: int
    generation: int
    seed: int


@dataclass
class ProfileTraits:
    """
    Stable personality trait substrate (L3/L4 predispositions).

    Values are typically in a bounded numeric range (e.g. 0–1),
    but clamping and interpretation are handled by systems.
    """

    introversion: float
    volatility: float
    conscientiousness: float
    agreeableness: float
    openness: float
    risk_tolerance: float


@dataclass
class SelfModelSubstrate:
    """
    Self-model numeric substrate (L3).

    Represents identity coherence, drift, and internal contradictions.
    Narrative interprets this; ECS stores only numbers.
    """

    identity_vector: list[float]
    self_consistency_pressure: float
    contradiction_count: int
    drift_score: float


@dataclass
class PersonaSubstrate:
    """
    Aesthetic/persona substrate (L7 numeric).

    Encodes style and symbolic preferences in numeric vectors only.
    No semantic labels are stored here.
    """

    style_vector: list[float]
    symbol_affinity_vector: list[float]
    expressiveness: float
    voice_register: float
