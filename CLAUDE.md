# Choose Your Mystery — Claude Code Instructions

## Project Overview
AI-powered social mystery party game. Players investigate crimes, interrogate AI characters,
and compete to solve the case first. Core innovation: the 75% information-sharing mechanic.

Key files:
- `app.py` — Streamlit UI
- `cli.py` — Terminal entry point (subcommands: `generate`, `extract`, `check`, `browse`, `solve`)
- `part_registry.py` — Mystery atomization and part sampling (1,469-part corpus)
- `coherence_validator.py` — P1 causal-chain validator
- `localization.py` — Setting-aware character name/occupation localization (3-tier cache)
- `extraction_protocols.py` — P1–P4 taxonomy definitions
- `SESSIONS.md` — Master session log and consolidated to-do list
- `RESEARCH_FINDINGS.md` — Writer-grounded mystery taxonomy (C1–C6, M1–M8, F1–F12)
- `docs/WIRING.md` — Full technical architecture (schemas, data flow, caching)

Active branch (current work):
- `claude/setup-api-and-mysteries-LRLQK`

Stale branches (do not develop on these):
- `claude/document-research-findings-LdlIV` — superseded
- `claude/mystery-versioning-system-TPblK` — pending merge into main

---

## Session Start Protocol — MANDATORY

At the start of every session you MUST:

1. **Identify the correct branch.** Check `CLAUDE.md → Active branch` above. If it doesn't
   match what you're on, switch:
   ```bash
   git fetch origin
   git checkout claude/setup-api-and-mysteries-LRLQK
   git pull origin claude/setup-api-and-mysteries-LRLQK
   ```

2. **Read SESSIONS.md** — specifically the most recent session block. It contains the exact
   next step, any blockers, and decisions that must not be revisited.

3. **Read docs/WIRING.md** if your task touches generation, localization, coherence, or
   the cinematic brief. The wiring doc is the canonical architecture reference.

4. **State your starting point** in the first reply: branch name, latest commit hash,
   and what you intend to do in this session.

---

## Session End Protocol — MANDATORY

At the end of every session you MUST:

1. **Run the session summary script:**
   ```bash
   python scripts/session_summary.py --auto
   ```
   If that fails, write the summary manually into `SESSIONS.md` and commit it.

2. **Merge the working branch into main:**
   ```bash
   git fetch origin main
   git checkout -b main --track origin/main   # first time only; else: git checkout main
   git pull origin main
   git merge <working-branch> --no-ff -m "Merge <branch> into main — <one-line summary>"
   git push origin main
   git checkout <working-branch>              # return to working branch
   ```
   This ensures `main` always reflects the current releasable state.

3. **Update `CLAUDE.md → Active branch`** if the branch name changed.

4. **Update `CLAUDE.md → Current To-Do`** to reflect what was completed and what is next.

### NEVER end a session without updating SESSIONS.md and merging to main.

---

## Coding Conventions
- Python 3.8+
- Claude model: `claude-sonnet-4-6`
- Mystery parts use `SOURCE(INDEX)` notation: `C(4)`, `F(2)`, `A(6)`
- Extraction protocols: P1 Skeleton (C1-C6), P2 Architecture (M1-M8), P3 Craft (F1-F8), P4 Texture (F9-F12)
- All generated mysteries must include a `_provenance` field
- UI is Streamlit; backend scripts are CLI via `cli.py`
- API auth: use Bearer token from `/home/claude/.claude/remote/.session_ingress_token` when `ANTHROPIC_API_KEY` is not set (see `extract_test_mysteries.py:_get_token()`)

---

## Design Principles — Feedback Loops, Coherence, Cost

Every new feature should answer at least one of these three questions:

### 1. Does it close a feedback loop?
Feedback loops are the mechanism by which the game improves. Before writing new code, ask:
- **Player signal**: Can player behavior (accusations, interrogation patterns, time-to-solve) feed back into which parts are used more or less?
- **Quality signal**: Is there a way to score or flag a generated mystery for coherence without replaying it?
- **Part signal**: Which `SOURCE(INDEX)` parts co-occur in high-rated mysteries? Can the registry weight them?

Prefer code that *captures* signal (even just logging) over code that generates more content with no signal.

### 2. Does it preserve mystery coherence?
A mystery is coherent when its P1 elements are causally consistent: crime → victim → closed world → culprit/motive → resolution must form an unbroken chain. Before adding generation features:
- P1 skeleton must be validated before P2 elements are added
- Motive must be consistent with suspect archetype
- Reveal mechanic must be satisfiable given the closed world's constraints
- When mixing parts across source mysteries, flag incompatibilities explicitly (don't silently blend)

The `_provenance` field exists precisely to make incoherence traceable. Use it.

### 3. Does it drive down cost?
Claude API calls are the primary cost driver. This is not just a preference — it is a standing mandate. **Before writing any code that calls the API, actively look for a caching or efficiency opportunity.**

Standing rules:
- **Cache extractions**: never re-extract a source text that already has a JSON result
- **Cache localization rulesets**: `mystery_database/localization_cache/` holds per-era naming rules; consult before making a localization call (see `localization.py`)
- **Skip modern-era localization**: contemporary / near-future settings need no localization call — modern names are already correct
- **Compact mapping over full rewrite**: when asking Claude to transform structured data, have it return only a mapping/diff and apply it in Python — never round-trip a full JSON blob
- **Test on 6**: use `extract_test_mysteries.py` (free, already extracted) before running corpus pipeline
- **Protocol triage**: run P1 first; only escalate to P2/P3 if P1 quality is high
- **Batch before prompting**: assemble all parts for a generation request before calling Claude, not incrementally
- **Dry-run first**: all pipeline scripts should support `--dry-run` to validate logic without API calls
- **Check coherence free**: `coherence_validator.check_mystery()` and `check_parts()` make zero API calls — always run these before deciding to re-generate

**Active caching inventory** (update this when you add new caches):
| Cache | Location | Key | What it stores |
|---|---|---|---|
| Localization rulesets | `mystery_database/localization_cache/<era_key>.json` | location+time_period | Name conventions, occupation map, forbidden titles |
| Part extractions | `mystery_database/extractions/*.json` | source filename | P1–P4 parts extracted from source texts |
| Generated mysteries | `mystery_database/generated/*.json` | slug+timestamp | Full mystery dicts with coherence report |

When you add a new cache, add a row to this table.

---

## Current To-Do (as of March 12, 2026)
See `SESSIONS.md` for the full prioritized list. Top items:

1. **Add `ANTHROPIC_API_KEY` secret to HuggingFace Space settings** (unblocks production)
2. **Full corpus run**: `python cli.py extract --protocol P1P2` (359 books → ~700 new parts)
3. **Merge `claude/mystery-versioning-system-TPblK`** once quality items validated
4. **Browse UI**: add a "Load saved mystery" dropdown to `app.py` so past mysteries are accessible
5. **Player knowledge tracking**: implement the 75% sharing mechanic in the UI
