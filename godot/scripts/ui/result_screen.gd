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
@onready var verdict_word_label: Label = $ScrollContainer/MainVBox/VerdictRow/VerdictWordLabel
@onready var verdict_rest_label: Label = $ScrollContainer/MainVBox/VerdictRow/VerdictRestLabel
@onready var portrait_rect: TextureRect = $ScrollContainer/MainVBox/SolutionRow/PortraitRect
@onready var solution_label: RichTextLabel = $ScrollContainer/MainVBox/SolutionRow/SolutionLabel
@onready var stamp: PanelContainer = $ScrollContainer/MainVBox/Stamp
## The reveal (Session 51): the case's closing moment, written at generation
## time (solution.reveal), under the live line saying who closed it. Until
## Session 51 the server wrote a narrative on every win and nothing showed it.
@onready var winner_line_label: Label = $ScrollContainer/MainVBox/WinnerLineLabel
@onready var reveal_label: Label = $ScrollContainer/MainVBox/RevealLabel
@onready var stamp_key: Label = $ScrollContainer/MainVBox/Stamp/StampRow/StampKey
@onready var stamp_text: Label = $ScrollContainer/MainVBox/Stamp/StampRow/StampText
@onready var ledger: VBoxContainer = $ScrollContainer/MainVBox/Ledger
@onready var rating_row: HBoxContainer = $ScrollContainer/MainVBox/RatingRow
@onready var play_again_button: Button = $ScrollContainer/MainVBox/Buttons/PlayAgainButton
@onready var review_button: Button = $ScrollContainer/MainVBox/Buttons/ReviewButton
@onready var disclosure_title: Label = $ScrollContainer/MainVBox/DisclosureTitle
@onready var disclosure_note: Label = $ScrollContainer/MainVBox/DisclosureNote
@onready var disclosure_container: VBoxContainer = $ScrollContainer/MainVBox/DisclosureContainer

var _rating_given: bool = false

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	play_again_button.pressed.connect(_on_play_again)
	review_button.pressed.connect(_go_case)
	_populate()
	_build_rating_buttons()
	_load_disclosure()

# ---------------------------------------------------------------------------
# Populate
# ---------------------------------------------------------------------------
func _populate() -> void:
	var result: Dictionary = GameState.accusation_result
	var correct: bool = result.get("correct", false)
	var suspect: String = result.get("suspect_guessed", "?")
	var culprit: String = result.get("culprit", "?")
	var plot: Dictionary = result.get("plot_reveal", {})

	## Split across two labels, not one -- owner, playtest ResultSept8: only
	## the single word ("Correct"/"Wrong") should be the big 35px message,
	## the rest of the sentence a size down. A Label can't mix two sizes in
	## its own text, so VerdictWordLabel and VerdictRestLabel share the
	## VerdictLabel variation's colour logic but carry different font sizes
	## (Style.gd).
	##
	## [Session 47] Night File's voice (docs/STYLE_GUIDE.md): a case report,
	## not a judgement. The big word names the person instead of grading the
	## player -- "Not Cadan Polglase." says what "Wrong." says and also WHO,
	## which is the thing a table turns to argue about. Same two labels, same
	## sizes the owner set on ResultSept8; only the words changed.
	var verdict_color: Color = Palette.POSITIVE if correct else Palette.NEGATIVE
	if correct:
		verdict_word_label.text = "Solved."
		verdict_rest_label.text = "%s did it." % culprit
	else:
		verdict_word_label.text = "Not %s." % suspect
		verdict_rest_label.text = "%s did it." % culprit
	verdict_word_label.add_theme_color_override("font_color", verdict_color)
	verdict_rest_label.add_theme_color_override("font_color", verdict_color)

	## Shown on a loss too: the reveal is the story of the crime, not a prize,
	## and full disclosure happens either way. The server's text first (a win
	## carries it, fallback included); otherwise the mystery's own, which the
	## host already holds. A label with no content is never drawn (STYLE_GUIDE).
	var reveal: String = str(result.get("resolution_narrative", "")).strip_edges()
	if reveal.is_empty():
		reveal = str(result.get("solution", {}).get("reveal", "")).strip_edges()
	reveal_label.text = reveal
	reveal_label.visible = not reveal.is_empty()
	var winner_line: String = str(result.get("winner_line", "")).strip_edges()
	winner_line_label.text = winner_line
	winner_line_label.visible = not winner_line.is_empty()

	# Full solution breakdown. plot_reveal.key_evidence entries are already
	# {id, name, description} -- resolved server-side (_format_plot_reveal(),
	# or locally on the single-player path via _local_plot_reveal()) -- so
	# this screen shows clue NAMES and never a bare id like "E2" (owner,
	# playtest SolvedSept7).
	var key_ev: Array = plot.get("key_evidence", [])
	var clue_names: Array = []
	for entry in key_ev:
		clue_names.append(str(entry.get("name", "?")))

	# GDScript has no implicit adjacent-string concatenation -- the `+` are
	# required, and without them this file fails to PARSE, so the whole script
	# never loads and every line in it silently does nothing.
	var sol_text: String = (
		"[b]The Culprit:[/b] %s\n"
		+ "[b]The Crime:[/b] %s\n"
		+ "[b]His/Her Motive:[/b] %s\n"
		+ "[b]Key Clues:[/b] %s"
	) % [
		plot.get("culprit", culprit),
		plot.get("method", "?"),
		plot.get("motive", "?"),
		", ".join(clue_names) if not clue_names.is_empty() else "?",
	]
	solution_label.text = sol_text

	## A portrait beside the solution text (owner, playtest ResultSept8: "too
	## much just text"). Same seeded-icon mechanism CaseDisplay's cast rows
	## already use (Icons.suspect/Icons.texture) -- not a real likeness, a
	## stable decorative silhouette for this culprit in this game. Icons.gd
	## returns null on an empty set on purpose, so this correctly draws
	## nothing rather than a placeholder box when no suspect icon exists yet.
	var culprit_icon: String = Icons.suspect(
		str(plot.get("culprit", culprit)), GameState.game_id,
		str(plot.get("culprit_pronouns", "")), str(plot.get("culprit_presentation", "")))
	portrait_rect.texture = Icons.texture(culprit_icon)
	portrait_rect.modulate = Icons.tint()

	_ledger_row("Your accusation", suspect)
	_ledger_row("The culprit", culprit)
	_populate_stats(result.get("gameplay_stats", {}))

