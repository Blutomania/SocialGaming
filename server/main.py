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

import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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
