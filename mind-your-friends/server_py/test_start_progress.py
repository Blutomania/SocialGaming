# Focused test for the game-start progress state and the concurrent
# fact-bank build (CLAUDE.md item 36) — the Python mirror of
# scripts/start-progress-test.js, asserting the same guarantees against
# server_py so the two backends can't drift.
#
# Costs ZERO API calls: it swaps a fake client into claude_client._client
# with controllable latency, which is the only way to assert the two things
# that actually matter — that the batches run concurrently rather than in
# sequence, and that a progress state reaches player_view() while the build
# is still running rather than only after it finishes.
#
# Unlike test_integration.py this needs no running server: it drives
# game_state directly.
#
# Run: python3 test_start_progress.py

import json
import re
import sys
import threading
import time

import claude_client
import game_state as gs
from constants import CATEGORIES_PER_FETCH_BATCH

failures = 0


def check(condition: bool, description: str) -> None:
    global failures
    print(f"  {'PASS' if condition else 'FAIL'}  {description}")
    if not condition:
        failures += 1


BATCH_LATENCY = 0.2


class FakeMessages:
    """Stands in for anthropic.messages: same create() shape, a fixed delay
    per call, and a reply built from whichever categories the prompt mentions
    so the merge behaviour is real rather than stubbed."""

    def __init__(self, latency: float, fail_on_call: int) -> None:
        self.latency = latency
        self.fail_on_call = fail_on_call
        self.calls = 0
        self.in_flight = 0
        self.concurrent_peak = 0
        self._lock = threading.Lock()

    def create(self, *, model, max_tokens, messages):
        with self._lock:
            self.calls += 1
            this_call = self.calls
            self.in_flight += 1
            self.concurrent_peak = max(self.concurrent_peak, self.in_flight)
        time.sleep(self.latency)
        with self._lock:
            self.in_flight -= 1
        if self.fail_on_call == this_call:
            raise RuntimeError("simulated batch failure")

        prompt = messages[0]["content"]
        header = prompt.split("\n")[0]
        names = re.findall(r'"([^"]+)"', header)
        out = {
            name: [{
                "fact": f"A fact about {name}",
                "answer": name,
                "bucket": 1,
                "difficulty": "easy",
                "answerWordCount": 1,
                "questionAngles": ["naming"],
                "sourceType": "encyclopedia",
            }]
            for name in names
        }
        return type("Reply", (), {"content": [type("Block", (), {"text": json.dumps(out)})()]})()


class FakeClient:
    def __init__(self, latency: float = BATCH_LATENCY, fail_on_call: int = 0) -> None:
        self.messages = FakeMessages(latency, fail_on_call)


def install_fake(**kwargs) -> FakeClient:
    fake = FakeClient(**kwargs)
    claude_client._client = fake
    return fake


