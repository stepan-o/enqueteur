# sim4/runtime/snapshots.py
from __future__ import annotations
import json
from dataclasses import asdict, is_dataclass

from ..ecs.entity import EntityID


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
    Convert ECS world → JSON-friendly entity payload.

    Output shape:
    {
        1: {"Transform": {...}, "EmotionalState": {...}},
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

            for ctype in comp_types:
                comp_instance = arch.columns[ctype][idx]
                out[eid][ctype.__name__] = encode_component(comp_instance)

    return out


# ---------------------------------------------------------------------------
# FULL SNAPSHOT
# ---------------------------------------------------------------------------

def build_snapshot(world, tick):
    """
    Minimal Sim4 snapshot expected by diff engine & Godot:

    {
        "tick": 12,
        "entities": {
            1: {"Transform": {...}, "EmotionalState": {...}},
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
