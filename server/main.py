"""
Choose Your Mystery — FastAPI Backend
======================================
Thin server that wraps the existing Python generation/interrogation/coherence
logic and exposes it over HTTP for the Godot client.

All Claude API calls happen here. The Godot client never touches the API key.

Endpoints:
  POST /generate          — generate a new mystery from a prompt
  POST /interrogate       — ask a character a question (in-character reply)
  POST /rate              — save a viability rating for a mystery
  GET  /mysteries         — list saved mysteries
  GET  /mysteries/{slug}  — load a saved mystery by slug

Run locally:
  cd /path/to/SocialGaming
  uvicorn server.main:app --reload --port 8000

SESSION ANNOTATION — Phase 1 complete when:
  curl -X POST localhost:8000/generate \
       -H "Content-Type: application/json" \
       -d '{"prompt":"a murder on a train","cinematic_brief":false}'
  returns a valid mystery JSON with _provenance and _coherence fields.
"""

import asyncio
import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from anthropic import Anthropic

# ---------------------------------------------------------------------------
# Path setup — when running as `uvicorn server.main:app` from project root,
# the repo root is already on sys.path. When running from inside server/,
# we add the parent directory so the backend modules are importable.
# ---------------------------------------------------------------------------
_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from part_registry import load_registry, PART_TYPE_NAMES  # noqa: E402
from coherence_validator import check_mystery               # noqa: E402
from localization import (                                  # noqa: E402
    localize_mystery as _localize_mystery,
    _is_modern,
    _era_key,
    _load_era_rules,
)

# ---------------------------------------------------------------------------
# API client — auth priority: env var → session ingress token
# ---------------------------------------------------------------------------
def _get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    token_path = Path("/home/claude/.claude/remote/.session_ingress_token")
    if token_path.exists():
        return token_path.read_text().strip()
    raise RuntimeError(
        "ANTHROPIC_API_KEY not set and no session ingress token found. "
        "Set the environment variable before starting the server."
    )

_client: Optional[Anthropic] = None

def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=_get_api_key())
    return _client

# ---------------------------------------------------------------------------
# Part registry — loaded once at startup
# ---------------------------------------------------------------------------
_DB_PATH = _repo_root / "mystery_database"
_registry = None

def get_registry():
    global _registry
    if _registry is None:
        _registry = load_registry(str(_DB_PATH))
    return _registry

# ---------------------------------------------------------------------------
# LLM helper
# ---------------------------------------------------------------------------
def llm(prompt: str, system: str = "You are a creative mystery game engine.") -> str:
    response = get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text

def _parse_json(raw: str) -> dict:
    """Strip markdown fences and parse JSON."""
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return json.loads(raw)

# ---------------------------------------------------------------------------
# Mystery generation (ported from app.py)
# ---------------------------------------------------------------------------
def _generate_mystery_dict(user_prompt: str) -> tuple[dict, object]:
    """Sample registry parts, call Claude, return (mystery_dict, recipe)."""
    registry = get_registry()
    parts, recipe = registry.sample_for_generation(target_setting=user_prompt)

    parts_block = "\n".join(
        f"  [{p.label()} — {p.part_type}]: {p.content}"
        for p in parts
    )

    prompt = f"""\
You are generating a mystery scenario for a social deduction game with 4 players.

SETTING: {user_prompt}

The following atomized parts have been selected from existing mystery literature
(recipe: {recipe.format()}). Adapt them to the target setting — do not copy verbatim.

SELECTED PARTS:
{parts_block}

QUALITY REQUIREMENTS — every generated mystery MUST satisfy these:

SETTING:
  - description must explicitly explain why suspects cannot simply leave (isolation mechanic).

CHARACTERS (include 1 victim, 3–4 suspects, optionally 1–2 witnesses):
  - alibi: SPECIFIC — state where the person was, with whom or doing what. Never "—" or vague.
  - secret: CONCRETE FACT (≥ 2 sentences) anchoring interrogation questions.
  - motive (suspects): specific stake — financial, relational, reputational, or political. Never "—".
  - occupation: always present; must logically place the character in the closed world.

EVIDENCE (include at least 6 items total):
  - At least 2 items with type "physical".
  - At least 1 item with relevance "red_herring" and type "physical" or "documentary".
  - At least 2 items with relevance "critical".
  - description: ≥ 2 sentences; state what the item is, where found, and what it suggests.

SOLUTION:
  - key_evidence must list at least 2 evidence IDs.
  - how_to_deduce: step-by-step logic chain (3+ steps).

GAMEPLAY NOTES:
  - estimated_playtime: must reflect difficulty — EASY: 30–45 min, MEDIUM: 45–60 min, HARD: 60–75 min.
    Do not exceed 75 minutes. This is a digital party game, not a dinner-event experience.

INVESTIGATION AREAS (exactly 5):
  - Named physical locations within the setting where players can search for clues.
  - Each area must be atmospherically distinct and plausible for the setting.
  - investigation_prompt: 1–2 sentences of private context Claude will use when a player investigates
    this area (what could be found there — may include red herrings). NOT shown to players.

LEADS (exactly 4):
  - Pre-existing tips, rumours, or documents that can be followed up on.
  - Each lead must be specific and actionable (not generic like "investigate the crime").
  - investigation_prompt: 1–2 sentences of private context Claude will use to resolve the lead.
    NOT shown to players. At least 1 lead should point toward the culprit; at least 1 is a red herring.

Generate a complete mystery JSON with this exact structure:
{{
  "title": "string",
  "setting": {{
    "location": "string",
    "time_period": "string",
    "environment": "string",
    "description": "2–3 sentence atmospheric description including why suspects cannot leave"
  }},
  "crime": {{
    "type": "string",
    "what_happened": "string",
    "when": "string",
    "initial_discovery": "string"
  }},
  "characters": [
    {{
      "name": "string",
      "role": "victim | suspect | detective | witness",
      "occupation": "string",
      "motive": "string",
      "alibi": "string",
      "secret": "string"
    }}
  ],
  "evidence": [
    {{
      "id": "E1",
      "name": "string",
      "description": "string",
      "type": "physical | testimonial | circumstantial | documentary",
      "relevance": "critical | supporting | red_herring"
    }}
  ],
  "investigation_areas": [
    {{
      "id": "A1",
      "name": "string",
      "description": "1–2 sentence atmospheric description of the location visible to players",
      "investigation_prompt": "private context for AI — what is here, what could be found"
    }}
  ],
  "leads": [
    {{
      "id": "L1",
      "title": "string",
      "brief": "1 sentence visible to players describing the tip or document",
      "investigation_prompt": "private context for AI — what this lead reveals when followed"
    }}
  ],
  "solution": {{
    "culprit": "string",
    "method": "string",
    "motive": "string",
    "key_evidence": ["E1", "E2"],
    "how_to_deduce": "step-by-step reasoning"
  }},
  "gameplay_notes": {{
    "difficulty": "EASY | MEDIUM | HARD",
    "estimated_playtime": "string",
    "key_twists": ["string"]
  }}
}}

Return only valid JSON. No commentary outside the JSON block."""

    raw = llm(prompt, system="You are a mystery game engine. Return only valid JSON.")
    mystery_dict = _parse_json(raw)
    mystery_dict["_provenance"] = recipe.to_dict()
    return mystery_dict, recipe


