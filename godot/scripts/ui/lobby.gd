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
## [Session 47] Night File (docs/STYLE_GUIDE.md). StatusBox is a steel stamp
## now -- "Waiting for Players" is a statement of record, which is the stamp's
## job everywhere else. The roster is drawn as rows with a seat number in the
## ID column, the same object a finding is drawn as: who is at the table is
## the first thing a social game has to make legible.

extends Control

@onready var room_code_label: Label = $VBox/RoomCodeLabel
@onready var join_url_label: Label = $VBox/JoinUrlLabel
@onready var mystery_title_label: Label = $VBox/MysteryTitleLabel
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
## of import"). `tag`, when given, is a small aside next to the name ("you —
## host") rather than folded into the big label itself, since that text
## growing to match would fight the point of growing the name in the first
## place.
func _add_player_row(display_name: String, tag: String = "") -> void:
	var seat: int = player_list.get_child_count() + 1
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

	var name_lbl := Label.new()
	name_lbl.theme_type_variation = &"PlayerNameLabel"
	name_lbl.text = display_name
	name_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_lbl.clip_text = true
	line.add_child(name_lbl)

	if not tag.is_empty():
		var tag_lbl := Label.new()
		tag_lbl.theme_type_variation = &"FaintLabel"
		tag_lbl.text = tag.to_upper()
		tag_lbl.size_flags_vertical = Control.SIZE_SHRINK_CENTER
		line.add_child(tag_lbl)

	player_list.add_child(row)
	_update_seat_count()

## The count, and the one fact a host needs before pressing Open: APF cannot
## assign to a table of one (constraint 2 -- the only casefile would be the
## whole case). Said, not enforced: the start route is shared with the gather
## loop, and gating it here would be a rule the server does not have.
func _update_seat_count() -> void:
	var seats: int = player_list.get_child_count()
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
