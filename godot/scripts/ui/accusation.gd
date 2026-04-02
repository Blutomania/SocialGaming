## Accusation — player selects a suspect and submits their final answer.
## Compares locally against the solution already in the mystery dict —
## no extra API call needed (the server included the solution in /generate).
##
## SESSION ANNOTATION — Phase 3:
## In multiplayer, accusation must be validated server-side to prevent cheating.
## Add a POST /accuse endpoint and call it here instead of comparing locally.
## The server broadcasts the result to all players.

extends Control

# ---------------------------------------------------------------------------
# Node references
# ---------------------------------------------------------------------------
@onready var bg_texture: TextureRect = $BgTexture
@onready var suspect_dropdown: OptionButton = $VBox/SuspectDropdown
@onready var submit_button: Button = $VBox/SubmitButton
@onready var back_button: Button = $VBox/BackButton
@onready var status_label: Label = $VBox/StatusLabel
@onready var confirm_dialog: ConfirmationDialog = $ConfirmDialog

var _mystery: MysteryData
var _selected_suspect: String = ""

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	for path in ["res://assets/ui/accusation_bg.png", "res://assets/ui/main_menu_bg.png"]:
		if ResourceLoader.exists(path):
			bg_texture.texture = load(path)
			break
	_mystery = MysteryData.from_dict(GameState.current_mystery)

	for name in _mystery.suspect_names():
		suspect_dropdown.add_item(name)

	submit_button.pressed.connect(_on_submit_pressed)
	back_button.pressed.connect(_go_case)
	confirm_dialog.confirmed.connect(_on_confirmed)

	if suspect_dropdown.item_count == 0:
		submit_button.disabled = true
		status_label.text = "No suspects found in this mystery."

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
func _on_submit_pressed() -> void:
	if suspect_dropdown.item_count == 0:
		return
	_selected_suspect = suspect_dropdown.get_item_text(suspect_dropdown.selected)
	confirm_dialog.dialog_text = (
		"Are you sure you want to accuse %s?\nThis ends the investigation." % _selected_suspect
	)
	confirm_dialog.popup_centered()

func _on_confirmed() -> void:
	var solution: Dictionary = GameState.current_mystery.get("solution", {})
	var culprit: String = solution.get("culprit", "")
	var correct: bool = _selected_suspect == culprit

	GameState.accusation_result = {
		"correct": correct,
		"suspect_guessed": _selected_suspect,
		"culprit": culprit,
		"solution": solution,
	}
	GameState.game_phase = GameState.Phase.RESULT
	get_tree().change_scene_to_file("res://scenes/ui/ResultScreen.tscn")

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
func _go_case() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")