def _run_localization(mystery_dict: dict) -> dict:
    setting = mystery_dict.get("setting", {})
    if _is_modern(setting):
        return mystery_dict
    return _localize_mystery(mystery_dict, llm)


def _run_coherence(mystery_dict: dict) -> dict:
    report = check_mystery(mystery_dict)
    mystery_dict["_coherence"] = {
        "passed": report.passed,
        "blocking": report.blocking_count,
        "warnings": report.warning_count,
    }
    return mystery_dict


def _generate_cinematic_brief(mystery_dict: dict) -> dict:
    m = mystery_dict
    s = m.get("setting", {})
    c = m.get("crime", {})
    chars = m.get("characters", [])
    suspects = [ch for ch in chars if ch.get("role") == "suspect"]
    cast_lines = "\n".join(
        f"  - {ch['name']} ({ch.get('occupation', '')}): {ch.get('secret', '')[:80]}"
        for ch in suspects
    )
    prompt = f"""\
You are writing a cinematic brief for an AI video generator (e.g. Sora, Runway Gen-3).
The brief will become the opening sequence of a mystery party game — 15–30 seconds,
no spoilers, pure visual and atmospheric hook.

MYSTERY TITLE: {m.get('title', '')}
SETTING: {s.get('location', '')} — {s.get('time_period', '')}
ATMOSPHERE: {s.get('description', '')}
CRIME: {c.get('what_happened', '')}
DISCOVERED BY: {c.get('initial_discovery', '')}
SUSPECTS (do NOT show guilt or motive — only appearance and first moment):
{cast_lines}

Return ONLY valid JSON:
{{
  "logline": "One sentence. Visual, urgent, present tense. Under 20 words.",
  "opening_shot": "Establishing shot description. 2–3 sentences.",
  "crime_reveal_shot": "The discovery moment. 2–3 sentences.",
  "atmosphere_tags": ["3–6 mood/texture/palette words"],
  "sound_design": "What the audience hears before dialogue. One sentence.",
  "cast_visuals": [
    {{"name": "character name", "appearance": "one sentence", "first_seen_doing": "one sentence"}}
  ],
  "title_card": "Short evocative text overlay."
}}"""
    raw = llm(prompt, system="You are a cinematic brief writer. Return only valid JSON.")
    return _parse_json(raw)


def _save_mystery(mystery_dict: dict) -> str:
    """Persist mystery to disk. Returns slug."""
    title = mystery_dict.get("title", "mystery")
    slug = title.lower().replace(" ", "_")[:40]
    timestamp = int(time.time())
    filename = f"{slug}_{timestamp}.json"
    out_path = _DB_PATH / "generated" / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(mystery_dict, f, indent=2)
    return slug

