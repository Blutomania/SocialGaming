# Choose Your Mystery — Session Log

A running record of what each Claude Code session built or decided.
Use this file to onboard any new session without losing context.
**Newest sessions are at the top.**

---

## Session 11 — April 2, 2026
**Branch:** `claude/start-godot-migration-mNrWD`
**Starting commit:** `380f0e2`
**Status:** Complete — Godot project loads without errors

### What was done
- Fixed `ApiClient.gd` parse error: GDScript can't handle multi-line lambdas capturing
  outer-scope variables. Rewrote using `.bind(req, callback)` on a named `_on_done()`
  method instead. Simpler and more reliable.
- Fixed `project.godot` version: updated `4.2` → `4.6` to match installed Godot version.
- Godot 4.6 confirmed: project opens and all autoloads load without errors.

### Known: project.godot drift
Godot rewrites `project.godot` on every open. Before pushing, run:
`git checkout -- godot/project.godot` to discard Godot's local changes, then pull.
Long-term fix: commit Godot's version after each session.

### Next steps (resume here — Phase 2)
1. Start backend: `cd SocialGaming && ANTHROPIC_API_KEY=sk-... uvicorn server.main:app --port 8000`
2. Press F5 in Godot — MainMenu should load and status label should go green
3. Click "New Game", type a prompt, click "Generate Mystery"
4. Verify CaseDisplay loads with mystery title, suspects, evidence
5. Interrogate a suspect, make an accusation, see result screen
6. Once full loop works: tag `phase2-single-player-prototype` and commit
7. Then: Phase 3 — lobby, ENet multiplayer, 75% clue-sharing

---

## Session 10 — April 2, 2026
**Branch:** `claude/start-godot-migration-mNrWD`
**Starting commit:** `ea5af2f`
**Status:** Complete — Phase 1 done (`phase1-backend-done`)

### What was done
Full Godot migration scaffolded. Project is now a multiplayer standalone game targeting
Steam, replacing the Streamlit creator tool. HuggingFace Spaces retired.

**Architecture decided:**
- Godot 4.x client (GDScript 2.0) — game UI, networking
- Python FastAPI backend — all Claude API calls (mystery generation, interrogation)
- Dedicated server model for multiplayer (Godot ENet, Phase 3)
- Steam via GodotSteam plugin (Phase 4)

**Files created:**

| File | Purpose |
|---|---|
| `server/main.py` | FastAPI app — `/generate`, `/interrogate`, `/rate`, `/mysteries`, `/health` |
| `server/requirements.txt` | fastapi, uvicorn, anthropic, python-dotenv |
| `server/Dockerfile` | Container — copies server + existing Python backend modules |
| `godot/project.godot` | Godot 4 project root; autoloads: GameState, ApiClient, NetworkManager |
| `godot/scripts/autoloads/GameState.gd` | Singleton: mystery, phase, history, accusation result |
| `godot/scripts/autoloads/ApiClient.gd` | HTTP wrapper; pooled HTTPRequest nodes per call |
| `godot/scripts/autoloads/NetworkManager.gd` | ENet multiplayer stub (Phase 3) |
| `godot/scripts/data/MysteryData.gd` | Typed GDScript wrapper for mystery JSON |
| `godot/scripts/ui/main_menu.gd` | MainMenu controller; health-checks backend on ready |
| `godot/scripts/ui/mystery_generation.gd` | Generation screen; calls /generate |
| `godot/scripts/ui/case_display.gd` | Case + evidence display; viability rating |
| `godot/scripts/ui/interrogation.gd` | Interrogation screen; calls /interrogate |
| `godot/scripts/ui/accusation.gd` | Accusation; compares locally vs solution dict |
| `godot/scripts/ui/result_screen.gd` | Result + solution reveal; calls /rate |
| `godot/scenes/ui/MainMenu.tscn` | MainMenu scene tree |
| `godot/scenes/ui/MysteryGeneration.tscn` | Generation scene tree |
| `godot/scenes/ui/CaseDisplay.tscn` | Case display scene tree |
| `godot/scenes/ui/Interrogation.tscn` | Interrogation scene tree |
| `godot/scenes/ui/Accusation.tscn` | Accusation scene tree |
| `godot/scenes/ui/ResultScreen.tscn` | Result scene tree |
| `CLAUDE.md` | Updated: Steam target, Godot architecture, retired HuggingFace |

**Files NOT modified (kept as-is):**
- `app.py` — retired (do not modify; will delete once Phase 2 confirmed)
- `mystery_generator.py`, `coherence_validator.py`, `part_registry.py`, `localization.py` — kept, used by FastAPI server

### Key decisions
- **Solution in client dict:** The `/generate` endpoint returns the full mystery including
  `solution`. The Godot client stores it in `GameState` but never displays it until the
  `ResultScreen`. Phase 3 will add server-side validation (`POST /accuse`) to prevent
  multiplayer cheating; Phase 2 compares locally.
