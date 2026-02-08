from __future__ import annotations

"""Host-level helpers for KVP-0001 defaults.

These helpers sit above the SOP-100 DAG and are intentionally placed in the
host layer. They provide convenience defaults for run_anchors and render_spec
without changing the integration SSoT modules.
"""

from typing import Sequence
import uuid

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
from backend.sim4.integration.schema_version import INTEGRATION_SCHEMA_VERSION
from backend.sim4.runtime.clock import TickClock

DEFAULT_ENGINE_NAME = "Sim4"
DEFAULT_ENGINE_VERSION = "1.0.0"
DEFAULT_WORLD_BOUNDS = Bounds(min_x=0.0, min_y=0.0, max_x=500.0, max_y=500.0)


def tick_rate_hz_from_clock(clock: TickClock) -> int:
    """Compute an integer tick rate from a TickClock's dt."""
    if clock.dt <= 0:
        raise ValueError("clock.dt must be > 0 to compute tick_rate_hz")
    return int(round(1.0 / float(clock.dt)))


def default_run_anchors(
    *,
    seed: int,
    tick_rate_hz: int,
    time_origin_ms: int = 0,
    engine_name: str = DEFAULT_ENGINE_NAME,
    engine_version: str = DEFAULT_ENGINE_VERSION,
    world_id: str | None = None,
    run_id: str | None = None,
) -> RunAnchors:
    """Build RunAnchors with sensible defaults and strict validation."""
    if world_id is None:
        world_id = str(uuid.uuid4())
    if run_id is None:
        run_id = str(uuid.uuid4())
    return RunAnchors.from_dict(
        {
            "engine_name": engine_name,
            "engine_version": engine_version,
            "schema_version": INTEGRATION_SCHEMA_VERSION,
            "world_id": world_id,
            "run_id": run_id,
            "seed": int(seed),
            "tick_rate_hz": int(tick_rate_hz),
            "time_origin_ms": int(time_origin_ms),
        }
    )


def default_render_spec(
    *,
    bounds: Bounds | None = None,
    units: str = "meters",
    units_per_tile: float = 1.0,
    axis_x_positive: str = "right",
    axis_y_positive: str = "down",
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    projection_kind: str = "isometric",
    recommended_iso_tile_w: int | None = 64,
    recommended_iso_tile_h: int | None = 32,
    z_layer_meaning: str = "tile_layers",
    draw_order_rooms: Sequence[str] | None = None,
    draw_order_agents: Sequence[str] | None = None,
    draw_order_items: Sequence[str] | None = None,
    local_sort_source: str = "y_then_x",
    local_sort_quantization: str = "Q1E3",
    local_sort_direction: str = "asc",
    asset_policy: str = "prefer_runtime_recommended",
    missing_ref_behavior: str = "error",
) -> RenderSpec:
    """Build a RenderSpec with defaults aligned to tests and KVP-0001."""
    if bounds is None:
        bounds = DEFAULT_WORLD_BOUNDS

    if draw_order_rooms is None:
        draw_order_rooms = ["floors", "walls"]
    if draw_order_agents is None:
        draw_order_agents = ["humans"]
    if draw_order_items is None:
        draw_order_items = ["props"]

    return RenderSpec(
        coord_system=CoordSystem(
            units=units,
            units_per_tile=float(units_per_tile),
            axis=AxisSpec(x_positive=axis_x_positive, y_positive=axis_y_positive),
            origin=Vec2(x=float(origin_x), y=float(origin_y)),
            bounds=bounds,
        ),
        projection=ProjectionSpec(
            kind=projection_kind,
            recommended_iso_tile_w=recommended_iso_tile_w,
            recommended_iso_tile_h=recommended_iso_tile_h,
        ),
        z_layer=ZLayerSpec(meaning=z_layer_meaning, stable_across_run=True, notes=None),
        draw_order=DrawOrderSpec(
            rooms=list(draw_order_rooms),
            agents=list(draw_order_agents),
            items=list(draw_order_items),
        ),
        local_sort_key=LocalSortKeySpec(
            source=local_sort_source,
            quantization=local_sort_quantization,
            direction=local_sort_direction,
            notes=None,
        ),
        asset_resolution=AssetResolutionSpec(
            policy=asset_policy,
            missing_ref_behavior=missing_ref_behavior,
        ),
    )


__all__ = [
    "DEFAULT_ENGINE_NAME",
    "DEFAULT_ENGINE_VERSION",
    "DEFAULT_WORLD_BOUNDS",
    "tick_rate_hz_from_clock",
    "default_run_anchors",
    "default_render_spec",
]
