## ApiClient -- Global singleton.
## Wraps all HTTP calls to the FastAPI backend (server_py/main.py), plus the
## WebSocket connection for real-time push events during a game.
##
## Ported from Choose Your Mystery's godot/scripts/autoloads/ApiClient.gd --
## same HTTP+WS wrapper shape, adapted to Mind Your Friends' actual endpoint
## paths (see server_py/main.py).
##
## Compiles and runs against Godot 4.6.stable headless, and is exercised
## end-to-end against a real server_py by scenes/tests/lobby_smoke_test.tscn.
## (The "no Godot binary in this environment" note that used to sit here was
## wrong — see CLAUDE.md item 34 and docs/WIRING.md "Verifying the Godot
## client" for how to run the compile check.)
##
## HTTP callbacks receive (error: String, data: Dictionary).
## error is "" on success, or an error message on failure.
##
## WebSocket:
##   Call connect_ws(code, player_id) once per game session.
##   Emits signal ws_event(event_name: String, data: Dictionary) on each
##   push from the server. Scenes connect to this signal instead of polling
##   -- same contract as CYM's, and main.py's ConnectionManager pushes the
##   same {"event": ..., "data": ...} envelope shape CYM's server does.

extends Node

signal ws_event(event_name: String, data: Dictionary)

const SERVER_URL_DEFAULT: String = "http://localhost:8001"
const REQUEST_TIMEOUT: float = 30.0  ## seconds; question generation can take ~5-10s

## Timeout for POST /games/{code}/start alone. The fact-bank build is the
## longest single request in the game by an order of magnitude: ~50s with the
## batches running concurrently, and ~250s before that fix landed (measured,
## 3 players x 5 categories -- see CLAUDE.md item 36). The old 120s here timed
## out client-side on every real game start. Set well above the measured worst
## case: the request being slow is normal, and the UI is driven off the
## "game:state" WS pushes anyway, so a generous ceiling costs nothing while a
## tight one silently breaks starting a game.
const START_GAME_TIMEOUT: float = 300.0
var server_url: String = SERVER_URL_DEFAULT

## Active WebSocket peer (null when not in a game session)
var _ws: WebSocketPeer = null
var _ws_code: String = ""

func _ready() -> void:
	var cfg := ConfigFile.new()
	if cfg.load("user://server_config.cfg") == OK:
		server_url = cfg.get_value("server", "url", SERVER_URL_DEFAULT)

func _process(_delta: float) -> void:
	if _ws == null:
		return
	_ws.poll()
	var state := _ws.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		while _ws.get_available_packet_count() > 0:
			var raw := _ws.get_packet().get_string_from_utf8()
			var json := JSON.new()
			if json.parse(raw) == OK and json.data is Dictionary:
				var msg: Dictionary = json.data
				ws_event.emit(msg.get("event", ""), msg.get("data", {}))
	elif state == WebSocketPeer.STATE_CLOSED:
		_ws = null

# ---------------------------------------------------------------------------
# WebSocket connection
# ---------------------------------------------------------------------------

func connect_ws(code: String, player_id: String) -> void:
	"""Open a persistent WebSocket to /ws/{code}?player_id=... Call once
	after joining a game (see main.py's ws_endpoint)."""
	if _ws != null:
		_ws.close()
	_ws_code = code
	_ws = WebSocketPeer.new()
	var ws_url := server_url.replace("http://", "ws://").replace("https://", "wss://")
	ws_url += "/ws/" + code + "?player_id=" + player_id
	_ws.connect_to_url(ws_url)

func disconnect_ws() -> void:
	if _ws != null:
		_ws.close()
		_ws = null

# ---------------------------------------------------------------------------
# Lobby
# ---------------------------------------------------------------------------

## POST /games/create {playerId, name} -> {code}
func create_game(player_id: String, name: String, callback: Callable) -> void:
	_post("/games/create", {"playerId": player_id, "name": name}, callback)

## POST /games/{code}/join {playerId, name}
func join_game(code: String, player_id: String, name: String, callback: Callable) -> void:
	_post("/games/%s/join" % code, {"playerId": player_id, "name": name}, callback)