- **No extra `/accuse` endpoint for Phase 2:** Simplification — accusation is a local
  comparison. The `POST /accuse` endpoint (Claude verdict narrative) is deferred to Phase 3.
- **NetworkManager is a stub:** All methods are present with Phase 3 annotations; Phase 2
  is single-player only.
- **HuggingFace retired:** `hf-deploy` branch is stale. Server runs locally via uvicorn.

### How to test Phase 1
```bash
# 1. Install server dependencies
cd server && pip install -r requirements.txt

# 2. Start backend (run from repo root)
ANTHROPIC_API_KEY=sk-... uvicorn server.main:app --port 8000

# 3. Smoke test
curl localhost:8000/health
# → {"ok":true}

# 4. Open godot/ in Godot 4 editor
# 5. Verify 3 autoloads appear in Project → Project Settings → Autoload
# 6. Press F5 — MainMenu should load
```

### Local sync steps
```bash
git fetch origin
git checkout claude/start-godot-migration-mNrWD
git pull origin claude/start-godot-migration-mNrWD
```

---

## Session 9 — March 12, 2026
**Branch:** `claude/setup-api-and-mysteries-LRLQK`
**Latest commit:** `d66657d`

### Files modified
- `app.py` — Multiple UI improvements (see decisions below)
- `CLAUDE.md` — Streamlined and updated to reflect current state
- `SESSIONS.md` — This entry

### Decisions made
- **Page header** now has two caption lines: "Ultimately: ..." (game vision) and "Currently: ..." (creator tool). The "Currently" line is **owner-maintained** — Claude Code must not change it.
- **Evidence surfaced** — all evidence items now shown in an expandable section (open by default) with type badge and ★/✗/· relevance tags. Previously generated but never displayed.
- **Gameplay notes surfaced** — difficulty, estimated playtime, key twists now shown inline below evidence.
- **Witnesses** added to cast display in the narrative and to the interrogation dropdown (alongside suspects).
- **`crime.when`** now shown in the crime narrative.
- **Viability rating** — 1–10 horizontal radio buttons with a descriptive label per score. Creator-side only. Stored in session state; **not persisted to disk yet** (intentional — owner wants to play with it first).
- **Feedback persistence deferred** — saving ratings + behavioral signals to disk is on the backlog (SESSIONS.md item 7) but must not be implemented until the owner explicitly requests it.

### Design decision — Multiplayer & invite mechanic
**Agreed direction (March 12, 2026):**
- The game is multi-player. The **initiator** creates and enters the mystery scenario.
- **Information sharing is global** — all players see the same 75% of information.
- **Invite mechanic:** shareable link with a short game code (e.g. `chooseyourmystery.com/game/XK7F2`).
  Jackbox / Skribbl.io model — lowest friction, works in any group-chat context.
- **Do not implement yet** — design is captured here for the session that picks up multiplayer work.

---

## Session 8 — March 12, 2026
**Branch:** `claude/review-changes-mmmec1tknjh846kb-08C3q`
**Latest commit:** `1f11171`

### Files created
- `coherence_validator.py` — P1 chain + witness interrogation foundation + scene investigation checks

### Decisions made
- Validator is **two-phase**: pre-generation (free) and post-generation
- `BLOCKING` issues prevent gameplay use; `WARNING` degrades quality; `INFO` is cosmetic
- All repair hints reference `part_type` re-sampling from registry (zero API cost)

---

## Session 7 — March 11, 2026
**Branch:** `claude/review-changes-mmmec1tknjh846kb-08C3q`
**Latest commit:** `501641c`

### What was done
- Deployed `app.py` to HuggingFace Spaces
- Created `hf-deploy` orphan branch (PDF-free history)
- Added HuggingFace Space YAML metadata to `README.md`

---

## Session 6 — March 9, 2026
**Branch:** `claude/upload-corpus-extraction-3uTq5`
**Status:** Complete

### What was done
- Built `extract_test_mysteries.py` — P1+P2 extraction against 6 built-in test mysteries
- Resolved Bearer token auth for environments without `ANTHROPIC_API_KEY`
- All 6 mysteries extracted: saved to `mystery_database/extractions/test_{a-f}_p1p2.json`

---

## Sessions 1–5 — March 7–8, 2026

Core foundation built across these sessions:
- `extraction_protocols.py` — P1–P4 taxonomy
- `test_mysteries.py` — canonical test corpus (A–F)
- `part_registry.py` — 1,469-part corpus with diversity-constrained sampling
- `cli.py` — terminal entry point (generate, extract, solve, list, registry)
- `corpus_loader.py`, `run_corpus_pipeline.py`
- `coherence_validator.py` wired into generation pipeline
- `localization.py` — 3-tier era-appropriate name/occupation localization (~11x cost reduction)
- `app.py` — Streamlit UI (now retired; replaced by Godot client)
- `docs/WIRING.md` — canonical architecture reference
- 9 generated mysteries with diverse settings committed to `mystery_database/generated/`