# ---------------------------------------------------------------------------
# Async job store
# ---------------------------------------------------------------------------
# Jobs are held in memory; they expire after 10 minutes.
# Structure: { job_id: { "status": str, "stage": str, "result": dict|None, "error": str, "ts": float } }
_jobs: dict = {}
_jobs_lock = threading.Lock()

JOB_TTL = 600  # seconds


def _job_create() -> str:
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"status": "queued", "stage": "Queued", "result": None, "error": "", "ts": time.time()}
    return job_id


def _job_update(job_id: str, status: str, stage: str) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = status
            _jobs[job_id]["stage"] = stage


def _job_finish(job_id: str, result: dict) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["stage"] = "Done"
            _jobs[job_id]["result"] = result


def _job_fail(job_id: str, error: str) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["stage"] = "Error"
            _jobs[job_id]["error"] = error


def _job_get(job_id: str) -> Optional[dict]:
    with _jobs_lock:
        return _jobs.get(job_id)


def _evict_old_jobs() -> None:
    cutoff = time.time() - JOB_TTL
    with _jobs_lock:
        stale = [k for k, v in _jobs.items() if v["ts"] < cutoff]
        for k in stale:
            del _jobs[k]


def _run_generation_job(job_id: str, prompt: str, cinematic_brief: bool) -> None:
    """Background thread: runs the full generation pipeline and updates job state."""
    try:
        _job_update(job_id, "running", "Generating mystery…")
        mystery_dict, recipe = _generate_mystery_dict(prompt)

        _job_update(job_id, "running", "Localizing characters…")
        mystery_dict = _run_localization(mystery_dict)

        _job_update(job_id, "running", "Checking coherence…")
        mystery_dict = _run_coherence(mystery_dict)

        if cinematic_brief:
            _job_update(job_id, "running", "Writing cinematic brief…")
            brief = _generate_cinematic_brief(mystery_dict)
            mystery_dict["cinematic_brief"] = brief

        _job_update(job_id, "running", "Saving…")
        slug = _save_mystery(mystery_dict)
        mystery_dict["_slug"] = slug

        _job_finish(job_id, mystery_dict)
        _evict_old_jobs()
    except Exception as exc:
        _job_fail(job_id, str(exc))


# ---------------------------------------------------------------------------
# Game session store
# ---------------------------------------------------------------------------
# In-memory; good for Phase 3. Replace with a DB if sessions need to survive restarts.
#
# Session structure:
# {
#   "game_id": str,
#   "mystery": dict,           # full mystery dict including investigation_areas + leads
#   "difficulty": str,
#   "share_min": float,        # minimum fraction of findings player must share
#   "witness_budget": int,
#   "investigation_budget": int,
#   "players": {player_id: {"name": str, "phase": str, "witness_budget": int,
#                            "investigation_budget": int, "leads_used": [lead_id],
#                            "witness_findings": [{id, character, question, response}],
#                            "investigation_findings": [{id, area_id, findings}],
#                            "lead_findings": [{id, lead_id, findings}]}},
#   "shared_pool": {
#       "witness": [{sender_name, id, character, question, response, ts}],
#       "investigation": [{sender_name, id, area_id, findings, ts}],
#       "lead": [{sender_name, id, lead_id, findings, ts}],
#   },
#   "block_pool": {
#       "witness": [{character, fingerprint}],
#       "investigation": [area_id],
#       "lead": [lead_id],
#   },
#   "ts": float,
# }

_games: dict = {}
_games_lock = threading.Lock()
_GAME_TTL = 3600  # 1 hour

_DIFFICULTY_CONFIG = {
    "EASY":   {"share_min": 0.70, "witness_budget": 8, "investigation_budget": 3},
    "MEDIUM": {"share_min": 0.60, "witness_budget": 6, "investigation_budget": 2},
    "HARD":   {"share_min": 0.50, "witness_budget": 4, "investigation_budget": 2},
}


def _new_game_id() -> str:
    return str(uuid.uuid4())[:8].upper()


def _new_player_id() -> str:
    return str(uuid.uuid4())


def _get_game(game_id: str) -> Optional[dict]:
    with _games_lock:
        return _games.get(game_id)


def _fingerprint(question: str) -> str:
    """Normalised lowercase question key for duplicate detection."""
    return question.strip().lower()


def _investigate_area_with_ai(mystery: dict, area: dict, player_name: str) -> str:
    setting = mystery.get("setting", {})
    crime = mystery.get("crime", {})
    prompt = (
        f"You are an AI narrator for a mystery game. A detective named {player_name} "
        f"is investigating '{area['name']}' at {setting.get('location', 'the scene')} "
        f"({setting.get('time_period', '')}).\n\n"
        f"Crime overview: {crime.get('what_happened', '')}\n\n"
        f"Private context for this area: {area.get('investigation_prompt', '')}\n\n"
        "Describe in 2–4 sentences what the detective finds when searching this area. "
        "Be atmospheric and specific. May include clues, red herrings, or atmosphere. "
        "Do not reveal the culprit directly."
    )
    return llm(prompt, system="You are a mystery game narrator. Be vivid and specific.")


