# res://scripts/playback/kvp_world_store.gd
extends Node
class_name KvpWorldStore

var tick: int = 0
var step_hash: String = ""
var desynced: bool = false
var desync_reason: String = ""

var world: Variant = null # Dictionary or null

var rooms := {}   # int -> Dictionary
var agents := {}  # int -> Dictionary
var items := {}   # int -> Dictionary
var objects := {} # int -> Dictionary
var events := {}  # String -> Dictionary (key fn TBD)

signal changed

func mark_desync(reason: String) -> void:
	desynced = true
	desync_reason = reason
	push_warning("KVP DESYNC: %s" % reason)
	emit_signal("changed")

func apply_snapshot(payload: Dictionary) -> void:
	if desynced:
		return
	if !payload.has("state"):
		mark_desync("Invalid snapshot payload (missing state)")
		return

	var state: Dictionary = payload["state"]

	rooms.clear()
	for r in state.get("rooms", []):
		rooms[int(r["room_id"])] = r

	agents.clear()
	for a in state.get("agents", []):
		agents[int(a["agent_id"])] = a

	items.clear()
	for i in state.get("items", []):
		items[int(i["item_id"])] = i

	objects.clear()
	for o in state.get("objects", []):
		objects[int(o["object_id"])] = o

	events.clear()
	for e in state.get("events", []):
		events[_event_key(e)] = e

	world = state.get("world", null)
	tick = int(payload.get("tick", 0))
	step_hash = str(payload.get("step_hash", ""))

	desynced = false
	desync_reason = ""
	emit_signal("changed")

func apply_diff(payload: Dictionary) -> void:
	if desynced:
		return
	if !payload.has("ops") or typeof(payload["ops"]) != TYPE_ARRAY:
		mark_desync("Invalid diff payload (ops not array)")
		return

	# FIX: don't infer typed var from a Variant (warnings-as-errors).
	var prev_hash: Variant = payload.get("prev_step_hash", null)
	if prev_hash is String and step_hash != "" and String(prev_hash) != step_hash:
		mark_desync("Step hash mismatch (diff chain broken)")
		return

	var from_tick := int(payload.get("from_tick", -1))
	if tick != 0 and from_tick != tick:
		mark_desync("Tick mismatch (expected %d, got %d)" % [tick, from_tick])
		return

	for op_v in payload["ops"]:
		if typeof(op_v) != TYPE_DICTIONARY:
			mark_desync("Invalid diff op (not a Dictionary)")
			return
		_apply_op(op_v)

	# Update to_tick + step hash
	tick = int(payload.get("to_tick", tick))
	step_hash = str(payload.get("step_hash", step_hash))
	emit_signal("changed")

func _apply_op(op: Dictionary) -> void:
	var kind := str(op.get("op", ""))
	match kind:
		"SET_WORLD":
			world = op.get("world", null)
		"CLEAR_WORLD":
			world = null

		"UPSERT_ROOM":
			var r: Dictionary = op["room"]
			rooms[int(r["room_id"])] = r
		"REMOVE_ROOM":
			rooms.erase(int(op["room_id"]))

		"UPSERT_AGENT":
			var a: Dictionary = op["agent"]
			agents[int(a["agent_id"])] = a
		"REMOVE_AGENT":
			agents.erase(int(op["agent_id"]))

		"UPSERT_ITEM":
			var i: Dictionary = op["item"]
			items[int(i["item_id"])] = i
		"REMOVE_ITEM":
			items.erase(int(op["item_id"]))

		"UPSERT_OBJECT":
			var o: Dictionary = op["object"]
			objects[int(o["object_id"])] = o
		"REMOVE_OBJECT":
			objects.erase(int(op["object_id"]))

		"UPSERT_EVENT":
			var e: Dictionary = op["event"]
			events[_event_key(e)] = e
		"REMOVE_EVENT":
			# TODO: parity needs eventKeyFromKey(...) logic.
			# For now: assume op.event_key is already the map key string.
			events.erase(str(op.get("event_key", "")))

		_:
			mark_desync("Unknown diff op: %s" % kind)

func _event_key(e: Dictionary) -> String:
	# TODO: replace with exact webview eventKey(e) once we inspect it.
	# Minimal fallback:
	if e.has("event_id"):
		return str(e["event_id"])
	return JSON.stringify(e)
