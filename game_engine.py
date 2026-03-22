"""
game_engine.py — Turn action logic for the multiplayer investigation system.

All Claude calls are routed through a llm_fn callable so the engine can be
tested without hitting the API. The caller (cli.py) supplies llm_fn.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from game_session import (
    CapturedEntry,
    GameSession,
    PlayerNotebook,
    SharedEntry,
    advance_turn,
    get_current_player,
    get_player_by_id,
    save_game,
)


# ---------------------------------------------------------------------------
# Action resolution
# ---------------------------------------------------------------------------

def resolve_action(
    session: GameSession,
    player_id: str,
    action_type: str,
    target: str,
    question: Optional[str],
    llm_fn: Callable[[str], str],
    db_dir: str = "./mystery_database",
) -> Tuple[str, GameSession]:
    """
    Execute one player action. Returns (response_text, updated_session).
    Does NOT advance the turn — caller does that after sharing.

    action_type must be one of: "interrogate" | "investigate" | "follow_lead" | "accuse"
    """
    player = get_player_by_id(session, player_id)
    turn_number = session.current_turn_index + 1  # 1-indexed for display

    if action_type == "interrogate":
        response = _interrogate(session, target, question or "", llm_fn)
        entry = CapturedEntry(
            turn_number=turn_number,
            action_type="interrogate",
            target=target,
            question=question,
            response=response,
            shared=False,
        )
        player.entries.append(entry)
        save_game(session, db_dir)
        return response, session

    elif action_type == "investigate":
        response, session = _investigate(session, player, turn_number, db_dir)
        return response, session

    elif action_type == "follow_lead":
        response = _follow_lead(session, target, llm_fn)
        entry = CapturedEntry(
            turn_number=turn_number,
            action_type="follow_lead",
            target=target,
            question=None,
            response=response,
            shared=False,
        )
        player.entries.append(entry)
        save_game(session, db_dir)
        return response, session

    elif action_type == "accuse":
        response, session = _accuse(session, player, target, db_dir)
        return response, session

    else:
        raise ValueError(f"Unknown action_type: {action_type!r}")


# ---------------------------------------------------------------------------
# Individual action implementations
# ---------------------------------------------------------------------------

def _find_character(mystery: dict, name: str) -> Optional[dict]:
    """Find a character by name (case-insensitive partial match)."""
    name_lower = name.lower().strip()
    characters = mystery.get("characters", [])
    # Exact match first
    for c in characters:
        if c["name"].lower() == name_lower:
            return c
    # Partial match
    for c in characters:
        if name_lower in c["name"].lower():
            return c
    return None


def _find_evidence(mystery: dict, evidence_id: str) -> Optional[dict]:
    """Find an evidence item by id."""
    for e in mystery.get("evidence", []):
        if e["id"].upper() == evidence_id.upper():
            return e
    return None


def _interrogate(
    session: GameSession,
    character_name: str,
    question: str,
    llm_fn: Callable[[str], str],
) -> str:
    """Ask a character a question. Returns in-character response."""
    mystery = session.mystery
    character = _find_character(mystery, character_name)
    if character is None:
        return f"There is no one by the name {character_name!r} in this investigation."

    setting = mystery.get("setting", {})
    crime = mystery.get("crime", {})
    solution = mystery.get("solution", {})
    is_culprit = character["name"].lower() == solution.get("culprit", "").lower()

    prompt = f"""You are {character['name']}, a {character['role']} in this mystery.
Setting: {setting.get('location', '')} — {setting.get('time_period', '')}
Crime: {crime.get('type', '')} — {crime.get('what_happened', '')}

Your private details (do NOT reveal directly):
- Occupation: {character.get('occupation', '')}
- Alibi: {character.get('alibi', '')}
- Secret: {character.get('secret', '')}
- Motive: {character.get('motive', 'None')}

Behavioural instruction:
{'You are the culprit. Be evasive, deflect suspicion, and protect yourself — but do not lie so obviously that it is immediately clear. You may admit partial truths that redirect suspicion.' if is_culprit else 'You are NOT the culprit. Be defensive but cooperative. You may be hiding something (your secret) but you did not commit the crime. Respond truthfully about your alibi even if it makes you look suspicious.'}