def _follow_lead_with_ai(mystery: dict, lead: dict, player_name: str) -> str:
    setting = mystery.get("setting", {})
    crime = mystery.get("crime", {})
    prompt = (
        f"You are an AI narrator for a mystery game. A detective named {player_name} "
        f"is following the lead: '{lead['title']}' at {setting.get('location', 'the scene')}.\n\n"
        f"Crime overview: {crime.get('what_happened', '')}\n\n"
        f"Private context for this lead: {lead.get('investigation_prompt', '')}\n\n"
        "Describe in 2–4 sentences what the detective discovers when following this lead. "
        "Be specific and atmospherically consistent with the mystery. "
        "Do not reveal the culprit directly."
    )
    return llm(prompt, system="You are a mystery game narrator. Be vivid and specific.")


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
# Maintains one set of open WebSocket connections per game_id (room).
# All server-side actions that change shared state call _ws_broadcast()
# so clients receive push events instead of polling.
#
# Push event envelope:
#   { "event": str, "data": dict }
#
# Events pushed today:
#   player_joined      — { name }
#   clues_shared       — { sender_name, phase, clues: [...] }
#   block_updated      — { witness: [...], investigation: [...], lead: [...] }
#   player_phase_done  — { player_name, phase }

class ConnectionManager:
    def __init__(self) -> None:
        # game_id → list of open WebSocket connections
        self._rooms: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, game_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._rooms.setdefault(game_id, []).append(ws)

    async def disconnect(self, game_id: str, ws: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(game_id, [])
            if ws in room:
                room.remove(ws)

    async def broadcast(self, game_id: str, event: str, data: dict) -> None:
        payload = json.dumps({"event": event, "data": data})
        async with self._lock:
            dead: list[WebSocket] = []
            for ws in self._rooms.get(game_id, []):
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._rooms[game_id].remove(ws)


_ws_manager = ConnectionManager()


def _broadcast_sync(game_id: str, event: str, data: dict) -> None:
    """
    Fire-and-forget WebSocket broadcast from a synchronous context
    (e.g. inside a regular FastAPI endpoint or thread).
    Creates a new event loop task if the running loop allows it.
    Safe to call from non-async code.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(
                _ws_manager.broadcast(game_id, event, data), loop
            )
        else:
            loop.run_until_complete(_ws_manager.broadcast(game_id, event, data))
    except RuntimeError:
        pass  # No event loop available — server is probably shutting down


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Choose Your Mystery — Backend", version="1.0.0")

# Allow the Godot client (and local dev tools) to call this server.
# In production, restrict origins to your actual domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve mobile.html and any other static phone-client assets from server/static/
_static_dir = Path(__file__).parent / "static"
_static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    prompt: str
    cinematic_brief: bool = False

class InterrogateRequest(BaseModel):
    mystery: dict                  # full mystery dict (sent by client)
    character_name: str
    question: str

class RateRequest(BaseModel):
    mystery_slug: str
    rating: int                    # 1–10

class AsyncGenerateRequest(BaseModel):
    prompt: str
    cinematic_brief: bool = False

class CreateGameRequest(BaseModel):
    mystery_slug: str
    host_name: str
    difficulty: str = "MEDIUM"   # "EASY" | "MEDIUM" | "HARD"

class JoinGameRequest(BaseModel):
    player_name: str

class InvestigateAreaRequest(BaseModel):
    player_id: str
    area_id: str

class FollowLeadRequest(BaseModel):
    player_id: str
    lead_id: str

class SharePhaseRequest(BaseModel):
    player_id: str
    phase: str          # "witness" | "investigation" | "lead"
    selected_ids: list  # list of clue/finding IDs the player chose to share

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    """Quick liveness check — no API calls."""
    return {"ok": True}


@app.post("/generate")
def generate(req: GenerateRequest):
    """
    Generate a mystery from a freetext prompt.

    Flow:
      1. Sample registry parts (free)
      2. Claude call: generate mystery JSON
      3. Localization pass (Claude call, or free if modern era)
      4. Coherence check (free)
      5. Optional: cinematic brief (Claude call)
      6. Save to disk
      7. Return full mystery dict

    SESSION ANNOTATION: This is the core endpoint. If this works,
    Phase 1 is functionally complete.
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt must not be empty")

    mystery_dict, recipe = _generate_mystery_dict(req.prompt)
    mystery_dict = _run_localization(mystery_dict)
    mystery_dict = _run_coherence(mystery_dict)

    if req.cinematic_brief:
        brief = _generate_cinematic_brief(mystery_dict)
        mystery_dict["cinematic_brief"] = brief

    slug = _save_mystery(mystery_dict)
    mystery_dict["_slug"] = slug
    return mystery_dict


@app.post("/generate/async")
def generate_async(req: AsyncGenerateRequest):
    """
    Kick off mystery generation in a background thread and return a job_id immediately.
    The client polls GET /jobs/{job_id} for progress and the final result.

    Stages returned in "stage":
      "Queued" → "Generating mystery…" → "Localizing characters…"
      → "Checking coherence…" → ["Writing cinematic brief…"] → "Saving…" → "Done"

    Status values: "queued" | "running" | "done" | "error"
    """
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt must not be empty")
    job_id = _job_create()
    thread = threading.Thread(
        target=_run_generation_job,
        args=(job_id, req.prompt, req.cinematic_brief),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    """
    Poll for job status.

    Returns:
      { "status": "queued"|"running"|"done"|"error",
        "stage":  human-readable progress label,
        "result": <mystery dict> | null,
        "error":  "" | "error message" }
    """
    job = _job_get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found (may have expired)")
    return {
        "status": job["status"],
        "stage":  job["stage"],
        "result": job["result"],
        "error":  job["error"],
    }


@app.get("/play", response_class=HTMLResponse)
async def play_page():
    """Serve the mobile phone client."""
    mobile_html = _static_dir / "mobile.html"
    if mobile_html.exists():
        return HTMLResponse(mobile_html.read_text())
    return HTMLResponse("<h2>mobile.html not found — server/static/mobile.html is missing.</h2>", status_code=503)


@app.websocket("/ws/{game_id}")
async def websocket_endpoint(ws: WebSocket, game_id: str, player_id: str = ""):
    """
    Persistent WebSocket connection for a game room.
    Clients connect here to receive real-time push events:
      - clues_shared      when another player's Share Selection is submitted
      - block_updated     when the block pool changes
      - player_joined     when a new player joins
      - player_phase_done when a player advances phase

    The client can also send messages, currently only used to confirm readiness:
      { "action": "ping" }  → ignored (keepalive)
    """
    game = _get_game(game_id)
    if game is None:
        await ws.close(code=4004, reason="game not found")
        return

    await _ws_manager.connect(game_id, ws)
    player_name = ""
    if player_id and player_id in game["players"]:
        player_name = game["players"][player_id]["name"]
        await _ws_manager.broadcast(game_id, "player_joined", {"name": player_name})

    try:
        while True:
            # Keep the connection alive; ignore any messages from client
            await ws.receive_text()
    except WebSocketDisconnect:
        await _ws_manager.disconnect(game_id, ws)


@app.post("/games/create")
def create_game(req: CreateGameRequest):
    """
    Create a new multiplayer game session from a previously generated mystery.
    Returns the game_id (room code) and per-difficulty budgets.
    """
    difficulty = req.difficulty.upper()
    if difficulty not in _DIFFICULTY_CONFIG:
        raise HTTPException(status_code=400, detail="difficulty must be EASY, MEDIUM, or HARD")

    # Load the mystery
    generated_dir = _DB_PATH / "generated"
    matches = list(generated_dir.glob(f"{req.mystery_slug}_*.json"))
    if not matches:
        raise HTTPException(status_code=404, detail="mystery not found")
    with open(sorted(matches)[-1]) as f:
        mystery = json.load(f)

    cfg = _DIFFICULTY_CONFIG[difficulty]
    game_id = _new_game_id()
    host_id = _new_player_id()

    session = {
        "game_id": game_id,
        "mystery": mystery,
        "difficulty": difficulty,
        "share_min": cfg["share_min"],
        "witness_budget": cfg["witness_budget"],
        "investigation_budget": cfg["investigation_budget"],
        "players": {
            host_id: {
                "name": req.host_name,
                "is_host": True,
                "phase": "witness",
                "witness_budget": cfg["witness_budget"],
                "investigation_budget": cfg["investigation_budget"],
                "leads_used": [],
                "witness_findings": [],
                "investigation_findings": [],
                "lead_findings": [],
            }
        },
        "shared_pool": {"witness": [], "investigation": [], "lead": []},
        "block_pool": {"witness": [], "investigation": [], "lead": []},
        "ts": time.time(),
    }
    with _games_lock:
        _games[game_id] = session

    return {
        "game_id": game_id,
        "player_id": host_id,
        "share_min": cfg["share_min"],
        "witness_budget": cfg["witness_budget"],
        "investigation_budget": cfg["investigation_budget"],
    }


@app.post("/games/{game_id}/join")
def join_game(game_id: str, req: JoinGameRequest):
    """Register a new player in the game session."""
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    player_id = _new_player_id()
    cfg = _DIFFICULTY_CONFIG[game["difficulty"]]
    with _games_lock:
        game["players"][player_id] = {
            "name": req.player_name,
            "is_host": False,
            "phase": "witness",
            "witness_budget": cfg["witness_budget"],
            "investigation_budget": cfg["investigation_budget"],
            "leads_used": [],
            "witness_findings": [],
            "investigation_findings": [],
            "lead_findings": [],
        }
    _broadcast_sync(game_id, "player_joined", {"name": req.player_name})
    return {
        "player_id": player_id,
        "game_id": game_id,
        "share_min": game["share_min"],
        "witness_budget": cfg["witness_budget"],
        "investigation_budget": cfg["investigation_budget"],
    }


@app.get("/games/{game_id}/block-pool")
def get_block_pool(game_id: str):
    """
    Return the current block pool for this game so the client can grey out
    already-shared questions, areas, and leads before the player tries them.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    return game["block_pool"]


@app.get("/games/{game_id}/shared-clues")
def get_shared_clues(game_id: str, player_id: str):
    """
    Return all clues that have been shared into this game session.
    In a future WebSocket version this would be pushed; for now the client polls.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if player_id not in game["players"]:
        raise HTTPException(status_code=404, detail="player not in game")
    # Return everything in shared_pool — all players receive all shared clues
    return game["shared_pool"]


@app.post("/games/{game_id}/investigate-area")
def investigate_area(game_id: str, req: InvestigateAreaRequest):
    """
    Player investigates a named crime scene area.
    - Checks hard block (area already in block pool)
    - Calls Claude to generate findings
    - Deducts 1 from the player's investigation budget
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if req.player_id not in game["players"]:
        raise HTTPException(status_code=404, detail="player not in game")

    player = game["players"][req.player_id]
    if player["phase"] != "investigation":
        raise HTTPException(status_code=400, detail="player is not in the investigation phase")
    if player["investigation_budget"] <= 0:
        raise HTTPException(status_code=400, detail="investigation budget exhausted")

    # Hard block check
    if req.area_id in game["block_pool"]["investigation"]:
        raise HTTPException(
            status_code=409,
            detail={"blocked": True, "reason": "This area has already been shared with the group. Try a different location."}
        )

    # Find the area definition in the mystery
    areas = game["mystery"].get("investigation_areas", [])
    area = next((a for a in areas if a["id"] == req.area_id), None)
    if area is None:
        raise HTTPException(status_code=404, detail="area not found in mystery")

    findings = _investigate_area_with_ai(game["mystery"], area, player["name"])
    finding_id = str(uuid.uuid4())[:8]

    with _games_lock:
        player["investigation_findings"].append({
            "id": finding_id,
            "area_id": req.area_id,
            "area_name": area["name"],
            "findings": findings,
        })
        player["investigation_budget"] -= 1

    return {"finding_id": finding_id, "area_name": area["name"], "findings": findings,
            "budget_remaining": player["investigation_budget"]}


@app.post("/games/{game_id}/follow-lead")
def follow_lead(game_id: str, req: FollowLeadRequest):
    """
    Player follows one of the pre-generated leads.
    - Checks hard block
    - Each player limited to 2 leads total
    - Calls Claude to generate findings
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if req.player_id not in game["players"]:
        raise HTTPException(status_code=404, detail="player not in game")

    player = game["players"][req.player_id]
    if player["phase"] != "lead":
        raise HTTPException(status_code=400, detail="player is not in the lead phase")
    if len(player["leads_used"]) >= 2:
        raise HTTPException(status_code=400, detail="lead budget exhausted (max 2 per player)")
    if req.lead_id in player["leads_used"]:
        raise HTTPException(status_code=400, detail="you already followed this lead")

    # Hard block check
    if req.lead_id in game["block_pool"]["lead"]:
        raise HTTPException(
            status_code=409,
            detail={"blocked": True, "reason": "This lead has already been shared with the group. Pick a different one."}
        )

    leads = game["mystery"].get("leads", [])
    lead = next((l for l in leads if l["id"] == req.lead_id), None)
    if lead is None:
        raise HTTPException(status_code=404, detail="lead not found in mystery")

    findings = _follow_lead_with_ai(game["mystery"], lead, player["name"])
    finding_id = str(uuid.uuid4())[:8]

    with _games_lock:
        player["lead_findings"].append({
            "id": finding_id,
            "lead_id": req.lead_id,
            "lead_title": lead["title"],
            "findings": findings,
        })
        player["leads_used"].append(req.lead_id)

    return {"finding_id": finding_id, "lead_title": lead["title"], "findings": findings,
            "leads_remaining": 2 - len(player["leads_used"])}


@app.post("/games/{game_id}/share-phase")
def share_phase(game_id: str, req: SharePhaseRequest):
    """
    Player submits their Share Selection at the end of a phase.

    - Validates minimum share % (must share ≥ share_min of findings)
    - Checks selected IDs for duplicates against the shared pool
    - If duplicates found: returns duplicate_flags, player must resubmit
    - If clean: broadcasts selected findings to all players, updates block pool
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if req.player_id not in game["players"]:
        raise HTTPException(status_code=404, detail="player not in game")

    player = game["players"][req.player_id]
    phase = req.phase

    # Get the player's findings for this phase
    findings_key = f"{phase}_findings"
    all_findings = player.get(findings_key, [])
    if not all_findings:
        raise HTTPException(status_code=400, detail="no findings to share for this phase")

    # Validate minimum share %
    min_required = max(1, round(len(all_findings) * game["share_min"]))
    if len(req.selected_ids) < min_required:
        raise HTTPException(
            status_code=400,
            detail=f"Must share at least {min_required} of {len(all_findings)} findings "
                   f"({int(game['share_min']*100)}% minimum)."
        )

    # Validate selected IDs exist in player's findings
    findings_by_id = {f["id"]: f for f in all_findings}
    invalid = [sid for sid in req.selected_ids if sid not in findings_by_id]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Unknown finding IDs: {invalid}")

    # Duplicate check against shared pool
    duplicate_flags = []
    for sid in req.selected_ids:
        finding = findings_by_id[sid]
        if phase == "witness":
            fp = _fingerprint(finding["question"])
            if any(b["character"] == finding["character"] and b["fingerprint"] == fp
                   for b in game["block_pool"]["witness"]):
                duplicate_flags.append(sid)
        elif phase == "investigation":
            if finding["area_id"] in game["block_pool"]["investigation"]:
                duplicate_flags.append(sid)
        elif phase == "lead":
            if finding["lead_id"] in game["block_pool"]["lead"]:
                duplicate_flags.append(sid)

    if duplicate_flags:
        return {"ok": False, "shared_count": 0, "duplicate_flags": duplicate_flags}

    # Broadcast to all: add to shared_pool and update block_pool
    sender_name = player["name"]
    with _games_lock:
        for sid in req.selected_ids:
            finding = findings_by_id[sid]
            entry = {"sender_name": sender_name, "ts": time.time(), **finding}
            game["shared_pool"][phase].append(entry)

            if phase == "witness":
                game["block_pool"]["witness"].append({
                    "character": finding["character"],
                    "fingerprint": _fingerprint(finding["question"]),
                })
            elif phase == "investigation":
                game["block_pool"]["investigation"].append(finding["area_id"])
            elif phase == "lead":
                game["block_pool"]["lead"].append(finding["lead_id"])

        # Advance player to next phase
        phase_order = ["witness", "investigation", "lead", "done"]
        current_idx = phase_order.index(phase)
        player["phase"] = phase_order[min(current_idx + 1, len(phase_order) - 1)]

    # Push events to all connected WebSocket clients in this room
    shared_clues = [findings_by_id[sid] for sid in req.selected_ids]
    _broadcast_sync(game_id, "clues_shared", {
        "sender_name": player["name"],
        "phase": phase,
        "clues": shared_clues,
    })
    _broadcast_sync(game_id, "block_updated", game["block_pool"])
    _broadcast_sync(game_id, "player_phase_done", {
        "player_name": player["name"],
        "phase": phase,
    })

    return {"ok": True, "shared_count": len(req.selected_ids), "duplicate_flags": []}


@app.post("/interrogate")
def interrogate(req: InterrogateRequest):
    """
    Ask a named character a question. Returns an in-character reply.

    The full mystery dict is sent by the client so the server can build
    the character context without a database lookup on every call.
    This is acceptable because mysteries are small (<10 KB).
    """
    chars = req.mystery.get("characters", [])
    char_data = next((c for c in chars if c["name"] == req.character_name), None)
    if char_data is None:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{req.character_name}' not found in mystery"
        )

    # Build setting narrative for context
    s = req.mystery.get("setting", {})
    c = req.mystery.get("crime", {})
    setting_summary = (
        f"Location: {s.get('location', '')}\n"
        f"Time period: {s.get('time_period', '')}\n"
        f"Crime: {c.get('what_happened', '')}"
    )

    char_context = (
        f"Role: {char_data.get('role', 'suspect')}\n"
        f"Occupation: {char_data.get('occupation', '')}\n"
        f"Alibi: {char_data.get('alibi', '')}\n"
        f"Secret: {char_data.get('secret', '')}\n"
        f"Motive: {char_data.get('motive', '')}"
    )

    prompt = f"""You are {req.character_name} in this mystery.

SETTING:
{setting_summary}

YOUR PRIVATE CHARACTER DETAILS (do NOT reveal these directly):
{char_context}

Answer the detective's question in character.
Be evasive if you are the culprit. Be defensive if you are innocent but suspicious.
Do NOT directly reveal the real culprit.

Detective's question: {req.question}"""

    reply = llm(prompt, system="You are a mystery game character. Stay in character.")
    return {"response": reply}


@app.post("/games/{game_id}/interrogate")
def game_interrogate(game_id: str, req: InterrogateRequest):
    """
    Game-session-aware interrogation used during Phase 3 multiplayer.
    - Validates player is in the witness phase
    - Checks hard-block (duplicate question already shared)
    - Deducts from witness budget
    - Stores finding so the player can share at phase end
    The underlying AI call is identical to the solo /interrogate endpoint.
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")

    # Look up player_id from the request body's mystery — we need it separately.
    # For game interrogation we expect a player_id field on the request.
    # We re-use InterrogateRequest but the player_id is passed as a query param.
    raise HTTPException(
        status_code=501,
        detail="Use POST /games/{game_id}/interrogate-witness instead."
    )


class GameInterrogateRequest(BaseModel):
    player_id: str
    character_name: str
    question: str


@app.post("/games/{game_id}/interrogate-witness")
def game_interrogate_witness(game_id: str, req: GameInterrogateRequest):
    """
    Multiplayer witness interrogation.
    - Player must be in 'witness' phase
    - Hard-block if (character, question_fingerprint) already in block pool
    - Calls Claude for in-character response
    - Deducts 1 from witness budget; stores in player's witness_findings
    """
    game = _get_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="game not found")
    if req.player_id not in game["players"]:
        raise HTTPException(status_code=404, detail="player not in game")

    player = game["players"][req.player_id]
    if player["phase"] != "witness":
        raise HTTPException(status_code=400, detail="player is not in the witness phase")
    if player["witness_budget"] <= 0:
        raise HTTPException(status_code=400, detail="witness budget exhausted")

    # Hard block check
    fp = _fingerprint(req.question)
    if any(b["character"] == req.character_name and b["fingerprint"] == fp
           for b in game["block_pool"]["witness"]):
        raise HTTPException(
            status_code=409,
            detail={
                "blocked": True,
                "reason": f"This question to {req.character_name} has already been shared with the group. Ask something different."
            }
        )

    # Retrieve character data from mystery for richer context
    chars = game["mystery"].get("characters", [])
    char_data = next((c for c in chars if c["name"] == req.character_name), None)
    if char_data is None:
        raise HTTPException(status_code=404, detail=f"Character '{req.character_name}' not found")

    s = game["mystery"].get("setting", {})
    c = game["mystery"].get("crime", {})
    setting_summary = (
        f"Location: {s.get('location', '')}\n"
        f"Time period: {s.get('time_period', '')}\n"
        f"Crime: {c.get('what_happened', '')}"
    )
    char_context = (
        f"Role: {char_data.get('role', 'suspect')}\n"
        f"Occupation: {char_data.get('occupation', '')}\n"
        f"Alibi: {char_data.get('alibi', '')}\n"
        f"Secret: {char_data.get('secret', '')}\n"
        f"Motive: {char_data.get('motive', '')}"
    )
    prompt = (
        f"You are {req.character_name} in this mystery.\n\n"
        f"SETTING:\n{setting_summary}\n\n"
        f"YOUR PRIVATE CHARACTER DETAILS (do NOT reveal directly):\n{char_context}\n\n"
        f"Detective's question: {req.question}"
    )
    response = llm(prompt, system="You are a mystery game character. Stay in character.")

    finding_id = str(uuid.uuid4())[:8]
    with _games_lock:
        player["witness_findings"].append({
            "id": finding_id,
            "character": req.character_name,
            "question": req.question,
            "response": response,
        })
        player["witness_budget"] -= 1

    return {
        "finding_id": finding_id,
        "response": response,
        "budget_remaining": player["witness_budget"],
    }


@app.post("/rate")
def rate(req: RateRequest):
    """
    Persist a viability rating (1–10) back into the saved mystery JSON.
    Updates the `_meta.viability_rating` field.
    """
    if not (1 <= req.rating <= 10):
        raise HTTPException(status_code=400, detail="rating must be 1–10")

    generated_dir = _DB_PATH / "generated"
    matches = list(generated_dir.glob(f"{req.mystery_slug}_*.json"))
    if not matches:
        raise HTTPException(status_code=404, detail="mystery not found")

    # Use the most recent file if multiple matches (shouldn't happen in practice)
    mystery_file = sorted(matches)[-1]
    with open(mystery_file) as f:
        data = json.load(f)

    if "_meta" not in data:
        data["_meta"] = {}
    data["_meta"]["viability_rating"] = req.rating

    with open(mystery_file, "w") as f:
        json.dump(data, f, indent=2)

    return {"ok": True}


@app.get("/mysteries")
def list_mysteries():
    """
    List all saved mysteries (slug, title, created_at timestamp).
    Sorted newest-first.
    """
    generated_dir = _DB_PATH / "generated"
    results = []
    for path in sorted(generated_dir.glob("*.json"), reverse=True):
        try:
            with open(path) as f:
                data = json.load(f)
            stem = path.stem  # e.g. "the_murder_on_the_train_1700000000"
            parts = stem.rsplit("_", 1)
            slug = parts[0] if len(parts) == 2 else stem
            ts = int(parts[1]) if len(parts) == 2 and parts[1].isdigit() else 0
            results.append({
                "slug": slug,
                "title": data.get("title", slug),
                "difficulty": data.get("gameplay_notes", {}).get("difficulty", "?"),
                "coherence_passed": data.get("_coherence", {}).get("passed", None),
                "viability_rating": data.get("_meta", {}).get("viability_rating", None),
                "created_at": ts,
            })
        except Exception:
            continue
    return results


@app.get("/mysteries/{slug}")
def get_mystery(slug: str):
    """Load the most recently saved mystery matching this slug."""
    generated_dir = _DB_PATH / "generated"
    matches = list(generated_dir.glob(f"{slug}_*.json"))
    if not matches:
        raise HTTPException(status_code=404, detail="mystery not found")
    mystery_file = sorted(matches)[-1]
    with open(mystery_file) as f:
        return json.load(f)
