# In-memory game state machine — ported from lib/gameState.js.
#
# Phases: LOBBY -> CATEGORY -> WAGER -> CARD -> QUESTION -> ANSWER -> RESULT -> (loop) -> GAME_OVER
#
# main.py is the only caller of these functions; it owns the process-wide
# `games` dict (code -> game dict) and broadcasts over WebSocket after each
# mutation. Unlike the JS version, every state-mutating call here must be
# made while holding that game's lock (see main.py) — Python/FastAPI doesn't
# give the single-threaded-event-loop correctness guarantee Node did for
# the FCFS mechanics (card play, Steal, The Lineup). See docs/WIRING.md.

import random
import string
import time

import claude_client
from cards import build_round_hand
from coherence import pick_factoid, round_constraints, turn_constraints, validate_question
from constants import (
    AUTO_ADVANCE_AWAY_THRESHOLD,
    CATEGORIES_PER_PLAYER,
    CATEGORY_OPTIONS_COUNT,
    LINEUP_COLOR_FLAVOR_CHANCE,
    MAX_PLAYERS,
    MAX_WAGER,
    MIN_PLAYERS,
    MIN_WAGER,
    QUESTIONS_PER_ROUND,
    TOTAL_QUESTIONS,
)
from lineup_data import build_color_options, pick_color_lineup_entry
from round_rules import ROUND_RULES, pick_random_round_rule, transform_answer

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # no I/O — avoid confusion with 1/0


class GameError(Exception):
    """Raised for expected game-rule violations (wrong phase, not your turn,
    etc.) — the caller (main.py) turns these into 4xx responses, not 500s."""


def _generate_game_code() -> str:
    return "".join(random.choice(_CODE_ALPHABET) for _ in range(4))


def make_player(player_id: str, name: str) -> dict:
    return {
        "id": player_id,
        "name": name,
        "score": 0,
        "categories": [],
        "pickedCardId": None,
        "pickedCardUsed": False,
        "hand": [],
        "registered": False,
        "connected": True,
        "droppedOut": False,
        "away": False,
        "autoAdvanceCount": 0,
    }


def create_game(host_id: str, host_name: str) -> dict:
    return {
        "code": _generate_game_code(),
        "phase": "LOBBY",
        "players": [make_player(host_id, host_name)],
        "questionIndex": 0,
        "activePlayerIndex": 0,
        "currentCategory": None,
        "currentWager": None,
        "roundRule": None,
        "cardSlot": None,
        "currentQuestion": None,
        "answererIndex": None,
        "highlightReel": [],
    }


def add_player(game: dict, player_id: str, name: str) -> dict:
    if game["phase"] != "LOBBY":
        raise GameError("Cannot join — game already started")
    if len(game["players"]) >= MAX_PLAYERS:
        raise GameError(f"Room is full (max {MAX_PLAYERS} players). Start a second game!")
    game["players"].append(make_player(player_id, name))
    return game


def register_player(game: dict, player_id: str, categories: list[str], picked_card_id: str) -> dict:
    player = get_player(game, player_id)
    if len(categories) != CATEGORIES_PER_PLAYER:
        raise GameError(f"Must submit exactly {CATEGORIES_PER_PLAYER} categories")
    player["categories"] = categories
    player["pickedCardId"] = picked_card_id
    player["pickedCardUsed"] = False
    player["registered"] = True
    return game


def _deal_round_hands(game: dict) -> None:
    for player in game["players"]:
        player["hand"] = build_round_hand(player["pickedCardId"], player["pickedCardUsed"])


def all_players_registered(game: dict) -> bool:
    return len(game["players"]) >= MIN_PLAYERS and all(p["registered"] for p in game["players"])


def build_fact_bank(game: dict) -> dict:
    all_categories = list({c for p in game["players"] for c in p["categories"]})
    game["factBank"] = claude_client.fetch_facts_batch(all_categories)
    return game


def start_game(game: dict) -> dict:
    if not all_players_registered(game):
        raise GameError("All players must register before the game can start")
    build_fact_bank(game)
    game["phase"] = "CATEGORY"
    game["activePlayerIndex"] = 0
    game["questionIndex"] = 0
    _deal_round_hands(game)
    _begin_turn(game)
    return game


