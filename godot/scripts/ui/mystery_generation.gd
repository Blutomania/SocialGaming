## MysteryGeneration — the "Set Your Mystery" screen.
## User types a prompt, presses Generate, waits for backend response,
## then is taken to CaseDisplay.
##
## SESSION ANNOTATION — Phase 2:
## This is the first scene that makes a real backend call. Test it by:
##   1. Running the FastAPI server: cd server && uvicorn main:app --port 8000
##   2. Press F5 in Godot, click "New Game", type any prompt, click "Generate".
##   3. Verify CaseDisplay loads with a populated mystery.

extends Control

# ---------------------------------------------------------------------------
# Node references (wire these in the .tscn)
# ---------------------------------------------------------------------------
@onready var prompt_input: LineEdit = $VBox/PromptInput
@onready var cinematic_checkbox: CheckBox = $VBox/CinematicCheckbox
@onready var generate_button: Button = $VBox/GenerateButton
@onready var back_button: Button = $VBox/BackButton
@onready var status_label: Label = $VBox/StatusLabel
@onready var spinner: ProgressBar = $VBox/Spinner          ## Indeterminate ProgressBar

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	generate_button.pressed.connect(_on_generate)
	back_button.pressed.connect(_on_back)
	prompt_input.text_submitted.connect(func(_t): _on_generate())
	_set_loading(false)

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
func _on_generate() -> void:
	var prompt := prompt_input.text.strip_edges()
	if prompt.is_empty():
		status_label.text = "Please describe your mystery scenario."
		return

	_set_loading(true)
	status_label.text = "Building the case…"
	ApiClient.generate_mystery(
		prompt,
		cinematic_checkbox.button_pressed,
		_on_mystery_ready
	)

func _on_mystery_ready(error: String, data: Dictionary) -> void:
	_set_loading(false)
	if error:
		status_label.text = "Error: " + error
		return
	GameState.current_mystery = data
	GameState.game_phase = GameState.Phase.CASE_DISPLAY
	get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")

func _on_back() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/MainMenu.tscn")

# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------
func _set_loading(loading: bool) -> void:
	generate_button.disabled = loading
	back_button.disabled = loading
	prompt_input.editable = not loading
	spinner.visible = loading
