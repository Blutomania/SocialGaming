## ShareSelection — shown when a player's phase budget hits 0.
##
## Lists all findings for the just-completed phase as checkboxes.
## Player must select at least share_min% of them before submitting.
## The selected subset is broadcast to ALL other players.
##
## Duplicate check: if the server returns duplicate_flags, the offending
## items are highlighted and the player must swap them out.
##
## Flow:
##   budget hits 0 → Interrogation.tscn changes scene here
##   Player selects findings → taps Share
##   Server returns ok:true  → advance invest_phase, back to Interrogation
##   Server returns duplicate_flags → highlight conflicts, player reselects

extends Control

# ---------------------------------------------------------------------------
# Node references (wire in ShareSelection.tscn)
# ---------------------------------------------------------------------------
@onready var title_label: Label = $VBox/TitleLabel
@onready var subtitle_label: Label = $VBox/SubtitleLabel
@onready var findings_container: VBoxContainer = $VBox/ScrollContainer/FindingsContainer
@onready var counter_label: Label = $VBox/CounterLabel
@onready var share_button: Button = $VBox/ShareButton
@onready var status_label: Label = $VBox/StatusLabel
@onready var spinner: ProgressBar = $VBox/Spinner

var _phase: String = ""
var _findings: Array = []          ## [{id, ...}, ...] — all findings for this phase
var _checkboxes: Array = []        ## Parallel array of CheckBox nodes
var _duplicate_ids: Array = []     ## IDs flagged by server on last submit attempt
var _min_required: int = 0

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	_phase = _phase_name_from_invest_phase(GameState.invest_phase)
	_findings = GameState.current_phase_findings()
	_min_required = max(1, ceili(_findings.size() * GameState.share_min))

	title_label.text = "Share Your Findings"
	subtitle_label.text = (
		"You must share at least %d of %d %s findings (%d%% minimum).\n"
		% [_min_required, _findings.size(), _phase, int(GameState.share_min * 100)]
		+ "Your selections will be shared with ALL other players."
	)

	_build_checkboxes()
	_auto_check_minimum()
	_update_counter()

	share_button.pressed.connect(_on_share)
	spinner.visible = false

# ---------------------------------------------------------------------------
# Build UI
# ---------------------------------------------------------------------------
func _build_checkboxes() -> void:
	for child in findings_container.get_children():
		child.queue_free()
	_checkboxes.clear()

	for finding in _findings:
		var hbox := HBoxContainer.new()
		var cb := CheckBox.new()
		cb.toggled.connect(_on_toggle)
		_checkboxes.append(cb)

		var lbl := Label.new()
		lbl.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		lbl.text = _finding_summary(finding)
		lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		hbox.add_child(cb)
		hbox.add_child(lbl)
		findings_container.add_child(hbox)

func _auto_check_minimum() -> void:
	for i in range(min(_min_required, _checkboxes.size())):
		_checkboxes[i].button_pressed = true

func _update_counter() -> void:
	var selected := _selected_count()
	counter_label.text = "%d selected (minimum %d)" % [selected, _min_required]
	share_button.disabled = (selected < _min_required)
	if selected < _min_required:
		counter_label.modulate = Color.ORANGE_RED
	else:
		counter_label.modulate = Color.WHITE

func _on_toggle(_val: bool) -> void:
	_update_counter()
	# Clear duplicate highlights on change
	if not _duplicate_ids.is_empty():
		_duplicate_ids.clear()
		_rebuild_duplicate_highlights()

# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------
func _on_share() -> void:
	var selected_ids: Array = _selected_ids()
	if selected_ids.size() < _min_required:
		status_label.text = "Select at least %d findings before sharing." % _min_required
		return

	_set_loading(true)
	status_label.text = "Sharing…"
	ApiClient.share_phase(
		GameState.game_id, GameState.player_id, _phase, selected_ids,
		_on_share_result
	)

func _on_share_result(error: String, data: Dictionary) -> void:
	_set_loading(false)
	if error:
		status_label.text = "Error: " + error
		return

	var dups: Array = data.get("duplicate_flags", [])
	if not dups.is_empty():
		_duplicate_ids = dups
		_rebuild_duplicate_highlights()
		status_label.text = (
			"%d of your selections were already shared by another player. "
			"Uncheck the highlighted items and replace them." % dups.size()
		)
		return

	# Success — advance to next invest_phase and return to interrogation
	status_label.text = "Shared!"
	_advance_phase()
	get_tree().change_scene_to_file("res://scenes/ui/Interrogation.tscn")

func _rebuild_duplicate_highlights() -> void:
	for i in range(_findings.size()):
		var hbox: HBoxContainer = findings_container.get_child(i)
		if _findings[i].get("id", "") in _duplicate_ids:
			hbox.modulate = Color.ORANGE_RED
		else:
			hbox.modulate = Color.WHITE

func _advance_phase() -> void:
	var order := [
		GameState.InvestPhase.WITNESS,
		GameState.InvestPhase.SHARE_WITNESS,
		GameState.InvestPhase.INVESTIGATION,
		GameState.InvestPhase.SHARE_INVESTIGATION,
		GameState.InvestPhase.LEAD,
		GameState.InvestPhase.SHARE_LEAD,
		GameState.InvestPhase.DONE,
	]
	var idx := order.find(GameState.invest_phase)
	if idx >= 0 and idx + 2 < order.size():
		GameState.invest_phase = order[idx + 2]   ## skip to next active phase
	else:
		GameState.invest_phase = GameState.InvestPhase.DONE

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
func _selected_count() -> int:
	var count := 0
	for cb in _checkboxes:
		if cb.button_pressed:
			count += 1
	return count

func _selected_ids() -> Array:
	var ids: Array = []
	for i in range(_findings.size()):
		if _checkboxes[i].button_pressed:
			ids.append(_findings[i].get("id", ""))
	return ids

func _finding_summary(finding: Dictionary) -> String:
	if finding.has("question"):
		return "[%s] %s\n→ %s" % [
			finding.get("character", "?"),
			finding.get("question", ""),
			finding.get("response", ""),
		]
	elif finding.has("area_name"):
		return "[%s]\n%s" % [finding.get("area_name", "?"), finding.get("findings", "")]
	elif finding.has("lead_title"):
		return "[Lead: %s]\n%s" % [finding.get("lead_title", "?"), finding.get("findings", "")]
	return str(finding)

func _phase_name_from_invest_phase(ip: GameState.InvestPhase) -> String:
	match ip:
		GameState.InvestPhase.SHARE_WITNESS:
			return "witness"
		GameState.InvestPhase.SHARE_INVESTIGATION:
			return "investigation"
		GameState.InvestPhase.SHARE_LEAD:
			return "lead"
	return "witness"

func _set_loading(loading: bool) -> void:
	share_button.disabled = loading
	spinner.visible = loading
