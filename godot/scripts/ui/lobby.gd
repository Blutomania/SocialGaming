## Lobby — host waits here after generating a mystery.
## Displays the room code, join URL, live player list, and "Start Game" button.
## Phones join via mobile.html; each join broadcasts player_joined over WebSocket.
##
## StatusBox (top right) is THE status-updates section of this screen (owner,
## playtest WaitingSept7) -- it opens on the static "Waiting for Players" and
## the same label is repointed to carry every status this screen ever shows
## ("Starting…", a start error), rather than that text living in a second,
## separate label at the bottom of the main column.
##
## [Session 47] Night File (docs/STYLE_GUIDE.md). [Session 49] StatusBox was a
## steel stamp; the owner's markup took the fill off. It is a NoticePanel now
## -- an ink outline, because "Waiting for Players" is a live state rather
## than a statement of record -- and its words shimmer while the room waits. The roster is drawn as rows with a seat number in the
## ID column, the same object a finding is drawn as: who is at the table is
## the first thing a social game has to make legible.

extends Control

@onready var room_code_label: Label = $VBox/CodeRows/CodeRow/Line/RoomCodeLabel
@onready var join_url_label: Label = $VBox/CodeRows/JoinRow/Line/JoinUrlLabel
## "The case of" over the title (owner's lobby markup, Session 49; moved from
## beside the title to above it and enlarged, Session 51): the lobby reads as
## the cover of a case file, not as a room-code screen.
@onready var mystery_title_label: Label = $VBox/TitleBlock/MysteryTitleLabel
## The table is always drawn as four seats (owner's markup, Session 51): empty
## ones are faint outlines, so a room of one still reads as a game for four and
## the column keeps its shape instead of sitting lopsided. A fifth player gets a
## fifth row. Real rows come first; placeholders fill the rest.
const _TABLE_SEATS: int = 4
## Placeholders are children of the same grid, so the count of real players is
## kept here rather than read from get_child_count().
var _seated: int = 0

## A two-column grid inside a scroll (Session 47, after the owner's first
## render): one roster row per player in a single column pushed a centred
## layout up into the logo at only two seats. Two columns seat four in two
## rows, the column is now pinned under the logo and grows downward only, and
## the scroll takes whatever height is left, so a bigger table scrolls rather
## than pushing Open the case off the screen.
@onready var player_list: GridContainer = $VBox/PlayerScroll/PlayerList
@onready var start_button: Button = $VBox/StartButton
@onready var back_button: Button = $VBox/BackButton
@onready var status_label: Label = $StatusBox/StatusLabel
@onready var players_header: Label = $VBox/PlayersHeader
@onready var seat_hint: Label = $VBox/SeatHint

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
func _ready() -> void:
	room_code_label.text = GameState.game_id
	join_url_label.text = ApiClient.server_url + "/play"
	mystery_title_label.text = GameState.current_mystery.get("title", "Mystery")
	_fit_title()
	_start_shimmer()

	start_button.pressed.connect(_on_start)
	back_button.pressed.connect(_on_back)
	ApiClient.ws_event.connect(_on_ws_event)
	ApiClient.connect_ws(GameState.game_id, GameState.player_id)

	_add_player_row(GameState.player_name, "you · host")

func _exit_tree() -> void:
	if ApiClient.ws_event.is_connected(_on_ws_event):
		ApiClient.ws_event.disconnect(_on_ws_event)

# ---------------------------------------------------------------------------
# WebSocket events
# ---------------------------------------------------------------------------
func _on_ws_event(event_name: String, data: Dictionary) -> void:
	match event_name:
		"player_joined":
			_add_player_row(data.get("name", "?"))
		"game_started":
			_go_to_game()

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
func _on_start() -> void:
	start_button.disabled = true
	_stop_shimmer()
	status_label.text = "Starting…"
	ApiClient.start_game(GameState.game_id, GameState.player_id, _on_started)

func _on_started(error: String, _data: Dictionary) -> void:
	if error:
		start_button.disabled = false
		status_label.text = "Error: " + error
		return
	_go_to_game()

func _on_back() -> void:
	ApiClient.disconnect_ws()
	GameState.reset()
	get_tree().change_scene_to_file("res://scenes/ui/MainMenu.tscn")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
## Player names are set as big as the room code (owner, playtest WaitingSept7:
## "it's a social game, so who you are playing with is high up in a hierarchy
## of import"). `tag`, when given, is a small aside under the name ("you —
## host") rather than folded into the big label itself, since that text
## growing to match would fight the point of growing the name in the first
## place.
func _add_player_row(display_name: String, tag: String = "") -> void:
	_seated += 1
	var row := _build_seat_row(_seated, display_name, tag)
	player_list.add_child(row)
	## Ahead of the placeholders, which are rebuilt behind it.
	player_list.move_child(row, _seated - 1)
	_fill_empty_seats()
	_update_seat_count()