def _get_category_options(game: dict) -> list[dict]:
    pool = [
        {"category": cat, "submittedBy": p["name"], "submittedById": p["id"]}
        for p in game["players"]
        for cat in p["categories"]
    ]
    options = []
    remaining = list(pool)
    count = min(CATEGORY_OPTIONS_COUNT, len(remaining))
    for _ in range(count):
        idx = random.randrange(len(remaining))
        options.append(remaining.pop(idx))
    return options


def _begin_turn(game: dict) -> None:
    game["roundRule"] = pick_random_round_rule()
    game["roundConstraints"] = round_constraints(game["roundRule"])
    game["currentCategory"] = None
    game["currentCategoryAttribution"] = None
    game["currentWager"] = None
    game["cardSlot"] = None
    game["currentQuestion"] = None
    game["answererIndex"] = game["activePlayerIndex"]
    game["categoryOptions"] = _get_category_options(game)
    game["submissions"] = None


def get_player(game: dict, player_id: str) -> dict:
    for p in game["players"]:
        if p["id"] == player_id:
            return p
    raise GameError("Player not found")


def get_active_player(game: dict) -> dict:
    return game["players"][game["activePlayerIndex"]]


def get_wager_player(game: dict) -> dict:
    """The wager-decider is always the next player after the active player."""
    idx = (game["activePlayerIndex"] + 1) % len(game["players"])
    return game["players"][idx]


def _assert_phase(game: dict, expected: str) -> None:
    if game["phase"] != expected:
        raise GameError(f"Expected phase {expected}, got {game['phase']}")


def pick_category(game: dict, player_id: str, category: str) -> dict:
    _assert_phase(game, "CATEGORY")
    if player_id != get_active_player(game)["id"]:
        raise GameError("Only the active player picks the category")
    match = next((o for o in game["categoryOptions"] if o["category"] == category), None)
    if not match:
        raise GameError("Category must be one of the offered options")
    game["currentCategory"] = match["category"]
    game["currentCategoryAttribution"] = {
        "submittedBy": match["submittedBy"], "submittedById": match["submittedById"]
    }
    game["phase"] = "WAGER"
    return game


def set_wager(game: dict, player_id: str, amount) -> dict:
    _assert_phase(game, "WAGER")
    if player_id != get_wager_player(game)["id"]:
        raise GameError("Only the wager-decider sets the wager")
    wager = max(MIN_WAGER, min(MAX_WAGER, round(amount)))
    if game["roundRule"].get("wagerMultiplier"):
        wager *= game["roundRule"]["wagerMultiplier"]
    game["currentWager"] = wager
    game["phase"] = "CARD"
    return game


def play_card(game: dict, player_id: str, card_id: str, payload=None) -> dict:
    """First-come-first-served: the first card played claims the single slot
    for this question. Cards are single-use — removed from the player's hand
    the moment they claim the slot."""
    _assert_phase(game, "CARD")
    if game["cardSlot"]:
        raise GameError("Card slot already claimed — too slow!")
    player = get_player(game, player_id)
    if card_id not in player["hand"]:
        raise GameError("Card not in hand")
    if card_id != "halfOff":
        player["hand"] = [c for c in player["hand"] if c != card_id]
    if card_id == player["pickedCardId"]:
        player["pickedCardUsed"] = True
    game["cardSlot"] = {"playerId": player_id, "cardId": card_id, "payload": payload}
    return game


def _log_highlight(game: dict, message: str) -> None:
    game["highlightReel"].append(message)


