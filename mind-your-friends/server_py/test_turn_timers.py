"""Turn-scoped timer guards — main.py's orchestration, not game_state's rules.

Costs ZERO API calls (a fake Anthropic client answers both call types) and
runs main.py's REAL threading.Timer callbacks in-process: _broadcast_sync
no-ops when no event loop has been captured, so no uvicorn is needed.

WHAT THIS PROTECTS. Every timer here is armed for one particular turn and
fires seconds later, by which time the turn it belongs to may be over. The
phase guard those callbacks have always had is not enough on its own, because
every turn walks the same phases: a timer left over from a question that was
answered early lands on the NEXT question, sitting in the same ANSWER phase,
and expires it. Found in the August 18 2026 playtest — a question three turns
in with an "ridiculously short" answer window. See MYF CLAUDE.md item 47.

The clock is shortened to 6s so this runs in ~40s rather than ~4 minutes.
Nothing else is faked.

Run: python3 test_turn_timers.py
"""

import json
import sys
import time

sys.path.insert(0, ".")

import claude_client
import game_state as gs
import main
from coherence_rules import round_constraints
from constants import CATEGORIES_PER_PLAYER, READING_SECONDS
from round_rules import NO_RULE

failures = 0
CORRECT_ANSWER = "Correct Answer"
CLOCK = 6      # stands in for BASE_TIMER_SECONDS (40) on the turn under test
LONG_CLOCK = 30  # a following turn whose own timers are far away
WAGER = 100


def window(clock):
    return READING_SECONDS + clock


def exclusive_end(clock):
    """When a turn's own exclusive window closes, measured from its start."""
    return READING_SECONDS + round(min(8, clock * 0.25))


def check(condition, description):
    global failures
    print(f"  {'PASS' if condition else 'FAIL'}  {description}")
    if not condition:
        failures += 1


class FakeResponse:
    def __init__(self, text):
        self.content = [type("Block", (), {"text": text})()]