## One seat row. A placeholder is the same row built with the same labels, so it
## is exactly the height of a real one, with the words made transparent rather
## than removed and the whole row faded: a seat, not an empty box of another size.
func _build_seat_row(seat: int, display_name: String, tag: String, empty: bool = false) -> PanelContainer:
	var row := PanelContainer.new()
	row.theme_type_variation = &"FindingRow"
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var line := HBoxContainer.new()
	line.add_theme_constant_override("separation", Palette.SPACE_WIDE)
	row.add_child(line)

	var seat_lbl := Label.new()
	seat_lbl.theme_type_variation = &"FindingIdLabel"
	seat_lbl.text = str(seat)
	seat_lbl.custom_minimum_size = Vector2(44, 0)
	seat_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	seat_lbl.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	line.add_child(seat_lbl)
	line.add_child(VSeparator.new())

	## Name and tag stacked, not side by side. Beside the name, the tag took
	## the width the name needed and clipped "Host" to "Hos" at two columns
	## (Session 49 playtest); under it, the name gets the whole row.
	var stack := VBoxContainer.new()
	stack.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	stack.alignment = BoxContainer.ALIGNMENT_CENTER
	stack.add_theme_constant_override("separation", 0)
	line.add_child(stack)

	var name_lbl := Label.new()
	name_lbl.theme_type_variation = &"PlayerNameLabel"
	name_lbl.text = display_name
	name_lbl.clip_text = true
	name_lbl.text_overrun_behavior = TextServer.OVERRUN_TRIM_ELLIPSIS
	stack.add_child(name_lbl)

	if not tag.is_empty():
		var tag_lbl := Label.new()
		tag_lbl.theme_type_variation = &"FaintLabel"
		tag_lbl.text = tag.to_upper()
		stack.add_child(tag_lbl)

	if empty:
		for child in stack.get_children():
			(child as Label).self_modulate.a = 0.0
		row.modulate.a = 0.3
		row.mouse_filter = Control.MOUSE_FILTER_IGNORE
		row.set_meta("empty_seat", true)
	return row

## Rebuilt whole each time rather than patched: at most three rows, once per
## join, so there is nothing to optimise and nothing to keep in step.
func _fill_empty_seats() -> void:
	for child in player_list.get_children():
		if child.has_meta("empty_seat"):
			player_list.remove_child(child)
			child.queue_free()
	for seat in range(_seated + 1, _TABLE_SEATS + 1):
		## Same placeholder words as a real row, so the heights match.
		player_list.add_child(_build_seat_row(seat, "Open seat", "waiting", true))

## The count, and the one fact a host needs before pressing Open: APF cannot
## assign to a table of one (constraint 2 -- the only casefile would be the
## whole case). Said, not enforced: the start route is shared with the gather
## loop, and gating it here would be a rule the server does not have.
func _update_seat_count() -> void:
	var seats: int = _seated
	players_header.text = "At the table · %d" % seats
	## Hidden, not just emptied: an empty Label still takes a line of height,
	## and this column has none to spare.
	seat_hint.visible = seats < 2
	seat_hint.text = "SEATS FILL AS PHONES JOIN. A SHARED CASE NEEDS TWO OR MORE."

func _go_to_game() -> void:
	GameState.game_phase = GameState.Phase.CASE_DISPLAY
	## CaseBrief, not CaseDisplay: a room gets the two-page brief, which reads
	## no evidence and no twists. CaseDisplay is the author's view (Session 48).
	get_tree().change_scene_to_file("res://scenes/ui/CaseBrief.tscn")

## A long title wraps instead of running under the status box. The Neriin
## title fits on one line at 720 wide; a generated title has no length limit,
## so the row is measured rather than trusted.
func _fit_title() -> void:
	## The column's width from its offsets, not size: size is not settled in
	## _ready(), and the offsets are what the scene fixes it to (720).
	## "The case of" sits above the title now, so the title has the full width.
	var room: float = $VBox.offset_right - $VBox.offset_left
	var font: Font = mystery_title_label.get_theme_font("font")
	var font_size: int = mystery_title_label.get_theme_font_size("font_size")
	var wide: float = font.get_string_size(mystery_title_label.text, HORIZONTAL_ALIGNMENT_LEFT, -1, font_size).x
	if wide > room:
		mystery_title_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		mystery_title_label.custom_minimum_size.x = room

# ---------------------------------------------------------------------------
# The shimmer -- owner's lobby markup, Session 49: "a subtle effect like
# shimmer" on Waiting for Players. A slow band of light crosses the words
# every few seconds. It runs ONLY while the room is waiting and stops the
# moment the status says anything else, so on this screen movement means
# "still live" and nothing else moves. One tiny shader on one label: no
# per-frame script work, no allocation after _ready().
# ---------------------------------------------------------------------------
const _SHIMMER: Shader = preload("res://shaders/shimmer.gdshader")

func _start_shimmer() -> void:
	var mat: ShaderMaterial = ShaderMaterial.new()
	mat.shader = _SHIMMER
	status_label.material = mat
	_size_shimmer()
	if not status_label.resized.is_connected(_size_shimmer):
		status_label.resized.connect(_size_shimmer)

func _size_shimmer() -> void:
	var mat: ShaderMaterial = status_label.material as ShaderMaterial
	if mat != null:
		mat.set_shader_parameter("width", maxf(status_label.size.x, 1.0))

func _stop_shimmer() -> void:
	status_label.material = null
