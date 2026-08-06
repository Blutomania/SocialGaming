# One-off integration test for the FastAPI port. Not a permanent pytest
# suite (none exists for the JS version either) — run manually with
# `python3 test_integration.py` to verify the full HTTP + WebSocket loop
# against real Claude API calls. Uses starlette's TestClient, which runs
# the app in-process (no separate server needed, and its WebSocket test
# client drives the same asyncio loop main.py's startup hook captures).

import json
import random
import threading
import time

from fastapi.testclient import TestClient

import main

client = TestClient(main.app)

PLAYERS = [("p1", "Alice"), ("p2", "Bob"), ("p3", "Cara")]


def post(path, **body):
    r = client.post(path, json=body)
    if r.status_code >= 400:
        raise RuntimeError(f"{path} -> {r.status_code}: {r.text}")
    return r.json()


def main_test():
    print("Creating game...")
    resp = post("/games/create", playerId="p1", name="Alice")
    code = resp["code"]
    print("code:", code)

    for pid, name in PLAYERS[1:]:
        post(f"/games/{code}/join", playerId=pid, name=name)

    for pid, name in PLAYERS:
        post(f"/games/{code}/register", playerId=pid,
             categories=["World Capitals"] * 5, pickedCardId="skip")

    game = main._games[code]
    assert main.gs.all_players_registered(game)
    print("all registered")

    print("Starting game (real fact-bank API call)...")
    post(f"/games/{code}/start", playerId="p1")
    print("phase after start:", game["phase"], "roundRule:", game["roundRule"]["name"])

    # Open a WebSocket for the active player and confirm it receives a
    # game:state push after the next mutation.
    ws_events = []
    with client.websocket_connect(f"/ws/{code}?player_id=p1") as ws:
        initial = json.loads(ws.receive_text())
        print("initial ws push event:", initial["event"], "phase:", initial["data"]["phase"])
        assert initial["event"] == "game:state"

        active_id = game["players"][game["activePlayerIndex"]]["id"]
        wager_id = main.gs.get_wager_player(game)["id"]
        category = game["categoryOptions"][0]["category"]

        print(f"active player picks category (as {active_id})...")
        post(f"/games/{code}/round/pick-category", playerId=active_id, category=category)
        push = json.loads(ws.receive_text())
        print("ws push after category pick:", push["data"]["phase"])
        assert push["data"]["phase"] == "WAGER"

        print(f"wager player sets wager (as {wager_id})...")
        post(f"/games/{code}/round/set-wager", playerId=wager_id, amount=250)
        push = json.loads(ws.receive_text())
        print("ws push after wager:", push["data"]["phase"])
        assert push["data"]["phase"] == "CARD"

    # Card window auto-resolves after CARD_WINDOW_SECONDS (8s) with no card
    # played -> triggers question generation (real API call) -> ANSWER.
    print("Waiting for card window to auto-resolve + question to generate (real API call)...")
    deadline = time.time() + 30
    while game["phase"] not in ("ANSWER", "RESULT") and time.time() < deadline:
        time.sleep(0.5)

    print("phase after card window:", game["phase"])
    assert game["phase"] == "ANSWER", f"expected ANSWER, got {game['phase']}"
    print("question:", game["currentQuestion"]["question"][:100])

    round_rule = game["roundRule"]
    if round_rule.get("lineupBased"):
        lineup = game["currentQuestion"]["lineup"]
        correct_id = lineup["correctOptionId"]
        wrong_id = next(o["id"] for o in lineup["options"] if o["id"] != correct_id)
        print("Lineup round — trying wrong option first...")
        r = post(f"/games/{code}/round/attempt-lineup", playerId="p2", optionId=wrong_id)
        assert r == {"correct": False}
        assert game["phase"] == "ANSWER"
        print("wrong tap correctly failed soft, phase still ANSWER")
        r2 = post(f"/games/{code}/round/attempt-lineup", playerId="p3", optionId=correct_id)
        assert r2 == {"correct": True}
        print("correct tap won, phase:", game["phase"], "p3 score:", next(p["score"] for p in game["players"] if p["id"] == "p3"))
    elif round_rule.get("submissionBased"):
        print("Worst Answer Wins round — all 3 players submit...")
        for pid, _ in PLAYERS:
            post(f"/games/{code}/round/submit-answer", playerId=pid, answer="a deliberately wrong answer", inputMode="text")
        deadline = time.time() + 30
        while game["phase"] not in ("RESULT",) and time.time() < deadline:
            time.sleep(0.5)
        print("phase after group eval:", game["phase"])
        assert game["phase"] == "RESULT"
        print("lastResult entries:", len(game["lastResult"]["entries"]))
    else:
        answerer_id = game["players"][game["answererIndex"]]["id"]
        correct_answer = game["currentQuestion"]["answer"]
        transformed = main.gs.transform_answer(round_rule, correct_answer, "text") if False else correct_answer
        # Apply the round rule's transform in reverse isn't needed for most
        # rules (identity) — for backItUp/oneWordOnly this simple test may
        # register as "wrong", which is fine: we're testing PHASE PLUMBING
        # (submit -> RESULT -> next turn), not per-rule answer correctness
        # (already verified separately for backItUp in this session).
        print(f"Standard round ({round_rule['name']}) — submitting answer as {answerer_id}...")
        post(f"/games/{code}/round/submit-answer", playerId=answerer_id, answer=correct_answer, inputMode="text")
        deadline = time.time() + 15
        while game["phase"] not in ("RESULT", "STEAL") and time.time() < deadline:
            time.sleep(0.5)
        print("phase after submit:", game["phase"])
        assert game["phase"] in ("RESULT", "STEAL")

    print("\n=== INTEGRATION TEST PASSED ===")


if __name__ == "__main__":
    main_test()
