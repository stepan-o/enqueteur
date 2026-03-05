# res://scripts/playback/kvp_offline_player.gd
extends Node
class_name KvpOfflinePlayer

@export var playback_scene_back: String = "res://scenes/ui/RunSelect.tscn"
@export var start_tick_override: int = -1
@export var end_tick_override: int = -1
@export var speed: float = 1.0

@onready var store: KvpWorldStore = get_parent().get_node("WorldStore") as KvpWorldStore
@onready var hud: Label = get_parent().get_node_or_null("HUD") as Label

var _manifest: Dictionary = {}
var _base_url: String = ""
var _tick_rate_hz: int = 30
var _current_tick: int = 0
var _end_tick: int = 0
var _timer: Timer

func _ready() -> void:
	_base_url = str(PlaybackContext.base_url).rstrip("/")
	if _base_url == "":
		push_error("PlaybackContext.base_url is empty")
		get_tree().change_scene_to_file(playback_scene_back)
		return

	_timer = Timer.new()
	_timer.one_shot = false
	add_child(_timer)
	_timer.timeout.connect(_on_tick)

	# Load everything synchronously for now (simple + reliable).
	# If you want async later, we can convert to Thread/await pattern.
	if !_load_manifest():
		get_tree().change_scene_to_file(playback_scene_back)
		return

	if !_load_initial_state():
		get_tree().change_scene_to_file(playback_scene_back)
		return

	_start_timer()

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel"): # Esc by default
		_stop()
		get_tree().change_scene_to_file(playback_scene_back)

func _stop() -> void:
	if _timer:
		_timer.stop()

func _start_timer() -> void:
	# Godot's max() returns Variant, and with warnings-as-errors
	# `:=` inference from Variant triggers an error. Use explicit types + casts.
	var hz: int = int(max(1, _tick_rate_hz))
	var hz_f: float = float(hz)
	var spd: float = max(0.01, float(speed))
	var interval_sec: float = max(0.005, (1.0 / hz_f) / spd)

	_timer.wait_time = interval_sec
	_timer.start()

func _load_manifest() -> bool:
	var manifest_path := _join_path(_base_url, "manifest.kvp.json")
	var manifest_root: Variant = _read_json(manifest_path)
	if !(manifest_root is Dictionary):
		push_error("Manifest invalid or missing: %s" % manifest_path)
		return false

	_manifest = manifest_root

	var anchors: Dictionary = _manifest.get("run_anchors", {})
	_tick_rate_hz = int(anchors.get("tick_rate_hz", 30))
	if _tick_rate_hz <= 0:
		_tick_rate_hz = 30

	# determine playback window
	var a_start := int(_manifest.get("available_start_tick", 1))
	var a_end := int(_manifest.get("available_end_tick", 0))

	var snapshots: Dictionary = _manifest.get("snapshots", {})
	if snapshots.is_empty():
		push_error("Manifest contains no snapshots")
		return false

	# If available_end_tick missing, fallback to max snapshot tick
	if a_end <= 0:
		a_end = _max_tick_key(snapshots)

	var start_tick := a_start
	var end_tick := a_end

	if start_tick_override >= 0:
		start_tick = start_tick_override
	if end_tick_override >= 0:
		end_tick = end_tick_override

	_current_tick = start_tick
	_end_tick = end_tick

	return true

