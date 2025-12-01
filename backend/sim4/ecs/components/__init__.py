"""
ECS substrate components package (Sprint 3.1).

Re-exports a minimal set of core mind-vector components for convenience.
All components are numeric/structural only and Rust-portable per SOT.
"""

from .identity import (
    AgentIdentity,
    ProfileTraits,
    SelfModelSubstrate,
    PersonaSubstrate,
)
from .drives import DriveState
from .emotion import EmotionFields
from .belief import BeliefGraphSubstrate, AgentInferenceState, SocialBeliefWeights
from .social import SocialSubstrate, SocialImpressionState, FactionAffinityState
from .motive_plan import (
    MotiveSubstrate,
    PlanStepSubstrate,
    PlanLayerSubstrate,
)

__all__ = [
    "AgentIdentity",
    "ProfileTraits",
    "SelfModelSubstrate",
    "PersonaSubstrate",
    "DriveState",
    "EmotionFields",
    "BeliefGraphSubstrate",
    "AgentInferenceState",
    "SocialBeliefWeights",
    "SocialSubstrate",
    "SocialImpressionState",
    "FactionAffinityState",
    "MotiveSubstrate",
    "PlanStepSubstrate",
    "PlanLayerSubstrate",
]