def resolve_card_slot(game: dict) -> dict:
    """Closes the card window and resolves state-side effects. Prompt
    modifiers (Language Barrier, Boxed In) are handled by the CE in
    run_question_phase() — this only handles state mutations + highlights."""
    _assert_phase(game, "CARD")
    slot = game["cardSlot"]
    game["heckleMessage"] = None

    if not slot:
        game["phase"] = "QUESTION"
        return game

    from cards import CARDS  # local import avoids a cycle at module load time

    player_name = get_player(game, slot["playerId"])["name"]
    active_name = get_active_player(game)["name"]
    card_id = slot["cardId"]

    if card_id == "skip":
        _log_highlight(game, f"{player_name} played Skip — {active_name}'s turn is skipped!")
        game["phase"] = "RESULT"
        game["skippedTurn"] = True
        return game

    if card_id == "redirect":
        others = [i for i in range(len(game["players"])) if i != game["activePlayerIndex"]]
        game["answererIndex"] = random.choice(others)
        _log_highlight(
            game,
            f"{player_name} played Redirect — {game['players'][game['answererIndex']]['name']} "
            "must answer instead!",
        )
    elif card_id == "whoaNellie":
        pool = [
            {"category": cat, "submittedBy": p["name"], "submittedById": p["id"]}
            for p in game["players"]
            for cat in p["categories"]
        ]
        alternatives = [o for o in pool if o["category"] != game["currentCategory"]]
        if alternatives:
            pick = random.choice(alternatives)
            old_category = game["currentCategory"]
            game["currentCategory"] = pick["category"]
            game["currentCategoryAttribution"] = {
                "submittedBy": pick["submittedBy"], "submittedById": pick["submittedById"]
            }
            _log_highlight(
                game,
                f'{player_name} played Whoa Nellie! Category swapped from "{old_category}" '
                f"to {pick['submittedBy']}'s \"{pick['category']}\"!",
            )
        else:
            _log_highlight(game, f"{player_name} played Whoa Nellie but there's nowhere to go — same category!")
    elif card_id in ("halfOff", "fiftyOff"):
        game["currentWager"] = round(game["currentWager"] / 2)
        label = "Half-Off" if card_id == "halfOff" else "50% Off"
        _log_highlight(game, f"{player_name} played {label} — the wager is now {game['currentWager']}!")
    elif card_id == "spotlight":
        _log_highlight(game, f"{player_name} played Spotlight — {active_name} must answer immediately!")
    elif card_id == "heckle":
        raw_heckle = (slot.get("payload") or {}).get("text", "...")
        result = claude_client.moderate_heckle(
            heckle_text=raw_heckle, active_player_name=active_name, heckler_name=player_name
        )
        game["heckleMessage"] = result["heckle"]
        _log_highlight(game, f'{player_name} heckled: "{game["heckleMessage"]}"')
    elif card_id == "languageBarrier":
        _log_highlight(game, f"{player_name} played Language Barrier!")
    elif card_id == "boxedIn":
        _log_highlight(game, f"{player_name} played Boxed In — the answer must be one or two words!")
    elif card_id == "insurance":
        _log_highlight(game, f"{player_name} played Insurance — this question proceeds normally.")
    elif card_id == "fixer":
        get_player(game, slot["playerId"])["score"] += 50
        _log_highlight(game, f"{player_name} played The Fixer — +50 pts, and this question proceeds normally.")
    else:
        raise GameError(f"Unknown card: {card_id}")

    game["phase"] = "QUESTION"
    return game


_ANTI_SABOTAGE = {"insurance", "fixer"}
_STATE_ONLY_CARDS = {"skip", "redirect", "fiftyOff", "halfOff", "heckle", "whoaNellie"}


def _get_effective_card(game: dict):
    card_id = (game.get("cardSlot") or {}).get("cardId")
    if not card_id or card_id in _ANTI_SABOTAGE or card_id in _STATE_ONLY_CARDS:
        return None
    return card_id


