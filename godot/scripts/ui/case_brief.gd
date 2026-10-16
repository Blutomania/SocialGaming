## CaseBrief — APF's opening in a ROOM: the crime told, then the cast met,
## before any finding is assigned. Two pages behind BACK / NEXT (owner's
## markup over the Red Flags question screen, Session 48): a header band with
## the game's name, the mystery's name large, one scrollable box of rows, and
## two boxes at the foot.
##
## WHY A SEPARATE SCREEN, not a mode of CaseDisplay. CaseDisplay is the
## AUTHOR's view of a mystery -- key twists, every piece of evidence, the
## coherence badge -- and the owner kept it that way for reading a saved
## mystery alone. Shown to a room, that view gave the case away before round 1
## (Session 48 found it printing the twist that names the forger). One screen
## per job means the room view cannot leak by a visibility flag left on.
##
## Nothing here is ever a spoiler by construction: it reads only the setting,
## the crime as discovered, and who is in the cast. No evidence, no twists, no
## solution field is touched.

extends Control

@onready var column: MarginContainer = $Column
@onready var page_label: Label = $Column/VBox/HeaderBand/HeaderText/PageLabel
@onready var mystery_title: Label = $Column/VBox/MysteryTitle
@onready var brief_scroll: ScrollContainer = $Column/VBox/BriefScroll
@onready var brief_list: VBoxContainer = $Column/VBox/BriefScroll/BriefList
## "MORE BELOW ↓" at the cut (owner, Session 49). Shown only while there IS
## more below -- a hint that stays after the reader reaches the end is a hint
## that lies. Archivo Narrow (FaintLabel) carries the ↓ glyph; the prose
## faces do not, which is why this is not set in them.
@onready var more_below: Label = $Column/VBox/MoreBelow
@onready var status_label: Label = $Column/VBox/StatusLabel
@onready var back_button: Button = $Column/VBox/Footer/BackButton
@onready var next_button: Button = $Column/VBox/Footer/NextButton

const _PAGE_CASE: int = 0
const _PAGE_CAST: int = 1
const _PAGE_COUNT: int = 2
const _PAGE_NAMES: Array[String] = ["The case", "The cast"]

## The column never grows past this, so a wide monitor gets margins rather
## than a line of prose a metre long -- and it can never overflow the window,
## which is what the old CaseDisplay did in a room.
const _COLUMN_MAX: float = 1000.0
## Chrome.gd draws the brand mark at the window's top-left on every screen.
## The column's side margin never drops below this, so the header band stays
## clear of it at any window width. Mark: 48px tall at a 12px margin.
const _CHROME_CLEARANCE: int = 136

## The ID column is words here ("SCENE", "CRIME"), not E3/L1, so it is wider
## than ApfRound's 44px; suspect and witness IDs reuse the same width so the
## rule lines up down the whole box.
const _ID_WIDTH: float = 96.0
const _PORTRAIT: float = 64.0

var _mystery: MysteryData
var _page: int = _PAGE_CASE

func _ready() -> void:
	_mystery = MysteryData.from_dict(GameState.current_mystery)
	## The header band carries the game's graphic mark, not its name typed
	## out (owner, Session 49) -- the same file the lobby shows, so the
	## artist's version replaces both at once.
	## A count is STEEL_BRIGHT in Night File.
	page_label.add_theme_color_override("font_color", Palette.STEEL_BRIGHT)
	mystery_title.text = _mystery.title

	back_button.pressed.connect(_on_back)
	next_button.pressed.connect(_on_next)
	get_viewport().size_changed.connect(_fit_column)
	var bar: VScrollBar = brief_scroll.get_v_scroll_bar()
	bar.changed.connect(_update_more_below)
	bar.value_changed.connect(func(_v: float) -> void: _update_more_below())
	_fit_column()

	## The host's Begin moves the whole room at once, whichever page each
	## person happens to be reading -- nobody is left on the brief.
	if not GameState.game_id.is_empty():
		ApiClient.ws_event.connect(_on_ws_event)

	_render_page()

func _exit_tree() -> void:
	if ApiClient.ws_event.is_connected(_on_ws_event):
		ApiClient.ws_event.disconnect(_on_ws_event)

func _on_ws_event(event_name: String, data: Dictionary) -> void:
	if event_name == "apf_opened":
		GameState.record_apf_open(data)
		_go_rounds()

## Centres a column of at most _COLUMN_MAX, never closer to the edge than the
## brand mark allows. Recomputed on resize rather than anchored, because a
## MarginContainer cannot express "max width" on its own.
func _fit_column() -> void:
	var width: float = get_viewport_rect().size.x
	var side: int = maxi(_CHROME_CLEARANCE, int((width - _COLUMN_MAX) / 2.0))
	column.add_theme_constant_override("margin_left", side)
	column.add_theme_constant_override("margin_right", side)

# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
func _render_page() -> void:
	## remove_child before queue_free: a freed-later child still takes layout
	## space for the rest of the frame, which flashes both pages at once.
	for child in brief_list.get_children():
		brief_list.remove_child(child)
		child.queue_free()

	page_label.text = "%02d / %02d · %s" % [_page + 1, _PAGE_COUNT, _PAGE_NAMES[_page]]
	if _page == _PAGE_CASE:
		_render_case()
	else:
		_render_cast()
	brief_scroll.scroll_vertical = 0
	_render_footer()

## CRIME, then WHO / WHAT / WHERE / WHEN (owner, Session 49): open on the
## crime in a line, then the questions a reader asks of it, instead of opening
## on a paragraph of weather. Every row is skipped when its source is empty
## (_add_text_row) -- a label with nothing beside it is never drawn.
func _render_case() -> void:
	_add_text_row("CRIME", _mystery.crime_type)
	_add_text_row("WHO", _victims_text())
	## FOUND folded into WHAT (owner): who found them and how is the end of
	## what happened -- and the bitter-sweet smell in it is the closest thing
	## the brief has to a clue, so it stays.
	_add_text_row("WHAT", _paragraphs([_mystery.what_happened, _mystery.initial_discovery]))
	var place: String = " — ".join(PackedStringArray(
		[_mystery.location, _mystery.time_period].filter(func(t: String) -> bool: return not t.strip_edges().is_empty())))
	## A blank line, not a bare newline: the place line ran straight into the
	## description and read as one paragraph (Session 49 playtest).
	_add_text_row("WHERE", _paragraphs([place, _mystery.setting_description]))
	_add_text_row("WHEN", _mystery.when_occurred)

## Victims only (owner): the suspects have page 2 to themselves, and naming
## them here would spend that page's reveal early.
func _victims_text() -> String:
	var lines: PackedStringArray = []
	for v in _mystery.get_victims():
		var victim: MysteryData.CharacterData = v
		if victim.name.strip_edges().is_empty():
			continue
		lines.append(victim.name if victim.occupation.is_empty() \
			else "%s, %s" % [victim.name, victim.occupation])
	return "\n".join(lines)

## Non-empty parts joined by a blank line, so a missing half leaves no gap.
func _paragraphs(parts: Array) -> String:
	var kept: PackedStringArray = []
	for part in parts:
		var text: String = str(part).strip_edges()
		if not text.is_empty():
			kept.append(text)
	return "\n\n".join(kept)

## Deferred a frame by the scroll bar's own `changed` signal: the bar's range
## is only right after the rows have been laid out.
func _update_more_below() -> void:
	var bar: VScrollBar = brief_scroll.get_v_scroll_bar()
	more_below.visible = bar.value + bar.page < bar.max_value - 4.0

func _render_cast() -> void:
	## Every victim, not just the first: the crime text names both dead men in
	## the Neriin case, so a cast list with one of them reads as an error.
	## A lone victim keeps the plain "V"; two or more are numbered like suspects.
	var victims: Array = _mystery.get_victims()
	for i in range(victims.size()):
		var v: MysteryData.CharacterData = victims[i]
		var vid: String = "V" if victims.size() == 1 else "V%d" % (i + 1)
		brief_list.add_child(_person_row(vid, v.name, v.occupation, ""))

	## 2×2 to start (owner, Session 48: "start with 2x2 and see how it feels").
	## The column count is the one knob if it does not.
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 12)
	grid.add_theme_constant_override("v_separation", 12)
	var suspects: Array = _mystery.get_suspects()
	for i in range(suspects.size()):
		var s: MysteryData.CharacterData = suspects[i]
		var icon: String = Icons.suspect(s.name, GameState.game_id, s.pronouns, s.presentation)
		var card: PanelContainer = _person_row("S%d" % (i + 1), s.name, s.occupation, icon)
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		grid.add_child(card)
	brief_list.add_child(grid)

	var witnesses: Array = _mystery.characters.filter(
		func(c: MysteryData.CharacterData) -> bool: return c.role == "witness")
	for i in range(witnesses.size()):
		var w: MysteryData.CharacterData = witnesses[i]
		var row: PanelContainer = _person_row(
			"W%d" % (i + 1), w.name, w.occupation, Icons.witness(w.name, GameState.game_id))
		brief_list.add_child(row)

## BACK on the first page is disabled, not hidden: hiding it would let NEXT
## jump to full width and the footer would change shape between pages.
## On the last page NEXT becomes the screen's one brass action -- for the
## host only. Everyone else sees the same box, disabled, saying why.
func _render_footer() -> void:
	back_button.disabled = _page == _PAGE_CASE
	if _page < _PAGE_COUNT - 1:
		next_button.text = "NEXT"
		next_button.theme_type_variation = &""
		next_button.disabled = false
	elif GameState.is_host:
		next_button.text = "BEGIN THE INVESTIGATION"
		next_button.theme_type_variation = &"PrimaryButton"
		next_button.disabled = false
	else:
		next_button.text = "WAITING FOR THE HOST"
		next_button.theme_type_variation = &""
		next_button.disabled = true