func _load_initial_state() -> bool:
	var snapshots: Dictionary = _manifest.get("snapshots", {})
	var diffs_by: Dictionary = _manifest.get("diffs", {}).get("diffs_by_from_tick", {})

	# Pick latest snapshot tick <= current_tick
	var snap_tick := _find_latest_snapshot_tick(snapshots, _current_tick)
	if snap_tick <= 0:
		push_error("Could not find a snapshot <= start tick (%d)" % _current_tick)
		return false

	var snap_ptr: Dictionary = snapshots.get(str(snap_tick), {})
	var snap_rel: String = str(snap_ptr.get("rel_path", ""))
	if snap_rel == "":
		push_error("Snapshot pointer missing rel_path for tick %d" % snap_tick)
		return false

	var snap_envelope: Variant = _read_json(_join_path(_base_url, snap_rel))
	if !(snap_envelope is Dictionary) or !(Dictionary(snap_envelope).get("payload", null) is Dictionary):
		push_error("Snapshot file invalid: %s" % snap_rel)
		return false

	var snap_payload: Dictionary = Dictionary(snap_envelope).get("payload", {})
	store.apply_snapshot(snap_payload)

	# Fast-forward to _current_tick if snapshot tick is behind
	var t := int(snap_payload.get("tick", snap_tick))
	while t < _current_tick:
		var ptr: Dictionary = diffs_by.get(str(t), {})
		var rel: String = str(ptr.get("rel_path", ""))
		if rel == "":
			push_error("Missing diff for tick %d" % t)
			return false

		var diff_envelope: Variant = _read_json(_join_path(_base_url, rel))
		if !(diff_envelope is Dictionary) or !(Dictionary(diff_envelope).get("payload", null) is Dictionary):
			push_error("Diff file invalid: %s" % rel)
			return false

		var diff_payload: Dictionary = Dictionary(diff_envelope).get("payload", {})
		store.apply_diff(diff_payload)
		if store.desynced:
			push_error("Desynced while fast-forwarding: %s" % store.desync_reason)
			return false
		t = int(diff_payload.get("to_tick", t + 1))

	_current_tick = store.tick
	_update_hud()
	return true

func _on_tick() -> void:
	if store.desynced:
		push_warning("Playback stopped (desynced): %s" % store.desync_reason)
		_stop()
		return

	if _current_tick >= _end_tick:
		push_warning("Playback reached end tick: %d" % _end_tick)
		_stop()
		return

	var diffs_by: Dictionary = _manifest.get("diffs", {}).get("diffs_by_from_tick", {})
	var ptr: Dictionary = diffs_by.get(str(_current_tick), {})
	var rel: String = str(ptr.get("rel_path", ""))
	if rel == "":
		push_warning("No diff for tick %d (stopping)" % _current_tick)
		_stop()
		return

	var diff_envelope: Variant = _read_json(_join_path(_base_url, rel))
	if !(diff_envelope is Dictionary) or !(Dictionary(diff_envelope).get("payload", null) is Dictionary):
		push_warning("Diff invalid: %s" % rel)
		_stop()
		return

	var diff_payload: Dictionary = Dictionary(diff_envelope).get("payload", {})
	store.apply_diff(diff_payload)
	if store.desynced:
		push_warning("Playback stopped (desynced): %s" % store.desync_reason)
		_stop()
		return

	_current_tick = store.tick
	_update_hud()

func _update_hud() -> void:
	if hud:
		hud.text = "RUN: %s  TICK: %d  END: %d" % [str(PlaybackContext.run_id), store.tick, _end_tick]

# ---------- helpers ----------

func _join_path(base: String, rel: String) -> String:
	if base.ends_with("/"):
		return base + rel.lstrip("/")
	return base + "/" + rel.lstrip("/")

func _read_json(path: String) -> Variant:
	# Local-only MVP: res://... or user://...
	# If you later want http(s), we’ll switch to HTTPRequest.
	if !path.begins_with("res://") and !path.begins_with("user://"):
		push_error("Only local paths supported right now: %s" % path)
		return null

	if !FileAccess.file_exists(path):
		push_error("File not found: %s" % path)
		return null

	var txt := FileAccess.get_file_as_string(path)
	return JSON.parse_string(txt)

func _max_tick_key(m: Dictionary) -> int:
	var best := 0
	for k in m.keys():
		var t := int(str(k))
		if t > best:
			best = t
	return best

func _find_latest_snapshot_tick(snapshots: Dictionary, target_tick: int) -> int:
	var best := -1
	for k in snapshots.keys():
		var t := int(str(k))
		if t <= target_tick and t > best:
			best = t
	return best
