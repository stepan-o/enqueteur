# res://scripts/playback/kvp_cinematic_view.gd
extends Node2D
class_name KvpCinematicView

@export var store_path: NodePath = NodePath("../WorldStore") # adjust if needed
@export var tiles_per_unit: int = 4 # 1 KVP unit => N tiles
@export var floor_tile_id: int = 0  # pick an atlas tile index in your Floor TileSet
@export var wall_tile_id: int = 0   # pick an atlas tile index in your Walls TileSet

@onready var store: KvpWorldStore = get_node(store_path) as KvpWorldStore
@onready var floor_tm: TileMap = $Floor
@onready var walls_tm: TileMap = $Walls
@onready var agents_root: Node2D = $Agents
@onready var cam: Camera2D = $Cam

var _agent_nodes: Dictionary = {} # int agent_id -> Node2D
var _pixels_per_unit: float

func _ready() -> void:
	_pixels_per_unit = float(16 * tiles_per_unit)
	store.changed.connect(_on_store_changed)
	_on_store_changed()

func _on_store_changed() -> void:
	if store.desynced:
		return

	_rebuild_rooms()
	_sync_agents()
	_auto_camera_center()

func _rebuild_rooms() -> void:
	floor_tm.clear()
	walls_tm.clear()

	for rid in store.rooms.keys():
		var r: Dictionary = store.rooms[rid]
		var b_v: Variant = r.get("bounds", null)
		if !(b_v is Dictionary):
			continue
		var b: Dictionary = b_v

		var min_x := float(b.get("min_x", 0.0))
		var min_y := float(b.get("min_y", 0.0))
		var max_x := float(b.get("max_x", 0.0))
		var max_y := float(b.get("max_y", 0.0))

		# Convert bounds to tile coords
		var x0 := int(floor(min_x * tiles_per_unit))
		var y0 := int(floor(min_y * tiles_per_unit))
		var x1 := int(ceil(max_x * tiles_per_unit))
		var y1 := int(ceil(max_y * tiles_per_unit))

		# Fill floor
		for y in range(y0, y1):
			for x in range(x0, x1):
				floor_tm.set_cell(0, Vector2i(x, y), 0, Vector2i(floor_tile_id, 0))

		# Outline walls (simple rectangle perimeter for now)
		for x in range(x0, x1):
			walls_tm.set_cell(0, Vector2i(x, y0), 0, Vector2i(wall_tile_id, 0))
			walls_tm.set_cell(0, Vector2i(x, y1 - 1), 0, Vector2i(wall_tile_id, 0))
		for y in range(y0, y1):
			walls_tm.set_cell(0, Vector2i(x0, y), 0, Vector2i(wall_tile_id, 0))
			walls_tm.set_cell(0, Vector2i(x1 - 1, y), 0, Vector2i(wall_tile_id, 0))

func _sync_agents() -> void:
	# Remove missing agents
	var present: Dictionary = {}
	for aid in store.agents.keys():
		present[int(aid)] = true
	for aid in _agent_nodes.keys():
		if !present.has(int(aid)):
			var n: Node = _agent_nodes[aid]
			if is_instance_valid(n):
				n.queue_free()
			_agent_nodes.erase(aid)

	# Upsert agents
	for aid_v in store.agents.keys():
		var aid := int(aid_v)
		var a: Dictionary = store.agents[aid_v]

		var node: Node2D
		if _agent_nodes.has(aid):
			node = _agent_nodes[aid] as Node2D
		else:
			node = _spawn_agent(aid)
			_agent_nodes[aid] = node

		_update_agent_node(node, a)

func _spawn_agent(agent_id: int) -> Node2D:
	# Minimal: animated sprite node. You can replace with a PackedScene later.
	var n := Node2D.new()
	n.name = "Agent_%d" % agent_id

	var spr := AnimatedSprite2D.new()
	spr.name = "Sprite"
	spr.centered = true
	spr.sprite_frames = preload("res://scenes/playback/robot_frames.tres")
	spr.animation = "idle_down"
	spr.play()

	n.add_child(spr)
	agents_root.add_child(n)
	return n

func _update_agent_node(node: Node2D, a: Dictionary) -> void:
	var t_v: Variant = a.get("transform", null)
	if !(t_v is Dictionary):
		return
	var t: Dictionary = t_v
	var x := float(t.get("x", 0.0))
	var y := float(t.get("y", 0.0))

	# KVP -> pixels
	var target := Vector2(x, y) * _pixels_per_unit

	# Smooth a bit so it feels “cinematic”
	node.position = node.position.lerp(target, 0.35)

	# (Later) choose animation based on movement direction / action_state_code

func _auto_camera_center() -> void:
	# Simple: center on average of agents, else center on rooms
	if _agent_nodes.size() > 0:
		var sum := Vector2.ZERO
		var n := 0
		for aid in _agent_nodes.keys():
			var a := _agent_nodes[aid] as Node2D
			sum += a.position
			n += 1
		cam.position = sum / float(max(1, n))
