# Mind Your Friends — FastAPI backend. Ported from server.js.
#
# All game logic lives in game_state.py — this file is the event hub: it
# validates the request, calls into game_state under _games_lock, and
# broadcasts the resulting state over WebSocket. The Godot client never
# calls the Claude API directly (same rule as CYM's server/main.py).
#
# Threading model (see docs/WIRING.md): FastAPI runs sync `def` endpoints in
# a thread pool automatically, so Claude-calling endpoints are plain `def`,
# not `async def`. A single process-wide `_games_lock` guards all game-dict
# mutation — coarser than per-game locking, but simple and correct for an
# MVP's expected concurrency; revisit if it becomes a bottleneck. Timers
# (card window, reading + exclusive windows, answer countdown, result-screen
# advance) use
# `threading.Timer`, matching server.js's `setTimeout` calls exactly —
# CYM's own lazy per-touch timeout checking doesn't fit here, since MYF's
# phases must advance even with zero client activity.

import asyncio
import json
import threading
import time

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import game_state as gs
from constants import RESULT_SCREEN_SECONDS

app = FastAPI(title="Mind Your Friends")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# code -> game dict (see game_state.create_game)
_games: dict[str, dict] = {}
_games_lock = threading.Lock()


# ---------------------------------------------------------------------------
# WebSocket connection manager — same shape as CYM's server/main.py
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self) -> None:
        # game code -> {player_id: WebSocket}
        self._rooms: dict[str, dict[str, WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, code: str, player_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms.setdefault(code, {})[player_id] = ws

    async def disconnect(self, code: str, player_id: str) -> None:
        async with self._lock:
            self._rooms.get(code, {}).pop(player_id, None)

    async def broadcast_state(self, code: str, game: dict) -> None:
        """Mirrors server.js's broadcast(): resend each connected player's
        own playerView() after every mutation."""
        async with self._lock:
            room = dict(self._rooms.get(code, {}))
        for player_id, ws in room.items():
            try:
                view = gs.player_view(game, player_id)
                await ws.send_text(json.dumps({"event": "game:state", "data": view}))
            except Exception:
                await self.disconnect(code, player_id)

_ws_manager = ConnectionManager()
_main_loop: asyncio.AbstractEventLoop | None = None


def _broadcast_sync(code: str, game: dict) -> None:
    """Fire-and-forget WebSocket broadcast from a synchronous context (a
    plain `def` endpoint, or a threading.Timer callback) — same bridge
    pattern as CYM's _broadcast_sync in server/main.py."""
    if _main_loop is None:
        return
    try:
        asyncio.run_coroutine_threadsafe(_ws_manager.broadcast_state(code, game), _main_loop)
    except RuntimeError:
        pass


@app.on_event("startup")
async def _capture_loop() -> None:
    global _main_loop
    _main_loop = asyncio.get_running_loop()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_game_or_404(code: str) -> dict:
    with _games_lock:
        game = _games.get(code)
    if not game:
        raise HTTPException(404, f"Game {code} not found")
    return game


def _apply_locked(code: str, game: dict, fn, *args, **kwargs):
    """Runs fn(game, *args, **kwargs) under _games_lock, broadcasts on
    success. Raises HTTPException(400) on GameError — matches server.js's
    withMyGame catch -> socket.emit('error', ...), but as a normal HTTP
    error response since this isn't a persistent socket."""
    with _games_lock:
        try:
            fn(game, *args, **kwargs)
        except gs.GameError as e:
            raise HTTPException(400, str(e))
    _broadcast_sync(code, game)


# CARD_WINDOW_SECONDS matches server.js's constant (not in constants.py —
# it's server-orchestration-only, same as the JS version keeping it in
# server.js rather than lib/constants.js).
CARD_WINDOW_SECONDS = 8


def _recover_from_failed_turn(code: str, game: dict, err: Exception) -> None:
    """If a Claude call in the turn pipeline throws, the turn would
    otherwise hang forever with no client feedback. Skip it and move on."""
    print(f"Turn failed for {code}, skipping:", err)
    with _games_lock:
        game["phase"] = "RESULT"
        game["skippedTurn"] = True
    _broadcast_sync(code, game)
    _schedule_next_turn(code, game)


def _start_card_window(code: str, game: dict) -> None:
    def fire():
        with _games_lock:
            if game["phase"] != "CARD":
                return  # already resolved by a card play
        _finish_card_phase(code, game)
    threading.Timer(CARD_WINDOW_SECONDS, fire).start()


def _resolve_card_window(code: str, game: dict) -> None:
    with _games_lock:
        if game["phase"] != "CARD":
            return
    _finish_card_phase(code, game)


def _finish_card_phase(code: str, game: dict) -> None:
    try:
        with _games_lock:
            gs.resolve_card_slot(game)
        _broadcast_sync(code, game)

        with _games_lock:
            phase = game["phase"]
        if phase == "RESULT":  # Skip card — turn ends with no question
            _schedule_next_turn(code, game)
            return

        # NOT under _games_lock: run_question_phase waits on the lazy fact
        # fetch and then makes a Claude call, and holding the lock across
        # either would freeze every other request in the room. The phase is
        # QUESTION for its duration, which is what keeps other actions out.
        gs.run_question_phase(game)
        _broadcast_sync(code, game)
        _start_active_window_timer(code, game)
        _start_answer_timer(code, game)
    except Exception as e:
        _recover_from_failed_turn(code, game, e)


def _start_answer_timer(code: str, game: dict) -> None:
    """One timer for the whole ANSWER phase. The reading window and the
    exclusive window are timestamps on the game, not phases of their own, so
    nothing else in this file's timer bookkeeping has to learn about them."""
    with _games_lock:
        seconds = gs.get_answer_window_seconds(game)

    def fire():
        with _games_lock:
            if game["phase"] != "ANSWER":
                return  # already resolved
            round_rule = game["roundRule"]
            if round_rule.get("submissionBased"):
                gs.auto_fill_missing_submissions(game)
            elif round_rule.get("lineupBased"):
                gs.expire_lineup(game)
            else:
                # Nobody got it in time. The answerer has normally been
                # settled with already — by their own answer or pass, or by
                # _start_active_window_timer charging them for freezing.
                gs.expire_answer_window(game)

        if round_rule.get("submissionBased"):
            _evaluate_group_answers(code, game)
            return

        _broadcast_sync(code, game)
        _schedule_next_turn(code, game)

    threading.Timer(seconds, fire).start()


def _start_active_window_timer(code: str, game: dict) -> None:
    """Flow B's exclusive window. A second timer inside the same ANSWER
    phase; expire_active_window no-ops if the answerer already acted, since
    answering or passing opened the buzzer then."""
    with _games_lock:
        if game["roundRule"].get("submissionBased") or game["roundRule"].get("lineupBased"):
            return
        seconds = gs.get_active_window_total_seconds(game)

    def fire():
        with _games_lock:
            if game["phase"] != "ANSWER":
                return
            answerer = game["players"][game["answererIndex"]]
            # Read before the call — expire_active_window writes the attempt.
            froze = answerer["id"] not in game["answerAttempts"] and not answerer["droppedOut"]
            if not gs.expire_active_window(game):
                return
            # Never acting on your own question is the inactivity signal, and
            # the answerer's own window closing is the exact moment it is
            # known. Passing is a real action, so a player who folds is not
            # marked away for it.
            if froze:
                gs.record_auto_advance(game, answerer["id"])
            phase = game["phase"]

        _broadcast_sync(code, game)
        # Locking also closes here, which can end the question outright when
        # nobody committed an answer to buzz with.
        if phase == "RESULT":
            _schedule_next_turn(code, game)

    threading.Timer(seconds, fire).start()


def _evaluate_group_answers(code: str, game: dict) -> None:
    """Worst Answer Wins (and future submission-based rules): flips to the
    transient EVALUATING phase synchronously first, so a submission landing
    at the exact instant the timer also fires can't trigger this twice."""
    try:
        with _games_lock:
            gs.begin_group_evaluation(game)
        _broadcast_sync(code, game)
        with _games_lock:
            gs.resolve_group_answers(game)
        _broadcast_sync(code, game)
        _schedule_next_turn(code, game)
    except Exception as e:
        _recover_from_failed_turn(code, game, e)


def _schedule_next_turn(code: str, game: dict) -> None:
    def fire():
        with _games_lock:
            if game["phase"] != "RESULT":
                return  # already advanced by another path
            gs.next_turn(game)
        _broadcast_sync(code, game)
    threading.Timer(RESULT_SCREEN_SECONDS, fire).start()


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

class CreateGameBody(BaseModel):
    playerId: str
    name: str


@app.post("/games/create")
def create_game_endpoint(body: CreateGameBody):
    with _games_lock:
        game = gs.create_game(body.playerId, body.name)
        attempts = 0
        while game["code"] in _games and attempts < 10:
            game = gs.create_game(body.playerId, body.name)
            attempts += 1
        if game["code"] in _games:
            raise HTTPException(500, "Could not generate a unique game code — try again")
        _games[game["code"]] = game
    return {"code": game["code"]}


class JoinGameBody(BaseModel):
    playerId: str
    name: str


@app.post("/games/{code}/join")
def join_game_endpoint(code: str, body: JoinGameBody):
    game = _get_game_or_404(code)
    _apply_locked(code, game, gs.add_player, body.playerId, body.name)
    return {"ok": True}


class RegisterBody(BaseModel):
    playerId: str
    categories: list[str]
    pickedCardId: str


@app.post("/games/{code}/register")
def register_endpoint(code: str, body: RegisterBody):
    game = _get_game_or_404(code)
    _apply_locked(code, game, gs.register_player, body.playerId, body.categories, body.pickedCardId)
    return {"ok": True}


class StartGameBody(BaseModel):
    playerId: str


@app.post("/games/{code}/start")
def start_game_endpoint(code: str, body: StartGameBody):
    """Instant now: no fact bank is built here. The bank fills in behind the
    game, so the room lands on the category screen immediately instead of
    watching a progress bar before anything has happened (CLAUDE.md item 36
    was about the ~250s version of this; item 37 note 3 removed it)."""
    game = _get_game_or_404(code)
    try:
        with _games_lock:
            gs.start_game(game)
    except gs.GameError as e:
        raise HTTPException(400, str(e))
    _broadcast_sync(code, game)
    # Fire-and-forget warm-up on its own thread; broadcasts as it progresses.
    gs.prefetch_fact_bank(game, lambda g: _broadcast_sync(code, g))
    return {"ok": True}


class PickCategoryBody(BaseModel):
    playerId: str
    category: str


@app.post("/games/{code}/round/pick-category")
def pick_category_endpoint(code: str, body: PickCategoryBody):
    game = _get_game_or_404(code)
    with _games_lock:
        gs.record_player_action(game, body.playerId)
        try:
            gs.pick_category(game, body.playerId, body.category)
        except gs.GameError as e:
            raise HTTPException(400, str(e))
    _broadcast_sync(code, game)

    # Start fetching this category's facts NOW rather than at question time:
    # the wager and card windows are about to run, which is free cover for the
    # round trip. run_question_phase waits on the same fetch, so this is a
    # head start, not a race. Off-thread — the lock must not be held across it.
    threading.Thread(
        target=gs.ensure_category_facts, args=(game, body.category), daemon=True
    ).start()
    return {"ok": True}


class SetWagerBody(BaseModel):
    playerId: str
    amount: float


@app.post("/games/{code}/round/set-wager")
def set_wager_endpoint(code: str, body: SetWagerBody):
    game = _get_game_or_404(code)
    with _games_lock:
        gs.record_player_action(game, body.playerId)
        try:
            gs.set_wager(game, body.playerId, body.amount)
        except gs.GameError as e:
            raise HTTPException(400, str(e))
    _broadcast_sync(code, game)
    _start_card_window(code, game)
    return {"ok": True}


class PlayCardBody(BaseModel):
    playerId: str
    cardId: str
    payload: dict | None = None


@app.post("/games/{code}/round/play-card")
def play_card_endpoint(code: str, body: PlayCardBody):
    game = _get_game_or_404(code)
    with _games_lock:
        gs.record_player_action(game, body.playerId)
        try:
            gs.play_card(game, body.playerId, body.cardId, body.payload)
        except gs.GameError as e:
            raise HTTPException(400, str(e))
    _broadcast_sync(code, game)
    _resolve_card_window(code, game)
    return {"ok": True}


class SubmitAnswerBody(BaseModel):
    playerId: str
    answer: str
    inputMode: str = "text"


@app.post("/games/{code}/round/submit-answer")
def submit_answer_endpoint(code: str, body: SubmitAnswerBody):
    """The answerer's live answer inside their own exclusive window.

    Claude-calling — plain `def`, so it runs in FastAPI's thread pool. Note
    the deliberate two-step: the attempt is CLAIMED under _games_lock (which
    fixes its place in the evaluation order) and then RESOLVED with the lock
    released, because the evaluation is an API call and holding the lock
    across it would freeze the whole room on every answer."""
    game = _get_game_or_404(code)
    with _games_lock:
        gs.record_player_action(game, body.playerId)
        submission_based = game["roundRule"].get("submissionBased")

    if submission_based:
        try:
            with _games_lock:
                all_in = gs.submit_group_answer(game, body.playerId, body.answer, body.inputMode)
        except gs.GameError as e:
            raise HTTPException(400, str(e))
        _broadcast_sync(code, game)
        if all_in:
            _evaluate_group_answers(code, game)
        return {"ok": True}

    try:
        with _games_lock:
            attempt = gs.submit_answer(game, body.playerId, body.answer, body.inputMode)
    except gs.GameError as e:
        raise HTTPException(400, str(e))

    # Buzzer is already open (submit_answer moved it), so tell the room before
    # spending the evaluation — that is seconds of shared clock.
    _broadcast_sync(code, game)
    try:
        gs.resolve_answer_attempt(game, attempt, body.inputMode, lock=_games_lock)
    except Exception as e:
        _recover_from_failed_turn(code, game, e)
        return {"ok": True}

    with _games_lock:
        phase = game["phase"]
    _broadcast_sync(code, game)
    if phase == "RESULT":
        _schedule_next_turn(code, game)
    return {"ok": True}


class LockAnswerBody(BaseModel):
    playerId: str
    answer: str
    inputMode: str = "text"


@app.post("/games/{code}/round/lock-answer")
def lock_answer_endpoint(code: str, body: LockAnswerBody):
    """Commit an answer during the answerer's exclusive window. Not evaluated
    and not revealed — it only becomes a real attempt if its owner buzzes."""
    game = _get_game_or_404(code)
    with _games_lock:
        gs.record_player_action(game, body.playerId)
    _apply_locked(code, game, gs.lock_answer, body.playerId, body.answer, body.inputMode)
    return {"ok": True}


class PlayerOnlyBody(BaseModel):
    playerId: str


@app.post("/games/{code}/round/buzz-in")
def buzz_in_endpoint(code: str, body: PlayerOnlyBody):
    """Play a committed answer. The buzz sets the order; the answer was fixed
    before the answerer fumbled. Same two-step lock discipline as
    submit-answer above."""
    game = _get_game_or_404(code)
    with _games_lock:
        gs.record_player_action(game, body.playerId)

    try:
        with _games_lock:
            attempt, input_mode = gs.buzz_in(game, body.playerId)
    except gs.GameError as e:
        raise HTTPException(400, str(e))

    try:
        gs.resolve_answer_attempt(game, attempt, input_mode, lock=_games_lock)
    except Exception as e:
        _recover_from_failed_turn(code, game, e)
        return {"ok": True}

    with _games_lock:
        phase = game["phase"]
    _broadcast_sync(code, game)
    if phase == "RESULT":
        _schedule_next_turn(code, game)
    return {"ok": True}


@app.post("/games/{code}/round/pass")
def pass_answer_endpoint(code: str, body: PlayerOnlyBody):
    """The answerer folds. Costs them nothing and opens the buzzer at once."""
    game = _get_game_or_404(code)
    with _games_lock:
        gs.record_player_action(game, body.playerId)
    _apply_locked(code, game, gs.pass_answer, body.playerId)
    return {"ok": True}


class AttemptLineupBody(BaseModel):
    playerId: str
    optionId: str


@app.post("/games/{code}/round/attempt-lineup")
def attempt_lineup_endpoint(code: str, body: AttemptLineupBody):
    """Wrong taps are NOT an HTTP error — see game_state.attempt_lineup_pick
    docstring. Only a genuinely invalid round (not lineupBased) raises."""
    game = _get_game_or_404(code)
    with _games_lock:
        gs.record_player_action(game, body.playerId)
        try:
            result = gs.attempt_lineup_pick(game, body.playerId, body.optionId)
        except gs.GameError as e:
            raise HTTPException(400, str(e))
    if result["correct"]:
        _broadcast_sync(code, game)
        _schedule_next_turn(code, game)
    return result


# ---------------------------------------------------------------------------
# WebSocket — push-only. All actions go through the REST endpoints above;
# this just delivers game:state / error events, matching ApiClient.gd's
# ws_event(event_name, data) signal contract from the CYM client.
# ---------------------------------------------------------------------------

@app.websocket("/ws/{code}")
async def ws_endpoint(ws: WebSocket, code: str, player_id: str = ""):
    game = _get_game_or_404(code)
    await _ws_manager.connect(code, player_id, ws)
    with _games_lock:
        view = gs.player_view(game, player_id)
    await ws.send_text(json.dumps({"event": "game:state", "data": view}))
    try:
        while True:
            await ws.receive_text()  # push-only; ignore any client sends
    except WebSocketDisconnect:
        await _ws_manager.disconnect(code, player_id)
        with _games_lock:
            gs.disconnect_player(game, player_id)
        _broadcast_sync(code, game)


@app.get("/health")
def health():
    return {"status": "ok", "games": len(_games)}
