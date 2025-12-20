import uuid
import pytest

from backend.sim4.integration.kvp_version import KVP_VERSION
from backend.sim4.integration.schema_version import INTEGRATION_SCHEMA_VERSION
from backend.sim4.integration.run_anchors import RunAnchors
from backend.sim4.integration.render_spec import (
    RenderSpec,
    CoordSystem,
    AxisSpec,
    Vec2,
    Bounds,
    ProjectionSpec,
    ZLayerSpec,
    DrawOrderSpec,
    LocalSortKeySpec,
    AssetResolutionSpec,
)


def _valid_render_spec_dict():
    return {
        "coord_system": {
            "units": "meters",
            "units_per_tile": 1.0,
            "axis": {"x_positive": "right", "y_positive": "down"},
            "origin": {"x": 0.0, "y": 0.0},
            "bounds": {"min_x": 0.0, "min_y": 0.0, "max_x": 10.0, "max_y": 5.0},
        },
        "projection": {"kind": "isometric", "recommended_iso_tile_w": 64, "recommended_iso_tile_h": 32},
        "z_layer": {"meaning": "tile_layers", "stable_across_run": True, "notes": None},
        "draw_order": {"rooms": ["floors", "walls"], "agents": ["humans"], "items": ["props"]},
        "local_sort_key": {"source": "y_then_x", "quantization": "Q1E3", "direction": "asc", "notes": None},
        "asset_resolution": {"policy": "prefer_runtime_recommended", "missing_ref_behavior": "error"},
    }


def test_kvp_version_constant():
    assert KVP_VERSION == "0.1"


def test_run_anchors_round_trip_and_schema_enforced():
    world_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    d = {
        "engine_name": "Sim4",
        "engine_version": "1.0.0",
        "schema_version": INTEGRATION_SCHEMA_VERSION,
        "world_id": world_id,
        "run_id": run_id,
        "seed": 42,
        "tick_rate_hz": 30,
        "time_origin_ms": 0,
    }
    anchors = RunAnchors.from_dict(d)
    assert anchors.to_dict() == d

    # schema version mismatch must raise
    bad = dict(d)
    bad["schema_version"] = "999"
    with pytest.raises(ValueError):
        RunAnchors.from_dict(bad)


def test_render_spec_missing_bounds_fails():
    d = _valid_render_spec_dict()
    # remove bounds
    d2 = dict(d)
    d2["coord_system"] = dict(d["coord_system"])  # shallow copy
    d2["coord_system"].pop("bounds", None)
    with pytest.raises(ValueError):
        RenderSpec.from_dict(d2)


def test_render_spec_invalid_bounds_min_max_fails():
    d = _valid_render_spec_dict()
    d_bad = dict(d)
    d_bad["coord_system"] = dict(d["coord_system"])  # shallow copy
    d_bad["coord_system"]["bounds"] = {"min_x": 5.0, "min_y": 5.0, "max_x": 1.0, "max_y": 1.0}
    with pytest.raises(ValueError):
        RenderSpec.from_dict(d_bad)


def test_render_spec_zlayer_stable_false_fails():
    d = _valid_render_spec_dict()
    d_bad = dict(d)
    d_bad["z_layer"] = {"meaning": "tile_layers", "stable_across_run": False, "notes": None}
    with pytest.raises(ValueError):
        RenderSpec.from_dict(d_bad)
