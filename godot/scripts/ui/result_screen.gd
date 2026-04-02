## ResultScreen — shows whether the accusation was correct and the full solution.
## Also hosts the viability rating (1–10) so the player/creator can rate
## the mystery quality before moving on.
##
## SESSION ANNOTATION — Phase 2:
## The rating save (ApiClient.rate_mystery) fires-and-forgets — failure is
## logged as a warning but does not block the player.
## Phase 3: In multiplayer, the result is broadcast to all players by the server.
## This scene should display who won (first correct accusation), not just
## whether the local player was right.

extends Control

# ---------------------------------------------------------------------------
# Node references
# ---------------------------------------------------------------------------
@onready var verdict_label: Label = $ScrollContainer/MainVBox/VerdictLabel
@onready var solution_label: RichTextLabel = $ScrollContainer/MainVBox/SolutionLabel
@onready var rating_row: HBoxContainer = $ScrollContainer/MainVBox/RatingRow
@onready var play_again_button: Button = $ScrollContainer/MainVBox/Buttons/PlayAgainButton
@onready var review_button: Button = $ScrollContainer/MainVBox/Buttons/ReviewButton

var _rating_given: bool = false

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	play_again_button.pressed.connect(_on_play_again)
	review_button.pressed.connect(_go_case)
	_populate()
	_build_rating_buttons()

# ---------------------------------------------------------------------------
# Populate
# ---------------------------------------------------------------------------
func _populate() -> void:
	var result: Dictionary = GameState.accusation_result
	var correct: bool = result.get("correct", false)
	var suspect: String = result.get("suspect_guessed", "?")
	var culprit: String = result.get("culprit", "?")
	var solution: Dictionary = result.get("solution", {})

	if correct:
		verdict_label.text = "Correct! %s is the culprit." % culprit
		verdict_label.modulate = Color.GREEN
	else:
		verdict_label.text = "Wrong. You accused %s — the real culprit was %s." % [suspect, culprit]
		verdict_label.modulate = Color.RED

	# Full solution breakdown
	var key_ev: Array = solution.get("key_evidence", [])
	var sol_text := (
		"[b]Culprit:[/b] %s\n"
		"[b]Method:[/b] %s\n"
		"[b]Motive:[/b] %s\n"
		"[b]Key evidence:[/b] %s\n\n"
		"[b]How to deduce:[/b]\n%s"
	) % [
		solution.get("culprit", "?"),
		solution.get("method", "?"),
		solution.get("motive", "?"),
		", ".join(key_ev),
		solution.get("how_to_deduce", "?"),
	]
	solution_label.text = sol_text

# ---------------------------------------------------------------------------
# Rating
# ---------------------------------------------------------------------------
func _build_rating_buttons() -> void:
	for i in range(1, 11):
		var btn := Button.new()
		btn.text = str(i)
		btn.custom_minimum_size = Vector2(36, 36)
		btn.pressed.connect(_on_rate.bind(i))
		rating_row.add_child(btn)

func _on_rate(rating: int) -> void:
	if _rating_given:
		return
	_rating_given = true
	var slug: String = GameState.current_mystery.get("_slug", "")
	if not slug.is_empty():
		ApiClient.rate_mystery(slug, rating, func(err, _d):
			if err:
				push_warning("Rating save failed: " + err)
		)
	# Dim all buttons to show rating was recorded
	for btn in rating_row.get_children():
		if btn is Button:
			btn.modulate = Color(0.5, 0.5, 0.5) if str(btn.text).to_int() != rating else Color.GOLD

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
func _on_play_again() -> void:
	GameState.reset()
	get_tree().change_scene_to_file("res://scenes/ui/MainMenu.tscn")

func _go_case() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")