## Night File's ledger (docs/STYLE_GUIDE.md): label left, value right, a
## hairline under each. A table of what happened, read down one column --
## the shape the reference uses for its own result, and the one place on this
## screen where facts are listed rather than told.
func _ledger_row(label_text: String, value_text: String) -> void:
	var row := HBoxContainer.new()
	var key := Label.new()
	key.theme_type_variation = &"FaintLabel"
	key.text = label_text.to_upper()
	key.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	key.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(key)
	var value := Label.new()
	value.theme_type_variation = &"LedgerValueLabel"
	value.text = value_text
	value.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	row.add_child(value)
	ledger.add_child(row)
	var rule := HSeparator.new()
	rule.add_theme_constant_override("separation", Palette.SPACE_BASE)
	ledger.add_child(rule)

## Rounds played and elapsed time, in place of "How to deduce" (owner, playtest
## SolvedSept7: "remove the how to deduce section, INSTEAD let's surface
## gameplay stats"). Empty on the single-player/legacy path -- no APF session
## ran, so there is nothing true to report, and those rows are left out rather
## than showing a guessed zero. Ledger rows since Session 47.
func _populate_stats(stats: Dictionary) -> void:
	if stats.is_empty():
		return
	var rounds_played: int = stats.get("rounds_played", 0)
	var rounds_total: int = stats.get("rounds_total", 0)
	var elapsed: int = stats.get("elapsed_seconds", 0)
	_ledger_row("Rounds played", "%d of %d" % [rounds_played, rounds_total])
	_ledger_row("Time played", _format_duration(elapsed))

## "127 seconds" means nothing at a table -- minutes and seconds, the way a
## player would actually say it back.
func _format_duration(seconds: int) -> String:
	var m: int = seconds / 60
	var s: int = seconds % 60
	if m == 0:
		return "%d sec" % s
	return "%d min %d sec" % [m, s]

# ---------------------------------------------------------------------------
# Full disclosure (docs/PLAYTEST_FLOW.md, "Full disclosure closes the game")
#
# NOT A TIE-BREAKER AND NOT A RESCUE. Owner, Session 41: "so much of the fun of
# this game is the Choose aspect of it… seeing the full disclosure is necessary
# to reward that choice." You picked the setting and paid for the generation, so
# you are owed the whole of it, not the fraction that happened to be shared.
#
# And it does a second job for free. Every finding somebody sat on appears with
# their name against it, which is what makes withholding a real decision rather
# than a costless one. "She was holding the ledger page the whole time" is the
# sentence the mechanic exists to produce, and nothing before the end can
# produce it.
#
# Nothing here costs an API call: it is the session's own log, reformatted.
# ---------------------------------------------------------------------------
func _load_disclosure() -> void:
	if GameState.game_id.is_empty():
		return
	ApiClient.apf_disclosure(GameState.game_id, _on_disclosure)

func _on_disclosure(error: String, data: Dictionary) -> void:
	## A single-player or pre-APF game has no assignment, so the server answers 409.
	## That is not an error worth showing anybody — this section simply is not
	## part of that game.
	if error or not bool(data.get("disclosed", false)):
		return

	var withheld: Array = data.get("withheld", [])
	disclosure_title.visible = true
	disclosure_note.visible = true
	_populate_stamp(withheld)
	_populate_own_record(data.get("by_player", []))

	if withheld.is_empty():
		disclosure_note.text = "Everything found was shared. Nobody held anything back."
		return

	disclosure_note.text = (
		"%d findings never reached the table until the case closed."
		% withheld.size()
	)

	disclosure_container.add_theme_constant_override("separation", Palette.SPACE_BASE)
	for entry in withheld:
		disclosure_container.add_child(_withheld_row(entry))

