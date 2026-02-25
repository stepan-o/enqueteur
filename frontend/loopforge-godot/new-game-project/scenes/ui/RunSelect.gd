# res://scenes/ui/RunSelect.gd
extends Control

@onready var menu: HBoxContainer = %Menu

var RUNS: Array = []

func _ready() -> void:
	RUNS = _load_runs_from_json("res://config/runs.json")
	_build_menu()

func _load_runs_from_json(path: String) -> Array:
	if !FileAccess.file_exists(path):
		push_warning("runs.json not found: %s" % path)
		return []

	var txt: String = FileAccess.get_file_as_string(path)

	# FIX: avoid typed var inferred from Variant (warnings-as-errors).
	var parsed_v: Variant = JSON.parse_string(txt)
	if !(parsed_v is Dictionary):
		push_warning("runs.json invalid (expected Dictionary root)")
		return []

	var parsed: Dictionary = parsed_v
	var runs_v: Variant = parsed.get("runs", [])
	if runs_v is Array:
		return runs_v

	return []

func _build_menu() -> void:
	# clear existing buttons (if any)
	for c in menu.get_children():
		c.queue_free()

	# run buttons
	for run_v in RUNS:
		if typeof(run_v) != TYPE_DICTIONARY:
			continue
		var run: Dictionary = run_v

		var b := Button.new()
		b.text = str(run.get("label", "RUN"))
		b.focus_mode = Control.FOCUS_ALL
		b.pressed.connect(func() -> void:
			_on_run_selected(run)
		)
		menu.add_child(b)

	# back button at the end
	var back := Button.new()
	back.text = "BACK"
	back.focus_mode = Control.FOCUS_ALL
	back.pressed.connect(_on_back_pressed)
	menu.add_child(back)

func _on_run_selected(run: Dictionary) -> void:
	# Store selection for Playback scene
	PlaybackContext.run_id = str(run.get("id", ""))
	PlaybackContext.base_url = str(run.get("base_url", ""))

	# Go to playback scene (adjust path to your actual playback scene)
	get_tree().change_scene_to_file("res://scenes/playback/Playback.tscn")

func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/FactoryMenu.tscn")