def _build_lineup_question(game: dict, constraints: dict) -> dict:
    """Two flavors, chosen randomly per question — see docs/WIRING.md for
    why color flavor is deliberately category-agnostic."""
    if random.random() < LINEUP_COLOR_FLAVOR_CHANCE:
        entry = pick_color_lineup_entry()
        options, correct_option_id = build_color_options(entry)
        return {
            "question": f"Which one is {entry['entity']} {entry['label']}?",
            "answer": f"{entry['entity']} ({entry['label']})",
            "hostQuip": f"Spot the real {entry['label']}, {get_active_player(game)['name']} — don't blink!",
            "lineup": {"flavor": "color", "options": options, "correctOptionId": correct_option_id},
        }

    factoid = pick_factoid(game["factBank"], game["currentCategory"], constraints) if game.get("factBank") else None
    result = claude_client.generate_lineup_options(
        factoid=factoid,
        active_player_name=get_active_player(game)["name"],
        player_names=[p["name"] for p in game["players"]],
    )

    options = [{"id": f"opt{i}", "label": label} for i, label in enumerate(result["options"])]
    correct_option_id = options[result["correctIndex"]]["id"] if 0 <= result["correctIndex"] < len(options) else options[0]["id"]

    return {
        "question": result["question"],
        "answer": result["options"][result["correctIndex"]] if 0 <= result["correctIndex"] < len(result["options"]) else result["options"][0],
        "hostQuip": result["hostQuip"],
        "lineup": {"flavor": "text", "options": options, "correctOptionId": correct_option_id},
    }


def run_question_phase(game: dict) -> dict:
    """Assembles constraints via the CE, calls Claude, validates the result."""
    _assert_phase(game, "QUESTION")

    constraints = turn_constraints(
        game["roundConstraints"],
        category=game["currentCategory"],
        wager=game["currentWager"],
        resolved_card=_get_effective_card(game),
    )

    if game["roundRule"].get("lineupBased"):
        result = _build_lineup_question(game, constraints)
    else:
        factoid = (
            pick_factoid(game["factBank"], game["currentCategory"], constraints)
            if game.get("factBank") else None
        )
        result = claude_client.generate_question(
            constraints=constraints,
            factoid=factoid,
            active_player_name=get_active_player(game)["name"],
            player_names=[p["name"] for p in game["players"]],
        )

    validation = validate_question(result, constraints)
    if not validation["passed"]:
        print("CE validation failed:", validation["issues"])

    game["currentQuestion"] = result
    game["turnConstraints"] = constraints
    game["phase"] = "ANSWER"
    if game["roundRule"].get("submissionBased"):
        game["submissions"] = {}
    return game


# --- Worst Answer Wins (submission-based rounds) ---

def _submission_eligible_players(game: dict) -> list[dict]:
    return [p for p in game["players"] if not p["droppedOut"]]


def all_submitted(game: dict) -> bool:
    eligible = _submission_eligible_players(game)
    return all(p["id"] in game["submissions"] for p in eligible)


def submit_group_answer(game: dict, player_id: str, raw_answer: str, input_mode: str) -> bool:
    _assert_phase(game, "ANSWER")
    if not game["roundRule"].get("submissionBased"):
        raise GameError("submit_group_answer called on a non-submission-based round")
    player = get_player(game, player_id)
    if player["droppedOut"]:
        raise GameError("Dropped-out players cannot submit")
    if player_id in game["submissions"]:
        raise GameError("Already submitted")
    game["submissions"][player_id] = {"rawAnswer": raw_answer, "inputMode": input_mode}
    return all_submitted(game)


def auto_fill_missing_submissions(game: dict) -> dict:
    for player in _submission_eligible_players(game):
        if player["id"] not in game["submissions"]:
            record_auto_advance(game, player["id"])
            game["submissions"][player["id"]] = {"rawAnswer": "", "inputMode": "text"}
    return game


def begin_group_evaluation(game: dict) -> dict:
    """Synchronous phase flip so a submission arriving at the same instant
    the timer fires can't trigger evaluation twice."""
    _assert_phase(game, "ANSWER")
    game["phase"] = "EVALUATING"
    return game


