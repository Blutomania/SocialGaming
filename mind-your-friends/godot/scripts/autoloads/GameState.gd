## GameState -- Global singleton. Client-side mirror of the authoritative
## server state (server_py/game_state.py's player_view()).
##
## This holds NO game logic. The server is authoritative for every rule:
## whose turn it is, what a wager costs, whether an answer was right. This
## node's only jobs are (1) keep the most recent player_view() dict, (2)
## expose it through typed accessors so scenes don't hand-parse raw
## dictionaries, and (3) turn the single firehose "game:state" push into
## granular signals scenes can subscribe to selectively.
##
## Why mirror rather than model: server_py broadcasts a COMPLETE per-player
## view after every mutation (see ConnectionManager.broadcast_state) -- there
## are no partial deltas to reconcile. So the correct client design is
## last-write-wins replacement, not incremental patching. Any client-side
## "prediction" would just be a second source of truth to drift out of sync.
##
## Lifecycle:
##   GameState.begin_session(code, player_id)  -- after create/join succeeds
##   ... scenes react to state_updated / phase_changed ...
##   GameState.end_session()                    -- on leaving the game
##
## Verified to compile against Godot 4.6.stable headless.

extends Node

# --- Signals -----------------------------------------------------------------

## Fired on every server push, after `view` has been replaced.
signal state_updated(view: Dictionary)

## Fired only when the phase actually changes. `previous` is "" on first push.
signal phase_changed(phase: String, previous: String)

## Fired when the player roster changes in a way scenes care about
## (join/leave/registration/score). Not fired for unrelated pushes.
signal players_changed(players: Array)

## Fired once when the server reports GAME_OVER.
signal game_over(winners: Array)

# --- Phase constants ---------------------------------------------------------
# Mirrors the phase strings set in server_py/game_state.py. Using constants
# rather than bare strings so a typo is a compile-time-ish error in one place.

const PHASE_LOBBY: String = "LOBBY"
const PHASE_CATEGORY: String = "CATEGORY"
const PHASE_WAGER: String = "WAGER"
const PHASE_CARD: String = "CARD"
const PHASE_QUESTION: String = "QUESTION"
const PHASE_ANSWER: String = "ANSWER"
const PHASE_EVALUATING: String = "EVALUATING"
const PHASE_STEAL: String = "STEAL"
const PHASE_RESULT: String = "RESULT"
const PHASE_GAME_OVER: String = "GAME_OVER"

# --- Rule mirrors ------------------------------------------------------------
# Kept in sync with server_py/constants.py. These are for UI affordances only
# (enabling a Start button, clamping a wager slider) -- the server re-validates
# everything, so a stale copy here can never corrupt a game, only mis-draw a
# button.

const MIN_PLAYERS: int = 3
const MAX_PLAYERS: int = 6
const MIN_WAGER: int = 50
const MAX_WAGER: int = 500
const CATEGORIES_PER_PLAYER: int = 5
const TOTAL_QUESTIONS: int = 24

# --- Session identity --------------------------------------------------------

var code: String = ""
var player_id: String = ""
var player_name: String = ""

## The most recent player_view() dict from the server. Empty before the first
## push. Scenes may read this directly, but prefer the accessors below.
var view: Dictionary = {}

var phase: String = ""

var _in_session: bool = false


func _ready() -> void:
	ApiClient.ws_event.connect(_on_ws_event)


# --- Session management ------------------------------------------------------

## Call after POST /games/create or /join returns successfully. Opens the
## WebSocket; the server's first push (see ws_endpoint) delivers the initial
## state, so there's no separate "fetch state" call to make.
func begin_session(game_code: String, id: String, display_name: String) -> void:
	code = game_code
	player_id = id
	player_name = display_name
	_in_session = true
	ApiClient.connect_ws(game_code, id)


func end_session() -> void:
	ApiClient.disconnect_ws()
	_in_session = false
	code = ""
	view = {}
	phase = ""


func is_in_session() -> bool:
	return _in_session


## Stable per-device player id, persisted so a reconnect after an app restart
## is recognized by the server's reconnect_player() path rather than being
## treated as a brand-new player.
func ensure_player_id() -> String:
	if player_id != "":
		return player_id
	var cfg := ConfigFile.new()
	if cfg.load("user://player.cfg") == OK:
		var stored: String = str(cfg.get_value("player", "id", ""))
		if stored != "":
			player_id = stored
			return player_id
	player_id = "p_%d_%d" % [Time.get_unix_time_from_system(), randi() % 100000]
	cfg.set_value("player", "id", player_id)
	cfg.save("user://player.cfg")
	return player_id


# --- Incoming state ----------------------------------------------------------

func _on_ws_event(event_name: String, data: Dictionary) -> void:
	if event_name == "game:state":
		_apply_view(data)


func _apply_view(next_view: Dictionary) -> void:
	var previous_phase: String = phase
	var previous_roster: Array = _roster_fingerprint()

	view = next_view
	phase = str(next_view.get("phase", ""))

	state_updated.emit(view)

	if phase != previous_phase:
		phase_changed.emit(phase, previous_phase)

	if _roster_fingerprint() != previous_roster:
		players_changed.emit(players())

	if phase == PHASE_GAME_OVER and previous_phase != PHASE_GAME_OVER:
		game_over.emit(winners())


