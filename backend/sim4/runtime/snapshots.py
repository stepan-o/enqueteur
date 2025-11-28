from __future__ import annotations
import json
from dataclasses import asdict, is_dataclass

from ..ecs.entity import EntityID
from .narrative.narrative import NarrativeEngine  # Import NarrativeEngine class, not the function


# ---------------------------------------------------------------------------
# SAFE SERIALIZATION HELPERS
# ---------------------------------------------------------------------------

def encode_value(v):
    """
    Recursively convert values into JSON/Godot friendly primitives.
    Supports:
    - EntityID → int
    - dataclasses → dict
    - lists/tuples → list
    - dicts → dict
    - primitives unchanged
    """
    if isinstance(v, EntityID):
        return v.value

    if is_dataclass(v):
        return {k: encode_value(val) for k, val in asdict(v).items()}

    if isinstance(v, (list, tuple)):
        return [encode_value(x) for x in v]

    if isinstance(v, dict):
        return {k: encode_value(val) for k, val in v.items()}

    return v


def encode_component(comp):
    if comp is None:
        return None
    return encode_value(comp)


# ---------------------------------------------------------------------------
# ECS → Snapshot Entity Extraction
# ---------------------------------------------------------------------------

def collect_entities(world):
    """
    Convert ECS world → JSON-friendly entity payload, including narrative data.

    Output shape:
    {
        1: {"Transform": {...}, "EmotionalState": {...}, "Narrative": "I feel conflicted..."},
        2: {...},
        ...
    }
    """
    out = {}

    for arch in world.archetypes.values():
        comp_types = list(arch.columns.keys())

        for idx, ent_id in enumerate(arch.entities):
            eid = ent_id.value

            if eid not in out:
                out[eid] = {}

            # Collect the entity's components (e.g., Transform, EmotionalState)
            for ctype in comp_types:
                comp_instance = arch.columns[ctype][idx]
                out[eid][ctype.__name__] = encode_component(comp_instance)

            # Add narrative (e.g., dialogue, emotional reflections) for each agent
            if 'Agent' in arch.columns:
                agent = arch.columns['Agent'][idx]  # Assuming we have an Agent component
                narrative_engine = NarrativeEngine(agent)  # Instantiate NarrativeEngine
                narrative = narrative_engine.generate_dialogue(agent.get_agent_state())  # Generate dialogue/reflection
                out[eid]["Narrative"] = narrative  # Add narrative to the entity snapshot

    return out


# ---------------------------------------------------------------------------
# FULL SNAPSHOT
# ---------------------------------------------------------------------------

def build_snapshot(world, tick):
    """
    Build a minimal Sim4 snapshot with narrative data for Godot.

    {
        "tick": 12,
        "entities": {
            1: {"Transform": {...}, "EmotionalState": {...}, "Narrative": "..."},
            2: {...}
        }
    }
    """
    ents = collect_entities(world)

    return {
        "tick": tick,
        "entities": ents,
    }


# ---------------------------------------------------------------------------
# JSON SERIALIZER
# ---------------------------------------------------------------------------

def snapshot_json(snapshot):
    """
    Pretty small, fast JSON output
    """
    return json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False)


def serialize_assets(world):
    out = {}
    for inst_id, inst in world.assets.items():
        out[inst_id] = {
            "asset_id": inst.asset_id,
            "identity": {
                "id": inst.identity.id,
                "label": inst.identity.label,
                "category": inst.identity.category,
                "interactable": inst.identity.interactable,
                "default_state": inst.identity.default_state,
            },
            "room": inst.room,
            "state": inst.state,
        }
    return out


# ---------------------------------------------------------------------------
# ROOM SERIALIZATION
# ---------------------------------------------------------------------------

def serialize_rooms(world):
    """
    Returns:
        {
            "A": {
                "label": "Lab Room",
                "kind": "default",
                "entities": [1, 2, ...]
            },
            "B": { ... }
        }
    """
    payload = {}

    for room_id, room in world.rooms.items():
        payload[room_id] = {
            "label": room.identity.label,
            "kind": room.identity.kind,
            "entities": [e.value for e in room.entities],
        }

    return payload


# ---------------------------------------------------------------------------
# FULL WORLD SNAPSHOT (Era V)
# ---------------------------------------------------------------------------

def build_world_snapshot(world, tick):
    """
    Unified snapshot of everything in the world.

    Expected structure:

    {
        "tick": 12,
        "identity": {
            "world_name": "...",
            "version": "..."
        },
        "rooms": {...},
        "assets": {...},
        "entities": {...}
    }
    """
    return {
        "tick": tick,

        # --------------------------------------
        # Static identity layer
        # --------------------------------------
        "identity": {
            "world_name": world.identity.world_name,
            "version": world.identity.version,
        },

        # --------------------------------------
        # Room layer (mutable)
        # --------------------------------------
        "rooms": serialize_rooms(world),

        # --------------------------------------
        # Asset layer
        # --------------------------------------
        "assets": serialize_assets(world),

        # --------------------------------------
        # ECS entity layer
        # --------------------------------------
        "entities": collect_entities(world),
    }
