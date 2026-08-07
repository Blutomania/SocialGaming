## Headless end-to-end test for the LOBBY -> CATEGORY transition.
##
## COSTS REAL MONEY. start_game() builds the fact bank, which is ~5-7 real
## Claude API calls and can take up to ~90 seconds. Kept as a SEPARATE scene
## from lobby_smoke_test.tscn deliberately so the everyday smoke test stays
## free and instantly repeatable -- run this one only when the game-start path
## itself is what changed.
##
## Run:
##   cd server_py && python3 -m uvicorn main:app --port 8001 &
##   godot --headless --path godot res://scenes/tests/game_start_smoke_test.tscn
##
## Exits 0 on pass, 1 on failure.

extends Node

const PLACEHOLDER_CATEGORIES: Array = ["90s Movies", "Geography", "Food", "Music", "Sports"]

var _failures: int = 0


func _ready() -> void:
	_run.call_deferred()


func _run() -> void:
	print("=== MYF game-start smoke test (COSTS API CALLS) ===")

	var created := await _post(func(cb: Callable) -> void:
		ApiClient.create_game(GameState.ensure_player_id(), "Host", cb)
	)
	var code := str(created["data"].get("code", ""))
	if code.is_empty():
		_check(false, "created a room (error: %s)" % created["error"])
		return _finish()
	print("  room code: %s" % code)

	var host_id := GameState.player_id
	GameState.begin_session(code, host_id, "Host")
	await _wait_until(func() -> bool: return not GameState.view.is_empty())

	var all_ids: Array[String] = [host_id, "bot_two", "bot_three"]
	for i in range(1, all_ids.size()):
		await _post(func(cb: Callable) -> void:
			ApiClient.join_game(code, all_ids[i], "Bot %d" % i, cb)
		)
	for id in all_ids:
		await _post(func(cb: Callable) -> void:
			ApiClient.register(code, id, PLACEHOLDER_CATEGORIES, "insurance", cb)
		)
	await _wait_until(func() -> bool: return GameState.can_start_game())
	_check(GameState.can_start_game(), "room is startable")

	# Watch for the phase_changed signal specifically -- the Lobby scene relies
	# on it to hand off to the next screen, so a silent state_updated without
	# phase_changed would break that handoff.
	var saw_phase_change := [false]
	GameState.phase_changed.connect(func(phase: String, _previous: String) -> void:
		if phase == GameState.PHASE_CATEGORY:
			saw_phase_change[0] = true
	)

	print("  starting game (fact bank build, may take ~90s)...")
	var started := await _post(func(cb: Callable) -> void:
		ApiClient.start_game(code, host_id, cb)
	, 150.0)
	_check(started["error"] == "", "start_game succeeded (error: '%s')" % started["error"])

	var reached := await _wait_until(
		func() -> bool: return GameState.phase == GameState.PHASE_CATEGORY, 150.0)
	_check(reached, "phase reached CATEGORY (got: '%s')" % GameState.phase)
	_check(saw_phase_change[0], "phase_changed signal fired for CATEGORY")

	# What the CategoryPicker screen will need to render.
	var options := GameState.category_options()
	_check(options.size() > 0, "categoryOptions delivered (got %d)" % options.size())
	if options.size() > 0:
		var first: Dictionary = options[0]
		_check(first.has("category") and first.has("submittedBy"),
			"category options carry attribution (keys: %s)" % str(first.keys()))
		print("  sample option: %s (from %s)" % [
			str(first.get("category", "?")), str(first.get("submittedBy", "?"))])

	# Hands are dealt at start_game -- now they should exist.
	_check(GameState.my_hand().size() > 0,
		"hand dealt at game start (got %d cards)" % GameState.my_hand().size())

	var rule := GameState.round_rule()
	_check(not rule.is_empty(), "round rule assigned (id: '%s')" % GameState.round_rule_id())
	print("  round rule: %s %s" % [str(rule.get("emoji", "")), str(rule.get("name", "?"))])

	_finish()


func _post(invoke: Callable, timeout: float = 30.0) -> Dictionary:
	var done := [false]
	var result := {"error": "", "data": {}}
	invoke.call(func(error, data) -> void:
		result["error"] = error
		result["data"] = data
		done[0] = true
	)
	var waited := 0.0
	while not done[0] and waited < timeout:
		await get_tree().process_frame
		waited += get_process_delta_time()
	if not done[0]:
		result["error"] = "timed out"
	return result


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
