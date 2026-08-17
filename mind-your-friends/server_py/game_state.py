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
import threading
import time

import claude_client
from cards import build_round_hand
from coherence import pick_factoid, round_constraints, turn_constraints, validate_question
from constants import (
    ACTIVE_WINDOW_MAX_SHARE,
    ACTIVE_WINDOW_SECONDS,
    AUTO_ADVANCE_AWAY_THRESHOLD,
    CATEGORIES_PER_PLAYER,
    CATEGORY_OPTIONS_COUNT,
    LINEUP_COLOR_FLAVOR_CHANCE,
    MAX_PLAYERS,
    MAX_WAGER,
    MIN_PLAYERS,
    MIN_WAGER,
    QUESTIONS_PER_ROUND,
    READING_SECONDS,
    ROUNDS,
    TOTAL_QUESTIONS,
    WAGER_VALUES,
    buzz_points_for_wager,
    wager_tier_index,
)
from lineup_data import build_color_options, pick_color_lineup_entry
from round_rules import (
    NO_RULE,
    ROUND_RULES,
    forced_rule_for_round_one,
    pick_random_round_rule,
    transform_answer,
)

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
        # Non-None only while start_game() is building the fact bank. The
        # build takes ~50s even with the batches running concurrently, which
        # is long enough that a lobby showing nothing reads as a hang — this
        # is what the client renders instead. See CLAUDE.md item 36.
        "startProgress": None,
        "factBank": {},
        # Category -> threading.Event for a fetch already in flight. See the
        # fact-bank section for why this is Events and not promises.
        "_factFetches": {},
        "factPrefetch": None,
        "roundNumber": None,
        "roundAnnouncement": None,
        # Rule ids already spent this game — the no-repeat picker reads it.
        "usedRuleIds": [],
        "answerAttempts": {},
        "lockedAnswers": {},
        # The evaluation queue. Tickets are handed out at claim time and
        # served strictly in order, which is what makes "first correct wins"
        # mean first submission rather than first API response — see
        # resolve_answer_attempt for why a plain Lock will not do.
        "_answerCond": threading.Condition(),
        "_answerTicket": 0,
        "_answerServing": 0,
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


# --- Fact bank -------------------------------------------------------------
#
# Facts are fetched per category, on demand, instead of all of them up front
# (playtest, Aug 12). Building the whole bank at Start Game meant a wait before
# anyone had touched the game — the worst possible place to put one, because
# nothing has happened yet to make it feel earned. Now Start Game is instant,
# categories nobody picks are never paid for at all, and the fetch for a
# category that IS picked happens behind the wager and card windows, where
# there is already time to fill.
#
# Two entry points, and both are needed:
#   ensure_category_facts() — correctness. Called before a question is
#     generated, so a category always has facts by the time it matters.
#   prefetch_fact_bank() — smoothness. Fired at game start; quietly fills in
#     everything else so the call above is almost always a no-op.
#
# THREADING NOTE, and it is a real difference from the JS version. There, both
# entry points return promises and de-duplication is a map of promises. Here
# they run on real threads, so the in-flight map holds threading.Event objects
# and a waiter blocks on the event rather than awaiting a promise. Callers must
# NOT hold the game lock across ensure_category_facts() — it can block on a
# network round trip.

def _track_fetch(game: dict, categories: list[str], event: threading.Event) -> None:
    """De-duplicates concurrent fetches for the same category: the prefetch and
    a player's pick can easily target the same category at the same moment, and
    paying twice for that is the exact cost this design avoids."""
    for c in categories:
        game["_factFetches"][c] = event


def _clear_fetch(game: dict, categories: list[str], event: threading.Event) -> None:
    for c in categories:
        if game["_factFetches"].get(c) is event:
            del game["_factFetches"][c]
    event.set()


def ensure_category_facts(game: dict, category: str) -> None:
    """Blocks until this category has facts. Safe to call when it already
    does — that is the common case, since the prefetch usually got there
    first."""
    if not category:
        return
    if game["factBank"].get(category):
        return

    in_flight = game["_factFetches"].get(category)
    if in_flight is not None:
        in_flight.wait()
        return

    event = threading.Event()
    _track_fetch(game, [category], event)
    try:
        facts = claude_client.fetch_facts_batch([category])
        game["factBank"].update(facts)
    except Exception as e:  # noqa: BLE001
        # Deliberately swallowed. generate_question() already has a
        # no-factoid fallback, so a failed fetch costs question quality, not
        # the turn — and raising here would take the whole turn down.
        print(f'Fact fetch failed for "{category}": {e}')
    finally:
        _clear_fetch(game, [category], event)


