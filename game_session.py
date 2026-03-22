"""
game_session.py — Multiplayer game session data models and file persistence.

Each active game is stored as mystery_database/games/<CODE>.json.
Game codes are 5-character uppercase alphanumeric strings (e.g. XK7F2).
"""

from __future__ import annotations

import json
import math
import os
import random
import string
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class CapturedEntry:
    """A single piece of data captured by a player during their turn."""
    turn_number: int
    action_type: str          # "interrogate" | "investigate" | "follow_lead"
    target: str               # character name, "crime_scene", or evidence id
    question: Optional[str]   # None for investigate actions
    response: str             # Claude response or formatted evidence description
    shared: bool = False      # True after player chooses to share this entry


@dataclass
class PlayerNotebook:
    """Per-player private investigation record."""
    player_id: str
    player_name: str
    is_host: bool
    entries: List[CapturedEntry] = field(default_factory=list)
    accusations_made: List[str] = field(default_factory=list)
    avatar_url: Optional[str] = None  # Phase 2: avatar support hook


@dataclass
class SharedEntry:
    """An investigation finding shared with all players."""
    contributed_by: str       # player_name
    turn_number: int
    action_type: str
    target: str
    response: str


@dataclass
class GameSession:
    """Top-level game state, serialised to mystery_database/games/<CODE>.json."""
    game_code: str
    mystery: dict
    mystery_file: str
    players: List[PlayerNotebook]
    turn_order: List[str]           # player_ids in rotation order
    current_turn_index: int
    phase: str                      # "lobby" | "playing" | "finished"
    evidence_pool: List[str]        # evidence IDs available to discover (75% of total)
    evidence_discovered: List[str]  # evidence IDs revealed via investigate actions
    shared_pool: List[SharedEntry]
    winner: Optional[str]           # player_name of winner, or None
    created_at: float
    last_updated: float


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _session_to_dict(session: GameSession) -> dict:
    return asdict(session)


def _session_from_dict(d: dict) -> GameSession:
    players = [
        PlayerNotebook(
            player_id=p["player_id"],
            player_name=p["player_name"],
            is_host=p["is_host"],
            entries=[CapturedEntry(**e) for e in p.get("entries", [])],
            accusations_made=p.get("accusations_made", []),
            avatar_url=p.get("avatar_url"),
        )
        for p in d["players"]
    ]
    shared_pool = [SharedEntry(**s) for s in d.get("shared_pool", [])]
    return GameSession(
        game_code=d["game_code"],
        mystery=d["mystery"],
        mystery_file=d["mystery_file"],
        players=players,
        turn_order=d["turn_order"],
        current_turn_index=d["current_turn_index"],
        phase=d["phase"],
        evidence_pool=d["evidence_pool"],
        evidence_discovered=d["evidence_discovered"],
        shared_pool=shared_pool,
        winner=d.get("winner"),
        created_at=d["created_at"],
        last_updated=d["last_updated"],
    )


# ---------------------------------------------------------------------------
# File persistence
# ---------------------------------------------------------------------------

def _games_dir(db_dir: str) -> Path:
    p = Path(db_dir) / "games"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _game_path(db_dir: str, game_code: str) -> Path:
    return _games_dir(db_dir) / f"{game_code}.json"


def save_game(session: GameSession, db_dir: str = "./mystery_database") -> None:
    """Atomically write game session to disk."""
    path = _game_path(db_dir, session.game_code)
    session.last_updated = time.time()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(_session_to_dict(session), indent=2))
    tmp.replace(path)


def load_game(game_code: str, db_dir: str = "./mystery_database") -> GameSession:
    """Load a game session from disk. Raises FileNotFoundError if not found."""
    path = _game_path(db_dir, game_code.upper())
    if not path.exists():
        raise FileNotFoundError(f"No game found with code {game_code.upper()!r}")
    return _session_from_dict(json.loads(path.read_text()))


# ---------------------------------------------------------------------------
# Game code generation
# ---------------------------------------------------------------------------

def generate_game_code(db_dir: str = "./mystery_database") -> str:
    """Generate a unique 5-character uppercase alphanumeric game code."""
    existing = {p.stem for p in _games_dir(db_dir).glob("?????.json")}
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(100):
        code = "".join(random.choices(alphabet, k=5))
        if code not in existing:
            return code
    raise RuntimeError("Could not generate a unique game code after 100 attempts")


# ---------------------------------------------------------------------------
# Evidence pool — 75% mechanic
# ---------------------------------------------------------------------------