def resolve_group_answers(game: dict) -> dict:
    _assert_phase(game, "EVALUATING")

    eligible = _submission_eligible_players(game)
    transformed_answers = [
        transform_answer(
            game["roundRule"], game["submissions"][p["id"]]["rawAnswer"], game["submissions"][p["id"]]["inputMode"]
        )
        for p in eligible
    ]

    scores = claude_client.evaluate_worst_answers(
        question=game["currentQuestion"]["question"],
        correct_answer=game["currentQuestion"]["answer"],
        submissions=[{"name": p["name"], "answer": a} for p, a in zip(eligible, transformed_answers)],
    )

    entries = []
    for p, s in zip(eligible, scores):
        total = s["factuallyWrong"] + s["creativelyWrong"] + s["plausibility"]
        entries.append({
            "playerId": p["id"],
            "name": p["name"],
            "answer": game["submissions"][p["id"]]["rawAnswer"],
            "factuallyWrong": s["factuallyWrong"],
            "creativelyWrong": s["creativelyWrong"],
            "plausibility": s["plausibility"],
            "total": total,
            "feedback": s["feedback"],
        })

    lowest_total = min(e["total"] for e in entries)
    wager = game["currentWager"]
    for entry in entries:
        entry["isWinner"] = entry["total"] == lowest_total
        if entry["isWinner"]:
            get_player(game, entry["playerId"])["score"] += wager

    winner_names = " & ".join(e["name"] for e in entries if e["isWinner"])
    _log_highlight(
        game, f"Worst Answer Wins: {winner_names} nailed being wrong (total {lowest_total}) and won {wager} pts!"
    )

    game["lastResult"] = {"submissionBased": True, "wager": wager, "entries": entries}
    game["phase"] = "RESULT"
    return game


def get_timer_seconds(game: dict) -> int:
    return (game.get("turnConstraints") or {}).get("timerSeconds", game["roundRule"]["timerSeconds"])


def submit_answer(game: dict, player_id: str, raw_answer: str, input_mode: str) -> dict:
    """Evaluates the answerer's submission via Claude and applies scoring.
    If the Steal round rule is active and the answer is wrong, transitions
    to the STEAL phase instead of RESULT."""
    _assert_phase(game, "ANSWER")
    answerer = game["players"][game["answererIndex"]]
    if player_id != answerer["id"]:
        raise GameError("Only the answerer may submit an answer")

    transformed = transform_answer(game["roundRule"], raw_answer, input_mode)
    result = claude_client.evaluate_answer(
        question=game["currentQuestion"]["question"],
        correct_answer=game["currentQuestion"]["answer"],
        player_answer=transformed,
        round_rule=game["roundRule"],
    )

    wager = game["currentWager"]
    game["lastResult"] = {**result, "wager": wager, "playerAnswer": raw_answer}

    if result["correct"]:
        answerer["score"] += wager
        game["phase"] = "RESULT"
    else:
        answerer["score"] -= wager
        _log_highlight(game, f'{answerer["name"]} wagered {wager} and answered "{raw_answer}" — wrong!')

        if game["roundRule"].get("stealOnWrong"):
            game["phase"] = "STEAL"
            game["stealSlot"] = None
            game["stealEligible"] = [p["id"] for p in game["players"] if p["id"] != answerer["id"]]
        else:
            game["phase"] = "RESULT"

    return game


def claim_steal(game: dict, player_id: str, raw_answer: str, input_mode: str) -> dict:
    """FCFS steal: first eligible player to buzz in claims the steal attempt."""
    _assert_phase(game, "STEAL")
    if game["stealSlot"]:
        raise GameError("Steal already claimed — too slow!")
    if player_id not in game["stealEligible"]:
        raise GameError("Not eligible to steal")

    game["stealSlot"] = player_id
    stealer = get_player(game, player_id)

    transformed = transform_answer(game["roundRule"], raw_answer, input_mode)
    result = claude_client.evaluate_answer(
        question=game["currentQuestion"]["question"],
        correct_answer=game["currentQuestion"]["answer"],
        player_answer=transformed,
        round_rule=game["roundRule"],
    )

    wager = game["currentWager"]
    if result["correct"]:
        stealer["score"] += wager
        _log_highlight(game, f"{stealer['name']} stole it for {wager} pts!")
    else:
        half = round(wager / 2)
        stealer["score"] -= half
        _log_highlight(game, f"{stealer['name']} tried to steal but got it wrong — loses {half} pts!")

    game["lastResult"] = {
        **result, "wager": wager, "playerAnswer": raw_answer, "stolen": True, "stealerName": stealer["name"]
    }
    game["phase"] = "RESULT"
    return game