A detective is questioning you. Stay completely in character as {character['name']}.
Do not break the fourth wall. Respond naturally as this person would speak.
Limit your response to 3–5 sentences.

Detective's question: {question}"""

    return llm_fn(prompt)


def _investigate(
    session: GameSession,
    player: PlayerNotebook,
    turn_number: int,
    db_dir: str,
) -> Tuple[str, GameSession]:
    """
    Reveal the next undiscovered evidence item from the pool.
    Zero Claude calls.
    """
    undiscovered = [
        eid for eid in session.evidence_pool
        if eid not in session.evidence_discovered
    ]
    if not undiscovered:
        response = (
            "You comb the scene carefully, but there is nothing more to find here. "
            "The crime scene has yielded all its physical secrets."
        )
        entry = CapturedEntry(
            turn_number=turn_number,
            action_type="investigate",
            target="crime_scene",
            question=None,
            response=response,
            shared=False,
        )
        player.entries.append(entry)
        save_game(session, db_dir)
        return response, session

    # Always reveal in pool order for reproducibility
    next_id = undiscovered[0]
    session.evidence_discovered.append(next_id)

    evidence = _find_evidence(session.mystery, next_id)
    if evidence:
        response = (
            f"[{evidence['id']}] {evidence['name']}\n"
            f"{evidence['description']}\n"
            f"Type: {evidence.get('type', 'unknown')}"
        )
    else:
        response = f"Evidence item {next_id} found but details unavailable."

    entry = CapturedEntry(
        turn_number=turn_number,
        action_type="investigate",
        target="crime_scene",
        question=None,
        response=response,
        shared=False,
    )
    player.entries.append(entry)
    save_game(session, db_dir)
    return response, session


def _follow_lead(
    session: GameSession,
    evidence_id: str,
    llm_fn: Callable[[str], str],
) -> str:
    """
    Dig deeper into a discovered evidence item. Requires one Claude call.
    """
    if evidence_id not in session.evidence_discovered:
        return (
            f"Evidence item {evidence_id!r} has not been discovered yet. "
            f"Investigate the crime scene first."
        )

    evidence = _find_evidence(session.mystery, evidence_id)
    if evidence is None:
        return f"No evidence item with id {evidence_id!r} exists in this mystery."

    mystery = session.mystery
    setting = mystery.get("setting", {})
    crime = mystery.get("crime", {})
    character_names = [c["name"] for c in mystery.get("characters", [])]

    prompt = f"""You are a veteran detective's analytical voice — third-person, clinical, observational.

Mystery context:
- Setting: {setting.get('location', '')} — {setting.get('time_period', '')}
- Crime: {crime.get('type', '')} — {crime.get('what_happened', '')}
- People present: {', '.join(character_names)}

Evidence item under investigation:
- ID: {evidence['id']}
- Name: {evidence['name']}
- Description: {evidence['description']}
- Type: {evidence.get('type', '')}

Provide 2–3 sentences of investigative analysis that goes beyond the surface description:
what physical or contextual details could be inferred, what questions it raises, or which
suspects it connects to — without naming the actual culprit or revealing the solution.
Do not start with "The" or repeat the evidence name verbatim."""

    return llm_fn(prompt)


def _accuse(
    session: GameSession,
    player: PlayerNotebook,
    suspect_name: str,
    db_dir: str,
) -> Tuple[str, GameSession]:
    """
    Make a final accusation. Correct: ends game. Wrong: logs and continues.
    Zero Claude calls.
    """
    solution = session.mystery.get("solution", {})
    culprit = solution.get("culprit", "").strip().lower()
    guess = suspect_name.strip().lower()

    player.accusations_made.append(suspect_name)

    if guess == culprit or culprit in guess or guess in culprit:
        session.winner = player.player_name
        session.phase = "finished"
        deduction = solution.get("how_to_deduce", "")
        response = (
            f"CORRECT! {player.player_name} has solved the case!\n\n"
            f"The culprit was {solution.get('culprit', suspect_name)}.\n"
            f"Method: {solution.get('method', '')}\n"
            f"Motive: {solution.get('motive', '')}\n\n"
            f"Deduction chain:\n{deduction}"
        )
        save_game(session, db_dir)
        return response, session
    else:
        response = (
            f"WRONG. {suspect_name} is not the culprit. "
            f"The investigation continues — {suspect_name} is cleared.\n"
            f"({player.player_name}'s turn ends.)"
        )
        save_game(session, db_dir)
        return response, session


