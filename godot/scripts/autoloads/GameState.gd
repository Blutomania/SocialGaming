## GameState — Global singleton.
## Tracks the current mystery, game phase, interrogation history,
## and player identity. Persists across scene changes.
##
## Access from any scene: GameState.current_mystery
##
## SESSION ANNOTATION — Phase 2:
## When multiplayer is added (Phase 3), add player_list and room_code here.
## Keep multiplayer state OUT of this file until Phase 3.

extends Node

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
enum Phase {
	MAIN_MENU,
	GENERATING,
	CASE_DISPLAY,
	INTERROGATION,
	ACCUSATION,
	RESULT,
}

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
var current_mystery: Dictionary = {}        ## Full mystery dict from server
var interrogation_history: Array = []       ## [{character, question, response}, ...]
var player_name: String = "Detective"
var game_phase: Phase = Phase.MAIN_MENU
var accusation_result: Dictionary = {}      ## {correct: bool, culprit: str, verdict: str}

# Multiplayer (Phase 3 — stubs only)
var room_code: String = ""
var player_list: Array = []                 ## [{id, name, is_host}, ...]
var shared_clues: Array = []               ## Clues received from other players

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

## Returns all suspect and witness characters from the current mystery.
func get_interrogatable_characters() -> Array:
	var chars: Array = current_mystery.get("characters", [])
	return chars.filter(func(c): return c.get("role") in ["suspect", "witness"])

## Returns just suspect names (used by accusation dropdown).
func get_suspect_names() -> Array:
	var chars: Array = current_mystery.get("characters", [])
	return chars.filter(func(c): return c.get("role") == "suspect") \
			.map(func(c): return c.get("name", ""))

## Appends one interrogation exchange to history.
func record_interrogation(character_name: String, question: String, response: String) -> void:
	interrogation_history.append({
		"character": character_name,
		"question": question,
		"response": response,
	})

## Resets all game state (call before starting a new mystery).
func reset() -> void:
	current_mystery = {}
	interrogation_history = []
	accusation_result = {}
	game_phase = Phase.MAIN_MENU
	# Note: player_name is intentionally NOT reset between games
