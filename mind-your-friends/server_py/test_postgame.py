"""Post-game: the question log and superlative voting (CLAUDE.md items 35, 46).

Python mirror of scripts/postgame-test.js, except that this one costs ZERO API
calls: a fake Anthropic client answers both superlative prompts, so the paths
the JS test cannot reach on demand — a failed generation, an empty one, Claude
echoing titles instead of ids — are asserted rather than hoped for.

Three parts:
  1. _log_question: every outcome shape, and that next_turn() is its funnel.
  2. Superlatives in game_state: claiming, voting, skipping, the tally.
  3. main.py's orchestration on a shortened clock: the last question's
     result timer opens voting, the vote endpoints close it, and a vote timer
     tallies for a room that never finishes.

Run: python3 test_postgame.py
"""

import json
import re
import sys
import threading
import time

sys.path.insert(0, ".")

import claude_client
import game_state as gs
import main
from constants import TOTAL_QUESTIONS
from round_rules import NO_RULE

failures = 0
AWARD_LINE = re.compile(r"^\[(\w+)\] ([^:]+):")


def check(condition, description):
    global failures
    print(f"  {'PASS' if condition else 'FAIL'}  {description}")
    if not condition:
        failures += 1


class FakeResponse:
    def __init__(self, text):
        self.content = [type("Block", (), {"text": text})()]


class FakeMessages:
    """Answers the two post-game prompts. `mode` switches how it misbehaves."""

    def __init__(self):
        self.mode = "ok"
        self.generate_calls = 0
        self.narrate_calls = 0
        self.latency = 0

    def create(self, **kwargs):
        prompt = kwargs["messages"][0]["content"]
        if self.latency:
            time.sleep(self.latency)

        if prompt.startswith("A group of friends just finished"):
            self.generate_calls += 1
            if self.mode == "generate_fails":
                raise RuntimeError("simulated API failure")
            if self.mode == "generate_empty":
                return FakeResponse("[]")
            return FakeResponse(json.dumps([
                {"id": "best_sabotage", "title": "Best Sabotage", "description": "The Skip that hurt"},
                {"id": "most_confident", "title": "Most Confident Wrong Answer", "description": "Venus"},
                {"id": "bad_title"},  # no title: must be filtered, or it draws an empty heading
            ]))

        if prompt.startswith("You are the AI host of a party trivia game announcing"):
            self.narrate_calls += 1
            if self.mode == "narrate_fails":
                raise RuntimeError("simulated API failure")
            # Award lines look like "[best_sabotage] Best Sabotage: Marcus (2 vote(s))".
            # The prompt's JSON example also starts with "[", so match the shape.
            awards = [m.groups() for m in (AWARD_LINE.match(l) for l in prompt.splitlines()) if m]
            ids = [award_id for award_id, _ in awards]
            if self.mode == "narrate_titles":
                # The item-35 bug: Claude echoes the award TITLE, not the id.
                titles = [title for _, title in awards]
                return FakeResponse(json.dumps([{"id": t, "quip": f"Quip for {t}"} for t in titles]))
            if self.mode == "narrate_garbage_ids":
                return FakeResponse(json.dumps([{"id": f"zzz{i}", "quip": f"Quip {i}"} for i in range(len(ids))]))
            return FakeResponse(json.dumps([{"id": i, "quip": f"Quip for {i}"} for i in ids]))

        raise AssertionError(f"unexpected prompt: {prompt[:60]}")


class FakeClient:
    def __init__(self):
        self.messages = FakeMessages()


def new_game():
    game = gs.create_game("p1", "Priya")
    gs.add_player(game, "p2", "Marcus")
    gs.add_player(game, "p3", "Cara")
    game["questionIndex"] = 0
    game["currentQuestion"] = {"question": "Which planet spins backwards?", "answer": "Venus", "hostQuip": "Priya, look up."}
    game["currentCategory"] = "Space"
    game["currentCategoryAttribution"] = {"submittedBy": "Marcus"}
    game["currentWager"] = 50
    game["answererIndex"] = 0
    game["roundRule"] = dict(NO_RULE)
    game["phase"] = "RESULT"
    return game