# ---------------------------------------------------------------------------
# Sharing
# ---------------------------------------------------------------------------

def apply_sharing(
    session: GameSession,
    player_id: str,
    entry_indices: List[int],
    db_dir: str = "./mystery_database",
) -> GameSession:
    """
    Share selected entries from the player's notebook with all players.

    entry_indices: 0-based indices into player.entries for entries captured
    this turn. Caller is responsible for passing only current-turn indices.
    """
    player = get_player_by_id(session, player_id)

    for idx in entry_indices:
        if 0 <= idx < len(player.entries):
            entry = player.entries[idx]
            entry.shared = True
            shared = SharedEntry(
                contributed_by=player.player_name,
                turn_number=entry.turn_number,
                action_type=entry.action_type,
                target=entry.target,
                response=entry.response,
            )
            session.shared_pool.append(shared)

    save_game(session, db_dir)
    return session


# ---------------------------------------------------------------------------
# Display helpers (used by cli.py)
# ---------------------------------------------------------------------------

def format_shared_pool(session: GameSession) -> str:
    """Return a formatted string of all shared findings so far."""
    if not session.shared_pool:
        return "  (Nothing shared yet.)"
    lines = []
    for i, entry in enumerate(session.shared_pool, 1):
        action_label = {
            "interrogate": f"Interrogated {entry.target}",
            "investigate": "Crime scene investigation",
            "follow_lead": f"Followed lead on {entry.target}",
        }.get(entry.action_type, entry.action_type)
        lines.append(
            f"  [{i}] Turn {entry.turn_number} — {entry.contributed_by} — {action_label}"
        )
        for line in entry.response.split("\n"):
            lines.append(f"      {line}")
    return "\n".join(lines)


def format_player_stats(session: GameSession) -> str:
    """Return an ASCII player stats table for the end-game summary."""
    header = f"{'Name':<20} {'Actions':>8} {'Shared':>7} {'Withheld':>9}"
    separator = "-" * len(header)
    rows = [header, separator]
    for p in session.players:
        total = len(p.entries)
        shared = sum(1 for e in p.entries if e.shared)
        withheld = total - shared
        rows.append(f"{p.player_name:<20} {total:>8} {shared:>7} {withheld:>9}")
    return "\n".join(rows)


def build_end_summary(session: GameSession) -> dict:
    """
    Build a summary dict suitable for JSON export.
    Used as the Phase 2 social export data source.
    """
    mystery = session.mystery
    solution = mystery.get("solution", {})
    player_stats = []
    for p in session.players:
        total = len(p.entries)
        shared = sum(1 for e in p.entries if e.shared)
        player_stats.append({
            "name": p.player_name,
            "is_host": p.is_host,
            "actions_taken": total,
            "clues_shared": shared,
            "clues_withheld": total - shared,
            "correct_accusation": session.winner == p.player_name,
            "accusations_made": p.accusations_made,
            "avatar_url": p.avatar_url,  # Phase 2 hook
        })
    setting = mystery.get("setting", {})
    return {
        "game_code": session.game_code,
        "mystery_title": mystery.get("title", ""),
        "setting": f"{setting.get('location', '')} — {setting.get('time_period', '')}",
        "culprit": solution.get("culprit", ""),
        "method": solution.get("method", ""),
        "motive": solution.get("motive", ""),
        "winner": session.winner,
        "total_turns": session.current_turn_index + 1,
        "total_players": len(session.players),
        "player_stats": player_stats,
        "evidence_discovered": session.evidence_discovered,
        "evidence_pool_size": len(session.evidence_pool),
        "total_evidence": len(mystery.get("evidence", [])),
        "shared_pool_size": len(session.shared_pool),
        # Phase 2: social export fields (populated by social_export.py)
        "social_share_text": None,
        "whatsapp_link": None,
        "twitter_link": None,
    }
