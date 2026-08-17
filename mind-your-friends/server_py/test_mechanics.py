"""Python mirror of scripts/mechanics-test.js — Flow B, pre-committed answers,
the wager ladder, the reading window and the lazy fact bank.

Costs ZERO API calls. A fake Anthropic client answers both call types this
exercises, keyed off the prompt, with controllable latency. That is what lets
the ordering claims be asserted rather than assumed: "first correct wins" is a
race, and a race cannot be tested against a real API whose response times are
the thing under test.

This suite matters more on the Python side than on the JS side. Node got FCFS
correctness free from its single event loop; here it is a ticket lock that has
to be right, and the two tests that would catch it breaking are the buzz-order
race and the "no double charge" pair.

Run: python3 test_mechanics.py
"""

import json
import sys
import threading
import time

sys.path.insert(0, ".")

import claude_client
import game_state as gs
from coherence import round_constraints
from constants import (
    ACTIVE_WINDOW_MAX_SHARE,
    ACTIVE_WINDOW_SECONDS,
    BUZZ_WAGER_SHARE,
    CATEGORIES_PER_PLAYER,
    QUESTIONS_PER_ROUND,
    READING_SECONDS,
    WAGER_VALUES,
)
from round_rules import BASE_TIMER_SECONDS, ROUND_RULES

failures = 0
CORRECT_ANSWER = "Correct Answer"


def check(condition, description):
    global failures
    print(f"  {'PASS' if condition else 'FAIL'}  {description}")
    if not condition:
        failures += 1