# 3 players x 5 categories = 15 unique categories = 5 batches, the exact
# shape CLAUDE.md item 36 measured at 250s.
EXPECTED_BATCHES = -(-15 // CATEGORIES_PER_FETCH_BATCH)


def registered_game() -> dict:
    game = gs.create_game("p1", "Alice")
    gs.add_player(game, "p2", "Bob")
    gs.add_player(game, "p3", "Cara")
    for pid, prefix, card in (("p1", "Alice", "insurance"), ("p2", "Bob", "insurance"), ("p3", "Cara", "skip")):
        gs.register_player(game, pid, [f"{prefix} Category {n}" for n in range(1, 6)], card)
    return game


def run() -> int:
    real_client = claude_client._client

    try:
        # --- Part 1: the batches run concurrently ---------------------------
        print("\n--- Concurrent fact-bank build ---")
        fake = install_fake()
        game = registered_game()

        started = time.time()
        gs.start_game(game)
        elapsed = time.time() - started

        check(fake.messages.calls == EXPECTED_BATCHES,
              f"15 categories became {EXPECTED_BATCHES} batches (got {fake.messages.calls})")
        check(fake.messages.concurrent_peak == EXPECTED_BATCHES,
              f"all {EXPECTED_BATCHES} batches were in flight at once (peak {fake.messages.concurrent_peak})")
        # Sequential would be 5 x 0.2s = 1.0s+; concurrent is one batch's
        # latency plus overhead. The gap is wide enough that a slow machine
        # can't produce a false pass.
        check(elapsed < BATCH_LATENCY * 2.5,
              f"finished in one batch's latency, not five ({elapsed:.2f}s, sequential would be ~{BATCH_LATENCY * EXPECTED_BATCHES:.1f}s)")
        check(len(game["factBank"]) == 15,
              f"fact bank merged all 15 categories (got {len(game['factBank'])})")
        check(game["phase"] == "CATEGORY", f"phase advanced to CATEGORY (got {game['phase']})")

        # --- Part 2: progress reaches clients during the build -------------
        print("\n--- Progress state ---")
        fake = install_fake()
        game = registered_game()

        pushes = []
        first_push_in_flight = []

        def on_update(g):
            # Record what a client would actually receive, not the raw game
            # dict. Called from worker threads once batches start landing,
            # hence the plain list append (GIL-atomic) rather than a lock.
            pushes.append(gs.player_view(g, "p1")["startProgress"])
            first_push_in_flight.append(fake.messages.in_flight)

        gs.start_game(game, on_update)

        # 1 initial + 1 for the (0, total) report + one per completed batch.
        check(len(pushes) == EXPECTED_BATCHES + 2,
              f"one push per batch plus the two openers (got {len(pushes)})")
        check(pushes[0] is not None and pushes[0]["active"] is True,
              "the first push has active: True")
        check(bool(pushes[0]["label"]), f"the first push carries a label (got \"{pushes[0]['label']}\")")
        # The two opening pushes go out before any request has been dispatched
        # — the client is told the build has begun immediately, not ~50s later.
        check(first_push_in_flight[0] == 0,
              f"the opening push happened before any batch was dispatched (in flight: {first_push_in_flight[0]})")
        check(pushes[1]["total"] == EXPECTED_BATCHES,
              f"the client learns the batch count up front (total={pushes[1]['total']})")
        completions = [p["completed"] for p in pushes]
        check(max(completions) == EXPECTED_BATCHES,
              f"progress reached {EXPECTED_BATCHES}/{EXPECTED_BATCHES} (got {max(completions)})")
        check(all(p["active"] is True for p in pushes),
              "every push during the build is active — the clearing push comes from main.py, not start_game")
        check(game["startProgress"] is None, "startProgress is cleared once the game starts")
        check(gs.player_view(game, "p1")["startProgress"] is None,
              "player_view reports startProgress: None after the build")

        # --- Part 3: a failed build clears the progress state --------------
        print("\n--- Failure path ---")
        install_fake(fail_on_call=2)
        game = registered_game()
        threw = None
        try:
            gs.start_game(game, lambda g: None)
        except Exception as e:  # noqa: BLE001
            threw = e
        check(threw is not None, "a failing batch still raises out of start_game")
        check(game["startProgress"] is None,
              "startProgress is cleared on failure — the lobby must not freeze on a bar that never advances")
        check(game["phase"] == "LOBBY", f"phase stayed LOBBY on failure (got {game['phase']})")

        # --- Part 4: progress never set by a rejected precondition ---------
        print("\n--- Precondition guard ---")
        install_fake()
        game = gs.create_game("p1", "Alice")
        gs.add_player(game, "p2", "Bob")
        threw = None
        try:
            gs.start_game(game, lambda g: None)
        except gs.GameError as e:
            threw = e
        check(threw is not None, "starting with unregistered players still raises")
        check(game["startProgress"] is None,
              "the registration check runs before any progress state is set")

        # --- Part 5: parity with the JS view shape -------------------------
        print("\n--- Cross-backend parity ---")
        install_fake()
        game = registered_game()
        keys = []
        gs.start_game(game, lambda g: keys.append(sorted(g["startProgress"].keys())))
        check(all(k == ["active", "completed", "label", "total"] for k in keys),
              "startProgress carries the same four keys lib/gameState.js sends")

    finally:
        claude_client._client = real_client

    print("\n=== ALL PASSED ===" if failures == 0 else f"\n=== {failures} FAILED ===")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