## POST /games/{code}/register {playerId, categories: [String;5], pickedCardId}
func register(code: String, player_id: String, categories: Array, picked_card_id: String, callback: Callable) -> void:
	_post("/games/%s/register" % code, {
		"playerId": player_id, "categories": categories, "pickedCardId": picked_card_id,
	}, callback)

## POST /games/{code}/start {playerId} -- triggers the real fact-bank Claude
## calls server-side; takes ~50s and the HTTP request stays in flight for the
## whole build.
##
## Drive the UI off the "game:state" WS pushes, NOT off this callback. The
## server pushes a room-wide progress state (view.startProgress -- see
## GameState.start_progress()) before the first Claude call and again as each
## batch lands, then a final push with phase CATEGORY. This callback only
## reports that the request finished, and it arrives last.
func start_game(code: String, player_id: String, callback: Callable) -> void:
	_post("/games/%s/start" % code, {"playerId": player_id}, callback, START_GAME_TIMEOUT)

# ---------------------------------------------------------------------------
# Round actions -- see server_py/main.py's round/* endpoints. All of these
# also trigger a WS "game:state" push to every connected player once the
# server-side mutation completes; the HTTP response here is just {"ok": true}
# (or the {"correct": bool} ack for attempt_lineup) -- scenes should drive
# their UI off ws_event("game:state", ...), not these callbacks, same as
# CYM's lobby.gd pattern.
# ---------------------------------------------------------------------------

func pick_category(code: String, player_id: String, category: String, callback: Callable) -> void:
	_post("/games/%s/round/pick-category" % code, {"playerId": player_id, "category": category}, callback)

func set_wager(code: String, player_id: String, amount: float, callback: Callable) -> void:
	_post("/games/%s/round/set-wager" % code, {"playerId": player_id, "amount": amount}, callback)

func play_card(code: String, player_id: String, card_id: String, payload, callback: Callable) -> void:
	var body := {"playerId": player_id, "cardId": card_id}
	if payload != null:
		body["payload"] = payload
	_post("/games/%s/round/play-card" % code, body, callback)

func submit_answer(code: String, player_id: String, answer: String, input_mode: String, callback: Callable) -> void:
	_post("/games/%s/round/submit-answer" % code, {
		"playerId": player_id, "answer": answer, "inputMode": input_mode,
	}, callback)

func claim_steal(code: String, player_id: String, answer: String, input_mode: String, callback: Callable) -> void:
	_post("/games/%s/round/claim-steal" % code, {
		"playerId": player_id, "answer": answer, "inputMode": input_mode,
	}, callback)

## Wrong picks are NOT an error from the server (200 with {"correct": false})
## -- see game_state.attempt_lineup_pick's docstring for why. callback's
## `data` param will be {"correct": true|false}; no `error` string for a
## wrong-but-valid pick.
func attempt_lineup(code: String, player_id: String, option_id: String, callback: Callable) -> void:
	_post("/games/%s/round/attempt-lineup" % code, {"playerId": player_id, "optionId": option_id}, callback)

# ---------------------------------------------------------------------------
# Internal HTTP helper
# ---------------------------------------------------------------------------

func _post(path: String, body: Dictionary, callback: Callable, timeout: float = REQUEST_TIMEOUT) -> void:
	var http := HTTPRequest.new()
	add_child(http)
	http.timeout = timeout
	http.request_completed.connect(func(_result: int, response_code: int, _headers: PackedStringArray, response_body: PackedByteArray) -> void:
		var text := response_body.get_string_from_utf8()
		var json := JSON.new()
		var parse_ok := json.parse(text) == OK
		var data: Dictionary = json.data if parse_ok and json.data is Dictionary else {}
		if response_code >= 200 and response_code < 300:
			callback.call("", data)
		else:
			var message: String = data.get("detail", "Request failed (%d)" % response_code)
			callback.call(message, data)
		http.queue_free()
	)
	var headers := ["Content-Type: application/json"]
	var err := http.request(server_url + path, headers, HTTPClient.METHOD_POST, JSON.stringify(body))
	if err != OK:
		callback.call("Failed to start request: %s" % err, {})
		http.queue_free()