class FakeMessages:
    def __init__(self, state, latency):
        self.state = state
        self.latency = latency

    def create(self, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        if self.latency:
            time.sleep(self.latency)

        if prompt.startswith("You are an expert researcher"):
            self.state["factCalls"] += 1
            names = prompt.split("\n")[0].split('"')[1::2]
            out = {
                name: [
                    {
                        "fact": f"Fact {i} about {name}",
                        "answer": CORRECT_ANSWER,
                        "bucket": (i % 5) + 1,
                        "difficulty": "easy",
                        "answerWordCount": 2,
                        "questionAngles": ["naming"],
                        "sourceType": "encyclopedia",
                    }
                    for i in range(10)
                ]
                for name in names
            }
            return FakeResponse(json.dumps(out))

        if prompt.startswith("Question:"):
            self.state["evalCalls"] += 1
            given = prompt.split("Player's answer: ")[1].split("\n")[0]
            expected = prompt.split("Expected answer: ")[1].split("\n")[0]
            self.state["evalOrder"].append(given)
            return FakeResponse(json.dumps({
                "correct": given.strip().lower() == expected.strip().lower(),
                "feedback": f"You said {given}",
            }))

        return FakeResponse(json.dumps({
            "question": "Who did the thing in the place at the time?",
            "answer": CORRECT_ANSWER,
            "hostQuip": "Here we go.",
        }))


class FakeResponse:
    def __init__(self, text):
        self.content = [type("Block", (), {"text": text})()]


class FakeClient:
    def __init__(self, latency=0):
        self.state = {"factCalls": 0, "evalCalls": 0, "evalOrder": []}
        self.messages = FakeMessages(self.state, latency)


def registered_game():
    game = gs.create_game("p1", "Alice")
    gs.add_player(game, "p2", "Bob")
    gs.add_player(game, "p3", "Cara")
    for pid, prefix, card in (("p1", "Alice", "insurance"), ("p2", "Bob", "insurance"), ("p3", "Cara", "skip")):
        gs.register_player(
            game, pid,
            [f"{prefix} Cat {n + 1}" for n in range(CATEGORIES_PER_PLAYER)],
            card,
        )
    return game


def to_active_window(game, wager=200, category=None):
    """CATEGORY -> an ANSWER phase with the reading window already elapsed.
    The answerer's exclusive window is still live."""
    pick = category or game["categoryOptions"][0]["category"]
    gs.pick_category(game, game["players"][game["activePlayerIndex"]]["id"], pick)
    wager_player = game["players"][(game["activePlayerIndex"] + 1) % len(game["players"])]
    gs.set_wager(game, wager_player["id"], wager)
    gs.resolve_card_slot(game)
    gs.run_question_phase(game)
    game["answerOpensAt"] = 0
    return game


def to_open_answer(game, wager=200, category=None):
    to_active_window(game, wager, category)
    game["buzzOpensAt"] = 0
    return game


def answer(game, player_id, text, input_mode="text"):
    """Claim + resolve, the two-step main.py performs with the lock in between."""
    attempt = gs.submit_answer(game, player_id, text, input_mode)
    gs.resolve_answer_attempt(game, attempt, input_mode)


def buzz(game, player_id):
    attempt, mode = gs.buzz_in(game, player_id)
    gs.resolve_answer_attempt(game, attempt, mode)


def main():
    # --- Instant start + lazy fact bank ------------------------------------
    print("\n--- Instant start + lazy fact bank ---")
    fake = FakeClient()
    claude_client.__set_client_for_tests(fake)
    game = registered_game()

    started = time.time()
    gs.start_game(game)
    elapsed = (time.time() - started) * 1000

    check(game["phase"] == "CATEGORY", f'start lands straight on CATEGORY (got {game["phase"]})')
    check(elapsed < 50, f"start is instant ({elapsed:.0f}ms)")
    check(fake.state["factCalls"] == 0, f'no facts fetched at start (got {fake.state["factCalls"]})')
    check(game["factBank"] == {}, "fact bank starts empty")
    check(len(game["categoryOptions"]) > 0, "category options are ready immediately")

    category = game["players"][0]["categories"][0]
    gs.ensure_category_facts(game, category)
    check(bool(game["factBank"].get(category)), "a picked category is fetched on demand")
    before = fake.state["factCalls"]
    gs.ensure_category_facts(game, category)
    check(fake.state["factCalls"] == before, "a warm category costs nothing")

    # --- The reading window ------------------------------------------------
    print("\n--- Reading window ---")
    claude_client.__set_client_for_tests(FakeClient())
    game = registered_game()
    gs.start_game(game)
    gs.pick_category(game, game["players"][0]["id"], game["categoryOptions"][0]["category"])
    gs.set_wager(game, game["players"][1]["id"], 100)
    gs.resolve_card_slot(game)
    gs.run_question_phase(game)

    check(game["phase"] == "ANSWER", f'question lands in ANSWER (got {game["phase"]})')
    reading_ms = game["answerOpensAt"] - gs._now_ms()
    check(reading_ms > (READING_SECONDS - 1) * 1000,
          f'buzzers open ~{READING_SECONDS}s after the question ({reading_ms / 1000:.0f}s)')

    threw = None
    try:
        answer(game, "p1", CORRECT_ANSWER)
    except gs.GameError as e:
        threw = e
    check(threw is not None, "answering during the reading window is rejected")
    check(len(game["answerAttempts"]) == 0, "a rejected early answer does not burn the attempt")

    check(gs.get_answer_window_seconds(game) == READING_SECONDS + BASE_TIMER_SECONDS,
          "answer window is reading + answer time")

    # --- Flow B: first refusal ---------------------------------------------
    print("\n--- Flow B: first refusal ---")
    claude_client.__set_client_for_tests(FakeClient())
    game = registered_game()
    gs.start_game(game)
    to_active_window(game, wager=100)

    answerer = game["players"][game["answererIndex"]]
    other = next(p for p in game["players"] if p["id"] != answerer["id"])

    check(gs.get_active_window_seconds(game) == ACTIVE_WINDOW_SECONDS,
          f'a 40s clock gives the full {ACTIVE_WINDOW_SECONDS}s window')

    gs.lock_answer(game, other["id"], CORRECT_ANSWER, "text")
    threw = None
    try:
        buzz(game, other["id"])
    except gs.GameError as e:
        threw = e
    check(threw is not None, "buzzing during the exclusive window is rejected")
    check(other["score"] == 0, "and pays nothing")

    answer(game, answerer["id"], CORRECT_ANSWER)
    check(game["phase"] == "RESULT", "the answerer answering correctly ends it")
    check(answerer["score"] == 100, f'and wins the whole wager ({answerer["score"]})')
    check(game["lastResult"]["buzzedIn"] is False, "nobody buzzed in")
    check(len(game["lastResult"]["unplayedAnswers"]) == 1,
          "the answer that never got played is revealed")

    # --- The 25% cap --------------------------------------------------------
    print("\n--- Exclusive window is capped ---")
    claude_client.__set_client_for_tests(FakeClient())
    game = registered_game()
    gs.start_game(game)
    game["roundRule"] = ROUND_RULES["lightningRound"]
    game["roundConstraints"] = round_constraints(game["roundRule"])
    to_active_window(game, wager=100)
    clock = ROUND_RULES["lightningRound"]["timerSeconds"]
    window = gs.get_active_window_seconds(game)
    check(window == round(clock * ACTIVE_WINDOW_MAX_SHARE),
          f"a halved clock gets a capped window ({window}s of {clock}s)")
    check(window < ACTIVE_WINDOW_SECONDS, "so a short round never becomes mostly-exclusive")

    # --- Pass vs freeze -----------------------------------------------------
    print("\n--- Pass vs freeze ---")
    claude_client.__set_client_for_tests(FakeClient())
    game = registered_game()
    gs.start_game(game)
    to_active_window(game, wager=200)
    answerer = game["players"][game["answererIndex"]]
    other = next(p for p in game["players"] if p["id"] != answerer["id"])
    gs.lock_answer(game, other["id"], CORRECT_ANSWER, "text")

    gs.pass_answer(game, answerer["id"])
    check(answerer["score"] == 0, f'folding costs nothing ({answerer["score"]})')
    check(game["buzzOpensAt"] <= gs._now_ms(), "and opens the buzzer at once")
    check(game["lockClosesAt"] > gs._now_ms(),
          "but does NOT slam the lock window shut on everyone still typing")

    buzz(game, other["id"])
    check(game["phase"] == "RESULT", "the room can then take it")
    check(other["score"] == gs.buzz_points_for_wager(200),
          f'for the buzz share ({other["score"]})')
    check(game["lastResult"]["activeOutcome"] == "passed", "the result records a fold")
    check(game["lastResult"]["wagerLost"] is False, "and does not report points the answerer kept")

    claude_client.__set_client_for_tests(FakeClient())
    game = registered_game()
    gs.start_game(game)
    to_active_window(game, wager=200)
    answerer = game["players"][game["answererIndex"]]
    other = next(p for p in game["players"] if p["id"] != answerer["id"])
    gs.lock_answer(game, other["id"], "nope", "text")

    game["lockClosesAt"] = 0
    gs.expire_active_window(game)
    check(answerer["score"] == -200,
          f'freezing costs the wager, exactly like a wrong answer ({answerer["score"]})')
    check(game["phase"] == "ANSWER", "and the room still gets its shot")
    gs.expire_answer_window(game)
    check(answerer["score"] == -200, f'and is never charged twice ({answerer["score"]})')
    check(game["lastResult"]["activeOutcome"] == "timedOut", "the result tells a freeze from a fold")

    # --- Locked answers -----------------------------------------------------
    print("\n--- Locked answers ---")
    claude_client.__set_client_for_tests(FakeClient())
    game = registered_game()
    gs.start_game(game)
    to_active_window(game, wager=100)
    answerer = game["players"][game["answererIndex"]]
    first, second = [p for p in game["players"] if p["id"] != answerer["id"]]

    gs.lock_answer(game, first["id"], CORRECT_ANSWER, "text")
    threw = None
    try:
        gs.lock_answer(game, first["id"], "changed my mind", "text")
    except gs.GameError as e:
        threw = e
    check(threw is not None, "a locked answer cannot be revised")
    check(game["lockedAnswers"][first["id"]]["answer"] == CORRECT_ANSWER, "the original stands")

    view = gs.player_view(game, second["id"])
    check(view["lockedCount"] == 1, "the room sees how many are ready")
    check(view["myLockedAnswer"] is None, "but not what they said")
    check(gs.player_view(game, first["id"])["iCanBuzz"] is True, "a committed player can buzz")
    check(view["iCanBuzz"] is False, "an uncommitted one cannot")

    game["lockClosesAt"] = 0
    game["buzzOpensAt"] = 0
    threw = None
    try:
        gs.lock_answer(game, second["id"], CORRECT_ANSWER, "text")
    except gs.GameError as e:
        threw = e
    check(threw is not None, "no locking in after the buzzer opens")
    threw = None
    try:
        buzz(game, second["id"])
    except gs.GameError as e:
        threw = e
    check(threw is not None, "and no answer means no buzz at all")

    buzz(game, first["id"])
    check(game["phase"] == "RESULT", "the committed player takes it")
    check(first["score"] == 75, f'for the buzz share ({first["score"]})')

    # --- The wager ladder ---------------------------------------------------
    print("\n--- Wager ladder ---")
    claude_client.__set_client_for_tests(FakeClient())
    game = registered_game()
    gs.start_game(game)
    gs.pick_category(game, game["players"][0]["id"], game["categoryOptions"][0]["category"])
    threw = None
    try:
        gs.set_wager(game, game["players"][1]["id"], 137)
    except gs.GameError as e:
        threw = e
    check(threw is not None, "a wager off the ladder is rejected, not clamped")
    gs.set_wager(game, game["players"][1]["id"], 200)
    check(game["currentWager"] == 200, "a real tier is accepted")
    check(gs.get_buzz_points(game) == 150, f"0.75 x 200 = {gs.get_buzz_points(game)}")
    check(gs.get_buzz_points(game) < game["currentWager"],
          "a buzz never out-earns the wager it was played for")
    check(BUZZ_WAGER_SHARE < 1, "the share is below 1 by design")
    check(WAGER_VALUES == [12, 25, 50, 100, 200], f"the ladder is the agreed one ({WAGER_VALUES})")

    # --- No locked answers, no dead air -------------------------------------
    print("\n--- No locked answers, no dead air ---")
    claude_client.__set_client_for_tests(FakeClient())
    game = registered_game()
    gs.start_game(game)
    to_active_window(game, wager=200)
    answerer = game["players"][game["answererIndex"]]
    answer(game, answerer["id"], "nope")
    check(game["phase"] == "ANSWER", "still open while locking is live")
    game["lockClosesAt"] = 0
    gs.expire_active_window(game)
    check(game["phase"] == "RESULT",
          "with nobody holding an answer the question ends instead of running the clock down")

    # --- First correct wins, decided by buzz order --------------------------
    print("\n--- Race resolution ---")
    fake = FakeClient(latency=0.06)
    claude_client.__set_client_for_tests(fake)
    game = registered_game()
    gs.start_game(game)
    to_active_window(game, wager=100)
    answerer = game["players"][game["answererIndex"]]
    first, second = [p for p in game["players"] if p["id"] != answerer["id"]]
    gs.lock_answer(game, first["id"], CORRECT_ANSWER, "text")
    gs.lock_answer(game, second["id"], CORRECT_ANSWER, "text")
    game["lockClosesAt"] = 0
    game["buzzOpensAt"] = 0

    # Claim in order (as main.py does under the game lock), then resolve on
    # real threads so both evaluations are genuinely in flight at once. The
    # ticket, not the API's response time, must decide this.
    a1 = gs.buzz_in(game, first["id"])
    a2 = gs.buzz_in(game, second["id"])
    threads = [
        threading.Thread(target=gs.resolve_answer_attempt, args=(game, a1[0], a1[1])),
        threading.Thread(target=gs.resolve_answer_attempt, args=(game, a2[0], a2[1])),
    ]
    # Start the LATER claim first, so a naive implementation that just races
    # threads would give the win to the wrong player.
    threads[1].start()
    time.sleep(0.01)
    threads[0].start()
    for t in threads:
        t.join()

    check(game["lastResult"]["winnerId"] == first["id"],
          f'the earlier buzz won even though its thread started second ({game["lastResult"]["winnerName"]})')
    check(second["score"] == 0, f'the later one was not also paid ({second["score"]})')
    check(first["score"] == 75, f'exactly one player was paid ({first["score"]})')

    # --- Per-round rules ----------------------------------------------------
    print("\n--- Round rules ---")
    claude_client.__set_client_for_tests(FakeClient())
    game = registered_game()
    gs.start_game(game)
    check(gs.current_round_number(game) == 1, "the game opens on round 1")
    check(game["roundRule"]["id"] == "none", f'round 1 has no rule (got {game["roundRule"]["id"]})')
    check(game["roundAnnouncement"]["round"] == 1, "round 1 is still announced")
    check(gs.player_view(game, "p1")["roundAnnouncement"] is not None,
          "and the announcement reaches clients")

    game["phase"] = "RESULT"
    game["lastResult"] = {"correct": True, "wager": 0}
    gs.next_turn(game)
    check(game["roundAnnouncement"] is None, "the announcement clears after one turn")
    check(game["roundRule"]["id"] == "none", "but the round rule stays put mid-round")

    while gs.current_round_number(game) == 1:
        game["phase"] = "RESULT"
        game["lastResult"] = {"correct": True, "wager": 0}
        gs.next_turn(game)
    check(gs.current_round_number(game) == 2, "round 2 begins after QUESTIONS_PER_ROUND questions")
    check(game["roundRule"]["id"] != "none", f'round 2 has a real rule ({game["roundRule"]["id"]})')
    check(game["roundRule"]["id"] in ROUND_RULES, "the announced rule is a real rule")

    claude_client.__set_client_for_tests(None)
    print("\n=== ALL PASSED ===" if failures == 0 else f"\n=== {failures} FAILED ===")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
