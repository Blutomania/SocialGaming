## Lobby — host waits here after generating a mystery.
## Displays the room code, join URL, live player list, and "Start Game" button.
## Phones join via mobile.html; each join broadcasts player_joined over WebSocket.

extends Control

@onready var room_code_label: Label = $VBox/RoomCodeLabel
@onready var join_url_label: Label = $VBox/JoinUrlLabel
@onready var mystery_title_label: Label = $VBox/MysteryTitleLabel
@onready var player_list: VBoxContainer = $VBox/PlayerList
@onready var start_button: Button = $VBox/StartButton
@onready var back_button: Button = $VBox/BackButton
@onready var status_label: Label = $VBox/StatusLabel

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

	_add_player_row(GameState.player_name + " (you — host)")

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
func _add_player_row(display_name: String) -> void:
	var lbl := Label.new()
	lbl.text = "• " + display_name
	player_list.add_child(lbl)

func _go_to_game() -> void:
	GameState.game_phase = GameState.Phase.CASE_DISPLAY
	get_tree().change_scene_to_file("res://scenes/ui/CaseDisplay.tscn")
