# sim4/runtime/snapshots.py
from __future__ import annotations
import json
from dataclasses import is_dataclass, asdict

from ..ecs.entity import EntityID


# ---------------------------------------------------------------------------
# SAFE COMPONENT SERIALIZATION
# ---------------------------------------------------------------------------

def encode_value(v):
    """
    Encode values into Godot/JSON compatible primitives.

    Handles:
    - dataclasses        -> dict
    - EntityID           -> int
    - lists/tuples       -> recurse
    - dicts              -> recurse
    - everything else    -> raw
    """
    # EntityID → int
    if isinstance(v, EntityID):
        return v.value

    # Dataclass → dict
    if is_dataclass(v):
        return {k: encode_value(val) for k, val in asdict(v).items()}

    # List/Tuple → iterate
    if isinstance(v, (list, tuple)):
        return [encode_value(x) for x in v]

    # Dict → iterate
    if isinstance(v, dict):
        return {k: encode_value(val) for k, val in v.items()}

    # Primitive
    return v


def encode_component(comp):
    if comp is None:
        return None
    return encode_value(comp)


# ---------------------------------------------------------------------------
# EXTRACT COMPONENTS FROM ECS
# ---------------------------------------------------------------------------

def collect_entity_components(ecs_world):
    """
    Iterate across all archetypes, reconstruct entity -> components mapping.

    ECS stores:
        archetype.columns[ComponentClass] = [component_instance, ...]
        archetype.entities = [EntityID, ...]

    We rebuild:
        { EntityID.value: { "Transform": {...}, "EmotionalState": {...} } }
    """
    out = {}

    for arch in ecs_world.archetypes.values():
        comp_types = list(arch.columns.keys())

        for idx, ent in enumerate(arch.entities):
            ent_int = ent.value

            if ent_int not in out:
                out[ent_int] = {}

            for ctype in comp_types:
                comp = arch.columns[ctype][idx]
                out[ent_int][ctype.__name__] = encode_component(comp)

    return out


# ---------------------------------------------------------------------------
# ROOM MEMBERSHIP SERIALIZATION
# ---------------------------------------------------------------------------

def serialize_rooms(world):
    """
    Returns:
        {
            "rooms": {
                "A": {
                    "label": "Living Room",
                    "kind": "default",
                    "entities": [1, 2, 3]
                },
                ...
            }
        }
    """
    payload = {}

    for room_id, room in world.state.rooms.items():
        payload[room_id] = {
            "label": room.identity.label,
            "kind": room.identity.kind,
            "entities": [e.value for e in room.entities],
        }

    return payload


# ---------------------------------------------------------------------------
# FULL WORLD SNAPSHOT
# ---------------------------------------------------------------------------

def build_world_snapshot(world):
    """
    Era-III → Era-V unified snapshot structure.

    Produces:
    {
        "identity": {...},
        "rooms": {...},
        "entities": {...},
        "tick": world.tick (optional – caller sets)
    }
    """
    ecs_entities = collect_entity_components(world.ecs)
    rooms = serialize_rooms(world)

    return {
        "identity": {
            "world_name": world.identity.world_name,
            "version": world.identity.version,
        },
        "rooms": rooms,
        "entities": ecs_entities,
    }


# ---------------------------------------------------------------------------
# JSON SERIALIZATION
# ---------------------------------------------------------------------------

def snapshot_json(snapshot, tick=None) -> str:
    """
    Attach tick → JSON string.
    """
    if tick is not None:
        snapshot["tick"] = tick

    return json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False)