def _build_evidence_pool(mystery: dict) -> List[str]:
    """
    Select 75% of evidence items for the game pool, guaranteeing at least one
    critical evidence item is always included.
    """
    all_evidence = mystery.get("evidence", [])
    if not all_evidence:
        return []

    all_ids = [e["id"] for e in all_evidence]
    critical_ids = [e["id"] for e in all_evidence if e.get("relevance") == "critical"]

    pool_size = math.ceil(len(all_ids) * 0.75)
    shuffled = all_ids[:]
    random.shuffle(shuffled)
    pool = set(shuffled[:pool_size])

    # Guarantee at least one critical item is always discoverable
    if critical_ids and not pool.intersection(critical_ids):
        pool.add(critical_ids[0])

    # Return in stable order matching original evidence list
    return [eid for eid in all_ids if eid in pool]


# ---------------------------------------------------------------------------
# Game lifecycle
# ---------------------------------------------------------------------------

def create_game(
    mystery_dict: dict,
    mystery_file: str,
    host_name: str,
    db_dir: str = "./mystery_database",
) -> GameSession:
    """
    Create a new game in lobby phase. Host is the first player.
    Returns the new GameSession (already saved to disk).
    """
    game_code = generate_game_code(db_dir)
    host_id = str(uuid.uuid4())
    host = PlayerNotebook(
        player_id=host_id,
        player_name=host_name,
        is_host=True,
    )
    evidence_pool = _build_evidence_pool(mystery_dict)
    now = time.time()
    session = GameSession(
        game_code=game_code,
        mystery=mystery_dict,
        mystery_file=mystery_file,
        players=[host],
        turn_order=[],
        current_turn_index=0,
        phase="lobby",
        evidence_pool=evidence_pool,
        evidence_discovered=[],
        shared_pool=[],
        winner=None,
        created_at=now,
        last_updated=now,
    )
    save_game(session, db_dir)
    return session


def join_game(
    game_code: str,
    player_name: str,
    db_dir: str = "./mystery_database",
) -> GameSession:
    """
    Add a player to an existing lobby. Raises ValueError if game is not in lobby phase
    or player name is already taken.
    """
    session = load_game(game_code, db_dir)
    if session.phase != "lobby":
        raise ValueError(f"Game {game_code} is already {session.phase}. Cannot join.")
    existing_names = {p.player_name.lower() for p in session.players}
    if player_name.lower() in existing_names:
        raise ValueError(f"Player name {player_name!r} is already taken in game {game_code}.")
    if len(session.players) >= 6:
        raise ValueError(f"Game {game_code} is full (6 players maximum).")
    new_player = PlayerNotebook(
        player_id=str(uuid.uuid4()),
        player_name=player_name,
        is_host=False,
    )
    session.players.append(new_player)
    save_game(session, db_dir)
    return session


def start_game(
    game_code: str,
    host_player_id: str,
    db_dir: str = "./mystery_database",
) -> GameSession:
    """
    Transition from lobby to playing. Only the host can start the game.
    Randomises turn order.
    """
    session = load_game(game_code, db_dir)
    if session.phase != "lobby":
        raise ValueError(f"Game {game_code} cannot be started: phase is {session.phase!r}.")
    host = next((p for p in session.players if p.player_id == host_player_id), None)
    if host is None or not host.is_host:
        raise ValueError("Only the host can start the game.")
    if len(session.players) < 1:
        raise ValueError("Need at least one player to start.")
    order = [p.player_id for p in session.players]
    random.shuffle(order)
    session.turn_order = order
    session.current_turn_index = 0
    session.phase = "playing"
    save_game(session, db_dir)
    return session


def get_current_player(session: GameSession) -> PlayerNotebook:
    """Return the PlayerNotebook for the player whose turn it is."""
    if not session.turn_order:
        raise ValueError("Game has not started — turn order is empty.")
    current_id = session.turn_order[session.current_turn_index % len(session.turn_order)]
    for p in session.players:
        if p.player_id == current_id:
            return p
    raise ValueError(f"Current player id {current_id!r} not found in players list.")


def advance_turn(session: GameSession, db_dir: str = "./mystery_database") -> GameSession:
    """Move to the next player's turn and save."""
    if not session.turn_order:
        raise ValueError("Cannot advance turn — game has not started.")
    session.current_turn_index = (session.current_turn_index + 1) % len(session.turn_order)
    save_game(session, db_dir)
    return session


def get_player_by_id(session: GameSession, player_id: str) -> PlayerNotebook:
    """Return the player with the given id, or raise ValueError."""
    for p in session.players:
        if p.player_id == player_id:
            return p
    raise ValueError(f"Player {player_id!r} not found in game {session.game_code}.")