func _on_back() -> void:
	if _page > _PAGE_CASE:
		_page -= 1
		_render_page()

func _on_next() -> void:
	if _page < _PAGE_COUNT - 1:
		_page += 1
		_render_page()
	elif GameState.is_host:
		_on_begin_rounds()

# ---------------------------------------------------------------------------
# Rows -- the finding row's shape (ID column, rule, text), reused so the
# brief already looks like the casefile it is about to become.
# ---------------------------------------------------------------------------
func _row_shell(id_text: String) -> Array:
	var row := PanelContainer.new()
	row.theme_type_variation = &"FindingRow"
	var line := HBoxContainer.new()
	line.add_theme_constant_override("separation", Palette.SPACE_WIDE)
	row.add_child(line)

	var id_label := Label.new()
	id_label.theme_type_variation = &"FindingIdLabel"
	id_label.text = id_text
	id_label.custom_minimum_size = Vector2(_ID_WIDTH, 0)
	id_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	id_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	line.add_child(id_label)
	line.add_child(VSeparator.new())
	return [row, line]

## A row of brief prose. Set in HeadingLabel (Archivo Narrow, 21) to match the
## owner's markup, which asked for the reference's size; each of these is a
## sentence or three, short enough that condensed type does not tire. A long
## setting_description is where that would show first.
func _add_text_row(id_text: String, body: String) -> void:
	if body.strip_edges().is_empty():
		return
	var shell: Array = _row_shell(id_text)
	var line: HBoxContainer = shell[1]
	var text := Label.new()
	text.theme_type_variation = &"HeadingLabel"
	text.text = body
	text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	line.add_child(text)
	brief_list.add_child(shell[0])

func _person_row(id_text: String, person: String, occupation: String, icon_path: String) -> PanelContainer:
	var shell: Array = _row_shell(id_text)
	var line: HBoxContainer = shell[1]

	var icon_tex: Texture2D = Icons.texture(icon_path)
	if icon_tex:
		var icon_rect := TextureRect.new()
		icon_rect.texture = icon_tex
		icon_rect.custom_minimum_size = Vector2(_PORTRAIT, _PORTRAIT)
		## IGNORE_SIZE, or the imported SVG's pixel size becomes the minimum
		## and the column overflows the window (the CaseDisplay bug, Session 48).
		icon_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon_rect.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		icon_rect.modulate = Icons.tint()
		icon_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
		line.add_child(icon_rect)

	var text := VBoxContainer.new()
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	text.alignment = BoxContainer.ALIGNMENT_CENTER
	text.add_theme_constant_override("separation", Palette.SPACE_TIGHT)
	var name_label := Label.new()
	name_label.theme_type_variation = &"HeadingLabel"
	name_label.text = person
	name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text.add_child(name_label)
	if not occupation.is_empty():
		var occ := Label.new()
		occ.theme_type_variation = &"MutedLabel"
		occ.text = occupation
		occ.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		text.add_child(occ)
	line.add_child(text)
	return shell[0]

# ---------------------------------------------------------------------------
# Begin -- moved here from CaseDisplay, unchanged in what it calls.
# ---------------------------------------------------------------------------
## The assignment is free and deterministic, so a refusal is a statement about
## the mystery rather than bad luck -- it is shown as such, not as a retry.
func _on_begin_rounds() -> void:
	next_button.disabled = true
	next_button.text = "OPENING THE CASE…"
	status_label.visible = false
	ApiClient.apf_open(GameState.game_id, GameState.player_id, _on_assigned)

func _on_assigned(error: String, data: Dictionary) -> void:
	if error:
		_render_footer()
		status_label.text = "This mystery cannot be assigned: " + error
		status_label.visible = true
		return
	GameState.record_apf_open(data)
	## Straight into round 1. Opening the assignment leaves the server at round
	## 0 -- every casefile assigned, none turned face up -- and the round screen
	## showed that as an empty "Round 0 of 4" the host had to click past
	## (Session 49 playtest). PLAYTEST_FLOW step 4 is "announces how many rounds,
	## and play begins": the count still shows, on round 1.
	ApiClient.apf_next_round(GameState.game_id, GameState.player_id, _on_first_round)

## A failure here is not fatal: the round screen opens at round 0 and the
## host's "Open the next round" makes the same call again.
func _on_first_round(_error: String, _data: Dictionary) -> void:
	_go_rounds()

func _go_rounds() -> void:
	GameState.game_phase = GameState.Phase.INTERROGATION
	get_tree().change_scene_to_file("res://scenes/ui/ApfRound.tscn")
