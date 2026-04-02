# Choose Your Mystery — Claude Code Instructions

## Project Overview
AI-powered social murder mystery party game. Players join a lobby, investigate crimes,
interrogate AI characters, share clues (75% mechanic), and compete to solve the case first.

**Target:** Multiplayer standalone / Steam release.
**Distribution:** Steam (GodotSteam SDK for Phase 4). One-time $100 Steam fee per title.
**Architecture:** Godot 4.x client + Python FastAPI backend (AI calls). No HuggingFace.

Core innovation: the **75% information-sharing mechanic** — when a player shares a clue,
it reaches exactly 75% of other players (randomly), forcing collaboration while preserving
individual advantage.

Current phase: **Phase 2 — single-player Godot prototype**.
Previous phase (complete): Phase 1 — FastAPI server + Godot scaffold (`phase1-backend-done`).
Retired: Streamlit creator tool on HuggingFace Spaces.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Godot 4.x Client (godot/)                          │
│  GDScript — game UI, input, multiplayer networking  │
│  Talks to backend over HTTP (ApiClient.gd autoload) │
└─────────────────┬───────────────────────────────────┘
                  │ HTTP JSON
┌─────────────────▼───────────────────────────────────┐
│  Python FastAPI Server (server/)                    │
│  POST /generate  — mystery generation               │
│  POST /interrogate — NPC in-character replies       │
│  POST /rate      — viability rating persistence     │
│  GET  /mysteries — list saved mysteries             │
│  GET  /mysteries/{slug} — load saved mystery        │
│  Wraps: part_registry, coherence_validator,         │
│         localization, mystery generation logic      │
└─────────────────────────────────────────────────────┘
```

**Multiplayer:** Godot's built-in ENet (dedicated server model). Room codes like Jackbox.
**AI backend:** All Claude API calls server-side — API key never in client.
**HuggingFace:** Retired. The `hf-deploy` orphan branch is stale.
**Steam:** Phase 4 — GodotSteam plugin. Defer until multiplayer prototype is stable.

---

## Key Files

| File | Purpose |
|---|---|
| `server/main.py` | FastAPI backend — all AI endpoints |
| `server/requirements.txt` | Server Python deps |
| `server/Dockerfile` | Container for deployment |
| `godot/project.godot` | Godot 4 project root |
| `godot/scripts/autoloads/GameState.gd` | Singleton: current mystery, phase, history |
| `godot/scripts/autoloads/ApiClient.gd` | HTTP wrapper for backend calls |
| `godot/scripts/autoloads/NetworkManager.gd` | ENet multiplayer singleton |
| `godot/scripts/data/MysteryData.gd` | Typed GDScript wrapper for mystery JSON |
| `godot/scenes/ui/` | All UI scenes (MainMenu → Generation → Case → Interrogation → Accusation) |
| `part_registry.py` | 1,469-part corpus; sampling logic |
| `coherence_validator.py` | P1 causal-chain + witness + evidence checks (free — no API call) |
| `localization.py` | Era-appropriate name/occupation localization with 3-tier disk cache |
| `extraction_protocols.py` | P1–P4 taxonomy definitions |
| `cli.py` | Terminal dev tools (`generate`, `extract`, `check`, `browse`, `solve`) |
| `docs/WIRING.md` | **Canonical generation architecture** — read before touching generation |
| `SESSIONS.md` | Session-by-session history and full to-do list |
| `RESEARCH_FINDINGS.md` | Writer-grounded mystery taxonomy (C1–C6, M1–M8, F1–F12) |

**Retired (do not modify):**
- `app.py` — Streamlit UI, replaced by Godot client
- HuggingFace `hf-deploy` branch — stale

---

## Active Branch

> **IMPORTANT: The harness creates a new `claude/*` branch each session starting from
> `main`. `main` may lag behind the latest work branch by one or more sessions.
> Always run the divergence check (Step 1 below) before doing anything else.**

The most recently pushed work branch can be found with:
```bash
git fetch origin
git branch -r --sort=-committerdate | grep 'origin/claude/' | head -5
```

The correct branch is the one that contains `godot/` and `server/`.

---

## Session Start Protocol — MANDATORY

### Step 1 — Divergence check (do this FIRST, every single time)

```bash
git fetch origin

# Check if the Godot project and server exist on your current branch:
ls godot/ server/ 2>/dev/null || echo "MISSING — you are on a stale branch, see below"
```

**If `godot/` or `server/` are missing**, the harness dropped you on a branch that
predates the Godot migration. Fix it immediately:

```bash
# Find the most recently pushed work branch:
git branch -r --sort=-committerdate | grep 'origin/claude/' | head -5

# Merge it into your current branch (replace <branch> with what you found above):
git merge origin/<branch>

# Confirm the files are now present:
ls godot/ server/
```

Then continue with Step 2.

### Step 2 — Read current state

Read **the first session block in `SESSIONS.md`** (newest sessions are at the top).
It has the exact next step, any blockers, and decisions that must not be revisited.

### Step 3 — State your starting point

In your first reply: current branch, latest commit hash (`git log --oneline -1`), what you'll do.

### Step 4 — Read architecture docs if needed

Read `docs/WIRING.md` if your task touches generation, localization, or coherence logic.

---

## Session End Protocol — MANDATORY

1. **Update `SESSIONS.md`** — add a new session block at the **TOP** of the file
   (above all previous sessions). Include: files changed, decisions made, next steps.
2. **Update `CLAUDE.md → Current To-Do`** to reflect completed and next items.
3. **Commit and push** on the current working branch.
4. **Tell the user to sync locally** with the exact `git pull` command for the branch.
5. The remote rejects `git push origin main` (HTTP 403). Use GitHub MCP tools to create a PR.

### NEVER end a session without updating SESSIONS.md.

---

## Godot Development Notes

- **Godot version:** 4.6 (GDScript 2.0 — typed, class_name declarations)
- **Scene autoloads** declared in `project.godot`: `GameState`, `ApiClient`, `NetworkManager`
- **Backend URL:** Configured via `ApiClient.SERVER_URL` — default `http://localhost:8000`
  Change to production URL once deployed.
- **Starting the server** (run from the repo root, not from `server/`):
  ```bash
  ANTHROPIC_API_KEY=sk-... uvicorn server.main:app --port 8000
  ```
- **project.godot drift:** Godot rewrites `project.godot` on every open. Before committing,
  run `git checkout -- godot/project.godot` to discard Godot's cosmetic changes unless
  you intentionally modified it.
- **Testing multiplayer:** Run 2 Godot instances; both connect to same localhost server.
- **No Godot binary in repo** — developer must install Godot 4 separately.

### Phase commit tags:
| Tag | Meaning |
|---|---|
| `phase1-backend-done` | FastAPI server + Godot scaffold complete ✅ |
| `phase2-single-player-prototype` | Full single-player loop works in Godot |
| `phase3-multiplayer` | Lobby + 75% mechanic working |
| `phase4-steam` | GodotSteam integrated |

---

## Coding Conventions

- Python 3.8+ (server-side)
- GDScript 2.0 with type annotations (client-side)
- Claude model: `claude-sonnet-4-6`
- Mystery parts: `SOURCE(INDEX)` notation — `C(4)`, `F(2)`, `A(6)`
- Extraction protocols: P1 Skeleton (C1–C6), P2 Architecture (M1–M8), P3 Craft (F1–F8), P4 Texture (F9–F12)
- All generated mysteries must include a `_provenance` field
- API auth (server-side only): (1) `ANTHROPIC_API_KEY` env var, (2) Bearer token from
  `/home/claude/.claude/remote/.session_ingress_token`

---

## Design Principles

Every new feature must answer at least one of these:

### 1. Does it close a feedback loop?
- **Creator signal**: viability rating (1–10) on each mystery
- **Player signal**: accusations, interrogation patterns, time-to-solve
- **Part signal** (future): which `SOURCE(INDEX)` parts appear in high-rated mysteries → weight registry

### 2. Does it preserve mystery coherence?
P1 causal chain must be unbroken: crime → victim → closed world → culprit/motive → resolution.
- Run `coherence_validator.check_parts()` before the Claude generation call
- Run `coherence_validator.check_mystery()` after — attach result as `_coherence` in the JSON

### 3. Does it drive down cost?
API calls are the primary cost driver.

| Rule | Detail |
|---|---|
| Cache localization rulesets | `mystery_database/localization_cache/<era_key>.json` |
| Skip modern-era localization | `_is_modern(setting)` → no API call |
| Compact mapping over full rewrite | Claude returns `[{old,new}]` only |
| Cache extractions | Never re-extract a source already in JSON |
| Coherence is free | `check_mystery()` / `check_parts()` — zero API calls |

**Active caching inventory:**

| Cache | Location | Key | What it stores |
|---|---|---|---|
| Localization rulesets | `mystery_database/localization_cache/<era_key>.json` | location+time_period slug | Name conventions, occupation map, forbidden titles |
| Part extractions | `mystery_database/extractions/*.json` | source filename | P1–P4 parts from source texts |
| Generated mysteries | `mystery_database/generated/*.json` | slug+timestamp | Full mystery dicts with `_coherence` |

---

## Current To-Do (as of April 2, 2026)

Full list in `SESSIONS.md`. Top priorities:

1. **[DONE]** Phase 1 — FastAPI server + Godot project scaffold (`phase1-backend-done`)
2. **[START HERE]** Phase 2 — Single-player Godot prototype: start server, press F5, run
   the full loop (generate → case display → interrogate → accuse → result). Fix any
   scene-tree/node-path errors that surface. Tag `phase2-single-player-prototype` when complete.
3. **[FUTURE]** Phase 3 — Multiplayer: lobby, ENet, 75% clue-sharing, dedicated server
4. **[FUTURE]** Phase 4 — Steam integration (GodotSteam plugin)

Retired / superseded:
- ~~Play-test on HuggingFace~~ — HuggingFace retired
- ~~Merge mystery-versioning-system-TPblK~~ — subsumed by migration
- ~~Load saved mystery dropdown in app.py~~ — replaced by Godot browse screen

> **DO NOT re-run the corpus extraction pipeline.** Expand corpus only by adding new quality source texts.
> **DO NOT modify app.py.** It is retired and will be deleted once Phase 2 is confirmed working.
