"""
Sim3 Runtime State Types (Era III — Clean Version)
=================================================

This module defines ONLY:
    - AgentState  (mutable per-agent state)
    - SimState    (global runtime container)

❗ World runtime state is NOT defined here.
    The authoritative runtime world state is:
        loopforge_sim3.types.world_types.WorldState

This prevents duplication and keeps the world
identity → runtime → snapshot layering intact.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from legacy.backend.loopforge_sim3.types.identity_types import AgentIdentity
from legacy.backend.loopforge_sim3.types.world_types import WorldState   # canonical runtime world state
from legacy.backend.loopforge_sim3.config.scenario_config import ScenarioConfig


# ============================================================================
# A. AgentState — mutable per-agent runtime state
# ============================================================================

@dataclass
class AgentState:
    """
    Tracks the live state of an agent during simulation.

    Includes:
        - current room
        - stress
        - status flags
        - pending actions
        - dynamic trait evolution
        - pointer to static AgentIdentity
    """

    id: str                     # stable agent id
    room_id: str                # current room the agent occupies

    stress: float = 0.0         # runtime stress 0–1
    status_flags: List[str] = field(default_factory=list)
    pending_actions: List[str] = field(default_factory=list)
    dynamic_traits: Dict[str, float] = field(default_factory=dict)

    # Immutable identity (type + role + presets merged)
    identity: Optional[AgentIdentity] = None


# ============================================================================
# B. SimState — whole-simulation runtime container
# ============================================================================

@dataclass
class SimState:
    """
    Canonical representation of a running simulation.

    Contains:
        - scenario config + parameters
        - world runtime state
        - agent identities + agent runtime states
        - time progression (ticks, days)
        - RNG seed
        - controller flags (debug, overrides)
        - optional rich presence tracking
    """

    # Scenario identity + parameters
    scenario: ScenarioConfig
    rng_seed: int = 0

    # Time
    tick: int = 0
    day_index: int = 0

    # World state (imported from world_types runtime layer)
    world: Optional[WorldState] = None

    # Agents
    agent_identities: Dict[str, AgentIdentity] = field(default_factory=dict)
    agents: Dict[str, AgentState] = field(default_factory=dict)

    # Additional scenario-level modifiers
    scenario_params: Dict[str, object] = field(default_factory=dict)

    # Debug / control flags (for controllers & devtools)
    control_flags: Dict[str, object] = field(default_factory=dict)

    # Optional richer tracking: agent → room per tick
    agent_presence_history: Dict[int, Dict[str, str]] = field(default_factory=dict)

    def record_presence(self):
        """
        Store each agent’s room location for the current tick.
        Enables richer UI queries later (timeline overlays, transitions).
        """
        self.agent_presence_history[self.tick] = {
            agent_id: state.room_id
            for agent_id, state in self.agents.items()
        }