def logged(game, last_result, rule=None, skipped=False):
    if rule:
        game["roundRule"] = rule
    game["lastResult"] = last_result
    game["skippedTurn"] = skipped
    gs._log_question(game)
    return game["questionLog"][-1] if game["questionLog"] else None


def game_over_game():
    game = new_game()
    game["phase"] = "GAME_OVER"
    return game


def vote_all(game, target="p2"):
    for voter in ("p1", "p2", "p3"):
        for c in game["postGame"]["categories"]:
            gs.cast_superlative_vote(game, voter, c["id"], target)


def main_test():
    fake = FakeClient()
    claude_client.__set_client_for_tests(fake)

    # ------------------------------------------------------------------
    print("\n1. The question log")

    entry = logged(new_game(), {"correct": True, "playerAnswer": "Venus"})
    check(entry["outcome"] == "correct", "a correct answer logs outcome 'correct'")
    check(entry["roomMissedIt"] is False, "and the room did not miss it")
    check(entry["answer"] == "Venus" and entry["playerAnswer"] == "Venus", "question, answer and what was said are kept")
    check(entry["categoryAttribution"] == "Marcus", "the category keeps its attribution")

    entry = logged(new_game(), {"correct": False, "activeOutcome": "wrong"})
    check(entry["outcome"] == "wrong" and entry["roomMissedIt"] is True, "nobody got it -> 'wrong', room missed it")
    check(entry["outcomeSummary"] == "Nobody got this one past Priya.", "and the summary says so")

    for active, phrase in (("passed", "passed and"), ("wrong", "got it wrong and"), ("timedOut", "froze and")):
        entry = logged(new_game(), {"correct": True, "buzzedIn": True, "winnerName": "Cara", "activeOutcome": active})
        check(entry["outcome"] == "buzzed" and phrase in entry["outcomeSummary"],
              f"a buzz-in after the answerer {active} reads '{phrase}'")
    check(entry["roomMissedIt"] is False, "a buzz-in win is not a room miss")

    entry = logged(new_game(), {"correct": False, "activeOutcome": "passed"})
    check(entry["outcome"] == "passed" and entry["roomMissedIt"] is True, "a pass nobody took -> 'passed', room missed it")

    entry = logged(new_game(), {"submissionBased": True}, rule={"id": "worstAnswerWins", "submissionBased": True})
    check(entry["outcome"] == "group", "Worst Answer Wins logs 'group'")

    lineup_game = new_game()
    lineup_game["currentQuestion"]["lineup"] = {"options": [{"id": "a"}, {"id": "b"}], "correctOptionId": "b"}
    entry = logged(lineup_game, {"lineupWinner": True, "winnerName": "Cara"}, rule={"id": "theLineup", "lineupBased": True})
    check(entry["outcome"] == "spotted" and entry["lineup"]["correctOptionId"] == "b", "a Lineup win logs 'spotted' with its lineup")
    entry = logged(lineup_game, {"lineupWinner": False}, rule={"id": "theLineup", "lineupBased": True})
    check(entry["outcome"] == "unclaimed" and entry["roomMissedIt"] is True, "a Lineup expiry logs 'unclaimed'")

    skipped = new_game()
    logged(skipped, {}, skipped=True)
    check(skipped["questionLog"] == [], "a skipped turn logs nothing")

    # The funnel: next_turn() must log, or every resolution path needs to.
    funnel = new_game()
    funnel["questionIndex"] = TOTAL_QUESTIONS - 1
    funnel["lastResult"] = {"correct": True}
    gs.next_turn(funnel)
    check(funnel["phase"] == "GAME_OVER", "the last next_turn() ends the game")
    check(len(funnel["questionLog"]) == 1, "and logs the question that just resolved")

    # The leak guard: every correct answer is in this log.
    mid = new_game()
    logged(mid, {"correct": True})
    mid["phase"] = "CATEGORY"
    check("questionLog" not in gs.player_view(mid, "p2"), "questionLog is NOT sent mid-game")
    mid["phase"] = "GAME_OVER"
    check(gs.player_view(mid, "p2").get("questionLog") == mid["questionLog"], "questionLog IS sent at GAME_OVER")

    # ------------------------------------------------------------------
    print("\n2. Superlatives")

    game = game_over_game()
    threw = None
    try:
        g = new_game()
        gs.begin_superlative_voting(g)
    except gs.GameError as e:
        threw = e
    check(threw is not None, "voting cannot open before GAME_OVER")

    opened = gs.begin_superlative_voting(game)
    check(opened and game["postGame"]["stage"] == "voting", "voting opens at GAME_OVER")
    check([c["id"] for c in game["postGame"]["categories"]] == ["best_sabotage", "most_confident"],
          "a category with no title is dropped")
    check(gs.begin_superlative_voting(game) is False and fake.messages.generate_calls == 1,
          "a second call does not generate again")

    # Two callers at once: the claim is made under the lock before the API
    # call, so exactly one of them generates.
    race = game_over_game()
    lock = threading.Lock()
    fake.messages.latency = 0.2
    before = fake.messages.generate_calls
    results = []
    threads = [threading.Thread(target=lambda: results.append(gs.begin_superlative_voting(race, lock=lock))) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    fake.messages.latency = 0
    check(fake.messages.generate_calls - before == 1, "two simultaneous starts generate once")
    check(sorted(results) == [False, True], "and exactly one of them reports it opened voting")

    for mode, label in (("generate_empty", "an empty set"), ("generate_fails", "a failed call")):
        fake.messages.mode = mode
        g = game_over_game()
        check(gs.begin_superlative_voting(g) is False and g["postGame"] is None,
              f"{label} clears postGame, leaving the plain scoreboard")
    fake.messages.mode = "ok"

    view = gs.player_view(game, "p2")["postGame"]
    check(view["stage"] == "voting" and view["myVotes"] == {} and view["results"] is None,
          "the view opens with no ballot and no results")

    for bad, label in ((("p1", "nope", "p2"), "an unknown category"), (("p1", "best_sabotage", "stranger"), "a non-player")):
        threw = None
        try:
            gs.cast_superlative_vote(game, *bad)
        except gs.GameError as e:
            threw = e
        check(threw is not None, f"a vote for {label} is rejected")

    gs.cast_superlative_vote(game, "p1", "best_sabotage", "p1")
    check(game["postGame"]["votes"]["p1"]["best_sabotage"] == "p1", "voting for yourself is allowed")
    check(gs.player_view(game, "p2")["postGame"]["myVotes"] == {}, "nobody sees another player's ballot")
    check(not gs.all_superlative_votes_in(game), "voting is not complete after one vote")

    gs.skip_superlative_voting(game, "p1")
    check(game["postGame"]["votes"]["p1"] == {"best_sabotage": "p1", "most_confident": gs.SKIPPED_VOTE},
          "Skip all keeps a cast vote and abstains from the rest")

    gs.cast_superlative_vote(game, "p2", "best_sabotage", "p1")
    gs.cast_superlative_vote(game, "p2", "most_confident", "p3")
    check(not gs.all_superlative_votes_in(game), "not complete while Cara is still here and hasn't voted")
    gs.disconnect_player(game, "p3")
    check(gs.all_superlative_votes_in(game), "Cara leaving completes the ballot")
    check(not any("waiting for reconnect" in h for h in game["highlightReel"]),
          "leaving after the game does not claim anyone is waiting")

    tallied_seen = []
    gs.resolve_superlatives(
        game, on_tallied=lambda: tallied_seen.append(
            [r["quip"] for r in game["postGame"]["results"]]))
    results = {r["id"]: r for r in game["postGame"]["results"]}
    check(game["postGame"]["stage"] == "results", "the stage moves to results")
    check(results["best_sabotage"]["winnerNames"] == ["Priya"] and results["best_sabotage"]["voteCount"] == 2,
          "the tally names the winner and counts their votes")
    check(results["most_confident"]["winnerNames"] == ["Cara"], "an abstention is not a candidate")
    check(tallied_seen == [[None, None]], "the tallies are published before the quips exist")
    check(results["best_sabotage"]["quip"] == "Quip for best_sabotage", "then the quips arrive, matched by id")

    narrate_before = fake.messages.narrate_calls
    gs.resolve_superlatives(game)
    check(fake.messages.narrate_calls == narrate_before, "resolving twice does nothing the second time")

    tie = game_over_game()
    gs.begin_superlative_voting(tie)
    for voter, target in (("p1", "p2"), ("p2", "p3"), ("p3", gs.SKIPPED_VOTE)):
        for c in tie["postGame"]["categories"]:
            gs.cast_superlative_vote(tie, voter, c["id"], target)
    gs.resolve_superlatives(tie)
    check(sorted(tie["postGame"]["results"][0]["winnerNames"]) == ["Cara", "Marcus"], "a tied award is a shared win")

    for mode, label in (("narrate_titles", "titles instead of ids"), ("narrate_garbage_ids", "ids that match nothing")):
        fake.messages.mode = mode
        g = game_over_game()
        gs.begin_superlative_voting(g)
        vote_all(g)
        gs.resolve_superlatives(g)
        check(all(r["quip"] for r in g["postGame"]["results"]), f"quips survive Claude returning {label}")
    fake.messages.mode = "narrate_fails"
    g = game_over_game()
    gs.begin_superlative_voting(g)
    vote_all(g)
    gs.resolve_superlatives(g)
    check(g["postGame"]["stage"] == "results" and g["postGame"]["results"][0]["winnerNames"] == ["Marcus"],
          "a failed narration still leaves correct results")
    fake.messages.mode = "ok"

    nobody = game_over_game()
    gs.begin_superlative_voting(nobody)
    for voter in ("p1", "p2", "p3"):
        gs.skip_superlative_voting(nobody, voter)
    narrate_before = fake.messages.narrate_calls
    gs.resolve_superlatives(nobody)
    check(all(not r["winnerNames"] for r in nobody["postGame"]["results"]), "if everyone skips, nobody wins")
    check(fake.messages.narrate_calls == narrate_before, "and no narration call is spent on it")

    # ------------------------------------------------------------------
    print("\n3. main.py orchestration (shortened clock)")

    main.RESULT_SCREEN_SECONDS = 0.1
    main.POST_GAME_VOTE_SECONDS = 0.6

    def finished_room(code):
        g = new_game()
        g["code"] = code
        g["questionIndex"] = TOTAL_QUESTIONS - 1
        g["lastResult"] = {"correct": True}
        main._games[code] = g
        return g

    g = finished_room("ENDA")
    main._schedule_next_turn("ENDA", g)
    time.sleep(0.4)
    check(g["phase"] == "GAME_OVER" and len(g["questionLog"]) == 1, "the last result timer ends the game and logs it")
    check(g["postGame"] and g["postGame"]["stage"] == "voting", "and opens superlative voting by itself")

    for voter in ("p1", "p2"):
        for c in g["postGame"]["categories"]:
            main.postgame_vote_endpoint("ENDA", main.SuperlativeVoteBody(playerId=voter, categoryId=c["id"], targetPlayerId="p3"))
    check(g["postGame"]["stage"] == "voting", "voting stays open while a player is still voting")
    main.postgame_skip_endpoint("ENDA", main.PlayerOnlyBody(playerId="p3"))
    check(g["postGame"]["stage"] == "results", "the last ballot closes voting at once")
    check(g["postGame"]["results"][0]["winnerNames"] == ["Cara"], "with the right winner")

    rejected = None
    try:
        main.postgame_vote_endpoint("ENDA", main.SuperlativeVoteBody(playerId="p1", categoryId="best_sabotage", targetPlayerId="p2"))
    except main.HTTPException as e:
        rejected = e.status_code
    check(rejected == 400, "a vote after voting closed is a 400, not a crash")

    g = finished_room("ENDB")
    main._schedule_next_turn("ENDB", g)
    time.sleep(0.4)
    main.postgame_skip_endpoint("ENDB", main.PlayerOnlyBody(playerId="p1"))
    check(g["postGame"]["stage"] == "voting", "a room that never finishes voting stays open...")
    time.sleep(0.8)
    check(g["postGame"]["stage"] == "results", "...until the vote timer tallies what came in")

    claude_client.__set_client_for_tests(None)
    print("\n=== ALL PASSED ===" if failures == 0 else f"\n=== {failures} FAILED ===")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main_test()