## Cheap comparable summary of the roster, so players_changed only fires on a
## change scenes would actually redraw for.
func _roster_fingerprint() -> Array:
	var out: Array = []
	for p in players():
		var entry: Dictionary = p
		out.append("%s|%s|%s|%s|%s" % [
			str(entry.get("id", "")),
			str(entry.get("name", "")),
			str(entry.get("score", 0)),
			str(entry.get("registered", false)),
			str(entry.get("connected", true)),
		])
	return out


# --- Accessors ---------------------------------------------------------------
# All of these are safe to call before the first push -- they return empty
# values rather than erroring, so a scene's _ready() can draw an empty state.

func players() -> Array:
	var raw: Variant = view.get("players", [])
	return raw if raw is Array else []


func player_count() -> int:
	return players().size()


func my_player() -> Dictionary:
	for p in players():
		var entry: Dictionary = p
		if str(entry.get("id", "")) == player_id:
			return entry
	return {}


func my_score() -> int:
	return int(my_player().get("score", 0))


## My hand of cards. Other players' hands are withheld by player_view(), so
## this is only ever populated for the local player.
func my_hand() -> Array:
	var raw: Variant = my_player().get("hand", [])
	return raw if raw is Array else []


func am_registered() -> bool:
	return bool(my_player().get("registered", false))


func all_registered() -> bool:
	var list: Array = players()
	if list.is_empty():
		return false
	for p in list:
		var entry: Dictionary = p
		if not bool(entry.get("registered", false)):
			return false
	return true


## Whether the Start Game button should be live. The server re-checks this in
## start_game(); this is purely so the button isn't clickable too early.
func can_start_game() -> bool:
	return phase == PHASE_LOBBY and player_count() >= MIN_PLAYERS and all_registered()


func is_room_full() -> bool:
	return player_count() >= MAX_PLAYERS


func is_active_player() -> bool:
	return bool(view.get("isActivePlayer", false))


func is_wager_player() -> bool:
	return bool(view.get("isWagerPlayer", false))


func current_category() -> String:
	return str(view.get("currentCategory", ""))


func current_wager() -> int:
	return int(view.get("currentWager", 0))


func category_options() -> Array:
	var raw: Variant = view.get("categoryOptions", [])
	return raw if raw is Array else []


## The active round rule: {id, name, emoji, description, submissionBased,
## lineupBased}. Empty dict before a round starts.
func round_rule() -> Dictionary:
	var raw: Variant = view.get("roundRule", {})
	return raw if raw is Dictionary else {}


func round_rule_id() -> String:
	return str(round_rule().get("id", ""))


## True when this round collects one answer from EVERY player (Worst Answer
## Wins) rather than a single answerer.
func is_submission_based() -> bool:
	return bool(round_rule().get("submissionBased", false))


## True when this round is multiple-choice tap-to-win (The Lineup).
func is_lineup_based() -> bool:
	return bool(round_rule().get("lineupBased", false))


func question_text() -> String:
	return str(view.get("question", ""))


func host_quip() -> String:
	return str(view.get("hostQuip", ""))


## The correct answer. Withheld by the server until RESULT/GAME_OVER, so this
## returns "" for the whole answering phase by design -- not a bug.
func answer_text() -> String:
	return str(view.get("answer", ""))


## Lineup payload: {flavor, options, correctOptionId?}. correctOptionId is
## absent until RESULT, same withholding rule as answer_text().
func lineup() -> Dictionary:
	var raw: Variant = view.get("lineup", {})
	return raw if raw is Dictionary else {}


func lineup_options() -> Array:
	var raw: Variant = lineup().get("options", [])
	return raw if raw is Array else []


func last_result() -> Dictionary:
	var raw: Variant = view.get("lastResult", {})
	return raw if raw is Dictionary else {}


func winners() -> Array:
	var raw: Variant = view.get("winners", [])
	return raw if raw is Array else []


func question_index() -> int:
	return int(view.get("questionIndex", 0))


func highlight_reel() -> Array:
	var raw: Variant = view.get("highlightReel", [])
	return raw if raw is Array else []


## True while the server has paused the game (a player dropped and the room is
## voting whether to wait). Scenes should overlay rather than accept input.
func is_paused() -> bool:
	return bool(view.get("paused", false))


func disconnect_vote() -> Dictionary:
	var raw: Variant = view.get("disconnectVote", {})
	return raw if raw is Dictionary else {}


## STEAL phase: whether I'm allowed to buzz in (I'm not the player who just
## missed, and nobody has claimed it yet).
func can_claim_steal() -> bool:
	return phase == PHASE_STEAL and bool(view.get("stealEligible", false))


## Submission rounds: how many players have answered so far, as [done, total].
func submission_progress() -> Array:
	return [int(view.get("submittedCount", 0)), int(view.get("totalToSubmit", 0))]


func have_i_submitted() -> bool:
	return bool(view.get("mySubmitted", false))
