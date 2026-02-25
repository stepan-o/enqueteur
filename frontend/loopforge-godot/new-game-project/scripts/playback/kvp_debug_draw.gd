# res://scripts/playback/kvp_debug_draw.gd
extends Node2D
class_name KvpDebugDraw

@export var store_path: NodePath = NodePath("../WorldStore")

@onready var store: KvpWorldStore = get_node(store_path) as KvpWorldStore

func _ready() -> void:
	store.changed.connect(queue_redraw)

func _draw() -> void:
	if store.desynced:
		var font: Font = ThemeDB.fallback_font
		draw_string(font, Vector2(20, 30), "DESYNC: %s" % store.desync_reason)
		return

	var font: Font = ThemeDB.fallback_font

	draw_string(
		font,
		Vector2(20, 30),
		"Tick: %d  Rooms: %d  Agents: %d" %
		[store.tick, store.rooms.size(), store.agents.size()]
	)

	for rid in store.rooms.keys():
		var r: Dictionary = store.rooms[rid]
		var b: Dictionary = r.get("bounds", {})
		if b.is_empty():
			continue

		var min_x: float = float(b.get("min_x", 0.0))
		var min_y: float = float(b.get("min_y", 0.0))
		var max_x: float = float(b.get("max_x", 0.0))
		var max_y: float = float(b.get("max_y", 0.0))

		var scale: float = 40.0
		var pos: Vector2 = Vector2(min_x, min_y) * scale + Vector2(50, 60)
		var size: Vector2 = Vector2(max_x - min_x, max_y - min_y) * scale

		draw_rect(Rect2(pos, size), Color(1, 1, 1, 0.08), true)
		draw_rect(Rect2(pos, size), Color(1, 1, 1, 0.35), false, 2.0)

		var label: String = str(r.get("label", "Room %s" % str(rid)))
		draw_string(font, pos + Vector2(6, 18), label)
