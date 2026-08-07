## Headless end-to-end smoke test for the lobby handshake.
##
## Drives the REAL ApiClient + GameState autoloads against a REAL running
## server_py backend -- no mocks, no stubs. This is the first test that
## exercises the Godot client against the FastAPI server at all, so it
## deliberately asserts on the boring things (does a room code come back, does
## the WebSocket push actually arrive, does GameState mirror the roster) rather
## than anything clever.
##
## Run:
##   cd server_py && python3 -m uvicorn main:app --port 8001 &
##   godot --headless --path godot res://scenes/tests/lobby_smoke_test.tscn
##
## Exits 0 on pass, 1 on failure.

extends Node

const HOST_NAME: String = "Host"
const BOT_NAMES: Array[String] = ["Bot Two", "Bot Three"]
const PLACEHOLDER_CATEGORIES: Array = ["90s Movies", "Geography", "Food", "Music", "Sports"]

var _failures: int = 0


func _ready() -> void:
	_run.call_deferred()


func _run() -> void:
	print("=== MYF lobby smoke test ===")

	# 0. The Lobby scene must actually instantiate. The rest of this test
	#    exercises the autoloads directly, which would happily pass even if
	#    lobby.tscn were broken -- and a mistyped %UniqueName only fails at
	#    runtime, in _ready(), as a null dereference.
	var lobby_scene: PackedScene = load("res://scenes/ui/lobby.tscn")
	_check(lobby_scene != null, "lobby.tscn loads")
	if lobby_scene != null:
		var lobby: Node = lobby_scene.instantiate()
		add_child(lobby)
		await get_tree().process_frame
		_check(is_instance_valid(lobby), "lobby.tscn instantiates and survives _ready()")
		_check(lobby.get_node_or_null("%StartButton") != null,
			"lobby unique-name lookups resolve (%StartButton found)")
		lobby.queue_free()
		await get_tree().process_frame

	# 1. Host creates a room.
	var created := await _post(func(cb: Callable) -> void:
		ApiClient.create_game(GameState.ensure_player_id(), HOST_NAME, cb)
	)
	_check(created["error"] == "", "create_game returned no error (got: %s)" % created["error"])
	var code := str(created["data"].get("code", ""))
	_check(code.length() == 4, "room code is 4 characters (got: '%s')" % code)
	if code.is_empty():
		return _finish()
	print("  room code: %s" % code)

	# 2. Host opens the WebSocket. The server pushes initial state on connect.
	var host_id := GameState.player_id
	GameState.begin_session(code, host_id, HOST_NAME)
	var got_state := await _wait_until(func() -> bool: return not GameState.view.is_empty())
	_check(got_state, "WebSocket delivered an initial game:state push")
	_check(GameState.phase == GameState.PHASE_LOBBY,
		"phase mirrored as LOBBY (got: '%s')" % GameState.phase)
	_check(GameState.player_count() == 1, "roster has 1 player (got: %d)" % GameState.player_count())

	# 3. Two more players join over plain HTTP (stateless -- no second socket
	#    needed to prove the push reaches the host).
	var bot_ids: Array[String] = []
	for bot_name in BOT_NAMES:
		var bot_id := "bot_%s" % bot_name.to_lower().replace(" ", "_")
		bot_ids.append(bot_id)
		var joined := await _post(func(cb: Callable) -> void:
			ApiClient.join_game(code, bot_id, bot_name, cb)
		)
		_check(joined["error"] == "", "%s joined (error: '%s')" % [bot_name, joined["error"]])

	# 4. The host's socket should have been pushed the updated roster.
	var roster_grew := await _wait_until(func() -> bool: return GameState.player_count() == 3)
	_check(roster_grew, "host was pushed the grown roster (got: %d players)" % GameState.player_count())
	_check(not GameState.all_registered(), "nobody is registered yet")
	_check(not GameState.can_start_game(), "start is blocked before registration")

	# 5. Everyone registers.
	var all_ids: Array[String] = [host_id]
	all_ids.append_array(bot_ids)
	for id in all_ids:
		var registered := await _post(func(cb: Callable) -> void:
			ApiClient.register(code, id, PLACEHOLDER_CATEGORIES, "insurance", cb)
		)
		_check(registered["error"] == "", "%s registered (error: '%s')" % [id, registered["error"]])

	var all_ready := await _wait_until(func() -> bool: return GameState.all_registered())
	_check(all_ready, "all three players mirrored as registered")
	_check(GameState.can_start_game(), "can_start_game() is true with 3 registered players")

	# 6. Hands are dealt by _deal_round_hands() inside start_game(), NOT at
	#    registration -- so an empty hand here is correct, and asserting
	#    otherwise would be asserting a bug into existence.
	_check(GameState.my_hand().is_empty(),
		"no hand dealt yet in LOBBY (dealt at start_game) -- got %d cards" % GameState.my_hand().size())

	# What registration DOES establish: my picked card, now public because
	# everyone has registered (player_view gates pickedCard on all_reg or is_me).
	_check(str(GameState.my_player().get("pickedCard", "")) == "insurance",
		"my picked card is mirrored back (got: '%s')" % str(GameState.my_player().get("pickedCard", "")))

	# Other players' hands stay withheld regardless of phase.
	var others_hidden := true
	for entry in GameState.players():
		var p: Dictionary = entry
		if str(p.get("id", "")) != GameState.player_id and p.get("hand") != null:
			others_hidden = false
	_check(others_hidden, "other players' hands are withheld by player_view()")

	_finish()


# --- Helpers -----------------------------------------------------------------

## Wraps an ApiClient call (which takes a callback as its last argument) into
## something awaitable. Returns {"error": String, "data": Dictionary}.
func _post(invoke: Callable) -> Dictionary:
	var done := [false]
	var result := {"error": "", "data": {}}
	invoke.call(func(error, data) -> void:
		result["error"] = error
		result["data"] = data
		done[0] = true
	)
	var waited := 0.0
	while not done[0] and waited < 30.0:
		await get_tree().process_frame
		waited += get_process_delta_time()
	if not done[0]:
		result["error"] = "timed out"
	return result


## Polls a predicate until true, letting ApiClient._process pump the socket.
func _wait_until(predicate: Callable, timeout: float = 10.0) -> bool:
	var waited := 0.0
	while waited < timeout:
		if bool(predicate.call()):
			return true
		await get_tree().process_frame
		waited += get_process_delta_time()
	return false


func _check(condition: bool, description: String) -> void:
	if condition:
		print("  PASS  %s" % description)
	else:
		print("  FAIL  %s" % description)
		_failures += 1


func _finish() -> void:
	print("=== %s ===" % ("ALL PASSED" if _failures == 0 else "%d FAILURE(S)" % _failures))
	GameState.end_session()
	get_tree().quit(1 if _failures > 0 else 0)