def prefetch_fact_bank(game: dict, on_update=None) -> None:
    """Fire-and-forget warm-up of every registered category. `on_update(game)`
    is the server's broadcast, so the room can see how much of the bank is
    warm. Runs on its own thread — start_game returns immediately."""
    all_categories = list({c for p in game["players"] for c in p["categories"]})
    missing = [
        c for c in all_categories
        if not game["factBank"].get(c) and c not in game["_factFetches"]
    ]
    if not missing:
        return

    def set_progress(progress) -> None:
        game["factPrefetch"] = progress
        if on_update is None:
            return
        try:
            on_update(game)
        except Exception as e:  # noqa: BLE001
            print(f"prefetch progress callback failed: {e}")

    event = threading.Event()
    _track_fetch(game, missing, event)

    def run() -> None:
        try:
            facts = claude_client.fetch_facts_batch(
                missing,
                lambda completed, total: set_progress(
                    {"active": completed < total, "completed": completed, "total": total}
                ),
            )
            game["factBank"].update(facts)
        except Exception as e:  # noqa: BLE001
            print(f"Fact-bank prefetch failed: {e}")
        finally:
            set_progress(None)
            _clear_fetch(game, missing, event)

    threading.Thread(target=run, daemon=True).start()


def build_fact_bank(game: dict, on_progress=None) -> dict:
    """Blocking, all-categories build. No longer used by start_game — kept
    because the Godot smoke tests drive it directly to get a warm bank without
    racing a background thread."""
    all_categories = list({c for p in game["players"] for c in p["categories"]})
    game["factBank"] = claude_client.fetch_facts_batch(all_categories, on_progress)
    return game


def _fact_bank_progress_label(completed: int, total: int) -> str:
    """Human-readable progress line for the lobby. Kept here rather than in
    the client so the Godot client shows the same words as the web client
    without either having to re-derive them (mirrors lib/gameState.js's
    factBankProgressLabel)."""
    if total <= 0 or completed <= 0:
        return "Building the question bank — this takes a minute…"
    if completed >= total:
        return "Question bank ready — dealing cards…"
    return f"Building the question bank — {completed} of {total} batches done…"


def start_game(game: dict, on_update=None) -> dict:
    """Instant. No fact bank is built here — the bank fills in behind the
    game (see the fact-bank section), so the room is on the category screen
    immediately instead of watching a progress bar for the better part of a
    minute before anything has happened.

    `on_update` is kept in the signature for main.py's prefetch broadcast; it
    is no longer called during start itself."""
    if not all_players_registered(game):
        raise GameError("All players must register before the game can start")

    game["startProgress"] = None
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


def current_round_number(game: dict) -> int:
    """1-based round number for the question about to be played."""
    return game["questionIndex"] // QUESTIONS_PER_ROUND + 1


def _begin_round_if_needed(game: dict) -> None:
    """Round rules are assigned once per ROUND, not per turn (playtest,
    Aug 12). Round 1 is deliberately plain: a new player should learn the base
    game before a rule bends it, which is the casual-first thesis applied to
    onboarding. Every round after that gets exactly one rule, announced at the
    top and kept on screen for its whole duration."""
    round_number = current_round_number(game)
    if game.get("roundNumber") == round_number and game.get("roundRule"):
        return

    game["roundNumber"] = round_number
    if round_number == 1:
        # MYF_FORCE_ROUND_RULE wins here so a playtest does not have to burn a
        # whole round to reach the rule under test. Unset, this is NO_RULE.
        game["roundRule"] = forced_rule_for_round_one() or NO_RULE
    else:
        # Rules do not repeat until every one has had a turn, so a 4-round
        # game shows four different twists.
        game["roundRule"] = pick_random_round_rule(game["usedRuleIds"])
        game["usedRuleIds"].append(game["roundRule"]["id"])
    game["roundConstraints"] = round_constraints(game["roundRule"])

    # Cleared one turn later (see next_turn) — it exists to be announced, and
    # the rule itself stays on screen for the round via view["roundRule"].
    game["roundAnnouncement"] = {
        "round": round_number,
        "ruleId": game["roundRule"]["id"],
        "name": game["roundRule"]["name"],
        "emoji": game["roundRule"]["emoji"],
        "description": game["roundRule"]["description"],
    }


