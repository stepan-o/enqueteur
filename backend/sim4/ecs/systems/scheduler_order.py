from __future__ import annotations

"""
Canonical scheduler order for ECS systems (Phases B–E).

Per SOT-SIM4-ECS-SYSTEMS §4, this module declares the deterministic order of
system classes for phases B through E. The runtime/scheduler imports these lists
to instantiate and run systems in order. This module contains no logic — it is
purely declarative wiring and remains layer‑pure within ECS.
"""

from .perception_system import PerceptionSystem
from .cognitive_preprocessor import CognitivePreprocessor
from .emotion_gradient_system import EmotionGradientSystem
from .drive_update_system import DriveUpdateSystem
from .motive_formation_system import MotiveFormationSystem
from .plan_resolution_system import PlanResolutionSystem
from .social_update_system import SocialUpdateSystem
from .intent_resolver_system import IntentResolverSystem
from .movement_resolution_system import MovementResolutionSystem
from .object_workstation_system import ObjectWorkstationSystem
from .interaction_resolution_system import InteractionResolutionSystem
from .inventory_system import InventorySystem
from .action_execution_system import ActionExecutionSystem


# Canonical registry; runtime uses these lists to drive phases B–E.

PHASE_B_SYSTEMS = [
    PerceptionSystem,
]

PHASE_C_SYSTEMS = [
    CognitivePreprocessor,
    EmotionGradientSystem,
    DriveUpdateSystem,
    MotiveFormationSystem,
    PlanResolutionSystem,
    SocialUpdateSystem,
]

PHASE_D_SYSTEMS = [
    IntentResolverSystem,
    MovementResolutionSystem,
    ObjectWorkstationSystem,
    InteractionResolutionSystem,
    InventorySystem,
]

PHASE_E_SYSTEMS = [
    ActionExecutionSystem,
]


__all__ = [
    "PHASE_B_SYSTEMS",
    "PHASE_C_SYSTEMS",
    "PHASE_D_SYSTEMS",
    "PHASE_E_SYSTEMS",
]