def expire_steal(game: dict) -> dict:
    if game["phase"] != "STEAL":
        return game
    _log_highlight(game, "Nobody stole — moving on!")
    game["phase"] = "RESULT"
    return game


# --- The Lineup (pick-one round rule) ---
# See docs/WIRING.md and the JS version's identical comment for the full
# rationale — ported unchanged.

def attempt_lineup_pick(game: dict, player_id: str, option_id: str) -> dict:
    """FCFS pick: any eligible player may tap any option at any time during
    ANSWER. Wrong taps fail silently — no penalty, no lockout. Unlike other
    phase-gated actions in this file, this deliberately does NOT raise for a
    stale/late tap (phase already moved past ANSWER) — treated the same as
    a wrong guess, not an error, since this mechanic invites genuinely
    simultaneous taps by design."""
    if not game.get("roundRule", {}).get("lineupBased"):
        raise GameError("attempt_lineup_pick called on a non-Lineup round")
    if game["phase"] != "ANSWER":
        return {"correct": False}

    player = get_player(game, player_id)
    if player["droppedOut"]:
        return {"correct": False}

    lineup = game["currentQuestion"]["lineup"]
    picked = next((o for o in lineup["options"] if o["id"] == option_id), None)
    if not picked or option_id != lineup["correctOptionId"]:
        return {"correct": False}

    wager = game["currentWager"]
    player["score"] += wager
    _log_highlight(game, f"{player['name']} spotted it in The Lineup and won {wager} pts!")
    game["lastResult"] = {
        "correct": True, "lineupWinner": True, "winnerName": player["name"],
        "wager": wager, "correctOptionId": lineup["correctOptionId"],
    }
    game["phase"] = "RESULT"
    return {"correct": True}


def expire_lineup(game: dict) -> dict:
    if game["phase"] != "ANSWER":
        return game
    wager = game["currentWager"]
    _log_highlight(game, f"Nobody spotted it in The Lineup — {wager} pts unclaimed!")
    game["lastResult"] = {
        "correct": False, "lineupWinner": False, "wager": wager,
        "correctOptionId": game["currentQuestion"]["lineup"]["correctOptionId"],
    }
    game["phase"] = "RESULT"
    return game


def next_turn(game: dict) -> dict:
    _assert_phase(game, "RESULT")
    game["skippedTurn"] = False
    game["questionIndex"] += 1
    if game["questionIndex"] >= TOTAL_QUESTIONS:
        game["phase"] = "GAME_OVER"
        return game
    if game["questionIndex"] % QUESTIONS_PER_ROUND == 0:
        _deal_round_hands(game)
    game["activePlayerIndex"] = (game["activePlayerIndex"] + 1) % len(game["players"])
    _skip_unavailable_players(game)
    if game["phase"] == "GAME_OVER":
        return game
    game["phase"] = "CATEGORY"
    _begin_turn(game)
    return game


def get_winners(game: dict) -> list[dict]:
    top = max(p["score"] for p in game["players"])
    return [p for p in game["players"] if p["score"] == top]  # ties are shared wins


# --- Inactivity detection ---

def record_auto_advance(game: dict, player_id: str) -> dict:
    player = get_player(game, player_id)
    player["autoAdvanceCount"] += 1
    if player["autoAdvanceCount"] >= AUTO_ADVANCE_AWAY_THRESHOLD:
        player["away"] = True
        _log_highlight(game, f"{player['name']} seems to be away — skipping their turns until they're back.")
    return game


def record_player_action(game: dict, player_id: str) -> None:
    player = next((p for p in game["players"] if p["id"] == player_id), None)
    if not player:
        return
    if player["away"]:
        player["away"] = False
        _log_highlight(game, f"{player['name']} is back in action!")
    player["autoAdvanceCount"] = 0


def is_player_away(game: dict, player_index: int) -> bool:
    if player_index is None or player_index >= len(game["players"]):
        return False
    return game["players"][player_index].get("away") is True


# --- Disconnection / Reconnection ---

def disconnect_player(game: dict, player_id: str) -> dict:
    player = next((p for p in game["players"] if p["id"] == player_id), None)
    if not player:
        return game
    player["connected"] = False
    if game["phase"] == "LOBBY":
        return game
    game.setdefault("disconnectPending", {})[player_id] = {"since": time.time()}
    _log_highlight(game, f"{player['name']} disconnected — waiting for reconnect…")
    return game