def _begin_turn(game: dict) -> None:
    _begin_round_if_needed(game)
    game["answerAttempts"] = {}
    game["lockedAnswers"] = {}
    game["answerOpensAt"] = None
    game["buzzOpensAt"] = None
    game["lockClosesAt"] = None
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
    # Snap to the ladder rather than clamping a free number: the wager screen
    # offers five buttons, so anything else arriving here is a stale client or
    # a malformed payload, and silently accepting 137 would put a value on the
    # board that no pie can draw.
    if amount not in WAGER_VALUES:
        raise GameError(f"Wager must be one of {', '.join(str(v) for v in WAGER_VALUES)}")
    wager = amount
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
    """Assembles constraints via the CE, calls Claude, validates the result.

    Callers must NOT hold the game lock here: the fact-bank backstop below can
    block on a network round trip, and so can the question generation."""
    _assert_phase(game, "QUESTION")

    # Correctness backstop for the lazy fact bank. The prefetch has usually
    # covered this already (started at game start, and the wager and card
    # windows have run since the pick), in which case it returns at once.
    ensure_category_facts(game, game["currentCategory"])

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
    game["answerAttempts"] = {}
    game["lockedAnswers"] = {}

    # The question and the clock used to arrive together, making the timer
    # partly a reading-speed test. Now the question lands, the room reads it,
    # and only then can anyone act. Rules with their own answer flow keep
    # their existing behaviour and open immediately.
    own_answer_flow = game["roundRule"].get("submissionBased") or game["roundRule"].get("lineupBased")
    reading_ms = 0 if own_answer_flow else READING_SECONDS * 1000
    game["answerOpensAt"] = _now_ms() + reading_ms

    # Flow B: the answerer alone may act between answerOpensAt and
    # buzzOpensAt. An answerer who has already dropped out never gets a
    # window — the room would sit through it waiting for somebody absent.
    answerer = game["players"][game["answererIndex"]]
    exclusive_ms = 0 if (own_answer_flow or answerer["droppedOut"]) else get_active_window_seconds(game) * 1000
    game["buzzOpensAt"] = game["answerOpensAt"] + exclusive_ms

    # The deadline for locking in an answer. Set from the SCHEDULED end of the
    # exclusive window and never moved, unlike buzzOpensAt, which the answerer
    # can bring forward by answering or passing. If a pass at second one also
    # slammed the lock window shut, everyone else would be cut off mid-
    # sentence and the question would die with nobody able to buzz.
    game["lockClosesAt"] = game["buzzOpensAt"]

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


def get_answer_window_seconds(game: dict) -> float:
    """Total length of the ANSWER phase: reading window plus answer clock.
    main.py arms one timer for this and a second for the exclusive window —
    both are timestamps on the game rather than phases of their own, because
    every phase-timeout and auto-advance helper in this file assumes the
    existing loop."""
    return READING_SECONDS + get_timer_seconds(game)


def get_active_window_seconds(game: dict) -> int:
    """Flow B: how long the answerer has the question to themselves. Carved
    out of the answer clock rather than added to it — the question is the same
    length either way — and capped at a share of that clock so a halved timer
    does not become a mostly-exclusive round."""
    clock = get_timer_seconds(game)
    return round(min(ACTIVE_WINDOW_SECONDS, clock * ACTIVE_WINDOW_MAX_SHARE))


def get_active_window_total_seconds(game: dict) -> float:
    """From the start of the ANSWER phase to the buzzer opening."""
    return READING_SECONDS + get_active_window_seconds(game)


def get_buzz_points(game: dict) -> int:
    return buzz_points_for_wager(game.get("currentWager"))


def _now_ms() -> int:
    """Wire timestamps are epoch milliseconds, matching the JS prototype, so
    both backends speak one contract to the same clients."""
    return int(time.time() * 1000)


def _is_answerer(game: dict, player_id: str) -> bool:
    idx = game.get("answererIndex")
    if idx is None:
        return False
    return game["players"][idx]["id"] == player_id


def _open_answer_eligible(game: dict) -> list[dict]:
    """Everyone who could still play an answer: not out of the game, has not
    already swung, and — since a buzz plays a pre-committed answer — is
    holding one."""
    return [
        p for p in game["players"]
        if not p["droppedOut"]
        and p["id"] not in game["answerAttempts"]
        and (_is_answerer(game, p["id"]) or p["id"] in game["lockedAnswers"])
    ]


