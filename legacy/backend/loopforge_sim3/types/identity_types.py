"""
Sim3 Identity Types (Era III)
=============================

Defines the full identity layer for agents:
- AgentTypeDefinition: deep “DNA” identity
- RoleIdentity: functional / narrative role identity
- CastPreset: named scenario presets (“default_four_bots”, etc.)
- AgentInstanceConfig: scenario-level cast specification
- AgentIdentity: resolved identity used in simulation
- AgentCharacterSheet: UI-facing character sheet (StageEpisodeV2.cast)

This module contains ONLY static data definitions.
No simulation logic, no runtime state transitions.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Base stress structure
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StressProfile:
    baseline: float         # 0–1
    volatility: float       # 0–1


# ---------------------------------------------------------------------------
# Agent Type (deep identity)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentTypeDefinition:
    """
    Defines a fundamental agent type (e.g. WorkerBot, SupervisorBot).

    Provides default UI/narrative identity:
        - display name, short name
        - vibe, archetype
        - color theme, icon
        - stress profile
        - narrative hooks

    RoleIdentity and AgentInstanceConfig override these defaults.
    """

    type: str                             # canonical type name

    default_display_name: Optional[str] = None
    default_short_name: Optional[str] = None

    default_vibe: str = ""
    default_archetype: str = ""
    default_color_theme: str = "gray"
    default_icon_key: Optional[str] = None

    default_stress: Optional[StressProfile] = None
    default_hooks: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Role Identity (functional layer)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RoleIdentity:
    """
    Defines functional + narrative role identity.

    Examples:
        - "Line Worker"
        - "Supervisor"
        - "QA Bot"
        - "Maintenance"

    Role modifiers:
        - stress multipliers (baseline & volatility)
        - room affinity (where the agent tends to appear)
        - narrative tags (story hints)
    """

    role: str

    stress_multiplier: float = 1.0
    stress_volatility_multiplier: float = 1.0

    room_affinity: Optional[List[str]] = None
    narrative_tags: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Scenario Cast Presets
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CastPreset:
    """
    A named cast preset, used by scenarios:
        - "default_four_bots"
        - "maintenance_heavy"
        - "supervisor_shift"

    Contains a list of agent instance configs.
    """

    id: str
    name: str
    agents: List["AgentInstanceConfig"]


# ---------------------------------------------------------------------------
# Scenario-level agent instance config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentInstanceConfig:
    """
    Defines one agent’s participation in a scenario.

    Example:
        AgentInstanceConfig(
            id="sprocket",
            type="WorkerBot",
            role="Maintenance",
            presets={
                "display_name": "Sprocket",
                "vibe": "tense but hopeful",
                "color_theme": "blue"
            }
        )

    Presets override:
        - display name / short name
        - vibe, archetype
        - color theme, icon
        - stress profile
        - hooks
    """

    id: str
    type: str
    role: str
    presets: Dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Resolved identity used by runtime + EpisodeBuilder
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentIdentity:
    """
    Final merged identity for a single agent after:
        AgentTypeDefinition
      + RoleIdentity
      + AgentInstanceConfig.presets

    This is used by:
        - runtime/state initialization
        - EpisodeBuilder to produce AgentCharacterSheet
    """

    id: str
    display_name: str
    short_name: Optional[str]

    type: str
    role: str

    vibe: str
    archetype: str

    color_theme: str
    icon_key: Optional[str]

    stress: Optional[StressProfile]
    hooks: Optional[List[str]]

    traits: Dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# UI-facing character sheet
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentCharacterSheet:
    """
    UI-facing character model for StageEpisodeV2.cast[].

    STRICTLY UI-oriented:
    - frontend uses displayName, shortName, colors, archetype
    - no runtime-internal fields exposed
    """

    id: str
    displayName: str
    shortName: Optional[str]

    role: str
    type: str

    vibe: str
    archetype: str

    colorTheme: str
    iconKey: Optional[str]

    stressProfile: Optional[StressProfile] = None
    narrativeHooks: Optional[List[str]] = None
