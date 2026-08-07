## Lobby -- first screen. Create or join a room, then wait for the roster to
## fill and everyone to register.
##
## Deliberately minimal: this scene exists to prove the client/server pair
## works end-to-end (HTTP create/join + WebSocket state push) before any of
## the round-loop UI gets built on top of it. Category selection and card
## picking -- the rest of registration -- are their own screens and are not
## built yet; the Register button here submits placeholder categories so the
## lobby handshake can be exercised on its own. See docs/WIRING.md.
##
## Pattern follows CYM's lobby.gd: fire an HTTP action, then drive all UI off
## the resulting "game:state" WebSocket push rather than the HTTP callback.
## The HTTP reply only tells us the request was accepted; the push tells us
## what the room actually looks like now, for every player at once.

extends Control

@onready var status_label: Label = %StatusLabel
@onready var name_edit: LineEdit = %NameEdit
@onready var code_edit: LineEdit = %CodeEdit
@onready var create_button: Button = %CreateButton
@onready var join_button: Button = %JoinButton
@onready var register_button: Button = %RegisterButton
@onready var start_button: Button = %StartButton
@onready var room_code_label: Label = %RoomCodeLabel
@onready var player_list: VBoxContainer = %PlayerList


func _ready() -> void:
	create_button.pressed.connect(_on_create_pressed)
	join_button.pressed.connect(_on_join_pressed)
	register_button.pressed.connect(_on_register_pressed)
	start_button.pressed.connect(_on_start_pressed)

	GameState.state_updated.connect(_on_state_updated)
	GameState.phase_changed.connect(_on_phase_changed)

	_set_status("Enter a name, then create or join a room.")
	_refresh_controls()


# --- Actions -----------------------------------------------------------------

func _on_create_pressed() -> void:
	var display_name := name_edit.text.strip_edges()
	if display_name.is_empty():
		_set_status("Enter a name first.")
		return
	_set_busy(true)
	_set_status("Creating room...")
	var id := GameState.ensure_player_id()
	ApiClient.create_game(id, display_name, func(error: String, data: Dictionary) -> void:
		_set_busy(false)
		if error != "":
			_set_status("Could not create room: %s" % error)
			return
		var new_code := str(data.get("code", ""))
		if new_code.is_empty():
			_set_status("Server returned no room code.")
			return
		GameState.begin_session(new_code, id, display_name)
		_set_status("Room created. Share the code.")
	)


func _on_join_pressed() -> void:
	var display_name := name_edit.text.strip_edges()
	var target_code := code_edit.text.strip_edges().to_upper()
	if display_name.is_empty():
		_set_status("Enter a name first.")
		return
	if target_code.is_empty():
		_set_status("Enter a room code.")
		return
	_set_busy(true)
	_set_status("Joining %s..." % target_code)
	var id := GameState.ensure_player_id()
	ApiClient.join_game(target_code, id, display_name, func(error: String, _data: Dictionary) -> void:
		_set_busy(false)
		if error != "":
			_set_status("Could not join: %s" % error)
			return
		GameState.begin_session(target_code, id, display_name)
		_set_status("Joined %s." % target_code)
	)


## Placeholder registration. The real flow is a category screen (5 categories)
## followed by a card-pick screen; neither exists yet. Submitting stand-ins
## here keeps the lobby independently testable instead of blocked on UI that
## hasn't been built.
func _on_register_pressed() -> void:
	if not GameState.is_in_session():
		return
	_set_busy(true)
	var placeholder_categories := [
		"90s Movies", "Geography", "Food", "Music", "Sports",
	]
	ApiClient.register(
		GameState.code, GameState.player_id, placeholder_categories, "insurance",
		func(error: String, _data: Dictionary) -> void:
			_set_busy(false)
			if error != "":
				_set_status("Registration failed: %s" % error)
			else:
				_set_status("Registered. Waiting for the others.")
	)


func _on_start_pressed() -> void:
	if not GameState.can_start_game():
		return
	_set_busy(true)
	_set_status("Starting -- building the fact bank, this can take a while...")
	ApiClient.start_game(GameState.code, GameState.player_id, func(error: String, _data: Dictionary) -> void:
		_set_busy(false)
		if error != "":
			_set_status("Could not start: %s" % error)
	)


# --- State-driven UI ---------------------------------------------------------

func _on_state_updated(_view: Dictionary) -> void:
	_refresh_roster()
	_refresh_controls()


func _on_phase_changed(phase: String, _previous: String) -> void:
	if phase != GameState.PHASE_LOBBY:
		_set_status("Game started (phase: %s)." % phase)


func _refresh_roster() -> void:
	for child in player_list.get_children():
		child.queue_free()

	for entry in GameState.players():
		var p: Dictionary = entry
		var row := Label.new()
		var marks := ""
		if bool(p.get("registered", false)):
			marks += " [ready]"
		if not bool(p.get("connected", true)):
			marks += " [disconnected]"
		if str(p.get("id", "")) == GameState.player_id:
			marks += " (you)"
		row.text = "%s%s" % [str(p.get("name", "?")), marks]
		player_list.add_child(row)


func _refresh_controls() -> void:
	var in_session := GameState.is_in_session()

	create_button.visible = not in_session
	join_button.visible = not in_session
	code_edit.visible = not in_session
	name_edit.editable = not in_session

	room_code_label.visible = in_session
	room_code_label.text = "Room code: %s" % GameState.code

	register_button.visible = in_session and not GameState.am_registered()
	start_button.visible = in_session
	start_button.disabled = not GameState.can_start_game()

	if in_session and GameState.player_count() < GameState.MIN_PLAYERS:
		var needed := GameState.MIN_PLAYERS - GameState.player_count()
		start_button.text = "Waiting for %d more player(s)" % needed
	elif in_session and not GameState.all_registered():
		start_button.text = "Waiting for everyone to be ready"
	else:
		start_button.text = "Start Game"


func _set_status(message: String) -> void:
	status_label.text = message


func _set_busy(busy: bool) -> void:
	create_button.disabled = busy
	join_button.disabled = busy
	register_button.disabled = busy
