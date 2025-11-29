"""
Sim3 World Registry
===================

Central place to define world layouts available to the simulation.

This is *pure data*:
- no simulation logic
- no time evolution
- no agent interaction rules

Purpose:
- Give the runner and backend a stable spatial model
- Give the frontend clear anchors for rendering maps/layouts
- Allow scenarios to swap worlds without modifying sim code
"""

from __future__ import annotations
from typing import Dict, Any, List, TypedDict


# ------------------------------
# World Schema
# ------------------------------

class ZoneSpec(TypedDict, total=False):
    """One spatial zone or room inside the world."""
    desc: str                  # short description
    tension_base: float        # default tension field value
    hazards: List[str]         # optional hazard tags


class WorldSpec(TypedDict, total=False):
    """Full world definition."""
    name: str
    zones: Dict[str, ZoneSpec]          # zone_id → zone spec
    adjacency: Dict[str, List[str]]     # zone_id → neighboring zone_ids
    world_traits: Dict[str, Any]        # global world modifiers
    size: str                            # "small", "medium", "large"
    desc: str                             # human-friendly description


# ------------------------------
# World Layout Definitions
# ------------------------------

WORLD_LAYOUTS: Dict[str, WorldSpec] = {

    "factory_floor_v1": {
        "name": "factory_floor_v1",
        "desc": "Initial canonical factory layout: a compact rust-goth floor with basic zones.",
        "size": "medium",
        "zones": {
            "assembly": {
                "desc": "Primary assembly corridor with grounding rails.",
                "tension_base": 0.3,
                "hazards": ["mechanical_noise"]
            },
            "welding_bay": {
                "desc": "High-heat welding environment; flickers with ember residue.",
                "tension_base": 0.5,
                "hazards": ["heat", "sparks"]
            },
            "control_room": {
                "desc": "Supervisor nest; high visibility but low physical danger.",
                "tension_base": 0.2,
                "hazards": []
            },
            "storage": {
                "desc": "Low-light storage with tight aisles and unsettling echoes.",
                "tension_base": 0.4,
                "hazards": ["poor_visibility"]
            },
        },
        "adjacency": {
            "assembly": ["welding_bay", "control_room"],
            "welding_bay": ["assembly", "storage"],
            "control_room": ["assembly"],
            "storage": ["welding_bay"]
        },
        "world_traits": {
            "global_noise": 0.3,
            "vibration": 0.2,
            "air_quality": 0.4,
        },
    },

    "factory_floor_expanded": {
        "name": "factory_floor_expanded",
        "desc": "A more complex floorplan with branching corridors and risk clusters.",
        "size": "large",
        "zones": {
            "assembly": {
                "desc": "Main line corridor, wide and noisy.",
                "tension_base": 0.3,
                "hazards": ["mechanical_noise"]
            },
            "welding_bay": {
                "desc": "Heat and sparks dance unpredictably across the bay.",
                "tension_base": 0.6,
                "hazards": ["heat", "sparks"]
            },
            "control_room": {
                "desc": "Supervisor overlook with direct broadcast channels.",
                "tension_base": 0.2,
                "hazards": []
            },
            "storage": {
                "desc": "Dim aisles; tension rises when overloaded.",
                "tension_base": 0.4,
                "hazards": ["poor_visibility"]
            },
            "maintenance": {
                "desc": "Tool racks, exposed wiring, risky repair spots.",
                "tension_base": 0.5,
                "hazards": ["electrical"]
            },
            "perimeter": {
                "desc": "Shadowed corridor encircling the core factory.",
                "tension_base": 0.3,
                "hazards": ["drafts", "poor_visibility"]
            },
        },
        "adjacency": {
            "assembly": ["welding_bay", "control_room", "maintenance"],
            "welding_bay": ["assembly", "storage"],
            "control_room": ["assembly"],
            "storage": ["welding_bay", "perimeter"],
            "maintenance": ["assembly", "perimeter"],
            "perimeter": ["storage", "maintenance"],
        },
        "world_traits": {
            "global_noise": 0.4,
            "vibration": 0.3,
            "air_quality": 0.5,
        },
    },

    "prototype_lab_v1": {
        "name": "prototype_lab_v1",
        "desc": "Experimental R&D lab with unstable energy sources.",
        "size": "small",
        "zones": {
            "lab_core": {
                "desc": "Central bench area, cluttered with prototypes.",
                "tension_base": 0.5,
                "hazards": ["unstable_prototypes"]
            },
            "analysis_room": {
                "desc": "Calmer space with sensory equipment.",
                "tension_base": 0.2,
                "hazards": []
            },
            "charging_bay": {
                "desc": "Low-tension recovery zone.",
                "tension_base": 0.1,
                "hazards": []
            },
        },
        "adjacency": {
            "lab_core": ["analysis_room", "charging_bay"],
            "analysis_room": ["lab_core"],
            "charging_bay": ["lab_core"],
        },
        "world_traits": {
            "instability": 0.6,
            "air_quality": 0.3,
            "global_noise": 0.1,
        },
    },
}
