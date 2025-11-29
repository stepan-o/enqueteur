"""
World Builder (Era III)
=======================

Responsible ONLY for constructing:
    WorldState  ←  WorldIdentity

This builder:
    - Instantiates RoomState for every RoomIdentity
    - Applies optional scenario overrides
    - Validates adjacency consistency
    - Returns a clean WorldState with timeTick = 0

It performs **no simulation logic** and **no snapshot logic**.
Snapshots are produced by:
    - world_snapshot_builder.py
    - episode_builder.py
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from legacy.backend.loopforge_sim3.types.world_types import (
    WorldIdentity,
    RoomState,
    WorldState,
)


class WorldBuilder:

    # ----------------------------------------------------------------------
    # PUBLIC API
    # ----------------------------------------------------------------------

    @staticmethod
    def build(
            identity: WorldIdentity,
            scenario_modifiers: Optional[Dict[str, Any]] = None,
    ) -> WorldState:
        """
        Build a fully-initialized WorldState from a WorldIdentity.

        Parameters
        ----------
        identity : WorldIdentity
            Static definition of the world.
        scenario_modifiers : Optional[Dict[str, Any]]
            Scenario-level configuration that can override tension,
            starting hazards, or initial state flags.

            Supported keys:
                - "tension_override": Dict[room_id → float]
                - "initial_hazards": Dict[room_id → List[str]]
                - "initial_flags": Dict[room_id → Dict[str, Any]]

        Returns
        -------
        WorldState
            Mutable runtime world state ready for simulation.
        """

        scenario_modifiers = scenario_modifiers or {}

        # Build room states
        room_states: Dict[str, RoomState] = {}

        for room_id, room_identity in identity.rooms.items():
            base_tension = room_identity.baseTension

            # Optional scenario tension overrides
            if "tension_override" in scenario_modifiers:
                base_tension = scenario_modifiers["tension_override"].get(
                    room_id, base_tension
                )

            # Initialize state
            room_state = RoomState(
                id=room_id,
                currentTension=base_tension,
                incidents=0,
                flags={}
            )

            # Optional scenario hazards
            if "initial_hazards" in scenario_modifiers:
                hazards = scenario_modifiers["initial_hazards"].get(room_id)
                if hazards:
                    room_state.flags["hazards"] = list(hazards)

            # Optional initial flags
            if "initial_flags" in scenario_modifiers:
                extra_flags = scenario_modifiers["initial_flags"].get(room_id)
                if extra_flags:
                    room_state.flags.update(extra_flags)

            room_states[room_id] = room_state

        # Validate adjacency graph
        WorldBuilder._validate_adjacency(identity)

        # Construct and return full world state
        return WorldState(
            identity=identity,
            rooms=room_states,
            timeTick=0,
        )

    # ----------------------------------------------------------------------
    # INTERNAL
    # ----------------------------------------------------------------------

    @staticmethod
    def _validate_adjacency(identity: WorldIdentity):
        """
        Ensure adjacency references are consistent.

        Warns (does not raise) if:
            - A room references a nonexistent neighbor
            - A neighbor link is unidirectional (A lists B but B doesn't list A)

        Purpose:
            - Prevent broken navigation
            - Help scenario authors catch typos
        """
        room_ids = set(identity.rooms.keys())

        for room_id, neighbors in identity.adjacency.items():
            for n in neighbors:
                if n not in room_ids:
                    print(
                        f"[WARN] World '{identity.id}': "
                        f"Room '{room_id}' references unknown neighbor '{n}'."
                    )

        # Check symmetry
        for room_id, neighbors in identity.adjacency.items():
            for n in neighbors:
                if room_id not in identity.adjacency.get(n, []):
                    print(
                        f"[WARN] World '{identity.id}': "
                        f"Asymmetric adjacency: '{room_id}' lists '{n}' "
                        f"but '{n}' does not list '{room_id}'."
                    )