class FakeMessages:
    def create(self, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        if prompt.startswith("You are an expert researcher"):
            names = prompt.split("\n")[0].split('"')[1::2]
            return FakeResponse(json.dumps({
                name: [{
                    "fact": f"Fact {i} about {name}",
                    "answer": CORRECT_ANSWER,
                    "bucket": (i % 5) + 1,
                    "difficulty": "easy",
                    "answerWordCount": 2,
                    "questionAngles": ["naming"],
                    "sourceType": "encyclopedia",
                } for i in range(10)]
                for name in names
            }))
        if prompt.startswith("Question:"):
            given = prompt.split("Player's answer: ")[1].split("\n")[0]
            expected = prompt.split("Expected answer: ")[1].split("\n")[0]
            return FakeResponse(json.dumps({
                "correct": given.strip().lower() == expected.strip().lower(),
                "feedback": f"You said {given}",
            }))
        return FakeResponse(json.dumps({
            "question": "Who did the thing in the place at the time?",
            "answer": CORRECT_ANSWER,
            "hostQuip": "Here we go.",
        }))


class FakeClient:
    def __init__(self):
        self.messages = FakeMessages()


def started_game():
    game = gs.create_game("p1", "Alice")
    gs.add_player(game, "p2", "Bob")
    gs.add_player(game, "p3", "Cara")
    for pid, name in (("p1", "Alice"), ("p2", "Bob"), ("p3", "Cara")):
        gs.register_player(
            game, pid,
            [f"{name} Cat {n + 1}" for n in range(CATEGORIES_PER_PLAYER)],
            "insurance",
        )
    gs.start_game(game)
    main._games[game["code"]] = game
    return game


def drive_to_answer(game, clock=CLOCK):
    """CATEGORY -> ANSWER, arming the real timers the way the real server does
    (via _finish_card_phase), on a shortened clock."""
    game["roundRule"] = dict(NO_RULE, timerSeconds=clock)
    game["roundConstraints"] = round_constraints(game["roundRule"])
    active = game["players"][game["activePlayerIndex"]]
    gs.pick_category(game, active["id"], game["categoryOptions"][0]["category"])
    setter = game["players"][(game["activePlayerIndex"] + 1) % len(game["players"])]
    gs.set_wager(game, setter["id"], WAGER)
    main._resolve_card_window(game["code"], game)
    game["answerOpensAt"] = 0  # reading window elapsed
    return time.time()


def answer_correctly(game):
    main.submit_answer_endpoint(game["code"], main.SubmitAnswerBody(
        playerId=game["players"][game["answererIndex"]]["id"],
        answer=CORRECT_ANSWER,
        inputMode="text",
    ))


def wait_for_phase(game, phase, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if game["phase"] == phase:
            return True
        time.sleep(0.05)
    return False


def main_test():
    claude_client.__set_client_for_tests(FakeClient())

    # --- A question answered early leaves its timers behind ----------------
    # Q1 is answered in its first two seconds, so BOTH of its ANSWER-phase
    # timers are still pending when Q2 opens. Pre-fix, Q1's exclusive-window
    # timer charged Q2's answerer for freezing on a question they had barely
    # seen (and locked them out of it), and Q1's answer timer then expired Q2
    # outright, at Q1's deadline rather than Q2's.
    #
    # Q2 runs on a long clock so its OWN timers are nowhere near the window
    # under test — anything that fires during it came from Q1.
    print("\n--- A finished turn's timers must not touch the next turn ---")
    game = started_game()

    q1_start = drive_to_answer(game)
    time.sleep(1.5)
    answer_correctly(game)
    check(game["phase"] == "RESULT", f'Q1 resolves early (phase={game["phase"]})')

    check(wait_for_phase(game, "CATEGORY"), "the turn advances to Q2")
    q2_answerer = game["players"][game["answererIndex"]]
    score_before = q2_answerer["score"]
    q2_start = drive_to_answer(game, LONG_CLOCK)
    q2_index = game["questionIndex"]

    # Sit past both of Q1's leftover deadlines, while Q2's own are still far off.
    stale_deadline = q1_start + window(CLOCK)
    check(
        stale_deadline < q2_start + exclusive_end(LONG_CLOCK),
        "the test window is valid: Q1's leftovers land inside Q2's exclusive window",
    )
    time.sleep(max(0, stale_deadline + 1 - time.time()))

    check(
        game["phase"] == "ANSWER" and game["questionIndex"] == q2_index,
        f'Q2 is still open after both of Q1\'s timers fired (phase={game["phase"]})',
    )
    check(
        q2_answerer["id"] not in game["answerAttempts"],
        "Q2's answerer has not been marked as having answered",
    )
    check(
        q2_answerer["score"] == score_before,
        f'Q2\'s answerer has not been charged ({score_before} -> {q2_answerer["score"]})',
    )
    check(
        q2_answerer["autoAdvanceCount"] == 0,
        "Q2's answerer has not been logged inactive for someone else's window",
    )

    # --- The guard must not stop a timer doing its own job ------------------
    # The obvious way to pass everything above is to make every timer a no-op.
    # A question nobody touches must still expire on ITS OWN deadline: with
    # nobody committed to buzz, that is the end of the exclusive window.
    print("\n--- A turn's own timers still fire ---")
    game = started_game()
    start = drive_to_answer(game)
    answerer = game["players"][game["answererIndex"]]

    while game["phase"] == "ANSWER" and time.time() - start < window(CLOCK) + 3:
        time.sleep(0.05)
    lived = time.time() - start
    expected = exclusive_end(CLOCK)
    check(
        abs(lived - expected) < 1.5,
        f"an untouched question expires on its own deadline ({lived:.1f}s, expected ~{expected}s)",
    )
    check(
        answerer["id"] in game["answerAttempts"],
        "freezing on your own question is still charged",
    )
    check(answerer["score"] == -WAGER, f'the charge is the wager (score {answerer["score"]})')
    check(wait_for_phase(game, "CATEGORY"), "and the turn still advances afterwards")

    claude_client.__set_client_for_tests(None)
    print("\n=== ALL PASSED ===" if failures == 0 else f"\n=== {failures} FAILED ===")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main_test()
