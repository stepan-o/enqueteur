# res://scripts/playback/kvp_units.gd
extends Node
class_name KvpUnits

# Asset pack tile size (px)
const TILE_PX: int = 16

# Your chosen mapping:
# 1 KVP unit = 4 tiles  =>  64 px
const TILES_PER_UNIT: float = 4.0
const PX_PER_UNIT: float = TILE_PX * TILES_PER_UNIT

# Extra helpers so nobody “hand-multiplies” elsewhere.
static func u_to_px(v: float) -> float:
	return v * PX_PER_UNIT

static func uv_to_px(p: Vector2) -> Vector2:
	return p * PX_PER_UNIT

static func rect_units_to_px(min_x: float, min_y: float, max_x: float, max_y: float, offset_px := Vector2.ZERO) -> Rect2:
	var pos := Vector2(min_x, min_y) * PX_PER_UNIT + offset_px
	var size := Vector2(max_x - min_x, max_y - min_y) * PX_PER_UNIT
	return Rect2(pos, size)
