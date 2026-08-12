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

## True between the server's first startProgress push and the one that clears
## it. Drives both the elapsed-time ticker in _process and the button states.
var _starting: bool = false
var _start_elapsed_seconds: float = 0.0


func _ready() -> void:
	create_button.pressed.connect(_on_create_pressed)
	join_button.pressed.connect(_on_join_pressed)
	register_button.pressed.connect(_on_register_pressed)
	start_button.pressed.connect(_on_start_pressed)

	GameState.state_updated.connect(_on_state_updated)
	GameState.phase_changed.connect(_on_phase_changed)
	GameState.start_progress_changed.connect(_on_start_progress_changed)

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


## The fact-bank build takes ~50s and the HTTP request stays in flight the
## whole time, so this fires the request and then says nothing more about it:
## the running commentary comes from the server's startProgress pushes
## (_on_start_progress_changed), and the phase change to CATEGORY is what
## signals success. The callback here only ever reports a failure.
func _on_start_pressed() -> void:
	if not GameState.can_start_game():
		return
	_set_busy(true)
	_start_elapsed_seconds = 0.0
	_set_status("Starting...")
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


## Room-wide, so every player's lobby narrates the wait -- not just the host
## who pressed Start. The elapsed counter matters as much as the batch count:
## the batches run concurrently and all land within a few seconds of each
## other, so the count sits at 0 for most of the wait and only a ticking clock
## proves the room is still alive.
func _on_start_progress_changed(progress: Dictionary) -> void:
	_starting = bool(progress.get("active", false))
	if _starting:
		_set_status(str(progress.get("label", "Starting...")))
	_refresh_controls()


func _process(delta: float) -> void:
	if not _starting:
		return
	_start_elapsed_seconds += delta
	var counts: Array = GameState.start_progress_counts()
	var suffix := ""
	if int(counts[1]) > 0:
		suffix = " (%d/%d batches)" % [int(counts[0]), int(counts[1])]
	_set_status("%s  [%ds]%s" % [
		GameState.start_progress_label(), int(_start_elapsed_seconds), suffix,
	])


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

	if _starting:
		start_button.text = "Starting..."
	elif in_session and GameState.player_count() < GameState.MIN_PLAYERS:
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
