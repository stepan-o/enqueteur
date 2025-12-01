"""Belief substrate components (Sprint 3.3).

These components live primarily in L3 (belief & concept) with social bridges.
All data is numeric/ID-based and Rust-portable per SOT-SIM4-ECS-SUBSTRATE-COMPONENTS.
No natural-language strings are stored in these components.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ..entity import EntityID


@dataclass
class BeliefGraphSubstrate:
    """
    Belief graph substrate (L3).

    - nodes: hashed concept/belief IDs.
    - edges: pairs of indices into `nodes` (not raw IDs).
    - weights: numeric strength/confidence per edge.
    - last_updated_tick: tick index when the graph was last updated.

    Optional fields like source_tags remain numeric only.
    """

    nodes: List[int]              # hashed concept IDs
    edges: List[Tuple[int, int]]  # indices into nodes
    weights: List[float]
    last_updated_tick: int
    # Optional per SOT: numeric tags for edge sources
    source_tags: List[int] | None = None


@dataclass
class AgentInferenceState:
    """
    Inference tracking substrate (L3).

    Tracks pending updates and uncertainty metrics for the belief graph.
    """

    pending_updates: int
    last_inference_tick: int
    uncertainty_score: float
    epistemic_drift: float


@dataclass
class SocialBeliefWeights:
    """
    Social belief weights (L3 with social bridge).

    Numeric beliefs about others:
    - perceived_reputation: overall reputation score.
    - perceived_status: status or hierarchy.
    - perceived_alignment: -1..1 alignment (opponent ↔ ally).
    """

    perceived_reputation: Dict[EntityID, float]
    perceived_status: Dict[EntityID, float]
    perceived_alignment: Dict[EntityID, float]  # expected range -1..1 (enforced by systems)
