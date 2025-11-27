"""
Sim3 Runtime State Types (Era III)
=================================

Defines the persistent, mutable state of a running simulation:
- WorldState: dynamic room + world data
- AgentState: dynamic per-agent state
- SimState: canonical container for the whole simulation runtime

These are the *live evolving state* mutated by:
    sim/controller.py
    state/world_state.py
    state/agent_state.py

And consumed by:
    recorder/trace_recorder.py
    episode/episode_builder.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from loopforge_sim3.types.identity_types import AgentIdentity
from loopforge_sim3.types.world_types import WorldIdentity
from loopforge_sim3.config.scenario_config import ScenarioConfig


# ---------------------------------------------------------------------------
# A. WorldState — dynamic & mutable
# ---------------------------------------------------------------------------

@dataclass
class WorldState:
    """
    Dynamic world-layer state:

    Includes:
        - dynamic room tension
        - hazards currently active
        - occupancy (agent counts)
        - global world modifiers (noise, instability)
    """

    # Room-level dynamic tension values, 0–1 range.
    room_tension: Dict[str, float] = field(default_factory=dict)

    # Hazards active in each room (e.g. ["overheat", "jam"]).
    hazards: Dict[str, List[str]] = field(default_factory=dict)

    # Room occupancy (agent-count by room).
    occupancy: Dict[str, int] = field(default_factory=dict)

    # World-level instability/noise dynamic parameters.
    world_noise: float = 0.0
    world_instability: float = 0.0

    # Pointer to identity to compute defaults if needed.
    world_identity: Optional[WorldIdentity] = None


# ---------------------------------------------------------------------------
# B. AgentState — everything mutable about one agent
# ---------------------------------------------------------------------------

@dataclass
class AgentState:
    """
    Mutable runtime state for one agent.

    Includes:
        - current room
        - stress value
        - status flags (fault, busy, idle, etc.)
        - pending actions for next tick
        - dynamic traits that may evolve over the episode
    """

    id: str                                # stable agent id

    # Live room location
    room_id: str

    # Stress level 0–1
    stress: float = 0.0

    # Status flags like ["fault", "arriving", "handoff"]
    status_flags: List[str] = field(default_factory=list)

    # Pending actions selected in the previous tick
    pending_actions: List[str] = field(default_factory=list)

    # Dynamic trait space (any runtime-evolving values)
    dynamic_traits: Dict[str, float] = field(default_factory=dict)

    # Immutable identity doc (shared)
    identity: Optional[AgentIdentity] = None


# ---------------------------------------------------------------------------
# C. SimState — complete runtime state container
# ---------------------------------------------------------------------------

@dataclass
class SimState:
    """
    The complete, mutable representation of a running simulation.

    Contains:
        - scenario identity + scenario parameters
        - world identity + dynamic world state
        - all agent identities + agent states
        - tick counter
        - current day index
        - RNG seed (for reproducibility)
    """

    # Scenario identity and configuration
    scenario: ScenarioConfig
    rng_seed: int = 0

    # Time progression
    tick: int = 0
    day_index: int = 0

    # World
    world_identity: Optional[WorldIdentity] = None
    world: Optional[WorldState] = None

    # Agents
    agent_identities: Dict[str, AgentIdentity] = field(default_factory=dict)
    agents: Dict[str, AgentState] = field(default_factory=dict)

    # Arbitrary scenario-level parameters (difficulty, pacing, etc.)
    scenario_params: Dict[str, object] = field(default_factory=dict)

    # For controller modules to store debug / control signals.
    control_flags: Dict[str, object] = field(default_factory=dict)
