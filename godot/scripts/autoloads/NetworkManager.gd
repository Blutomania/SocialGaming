## NetworkManager — Global singleton.
## Handles all ENet multiplayer networking for the dedicated server model.
##
## SESSION ANNOTATION — Phase 3:
## This file is a STUB for Phase 2. It exposes the same API that Phase 3
## will implement, so scenes can call NetworkManager.host_game() etc.
## without needing changes when Phase 3 wires it up.
##
## Phase 3 implementation tasks (do not implement in Phase 2):
##   - host_game(): start ENet server, generate room_code, return via signal
##   - join_game(): connect to server, send room_code for validation
##   - share_clue(): send clue to server; server applies 75% fanout
##   - Signals: player_joined, player_left, clue_received, game_started, accusation_made
##
## For now every "network" action just fires the signal immediately (single-player sim).

extends Node

signal player_joined(player_id: int, player_name: String)
signal player_left(player_id: int)
signal clue_received(clue_data: Dictionary)
signal game_started(mystery: Dictionary)
signal accusation_made(player_id: int, suspect_name: String)
signal room_created(room_code: String)
signal join_failed(reason: String)

## True when connected to a multiplayer session (Phase 3+).
var is_multiplayer: bool = false

## --- Phase 2 stubs (single-player passthrough) ---

func host_game(_port: int = 7777) -> void:
	## Phase 3: Start ENet server, generate room code.
	## Phase 2 stub: emit immediately with a fake code.
	push_warning("NetworkManager.host_game() is a stub — Phase 3 not yet implemented.")
	emit_signal("room_created", "DEMO01")

func join_game(_server_ip: String, _room_code: String) -> void:
	## Phase 3: Connect to server, validate room code.
	push_warning("NetworkManager.join_game() is a stub — Phase 3 not yet implemented.")
	emit_signal("join_failed", "Multiplayer not yet implemented (Phase 3).")

## share_clue() — Phase 3 will route this through the server.
## Server applies 75% fanout: randomly picks 75% of players to receive the clue.
## Phase 2 stub: no-op (single player, no one to share with).
func share_clue(_clue_data: Dictionary) -> void:
	push_warning("NetworkManager.share_clue() is a stub — Phase 3 not yet implemented.")

func disconnect_from_game() -> void:
	is_multiplayer = false