def _anyone_still_to_play(game: dict) -> bool:
    """Two ways to still be in it: holding a committed answer you have not
    buzzed, or still being able to commit one. The second half is why this is
    not just an eligibility count — ending a question out from under somebody
    mid-sentence would punish thinking."""
    if _open_answer_eligible(game):
        return True
    if _now_ms() >= game.get("lockClosesAt", 0):
        return False
    return any(
        not p["droppedOut"]
        and not _is_answerer(game, p["id"])
        and p["id"] not in game["answerAttempts"]
        and p["id"] not in game["lockedAnswers"]
        for p in game["players"]
    )


def _close_question_if_nobody_left(game: dict) -> bool:
    """A buzzer nobody can press is just dead air. With pre-committed answers
    a room where nobody locked one in has no way to resolve the question and
    would otherwise sit watching the clock run down — end it there instead."""
    if game["phase"] != "ANSWER":
        return False
    if _anyone_still_to_play(game):
        return False

    _log_highlight(
        game,
        "Nobody had an answer locked in — the points go unclaimed."
        if not game["lockedAnswers"]
        else "Nobody got it — the points go unclaimed.",
    )
    _finish_open_answer(game, winner=None, points=0)
    return True


# --- Answering: Flow B ------------------------------------------------------
#
# Three windows, one after the other, all inside the ANSWER phase:
#
#   1. Reading (READING_SECONDS) — nobody may act.
#   2. Exclusive (get_active_window_seconds) — the answerer may answer or
#      pass; either one opens the buzzer immediately. Meanwhile everyone ELSE
#      is committing an answer they cannot yet play.
#   3. Open — anyone holding a committed answer may buzz. One attempt each,
#      first correct buzz wins get_buzz_points().
#
# Step 2 is Flow B (GAME_DESIGN.md → "The Round Loop"). Without it a faster
# player takes every question and the answerer's wager never bites — worse, it
# breaks "I cut, you choose": if anyone can claim the wager, the setter is no
# longer setting a punishment but a bounty they might collect themselves, so
# they would always set maximum. See PLAYTEST.md PT-4.
#
# PRE-COMMITMENT: a buzz plays an answer locked in BEFORE its owner knew they
# would get the chance. That closes the lookup window (the moment worth
# cheating in is the one after the answerer fumbles, and it no longer accepts
# new answers), turns buzzing from a typing race into a one-tap decision, and
# keeps the room busy during the exclusive window. No lock, no buzz.
#
# --- Why the ticket lock ----------------------------------------------------
#
# "First correct wins" must mean first SUBMISSION, never first API response.
# Node got that free: one event loop plus one promise chain. Python does not,
# and two things have to be true at once here:
#
#   * Evaluations must run in submission order. A plain threading.Lock will
#     NOT do it — Python locks make no FIFO promise, so two threads blocked on
#     one can be granted in either order, which is exactly the coin flip this
#     has to avoid.
#   * The evaluation is a Claude call and must NOT hold the caller's game lock
#     while it waits, or the whole room freezes on every answer.
#
# So each attempt takes a ticket at claim time (under the caller's lock, in
# the same critical section that claims the attempt slot, so the order cannot
# be interleaved) and then waits its turn on a condition variable with no game
# lock held. Deliberately explicit about which lock is held where — see
# resolve_answer_attempt's `lock` parameter.


