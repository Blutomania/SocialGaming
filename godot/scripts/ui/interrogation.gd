## Interrogation — select a suspect, ask a question, get an in-character reply.
## History of all Q&A pairs is stored in GameState.interrogation_history
## and displayed in a scroll view.
##
## SESSION ANNOTATION — Phase 2:
## Each "Ask" press makes one Claude API call via ApiClient.interrogate().
## Phase 3: Add a "Share This Clue" button next to each reply in the history.
## Clicking it calls NetworkManager.share_clue({character, question, response}).
## The 75% fanout happens server-side.

extends Control

# ---------------------------------------------------------------------------
# Node references
# ---------------------------------------------------------------------------
@onready var suspect_dropdown: OptionButton = $VBox/SuspectDropdown
@onready var question_input: LineEdit = $VBox/QuestionInput
@onready var ask_button: Button = $VBox/ButtonRow/AskButton
@onready var back_button: Button = $VBox/ButtonRow/BackButton
@onready var accuse_button: Button = $VBox/ButtonRow/AccuseButton
@onready var history_container: VBoxContainer = $VBox/ScrollContainer/HistoryContainer
@onready var status_label: Label = $VBox/StatusLabel
@onready var spinner: ProgressBar = $VBox/Spinner

var _mystery: MysteryData

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	_mystery = MysteryData.from_dict(GameState.current_mystery)

	# Populate suspect dropdown
	for ch in _mystery.get_interrogatable():
		suspect_dropdown.add_item(ch.name)

	ask_button.pressed.connect(_on_ask)
	back_button.pressed.connect(_go_case)
	accuse_button.pressed.connect(_go_accuse)
	question_input.text_submitted.connect(func(_t): _on_ask())

	_set_loading(false)
	_rebuild_history()

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
func _on_ask() -> void:
	var question := question_input.text.strip_edges()
	if question.is_empty():
		status_label.text = "Type a question first."
		return
	if suspect_dropdown.item_count == 0:
		status_label.text = "No suspects to interrogate."
		return

	var character_name: String = suspect_dropdown.get_item_text(suspect_dropdown.selected)
	_set_loading(true)
	status_label.text = "Interrogating %s…" % character_name

	ApiClient.interrogate(
		GameState.current_mystery,
		character_name,
		question,
		_on_reply.bind(character_name, question)
	)

func _on_reply(error: String, data: Dictionary, character_name: String, question: String) -> void:
	_set_loading(false)
	if error:
		status_label.text = "Error: " + error
		return

	var response: String = data.get("response", "(no response)")
	status_label.text = ""
	question_input.clear()

	GameState.record_interrogation(character_name, question, response)
	_add_history_entry(character_name, question, response)

# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
func _rebuild_history() -> void:
	for child in history_container.get_children():
		child.queue_free()
	for entry in GameState.interrogation_history:
		_add_history_entry(entry["character"], entry["question"], entry["response"])

func _add_history_entry(character: String, question: String, response: String) -> void:
	var panel := PanelContainer.new()
	var vbox := VBoxContainer.new()

	var q_label := Label.new()
	q_label.text = "[%s] %s" % [character, question]
	q_label.modulate = Color.ORANGE

	var r_label := Label.new()
	r_label.text = response
	r_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART

	# SESSION ANNOTATION — Phase 3:
	# Add a "Share Clue" button here.
	# btn.pressed.connect(NetworkManager.share_clue.bind({...}))

	vbox.add_child(q_label)
	vbox.add_child(r_label)
	panel.add_child(vbox)
	history_container.add_child(panel)

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
func _go_case() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")

func _go_accuse() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/Accusation.tscn")

# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------
func _set_loading(loading: bool) -> void:
	ask_button.disabled = loading
	question_input.editable = not loading
	suspect_dropdown.disabled = loading
	spinner.visible = loading