## The stamp under the verdict (Night File): the one sentence full disclosure
## exists to produce, said where the table is already looking. Names the
## first finding somebody sat on and counts the rest; the full list is below.
func _populate_stamp(withheld: Array) -> void:
	stamp.visible = true
	if withheld.is_empty():
		stamp_key.text = "Nothing kept back"
		stamp_text.text = "EVERY FINDING REACHED THE TABLE."
		return
	var first: Dictionary = withheld[0]
	stamp_key.text = "Kept back"
	var sentence: String = "%s sat on %s." % [str(first.get("shared_by", "Someone")),
		_clip_words(str(first.get("title", "a finding")), _STAMP_TITLE_CHARS)]
	if withheld.size() > 1:
		sentence += "  +%d more." % (withheld.size() - 1)
	stamp_text.text = sentence.to_upper()

## The stamp is one unwrapped line in caps -- a stamp that wraps stops
## reading as a stamp -- so a long finding title is cut at a word boundary.
## The full title is in the list directly below it.
const _STAMP_TITLE_CHARS: int = 36

func _clip_words(text: String, limit: int) -> String:
	if text.length() <= limit:
		return text
	var cut: int = text.rfind(" ", limit)
	if cut <= 0:
		cut = limit
	return text.substr(0, cut) + "…"

## This player's own line in the record: what they volunteered against what
## they held, and what disclosure had to prise out of them. Read off
## by_player, which the server already counts -- the client derives nothing.
func _populate_own_record(by_player: Array) -> void:
	for entry in by_player:
		var p: Dictionary = entry
		if str(p.get("player_id", "")) != GameState.player_id:
			continue
		_ledger_row("Findings you shared",
			"%d of %d" % [int(p.get("volunteered", 0)), int(p.get("held", 0))])
		_ledger_row("Findings you kept back", str(int(p.get("withheld", 0))))
		return

## One finding somebody sat on, drawn as the same finding row ApfRound uses
## (ID column | rule | finding), so it reads as the same object it was during
## play -- now with a name against it.
func _withheld_row(item: Dictionary) -> Control:
	var row := PanelContainer.new()
	row.theme_type_variation = &"FindingRow"
	var line := HBoxContainer.new()
	line.add_theme_constant_override("separation", Palette.SPACE_WIDE)
	row.add_child(line)

	var id_label := Label.new()
	id_label.theme_type_variation = &"FindingIdLabel"
	id_label.text = GameState.finding_display_id(str(item.get("id", "")))
	id_label.custom_minimum_size = Vector2(44, 0)
	id_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	id_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	line.add_child(id_label)
	line.add_child(VSeparator.new())

	var body := VBoxContainer.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", Palette.SPACE_TIGHT)
	var who := Label.new()
	who.theme_type_variation = &"FaintLabel"
	who.text = "%s KEPT THIS BACK" % str(item.get("shared_by", "?")).to_upper()
	who.add_theme_color_override("font_color", Palette.STEEL_BRIGHT)
	body.add_child(who)
	var title := Label.new()
	title.theme_type_variation = &"HeadingLabel"
	title.text = str(item.get("title", "?"))
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_child(title)
	var text := Label.new()
	text.theme_type_variation = &"MutedLabel"
	text.text = str(item.get("body", ""))
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_child(text)
	line.add_child(body)
	return row

# ---------------------------------------------------------------------------
# Rating
# ---------------------------------------------------------------------------
## Ten choice tiles in one ButtonGroup (Night File): a rating is a choice,
## so the theme's steel "chosen" fill marks it -- the same signal as every
## other choice in the product, instead of this screen inventing its own.
func _build_rating_buttons() -> void:
	var group := ButtonGroup.new()
	for i in range(1, 11):
		var btn := Button.new()
		btn.text = str(i)
		btn.toggle_mode = true
		btn.button_group = group
		btn.custom_minimum_size = Vector2(44, 44)
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
	# The chosen tile is already filled -- the ButtonGroup did that. The rest
	# are disabled so the rating reads as recorded rather than still open: the
	# theme's disabled box sinks them to the well tier with faint text, which
	# is the "step back" the old modulate hack was approximating by hand.
	for child: Node in rating_row.get_children():
		if child is Button:
			var btn: Button = child
			btn.disabled = btn.text.to_int() != rating

# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
func _on_play_again() -> void:
	GameState.reset()
	get_tree().change_scene_to_file("res://scenes/ui/MainMenu.tscn")

func _go_case() -> void:
	get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")
