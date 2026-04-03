## MysteryGeneration — the "Set Your Mystery" screen.
## User types a prompt, presses Generate, waits for backend response,
## then is taken to CaseDisplay.
##
## Uses the async job system so Godot never blocks on a 60-90s HTTP call.
## Flow:
##   1. POST /generate/async  → job_id (returns in < 1s)
##   2. Poll GET /jobs/{job_id} every POLL_INTERVAL seconds
##   3. Show live "stage" text from the server (Generating… / Localizing… / etc.)
##   4. On status == "done" → load CaseDisplay
##   5. On status == "error" → show error, re-enable form
##
## SESSION ANNOTATION — Phase 2:
## This is the first scene that makes a real backend call. Test it by:
##   1. Running the FastAPI server: cd server && uvicorn main:app --port 8000
##   2. Press F5 in Godot, click "New Game", type any prompt, click "Generate".
##   3. Verify CaseDisplay loads with a populated mystery.

extends Control

const POLL_INTERVAL: float = 2.0   ## seconds between job status polls

# ---------------------------------------------------------------------------
# Node references (wire these in the .tscn)
# ---------------------------------------------------------------------------
@onready var prompt_input: LineEdit = $VBox/PromptInput
@onready var cinematic_checkbox: CheckBox = $VBox/CinematicCheckbox
@onready var generate_button: Button = $VBox/GenerateButton
@onready var back_button: Button = $VBox/BackButton
@onready var status_label: Label = $VBox/StatusLabel
@onready var spinner: ProgressBar = $VBox/Spinner          ## Indeterminate ProgressBar

var _job_id: String = ""
var _poll_timer: float = 0.0
var _polling: bool = false

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	generate_button.pressed.connect(_on_generate)
	back_button.pressed.connect(_on_back)
	prompt_input.text_submitted.connect(func(_t): _on_generate())
	_set_loading(false)

func _process(delta: float) -> void:
	if not _polling:
		return
	_poll_timer -= delta
	if _poll_timer <= 0.0:
		_poll_timer = POLL_INTERVAL
		ApiClient.poll_job(_job_id, _on_poll_result)

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
func _on_generate() -> void:
	var prompt := prompt_input.text.strip_edges()
	if prompt.is_empty():
		status_label.text = "Please describe your mystery scenario."
		return

	_set_loading(true)
	status_label.text = "Contacting server…"
	ApiClient.generate_mystery_async(
		prompt,
		cinematic_checkbox.button_pressed,
		_on_job_created
	)

func _on_job_created(error: String, data: Dictionary) -> void:
	if error:
		_set_loading(false)
		status_label.text = "Error: " + error
		return
	_job_id = data.get("job_id", "")
	if _job_id.is_empty():
		_set_loading(false)
		status_label.text = "Error: server did not return a job ID."
		return
	_poll_timer = 0.0   ## poll immediately on next _process tick
	_polling = true

func _on_poll_result(error: String, data: Dictionary) -> void:
	if error:
		_polling = false
		_set_loading(false)
		status_label.text = "Error polling job: " + error
		return

	var stage: String = data.get("stage", "Working…")
	status_label.text = stage

	match data.get("status", ""):
		"done":
			_polling = false
			var result: Dictionary = data.get("result", {})
			if result.is_empty():
				_set_loading(false)
				status_label.text = "Error: server returned an empty result."
				return
			_set_loading(false)
			GameState.current_mystery = result
			GameState.game_phase = GameState.Phase.CASE_DISPLAY
			get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")
		"error":
			_polling = false
			_set_loading(false)
			status_label.text = "Generation failed: " + data.get("error", "unknown error")
		_:
			pass   ## queued / running — keep polling

func _on_back() -> void:
	_polling = false
	_job_id = ""
	get_tree().change_scene_to_file("res://scenes/ui/MainMenu.tscn")

# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------
func _set_loading(loading: bool) -> void:
	generate_button.disabled = loading
	back_button.disabled = loading
	prompt_input.editable = not loading
	spinner.visible = loading