class _NullLock:
    """Stand-in for callers with no game lock — the test suite, which is
    single-threaded, and any future caller that already holds nothing."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


_NULL_LOCK = _NullLock()


def _claim_attempt(game: dict, player_id: str, name: str, answer: str, buzzed: bool) -> dict:
    """Claims the attempt slot AND takes an evaluation ticket in one step.
    Callers must hold the game lock across this — the ticket is what fixes
    submission order, so handing them out in a different critical section than
    the slot claim would let two answers swap places."""
    attempt = {
        "playerId": player_id,
        "name": name,
        "answer": answer,
        "correct": None,
        "buzzed": buzzed,
    }
    game["answerAttempts"][player_id] = attempt
    attempt["ticket"] = game["_answerTicket"]
    game["_answerTicket"] += 1
    return attempt


def resolve_answer_attempt(game: dict, attempt: dict, input_mode: str, lock=None) -> dict:
    """Evaluates one claimed attempt. MUST be called with no game lock held:
    it blocks until earlier attempts have been judged, then makes a real API
    call. `lock` is the caller's game lock, re-acquired only for the short
    span that applies the result."""
    lock = lock or _NULL_LOCK
    cond = game["_answerCond"]

    with cond:
        while game["_answerServing"] != attempt["ticket"]:
            cond.wait()

    try:
        # Somebody already won (or the window closed) while this was queued.
        with lock:
            if game["phase"] != "ANSWER":
                attempt["correct"] = False
                attempt["moot"] = True
                return game
            question = game["currentQuestion"]["question"]
            correct_answer = game["currentQuestion"]["answer"]
            round_rule = game["roundRule"]
            transformed = transform_answer(round_rule, attempt["answer"], input_mode)

        # The API call, with no game lock held — the whole point of the split.
        result = claude_client.evaluate_answer(
            question=question,
            correct_answer=correct_answer,
            player_answer=transformed,
            round_rule=round_rule,
        )

        with lock:
            # Re-check: the window can close while the evaluation is in flight.
            if game["phase"] != "ANSWER":
                attempt["correct"] = False
                attempt["moot"] = True
                return game
            _apply_answer_result(game, attempt, result)
        return game
    finally:
        # Always advance the queue, including on the moot and error paths, or
        # every later attempt blocks forever.
        with cond:
            game["_answerServing"] += 1
            cond.notify_all()


def _apply_answer_result(game: dict, attempt: dict, result: dict) -> None:
    attempt["correct"] = bool(result.get("correct"))
    attempt["feedback"] = result.get("feedback")

    player = get_player(game, attempt["playerId"])
    answerer = game["players"][game["answererIndex"]]
    is_answerer = attempt["playerId"] == answerer["id"]
    wager = game["currentWager"]

    if attempt["correct"]:
        points = wager if is_answerer else get_buzz_points(game)
        player["score"] += points
        _log_highlight(
            game,
            f'{player["name"]} took their own question for {points} pts.'
            if is_answerer
            else f'{player["name"]} pounced on {answerer["name"]}\'s question for {points} pts!',
        )
        _finish_open_answer(game, winner=attempt, points=points, **result)
        return

    if is_answerer:
        player["score"] -= wager
        _log_highlight(
            game,
            f'{player["name"]} wagered {wager} and answered "{attempt["answer"]}" — wrong!',
        )

    if not _anyone_still_to_play(game):
        _finish_open_answer(game, winner=None, points=0, **result)


def submit_answer(game: dict, player_id: str, raw_answer: str, input_mode: str) -> dict:
    """The answerer's live answer, inside their own exclusive window.

    Claims the slot only — the caller must then call resolve_answer_attempt()
    with the game lock RELEASED. Returns the claimed attempt."""
    _assert_phase(game, "ANSWER")
    if game["roundRule"].get("submissionBased") or game["roundRule"].get("lineupBased"):
        raise GameError("This round rule has its own answer flow")
    if not _is_answerer(game, player_id):
        raise GameError("Not your question — lock an answer in and buzz instead")
    player = get_player(game, player_id)
    if player["droppedOut"]:
        raise GameError("You are out of this game")
    if _now_ms() < game.get("answerOpensAt", 0):
        raise GameError("Still reading — nobody can answer yet")
    if player_id in game["answerAttempts"]:
        raise GameError("You already had your shot at this one")

    attempt = _claim_attempt(game, player_id, player["name"], raw_answer, buzzed=False)

    # The answerer has spoken, so the room is in. Opened on SUBMISSION, not on
    # the evaluation coming back: making everyone wait out an API call would
    # hand seconds of a shared clock to whoever the API happened to be slow
    # for. Ordering stays safe — the ticket above already fixed it.
    game["buzzOpensAt"] = _now_ms()
    return attempt


def lock_answer(game: dict, player_id: str, raw_answer: str, input_mode: str) -> dict:
    """Commit an answer you may or may not get to play. Non-answerers only,
    and only before lockClosesAt.

    Immutable once set: a commitment you can revise until the last instant is
    not a commitment, and the whole mechanic rests on having decided early."""
    _assert_phase(game, "ANSWER")
    if game["roundRule"].get("submissionBased") or game["roundRule"].get("lineupBased"):
        raise GameError("This round rule has its own answer flow")
    if _is_answerer(game, player_id):
        raise GameError("This one is yours to answer, not to lock in")
    player = get_player(game, player_id)
    if player["droppedOut"]:
        raise GameError("You are out of this game")
    trimmed = (raw_answer or "").strip()
    if not trimmed:
        raise GameError("Nothing to lock in")
    now = _now_ms()
    if now < game.get("answerOpensAt", 0):
        raise GameError("Still reading — nobody can act yet")
    if now >= game.get("lockClosesAt", 0):
        raise GameError("Too late — answers are locked for this question")
    if player_id in game["lockedAnswers"]:
        raise GameError("You already locked one in — no changing it now")

    game["lockedAnswers"][player_id] = {"answer": trimmed, "inputMode": input_mode or "text"}
    return game


def buzz_in(game: dict, player_id: str) -> dict:
    """Play the answer you committed earlier. Claims the slot only — same
    two-step contract as submit_answer(). Returns (attempt, inputMode)."""
    _assert_phase(game, "ANSWER")
    if game["roundRule"].get("submissionBased") or game["roundRule"].get("lineupBased"):
        raise GameError("This round rule has its own answer flow")
    player = get_player(game, player_id)
    if player["droppedOut"]:
        raise GameError("You are out of this game")
    if _now_ms() < game.get("buzzOpensAt", 0):
        answerer = game["players"][game["answererIndex"]]
        raise GameError(f'{answerer["name"]} gets first shot at their own question')
    if player_id in game["answerAttempts"]:
        raise GameError("You already had your shot at this one")
    locked = game["lockedAnswers"].get(player_id)
    if locked is None:
        raise GameError("You did not lock an answer in for this one")

    attempt = _claim_attempt(game, player_id, player["name"], locked["answer"], buzzed=True)
    return attempt, locked["inputMode"]


def pass_answer(game: dict, player_id: str) -> dict:
    """Folding. The answerer declines their own question, the buzzer opens
    immediately, and it costs them nothing.

    Passing must be EXPLICIT and must not be reachable by doing nothing — see
    expire_active_window. A free opt-out from any hard question would put the
    wager right back where Flow B found it."""
    _assert_phase(game, "ANSWER")
    if game["roundRule"].get("submissionBased") or game["roundRule"].get("lineupBased"):
        raise GameError("This round rule has its own answer flow")
    if not _is_answerer(game, player_id):
        raise GameError("Only the player whose question it is can pass")
    answerer = game["players"][game["answererIndex"]]
    now = _now_ms()
    if now < game.get("answerOpensAt", 0):
        raise GameError("Still reading — nobody can act yet")
    if player_id in game["answerAttempts"]:
        raise GameError("You already had your shot at this one")
    if now >= game.get("buzzOpensAt", 0):
        raise GameError("Too late to pass — the buzzer is already open")

    # Recorded as a spent attempt so the rest of this file needs no new
    # concept: it is what stops them buzzing back in on a question they
    # folded on, and what stops expire_answer_window charging them later.
    game["answerAttempts"][player_id] = {
        "playerId": player_id,
        "name": answerer["name"],
        "answer": "",
        "correct": False,
        "passed": True,
    }
    game["buzzOpensAt"] = now
    _log_highlight(game, f'{answerer["name"]} passed on {game["currentWager"]} pts — over to the room.')
    return game


def expire_active_window(game: dict) -> bool:
    """The exclusive window closing with the answerer having done nothing.

    This is the load-bearing half of the pass/timeout split: folding is a
    decision and costs nothing, freezing is a failure and costs the wager,
    exactly as answering wrong would. Collapse the two and "pass" becomes a
    free opt-out of every hard question.

    Returns True when it changed anything, so the caller knows to broadcast."""
    if game["phase"] != "ANSWER":
        return False
    if game["roundRule"].get("submissionBased") or game["roundRule"].get("lineupBased"):
        return False

    answerer = game["players"][game["answererIndex"]]
    # They answered or passed inside the window, so the buzzer opened then,
    # not now. Locking still closes at this instant though, and that can be
    # the moment the question becomes unanswerable by anyone.
    if answerer["id"] in game["answerAttempts"]:
        return _close_question_if_nobody_left(game)

    game["buzzOpensAt"] = _now_ms()
    if not answerer["droppedOut"]:
        answerer["score"] -= game["currentWager"]
        game["answerAttempts"][answerer["id"]] = {
            "playerId": answerer["id"],
            "name": answerer["name"],
            "answer": "",
            "correct": False,
            "timedOut": True,
        }
        _log_highlight(
            game,
            f'{answerer["name"]} froze and dropped {game["currentWager"]} pts — buzzers open!',
        )

    _close_question_if_nobody_left(game)
    return True


def expire_answer_window(game: dict) -> dict:
    """The whole ANSWER phase closing with nobody having got it right.

    Under Flow B the answerer has almost always been dealt with already — by
    expire_active_window when they froze, or by their own answer or pass. The
    charge below still stands for the paths that skip the exclusive window,
    and never double-charges: a spent attempt of any kind takes the else."""
    if game["phase"] != "ANSWER":
        return game
    if game["roundRule"].get("submissionBased") or game["roundRule"].get("lineupBased"):
        return game

    answerer = game["players"][game["answererIndex"]]
    if answerer["id"] not in game["answerAttempts"] and not answerer["droppedOut"]:
        answerer["score"] -= game["currentWager"]
        game["answerAttempts"][answerer["id"]] = {
            "playerId": answerer["id"],
            "name": answerer["name"],
            "answer": "",
            "correct": False,
            "timedOut": True,
        }
        _log_highlight(
            game,
            f'{answerer["name"]} ran out of time and lost {game["currentWager"]} pts.',
        )
    else:
        _log_highlight(game, "Nobody got it — the points go unclaimed.")

    _finish_open_answer(game, winner=None, points=0)
    return game


def _finish_open_answer(game: dict, winner=None, points=0, **result) -> None:
    answerer = game["players"][game["answererIndex"]]
    answerer_attempt = game["answerAttempts"].get(answerer["id"])

    # What became of the person whose wager it was. The result screen and the
    # question log both need to tell "passed" (costs nothing) apart from
    # "froze" (costs the wager) — they look identical from outside otherwise,
    # and reporting a fold as a forfeit is a lie about the score.
    if not answerer_attempt:
        active_outcome = "none"
    elif answerer_attempt.get("passed"):
        active_outcome = "passed"
    elif answerer_attempt.get("timedOut"):
        active_outcome = "timedOut"
    elif answerer_attempt.get("correct"):
        active_outcome = "correct"
    else:
        active_outcome = "wrong"

    game["lastResult"] = {
        **result,
        "correct": bool(winner),
        "wager": game["currentWager"],
        "playerAnswer": winner["answer"] if winner else (answerer_attempt or {}).get("answer") or None,
        "winnerId": winner["playerId"] if winner else None,
        "winnerName": winner["name"] if winner else None,
        "points": points or 0,
        "buzzedIn": bool(winner) and winner["playerId"] != answerer["id"],
        "activeOutcome": active_outcome,
        "wagerLost": active_outcome in ("wrong", "timedOut"),
        "buzzPoints": get_buzz_points(game),
        "attempts": [
            {
                "playerId": a["playerId"],
                "name": a["name"],
                "answer": a["answer"],
                "correct": bool(a.get("correct")),
                "passed": bool(a.get("passed")),
                "timedOut": bool(a.get("timedOut")),
            }
            for a in game["answerAttempts"].values()
        ],
        # Answers locked in that never got played. Revealed because it is the
        # best social content the mechanic produces: "you HAD it and sat on
        # it" is the line people shout, and it is invisible otherwise.
        "unplayedAnswers": [
            {
                "playerId": pid,
                "name": get_player(game, pid)["name"],
                "answer": locked["answer"],
            }
            for pid, locked in game["lockedAnswers"].items()
            if pid not in game["answerAttempts"]
        ],
    }
    game["phase"] = "RESULT"


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
    # The announcement gets exactly one turn on screen; the rule itself stays
    # visible for the whole round via view["roundRule"].
    game["roundAnnouncement"] = None
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
                # The client renders the countdown from this. Card effects can
                # shorten it (Spotlight), hence the helper rather than the raw
                # rule value.
                "timerSeconds": get_timer_seconds(game),
            }
            if round_rule else None
        ),
        "categoryOptions": game.get("categoryOptions"),
        "heckleMessage": game.get("heckleMessage"),
        "highlightReel": game["highlightReel"],
        "skippedTurn": bool(game.get("skippedTurn")),
        "roundNumber": game.get("roundNumber") or 1,
        "totalRounds": ROUNDS,
        # Set for exactly one turn at the top of each round; the client shows
        # it as a banner. None the rest of the time.
        "roundAnnouncement": game.get("roundAnnouncement"),
        # None except while the fact bank is building. Same shape for every
        # player — this is room-wide progress, not per-player state.
        "startProgress": game.get("startProgress"),
        # Background fact-bank warm-up. Not blocking anything — shown as a
        # quiet footer so a slow first question reads as "still loading"
        # rather than "broken".
        "factPrefetch": game.get("factPrefetch"),
    }

    if game.get("cardSlot"):
        view["cardSlot"] = {"playerId": game["cardSlot"]["playerId"], "cardId": game["cardSlot"]["cardId"]}

    if game.get("currentQuestion"):
        view["question"] = game["currentQuestion"]["question"]
        view["hostQuip"] = game["currentQuestion"]["hostQuip"]
        # Which rung of the wager ladder this question was written to. The
        # client prints the question in the matching green. Sent as a tier
        # rather than a colour so the palette stays a client concern.
        view["difficultyTier"] = wager_tier_index(game.get("currentWager"))

        if game["currentQuestion"].get("lineup"):
            view["lineup"] = {
                "flavor": game["currentQuestion"]["lineup"]["flavor"],
                "options": game["currentQuestion"]["lineup"]["options"],
            }

        if phase in ("RESULT", "GAME_OVER"):
            view["answer"] = game["currentQuestion"]["answer"]
            if game["currentQuestion"].get("lineup"):
                view["lineup"]["correctOptionId"] = game["currentQuestion"]["lineup"]["correctOptionId"]

    # Flow B. Deliberately does NOT include other players' answer TEXT while
    # the question is live — only who has burned their attempt — so nobody can
    # copy a neighbour's wording.
    #
    # The timestamps go out raw and the client compares them against its own
    # clock: a view is only rebuilt when the server broadcasts, so anything
    # computed from "now" here would be stale on arrival, and both windows are
    # short enough for that to matter.
    if phase == "ANSWER" and round_rule and not round_rule.get("submissionBased") and not round_rule.get("lineupBased"):
        mine = game["answerAttempts"].get(player_id)
        am_answerer = _is_answerer(game, player_id)
        me = next((p for p in game["players"] if p["id"] == player_id), None)
        out = bool(me and me["droppedOut"])
        my_lock = game["lockedAnswers"].get(player_id)

        view["answerOpensAt"] = game.get("answerOpensAt")
        view["buzzOpensAt"] = game.get("buzzOpensAt")
        view["lockClosesAt"] = game.get("lockClosesAt")
        view["activeWindowSeconds"] = get_active_window_seconds(game)
        view["iAmAnswerer"] = am_answerer
        view["iCanAnswer"] = am_answerer and not mine and not out
        view["iCanPass"] = am_answerer and not mine and not out
        view["iCanLock"] = not am_answerer and not mine and not out and my_lock is None
        view["iCanBuzz"] = not am_answerer and not mine and not out and my_lock is not None
        # My own commitment comes back to me so a reconnect does not lose it.
        # Nobody else's does — see unplayedAnswers, which reveals them all
        # once the question is over and there is nothing left to spoil.
        view["myLockedAnswer"] = my_lock["answer"] if my_lock else None
        view["lockedCount"] = len(game["lockedAnswers"])
        view["myAttempt"] = (
            {
                "answer": mine["answer"],
                "correct": mine.get("correct"),
                "passed": bool(mine.get("passed")),
                "timedOut": bool(mine.get("timedOut")),
            }
            if mine else None
        )
        view["spentAttempts"] = [
            {
                "playerId": a["playerId"],
                "name": a["name"],
                "correct": a.get("correct"),
                "passed": bool(a.get("passed")),
                "timedOut": bool(a.get("timedOut")),
            }
            for a in game["answerAttempts"].values()
        ]
        view["buzzPoints"] = get_buzz_points(game)

    if phase in ("ANSWER", "EVALUATING") and round_rule and round_rule.get("submissionBased"):
        eligible = _submission_eligible_players(game)
        view["mySubmitted"] = player_id in (game.get("submissions") or {})
        view["submittedCount"] = sum(1 for p in eligible if p["id"] in (game.get("submissions") or {}))
        view["totalToSubmit"] = len(eligible)

    if game.get("lastResult") and phase in ("RESULT", "GAME_OVER"):
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
