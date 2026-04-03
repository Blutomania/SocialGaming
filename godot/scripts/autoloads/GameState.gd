## GameState — Global singleton.
## Tracks the current mystery, game phase, interrogation history,
## and player identity. Persists across scene changes.
##
## Access from any scene: GameState.current_mystery

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

## Investigation sub-phases (used within INTERROGATION phase for Phase 3)
enum InvestPhase {
	WITNESS,
	SHARE_WITNESS,       ## Share Selection screen after witness budget exhausted
	INVESTIGATION,
	SHARE_INVESTIGATION,
	LEAD,
	SHARE_LEAD,
	DONE,
}

# ---------------------------------------------------------------------------
# Core state (single-player + multiplayer)
# ---------------------------------------------------------------------------
var current_mystery: Dictionary = {}        ## Full mystery dict from server
var interrogation_history: Array = []       ## [{character, question, response}, ...]
var player_name: String = "Detective"
var game_phase: Phase = Phase.MAIN_MENU
var accusation_result: Dictionary = {}      ## {correct: bool, culprit: str, verdict: str}

# ---------------------------------------------------------------------------
# Phase 3 — multiplayer + structured investigation
# ---------------------------------------------------------------------------
var game_id: String = ""
var player_id: String = ""
var player_list: Array = []                 ## [{id, name, is_host}, ...]

## Current investigation sub-phase
var invest_phase: InvestPhase = InvestPhase.WITNESS

## Budgets (populated on game create/join)
var witness_budget: int = 0
var investigation_budget: int = 0
var leads_remaining: int = 2
var share_min: float = 0.6                  ## Minimum fraction player must share

## Findings accumulated this phase (cleared after sharing)
var witness_findings: Array = []            ## [{id, character, question, response}, ...]
var investigation_findings: Array = []      ## [{id, area_id, area_name, findings}, ...]
var lead_findings: Array = []              ## [{id, lead_id, lead_title, findings}, ...]

## Clues received from other players (all phases, appended as shares arrive)
var shared_clues: Dictionary = {
	"witness": [],
	"investigation": [],
	"lead": [],
}

## Block pool — cached from server, used to grey out UI options
var block_pool: Dictionary = {
	"witness": [],         ## [{character, fingerprint}, ...]
	"investigation": [],   ## [area_id, ...]
	"lead": [],            ## [lead_id, ...]
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

func get_interrogatable_characters() -> Array:
	var chars: Array = current_mystery.get("characters", [])
	return chars.filter(func(c): return c.get("role") in ["suspect", "witness"])

func get_suspect_names() -> Array:
	var chars: Array = current_mystery.get("characters", [])
	return chars.filter(func(c): return c.get("role") == "suspect") \
			.map(func(c): return c.get("name", ""))

## Single-player interrogation history (Phase 2 compatibility).
func record_interrogation(character_name: String, question: String, response: String) -> void:
	interrogation_history.append({
		"character": character_name,
		"question": question,
		"response": response,
	})

## Phase 3: record a witness finding returned by /games/{id}/interrogate-witness.
func record_witness_finding(finding: Dictionary) -> void:
	witness_findings.append(finding)
	witness_budget = finding.get("budget_remaining", witness_budget)

## Phase 3: record an investigation finding.
func record_investigation_finding(finding: Dictionary) -> void:
	investigation_findings.append(finding)
	investigation_budget = finding.get("budget_remaining", investigation_budget)

## Phase 3: record a lead finding.
func record_lead_finding(finding: Dictionary) -> void:
	lead_findings.append(finding)
	leads_remaining = finding.get("leads_remaining", leads_remaining)

## Phase 3: cache the server's block pool response.
func update_block_pool(pool: Dictionary) -> void:
	block_pool = pool

## Phase 3: append incoming shared clues from server poll.
func merge_shared_clues(pool: Dictionary) -> void:
	for phase_key in ["witness", "investigation", "lead"]:
		var incoming: Array = pool.get(phase_key, [])
		var existing_ids: Array = shared_clues[phase_key].map(func(c): return c.get("id", ""))
		for clue in incoming:
			if clue.get("id", "") not in existing_ids:
				shared_clues[phase_key].append(clue)

## Returns true if the given (character, question) is in the witness block pool.
func is_witness_blocked(character: String, question: String) -> bool:
	var fp := question.strip_edges().to_lower()
	for b in block_pool.get("witness", []):
		if b.get("character") == character and b.get("fingerprint") == fp:
			return true
	return false

func is_area_blocked(area_id: String) -> bool:
	return area_id in block_pool.get("investigation", [])

func is_lead_blocked(lead_id: String) -> bool:
	return lead_id in block_pool.get("lead", [])

## Returns the findings array for the current invest_phase.
func current_phase_findings() -> Array:
	match invest_phase:
		InvestPhase.SHARE_WITNESS:
			return witness_findings
		InvestPhase.SHARE_INVESTIGATION:
			return investigation_findings
		InvestPhase.SHARE_LEAD:
			return lead_findings
	return []

## Resets all game state (call before starting a new mystery).
func reset() -> void:
	current_mystery = {}
	interrogation_history = []
	accusation_result = {}
	game_phase = Phase.MAIN_MENU
	game_id = ""
	player_id = ""
	player_list = []
	invest_phase = InvestPhase.WITNESS
	witness_budget = 0
	investigation_budget = 0
	leads_remaining = 2
	witness_findings = []
	investigation_findings = []
	lead_findings = []
	shared_clues = {"witness": [], "investigation": [], "lead": []}
	block_pool = {"witness": [], "investigation": [], "lead": []}
	# Note: player_name is intentionally NOT reset between games
