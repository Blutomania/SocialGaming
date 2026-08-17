# One-off integration test for the FastAPI port. Not a permanent pytest
# suite (none exists for the JS version either) — run manually with
# `python3 test_integration.py` against a real running uvicorn server
# (`python3 -m uvicorn main:app --port 8001`). Uses real HTTP + a real
# WebSocket client — TestClient's in-process lifespan semantics turned out
# not to reliably deliver the threading.Timer-originated broadcasts (the
# ones fired via _broadcast_sync from a background thread), so this tests
# against the real thing instead, which is also more representative of
# what the Godot client will actually talk to.

import json
import sys
import threading
import time

import requests
import websocket

sys.path.insert(0, ".")
from constants import READING_SECONDS

BASE = "http://localhost:8001"
WS_BASE = "ws://localhost:8001"

PLAYERS = [("p1", "Alice"), ("p2", "Bob"), ("p3", "Cara")]


def post(path, **body):
    r = requests.post(f"{BASE}{path}", json=body, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"{path} -> {r.status_code}: {r.text}")
    return r.json()


def post_expect_error(path, **body):
    """For the calls this suite asserts are REFUSED — a rejected buzz is the
    guarantee under test, not a failure."""
    r = requests.post(f"{BASE}{path}", json=body, timeout=30)
    return r.status_code >= 400


class WSListener:
    """Collects game:state pushes on a background thread so the main
    thread can just wait for the next one with a timeout."""

    def __init__(self, code, player_id):
        self.events = []
        self._lock = threading.Lock()
        self.ws = websocket.create_connection(f"{WS_BASE}/ws/{code}?player_id={player_id}", timeout=30)
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop:
            try:
                raw = self.ws.recv()
            except Exception:
                break
            if not raw:
                break
            with self._lock:
                self.events.append(json.loads(raw))

    def wait_for_phase(self, phase, timeout=40):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                for e in reversed(self.events):
                    if e["event"] == "game:state" and e["data"]["phase"] == phase:
                        return e["data"]
            time.sleep(0.3)
        raise TimeoutError(f"never saw phase={phase} within {timeout}s (last events: {[e['data'].get('phase') for e in self.events if e['event']=='game:state'][-5:]})")

    def close(self):
        self._stop = True
        try:
            self.ws.close()
        except Exception:
            pass


def run():
    print("Creating game...")
    resp = post("/games/create", playerId="p1", name="Alice")
    code = resp["code"]
    print("code:", code)

    for pid, name in PLAYERS[1:]:
        post(f"/games/{code}/join", playerId=pid, name=name)

    for pid, name in PLAYERS:
        post(f"/games/{code}/register", playerId=pid,
             categories=["World Capitals"] * 5, pickedCardId="skip")
    print("all registered")

    listener = WSListener(code, "p1")
    initial = listener.wait_for_phase("LOBBY", timeout=10)
    print("initial ws push OK, phase:", initial["phase"])

    print("Starting game (real fact-bank API call, can take ~20-90s)...")
    post(f"/games/{code}/start", playerId="p1")
    state = listener.wait_for_phase("CATEGORY", timeout=120)
    round_rule_name = state["roundRule"]["name"]
    print("phase after start: CATEGORY, roundRule:", round_rule_name)

    active_id = state["activePlayerIndex"]
    active_player_id = [p["id"] for p in state["players"]][active_id]
    wager_player_idx = (active_id + 1) % len(state["players"])
    wager_player_id = state["players"][wager_player_idx]["id"]
    category = state["categoryOptions"][0]["category"]

    print(f"active player ({active_player_id}) picks category...")
    post(f"/games/{code}/round/pick-category", playerId=active_player_id, category=category)
    state = listener.wait_for_phase("WAGER", timeout=15)
    print("phase: WAGER OK")

    print(f"wager player ({wager_player_id}) sets wager...")
    post(f"/games/{code}/round/set-wager", playerId=wager_player_id, amount=100)
    state = listener.wait_for_phase("CARD", timeout=15)
    print("phase: CARD OK")

    print("Waiting for card window (8s) to auto-resolve + question generation (real API call)...")
    state = listener.wait_for_phase("ANSWER", timeout=40)
    print("phase: ANSWER OK")
    print("question:", state["question"][:100])

    round_rule = state["roundRule"]
    if round_rule.get("lineupBased"):
        lineup = state["lineup"]
        options = lineup["options"]
        print(f"Lineup round, {len(options)} options — trying each until correct...")
        won = False
        for opt in options:
            r = requests.post(
                f"{BASE}/games/{code}/round/attempt-lineup",
                json={"playerId": "p2", "optionId": opt["id"]}, timeout=15,
            ).json()
            if r["correct"]:
                won = True
                break
        assert won, "no option registered as correct — bug"
        state = listener.wait_for_phase("RESULT", timeout=15)
        print("Lineup RESULT OK, lastResult:", state["lastResult"])
    elif round_rule.get("submissionBased"):
        print("Worst Answer Wins — all 3 players submit...")
        for pid, _ in PLAYERS:
            post(f"/games/{code}/round/submit-answer", playerId=pid, answer="a deliberately wrong answer", inputMode="text")
        state = listener.wait_for_phase("RESULT", timeout=30)
        print("Worst Answer Wins RESULT OK, entries:", len(state["lastResult"]["entries"]))
    else:
        answerer_idx = state["answererIndex"]
        answerer_id = state["players"][answerer_idx]["id"]
        others = [p["id"] for p in state["players"] if p["id"] != answerer_id]

        # Flow B. The room commits answers during the answerer's exclusive
        # window, the answerer fumbles, and a committed player buzzes in.
        # Sleeping past the reading window is the point, not incidental — the
        # server rejects everything before it, which is the guarantee.
        print(f"Standard round ({round_rule['name']}) — waiting out the reading window...")
        time.sleep(READING_SECONDS + 0.5)

        print(f"{others[0]} locks an answer in before the buzzer opens...")
        post(f"/games/{code}/round/lock-answer", playerId=others[0], answer="a committed answer", inputMode="text")

        print(f"{others[1]} tries to buzz during the exclusive window — should be refused...")
        refused = post_expect_error(f"/games/{code}/round/buzz-in", playerId=others[1])
        assert refused, "buzzing during the answerer's exclusive window must be rejected"

        print(f"answerer {answerer_id} passes...")
        post(f"/games/{code}/round/pass", playerId=answerer_id)

        print(f"{others[0]} buzzes in with their committed answer...")
        post(f"/games/{code}/round/buzz-in", playerId=others[0])
        state = listener.wait_for_phase("RESULT", timeout=25)
        result = state["lastResult"]
        print("RESULT OK:", result["activeOutcome"], result["winnerName"], result["points"])
        assert result["activeOutcome"] == "passed", f'expected a recorded fold, got {result["activeOutcome"]}'
        assert result["wagerLost"] is False, "a fold must not cost the wager"

    listener.close()
    print("\n=== INTEGRATION TEST PASSED ===")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"\n=== INTEGRATION TEST FAILED: {e} ===")
        sys.exit(1)