def should_pause(game: dict) -> bool:
    if game["phase"] in ("LOBBY", "GAME_OVER"):
        return False
    active_player = get_active_player(game)
    answerer = game["players"][game["answererIndex"]] if game["answererIndex"] is not None else None
    wager_player = get_wager_player(game) if len(game["players"]) >= 2 else None
    needs_action = [p for p in (active_player, answerer, wager_player) if p]
    return any(not p["connected"] and not p["droppedOut"] for p in needs_action)


def reconnect_player(game: dict, old_player_id: str, new_socket_id: str):
    player = next((p for p in game["players"] if p["id"] == old_player_id), None)
    if not player:
        return None
    player["id"] = new_socket_id
    player["connected"] = True
    if game.get("disconnectPending"):
        game["disconnectPending"].pop(old_player_id, None)
    if game.get("disconnectVote"):
        game["disconnectVote"] = None
    _log_highlight(game, f"{player['name']} is back!")
    return game


def start_disconnect_vote(game: dict, disconnected_player_id: str) -> dict:
    player = next((p for p in game["players"] if p["id"] == disconnected_player_id), None)
    if not player:
        return game
    game["disconnectVote"] = {"targetPlayerId": disconnected_player_id, "targetName": player["name"], "votes": {}}
    return game


def cast_disconnect_vote(game: dict, player_id: str, vote: str) -> dict:
    if not game.get("disconnectVote"):
        return {"resolved": False}
    if player_id == game["disconnectVote"]["targetPlayerId"]:
        return {"resolved": False}
    game["disconnectVote"]["votes"][player_id] = vote  # 'wait' | 'continue'

    eligible = [
        p for p in game["players"]
        if p["id"] != game["disconnectVote"]["targetPlayerId"] and p["connected"]
    ]
    vote_count = len(game["disconnectVote"]["votes"])
    if vote_count < len(eligible):
        return {"resolved": False}

    continue_votes = sum(1 for v in game["disconnectVote"]["votes"].values() if v == "continue")
    majority = continue_votes > len(eligible) / 2
    target_id = game["disconnectVote"]["targetPlayerId"]

    if majority:
        target = next((p for p in game["players"] if p["id"] == target_id), None)
        if target:
            target["droppedOut"] = True
            _log_highlight(game, f"The group voted to continue without {target['name']}. Score frozen.")
        game["disconnectVote"] = None
        if game.get("disconnectPending"):
            game["disconnectPending"].pop(target_id, None)
        return {"resolved": True, "action": "continue"}

    _log_highlight(game, f"The group voted to wait for {game['disconnectVote']['targetName']}.")
    game["disconnectVote"] = None
    return {"resolved": True, "action": "wait"}


def is_player_dropped_out(game: dict, player_index: int) -> bool:
    if player_index is None or player_index >= len(game["players"]):
        return False
    return game["players"][player_index].get("droppedOut") is True


def _should_skip_player(game: dict, player_index: int) -> bool:
    return is_player_dropped_out(game, player_index) or is_player_away(game, player_index)


def _skip_unavailable_players(game: dict) -> dict:
    n = len(game["players"])
    checks = 0
    while _should_skip_player(game, game["activePlayerIndex"]) and checks < n:
        game["questionIndex"] += 1
        if game["questionIndex"] >= TOTAL_QUESTIONS:
            game["phase"] = "GAME_OVER"
            return game
        game["activePlayerIndex"] = (game["activePlayerIndex"] + 1) % n
        checks += 1
    return game


def resume_after_drop(game: dict) -> dict:
    _skip_unavailable_players(game)
    if game["phase"] != "GAME_OVER":
        _begin_turn(game)
        game["phase"] = "CATEGORY"
    return game


