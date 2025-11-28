# sim4/runtime/diff.py

from typing import Dict, Any


def diff_snapshots(prev: Dict[str, Any], curr: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a minimal patch describing changes between two snapshots.

    Typical output:
    {
        "tick": 42,
        "added": { entity_id: {...} },
        "removed": [entity_id, ...],
        "updated": {
            entity_id: {
                "Transform": {"x": 12.0},
                "EmotionalState": {"tension": 0.3}
            }
        }
    }
    """

    patch = {
        "tick": curr["tick"],
        "added": {},
        "removed": [],
        "updated": {}
    }

    prev_ents = prev.get("entities", {})
    curr_ents = curr.get("entities", {})

    # --------------------------------------------------------------
    # 1. Detect REMOVED entities
    # --------------------------------------------------------------
    for ent_id in prev_ents.keys():
        if ent_id not in curr_ents:
            patch["removed"].append(ent_id)

    # --------------------------------------------------------------
    # 2. Detect ADDED entities
    # --------------------------------------------------------------
    for ent_id, comp_map in curr_ents.items():
        if ent_id not in prev_ents:
            patch["added"][ent_id] = comp_map

    # --------------------------------------------------------------
    # 3. Detect UPDATED entities
    # --------------------------------------------------------------
    for ent_id, curr_comps in curr_ents.items():
        if ent_id not in prev_ents:
            continue  # handled in "added"

        prev_comps = prev_ents[ent_id]

        entity_updates = _diff_components(prev_comps, curr_comps)

        if entity_updates:
            patch["updated"][ent_id] = entity_updates

    return patch


# --------------------------------------------------------------
# INTERNAL: Component-level diffing
# --------------------------------------------------------------

def _diff_components(prev_comps: Dict[str, Any],
                     curr_comps: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare component dicts for a single entity.

    prev_comps = {"Transform": {"x":0,"y":0}, "EmotionalState": {...}}
    curr_comps = {"Transform": {"x":1,"y":0}, ...}

    Output:
    {
        "Transform": {"x":1},
        "EmotionalState": {"tension":0.3}
    }
    """
    component_diff = {}

    for comp_name, curr_vals in curr_comps.items():
        prev_vals = prev_comps.get(comp_name)

        if prev_vals is None:
            # Entire component added
            component_diff[comp_name] = curr_vals
            continue

        # diff individual fields
        changed_fields = {}
        for field, value in curr_vals.items():
            if field not in prev_vals or prev_vals[field] != value:
                changed_fields[field] = value

        if changed_fields:
            component_diff[comp_name] = changed_fields

    return component_diff
