from __future__ import annotations

"""Typed render_spec structures (SSoT) with strict validation.

Mirrors KVP-0001 KERNEL_HELLO.render_spec (subset needed for Sprint 14.1).

Validation rules (minimum):
- bounds required and must satisfy max_x > min_x and max_y > min_y
- z_layer.stable_across_run must be True in v0.1
- draw_order lists must be non-empty
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# --- Small primitives ---


@dataclass(frozen=True)
class Vec2:
    x: float
    y: float

    def to_dict(self) -> Dict[str, float]:
        return {"x": float(self.x), "y": float(self.y)}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Vec2":
        if not isinstance(d, dict):
            raise ValueError("Vec2 requires a dict")
        for k in ("x", "y"):
            if k not in d:
                raise ValueError("Vec2 missing field: " + k)
        try:
            x = float(d["x"])  # type: ignore[arg-type]
            y = float(d["y"])  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            raise ValueError("Vec2 fields must be numbers") from e
        return Vec2(x=x, y=y)


@dataclass(frozen=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "min_x": float(self.min_x),
            "min_y": float(self.min_y),
            "max_x": float(self.max_x),
            "max_y": float(self.max_y),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Bounds":
        if not isinstance(d, dict):
            raise ValueError("Bounds requires a dict")
        required = ("min_x", "min_y", "max_x", "max_y")
        missing = [k for k in required if k not in d]
        if missing:
            raise ValueError("Bounds missing fields: " + ", ".join(missing))
        try:
            min_x = float(d["min_x"])  # type: ignore[arg-type]
            min_y = float(d["min_y"])  # type: ignore[arg-type]
            max_x = float(d["max_x"])  # type: ignore[arg-type]
            max_y = float(d["max_y"])  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            raise ValueError("Bounds fields must be numbers") from e
        if not (max_x > min_x and max_y > min_y):
            raise ValueError("Bounds must satisfy max_x > min_x and max_y > min_y")
        return Bounds(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)


@dataclass(frozen=True)
class AxisSpec:
    x_positive: str
    y_positive: str

    def to_dict(self) -> Dict[str, str]:
        if not self.x_positive or not self.y_positive:
            raise ValueError("AxisSpec directions must be non-empty strings")
        return {"x_positive": self.x_positive, "y_positive": self.y_positive}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AxisSpec":
        if not isinstance(d, dict):
            raise ValueError("AxisSpec requires a dict")
        for k in ("x_positive", "y_positive"):
            if k not in d or not isinstance(d[k], str) or not d[k]:
                raise ValueError("AxisSpec missing/invalid field: " + k)
        return AxisSpec(x_positive=d["x_positive"], y_positive=d["y_positive"])


@dataclass(frozen=True)
class ProjectionSpec:
    kind: str
    recommended_iso_tile_w: Optional[int]
    recommended_iso_tile_h: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "recommended_iso_tile_w": self.recommended_iso_tile_w,
            "recommended_iso_tile_h": self.recommended_iso_tile_h,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ProjectionSpec":
        if not isinstance(d, dict):
            raise ValueError("ProjectionSpec requires a dict")
        if "kind" not in d or not isinstance(d["kind"], str) or not d["kind"]:
            raise ValueError("ProjectionSpec.kind must be a non-empty string")
        w = d.get("recommended_iso_tile_w")
        h = d.get("recommended_iso_tile_h")
        if w is not None and not isinstance(w, int):
            raise ValueError("recommended_iso_tile_w must be int or None")
        if h is not None and not isinstance(h, int):
            raise ValueError("recommended_iso_tile_h must be int or None")
        return ProjectionSpec(kind=d["kind"], recommended_iso_tile_w=w, recommended_iso_tile_h=h)


@dataclass(frozen=True)
class ZLayerSpec:
    meaning: str
    stable_across_run: bool
    notes: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        if self.stable_across_run is not True:
            # Enforce during serialization too for defensive posture
            raise ValueError("z_layer.stable_across_run must be True in v0.1")
        return {
            "meaning": self.meaning,
            "stable_across_run": True,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ZLayerSpec":
        if not isinstance(d, dict):
            raise ValueError("ZLayerSpec requires a dict")
        if "meaning" not in d or not isinstance(d["meaning"], str) or not d["meaning"]:
            raise ValueError("ZLayerSpec.meaning must be a non-empty string")
        if "stable_across_run" not in d or not isinstance(d["stable_across_run"], bool):
            raise ValueError("ZLayerSpec.stable_across_run must be a bool")
        if d["stable_across_run"] is not True:
            raise ValueError("z_layer.stable_across_run must be True in v0.1")
        notes = d.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise ValueError("ZLayerSpec.notes must be str or None")
        return ZLayerSpec(meaning=d["meaning"], stable_across_run=True, notes=notes)


@dataclass(frozen=True)
class DrawOrderSpec:
    rooms: List[str]
    agents: List[str]
    items: List[str]

    def to_dict(self) -> Dict[str, Any]:
        if not (self.rooms and self.agents and self.items):
            raise ValueError("draw_order lists must be non-empty")
        return {"rooms": list(self.rooms), "agents": list(self.agents), "items": list(self.items)}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "DrawOrderSpec":
        if not isinstance(d, dict):
            raise ValueError("DrawOrderSpec requires a dict")
        for k in ("rooms", "agents", "items"):
            if k not in d or not isinstance(d[k], list) or len(d[k]) == 0:
                raise ValueError("draw_order." + k + " must be a non-empty list of strings")
            if not all(isinstance(x, str) and x for x in d[k]):
                raise ValueError("draw_order." + k + " must contain non-empty strings")
        return DrawOrderSpec(rooms=list(d["rooms"]), agents=list(d["agents"]), items=list(d["items"]))


@dataclass(frozen=True)
class LocalSortKeySpec:
    source: str
    quantization: str
    direction: str
    notes: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "quantization": self.quantization,
            "direction": self.direction,
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "LocalSortKeySpec":
        if not isinstance(d, dict):
            raise ValueError("LocalSortKeySpec requires a dict")
        for k in ("source", "quantization", "direction"):
            if k not in d or not isinstance(d[k], str) or not d[k]:
                raise ValueError("LocalSortKeySpec missing/invalid field: " + k)
        notes = d.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise ValueError("LocalSortKeySpec.notes must be str or None")
        return LocalSortKeySpec(source=d["source"], quantization=d["quantization"], direction=d["direction"], notes=notes)


@dataclass(frozen=True)
class AssetResolutionSpec:
    policy: str
    missing_ref_behavior: str

    def to_dict(self) -> Dict[str, Any]:
        return {"policy": self.policy, "missing_ref_behavior": self.missing_ref_behavior}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AssetResolutionSpec":
        if not isinstance(d, dict):
            raise ValueError("AssetResolutionSpec requires a dict")
        for k in ("policy", "missing_ref_behavior"):
            if k not in d or not isinstance(d[k], str) or not d[k]:
                raise ValueError("AssetResolutionSpec missing/invalid field: " + k)
        return AssetResolutionSpec(policy=d["policy"], missing_ref_behavior=d["missing_ref_behavior"])


@dataclass(frozen=True)
class CoordSystem:
    units: str
    units_per_tile: float
    axis: AxisSpec
    origin: Vec2
    bounds: Bounds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "units": self.units,
            "units_per_tile": float(self.units_per_tile),
            "axis": self.axis.to_dict(),
            "origin": self.origin.to_dict(),
            "bounds": self.bounds.to_dict(),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "CoordSystem":
        if not isinstance(d, dict):
            raise ValueError("CoordSystem requires a dict")
        required = ("units", "units_per_tile", "axis", "origin", "bounds")
        missing = [k for k in required if k not in d]
        if missing:
            raise ValueError("CoordSystem missing fields: " + ", ".join(missing))
        if not isinstance(d["units"], str) or not d["units"]:
            raise ValueError("units must be a non-empty string")
        try:
            upt = float(d["units_per_tile"])  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001
            raise ValueError("units_per_tile must be a number") from e
        axis = AxisSpec.from_dict(d["axis"])  # type: ignore[arg-type]
        origin = Vec2.from_dict(d["origin"])  # type: ignore[arg-type]
        if d.get("bounds") is None:
            raise ValueError("bounds is required")
        bounds = Bounds.from_dict(d["bounds"])  # type: ignore[arg-type]
        return CoordSystem(units=d["units"], units_per_tile=upt, axis=axis, origin=origin, bounds=bounds)


@dataclass(frozen=True)
class RenderSpec:
    coord_system: CoordSystem
    projection: ProjectionSpec
    z_layer: ZLayerSpec
    draw_order: DrawOrderSpec
    local_sort_key: LocalSortKeySpec
    asset_resolution: AssetResolutionSpec

    def to_dict(self) -> Dict[str, Any]:
        return {
            "coord_system": self.coord_system.to_dict(),
            "projection": self.projection.to_dict(),
            "z_layer": self.z_layer.to_dict(),
            "draw_order": self.draw_order.to_dict(),
            "local_sort_key": self.local_sort_key.to_dict(),
            "asset_resolution": self.asset_resolution.to_dict(),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RenderSpec":
        if not isinstance(d, dict):
            raise ValueError("RenderSpec requires a dict")
        required = (
            "coord_system",
            "projection",
            "z_layer",
            "draw_order",
            "local_sort_key",
            "asset_resolution",
        )
        missing = [k for k in required if k not in d]
        if missing:
            raise ValueError("RenderSpec missing fields: " + ", ".join(missing))
        cs = CoordSystem.from_dict(d["coord_system"])  # type: ignore[arg-type]
        proj = ProjectionSpec.from_dict(d["projection"])  # type: ignore[arg-type]
        zl = ZLayerSpec.from_dict(d["z_layer"])  # type: ignore[arg-type]
        do = DrawOrderSpec.from_dict(d["draw_order"])  # type: ignore[arg-type]
        lsk = LocalSortKeySpec.from_dict(d["local_sort_key"])  # type: ignore[arg-type]
        ar = AssetResolutionSpec.from_dict(d["asset_resolution"])  # type: ignore[arg-type]
        return RenderSpec(
            coord_system=cs,
            projection=proj,
            z_layer=zl,
            draw_order=do,
            local_sort_key=lsk,
            asset_resolution=ar,
        )


__all__ = [
    "Vec2",
    "Bounds",
    "AxisSpec",
    "ProjectionSpec",
    "ZLayerSpec",
    "DrawOrderSpec",
    "LocalSortKeySpec",
    "AssetResolutionSpec",
    "CoordSystem",
    "RenderSpec",
]