def player_view(game: dict, player_id: str) -> dict:
    """Build a state view tailored to a specific player. Hides information
    the game rules say they shouldn't see: other players' hands, the
    correct answer (until RESULT), and internal CE/constraint data."""
    phase = game["phase"]
    all_reg = all(p["registered"] for p in game["players"])

    players = []
    for p in game["players"]:
        is_me = p["id"] == player_id
        players.append({
            "id": p["id"],
            "name": p["name"],
            "score": p["score"],
            "registered": p["registered"],
            "connected": p["connected"],
            "droppedOut": p["droppedOut"],
            "away": p["away"],
            "categories": p["categories"],
            "cardCount": len(p["hand"]),
            "hand": p["hand"] if is_me else None,
            "pickedCard": p["pickedCardId"] if (all_reg or is_me) else None,
            "pickedCardUsed": p["pickedCardUsed"],
        })

    my_index = next((i for i, p in enumerate(game["players"]) if p["id"] == player_id), -1)
    is_active_player = game["activePlayerIndex"] == my_index
    is_wager_player = len(game["players"]) >= 2 and game["players"].index(get_wager_player(game)) == my_index

    round_rule = game.get("roundRule")
    view = {
        "code": game["code"],
        "phase": phase,
        "myPlayerId": player_id,
        "players": players,
        "questionIndex": game["questionIndex"],
        "activePlayerIndex": game["activePlayerIndex"],
        "answererIndex": game["answererIndex"],
        "isActivePlayer": is_active_player,
        "isWagerPlayer": is_wager_player,
        "currentCategory": game["currentCategory"],
        "currentCategoryAttribution": game.get("currentCategoryAttribution"),
        "currentWager": game["currentWager"],
        "roundRule": (
            {
                "id": round_rule["id"],
                "name": round_rule["name"],
                "emoji": round_rule["emoji"],
                "description": round_rule["description"],
                "submissionBased": bool(round_rule.get("submissionBased")),
                "lineupBased": bool(round_rule.get("lineupBased")),
            }
            if round_rule else None
        ),
        "categoryOptions": game.get("categoryOptions"),
        "heckleMessage": game.get("heckleMessage"),
        "highlightReel": game["highlightReel"],
        "skippedTurn": bool(game.get("skippedTurn")),
    }

    if game.get("cardSlot"):
        view["cardSlot"] = {"playerId": game["cardSlot"]["playerId"], "cardId": game["cardSlot"]["cardId"]}

    if game.get("currentQuestion"):
        view["question"] = game["currentQuestion"]["question"]
        view["hostQuip"] = game["currentQuestion"]["hostQuip"]

        if game["currentQuestion"].get("lineup"):
            view["lineup"] = {
                "flavor": game["currentQuestion"]["lineup"]["flavor"],
                "options": game["currentQuestion"]["lineup"]["options"],
            }

        if phase in ("RESULT", "GAME_OVER"):
            view["answer"] = game["currentQuestion"]["answer"]
            if game["currentQuestion"].get("lineup"):
                view["lineup"]["correctOptionId"] = game["currentQuestion"]["lineup"]["correctOptionId"]

    if phase == "STEAL":
        view["stealEligible"] = player_id in game.get("stealEligible", []) and not game.get("stealSlot")
        view["stealClaimed"] = bool(game.get("stealSlot"))

    if phase in ("ANSWER", "EVALUATING") and round_rule and round_rule.get("submissionBased"):
        eligible = _submission_eligible_players(game)
        view["mySubmitted"] = player_id in (game.get("submissions") or {})
        view["submittedCount"] = sum(1 for p in eligible if p["id"] in (game.get("submissions") or {}))
        view["totalToSubmit"] = len(eligible)

    if game.get("lastResult") and phase in ("RESULT", "GAME_OVER", "STEAL"):
        view["lastResult"] = game["lastResult"]

    if phase == "GAME_OVER":
        view["winners"] = [{"id": p["id"], "name": p["name"], "score": p["score"]} for p in get_winners(game)]

    if game.get("disconnectVote"):
        view["disconnectVote"] = {
            "targetName": game["disconnectVote"]["targetName"],
            "canVote": player_id != game["disconnectVote"]["targetPlayerId"]
            and player_id not in game["disconnectVote"]["votes"],
        }

    view["paused"] = should_pause(game)

    return view
