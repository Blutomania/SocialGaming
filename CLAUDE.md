# Choose Your Mystery — Claude Code Instructions

## Project Overview
AI-powered social mystery party game. Players investigate crimes, interrogate AI characters,
and compete to solve the case first. Core innovation: the 75% information-sharing mechanic.

Current phase: **mystery creator / output verification** (single-player, creator-side).
Next phase: multiplayer gameplay with the 75% sharing mechanic.

---

## Key Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — generation, interrogation, accusation, viability rating |
| `cli.py` | Terminal entry point (`generate`, `extract`, `check`, `browse`, `solve`) |
| `part_registry.py` | 1,469-part corpus; sampling logic |
| `coherence_validator.py` | P1 causal-chain + witness + evidence checks (free — no API call) |
| `localization.py` | Era-appropriate name/occupation localization with 3-tier disk cache |
| `extraction_protocols.py` | P1–P4 taxonomy definitions |
| `scripts/browse_mysteries.py` | Rich terminal mystery browser (scene, cast, evidence, solution) |
| `docs/WIRING.md` | **Canonical architecture reference** — read before touching generation |
| `SESSIONS.md` | Session-by-session history and full to-do list |
| `RESEARCH_FINDINGS.md` | Writer-grounded mystery taxonomy (C1–C6, M1–M8, F1–F12) |

---

## Active Branch

**`claude/review-and-docs-n4rHY`** — all current development goes here.

Stale / pending:
- `claude/mystery-versioning-system-TPblK` — pending merge into main (CLI + part registry)
- `claude/setup-api-and-mysteries-LRLQK` — merged into main (March 2026)

---

## Session Start Protocol — MANDATORY

1. **Verify branch:**
   ```bash
   git fetch origin
   git checkout claude/review-and-docs-n4rHY
   git pull origin claude/review-and-docs-n4rHY
   ```
2. **Read the most recent block in `SESSIONS.md`** — it has the exact next step, any blockers,
   and decisions that must not be revisited.
3. **Read `docs/WIRING.md`** if your task touches generation, localization, coherence, or
   the cinematic brief.
4. **State your starting point** in the first reply: branch, latest commit hash, what you'll do.

---

## Session End Protocol — MANDATORY

1. **Update `SESSIONS.md`** with a new session block (files changed, decisions made, next steps).
   Run `python scripts/session_summary.py --auto` or write it manually.
2. **Update `CLAUDE.md → Current To-Do`** to reflect completed and next items.
3. **Commit everything** on the working branch and push.
4. **Tell the user to sync locally** (see local sync steps at bottom of each SESSIONS.md block).
5. The remote rejects `git push origin main` (HTTP 403). Promote to main via PR:
   ```bash
   gh pr create --base main --head claude/review-and-docs-n4rHY --title "..."
   ```

### NEVER end a session without updating SESSIONS.md.

---

## Coding Conventions

- Python 3.8+
- Claude model: `claude-sonnet-4-6`
- Mystery parts: `SOURCE(INDEX)` notation — `C(4)`, `F(2)`, `A(6)`
- Extraction protocols: P1 Skeleton (C1–C6), P2 Architecture (M1–M8), P3 Craft (F1–F8), P4 Texture (F9–F12)
- All generated mysteries must include a `_provenance` field
- UI: Streamlit (`app.py`). Backend scripts: CLI via `cli.py`
- API auth priority: (1) `ANTHROPIC_API_KEY` env var, (2) Bearer token from
  `/home/claude/.claude/remote/.session_ingress_token`

---

## Design Principles

Every new feature must answer at least one of these:

### 1. Does it close a feedback loop?
- **Creator signal**: viability rating (1–10) on each mystery
- **Player signal** (future): accusations, interrogation patterns, time-to-solve
- **Part signal** (future): which `SOURCE(INDEX)` parts appear in high-rated mysteries → weight registry

Prefer code that *captures* signal over code that generates more content with no signal.

### 2. Does it preserve mystery coherence?
P1 causal chain must be unbroken: crime → victim → closed world → culprit/motive → resolution.
- Run `coherence_validator.check_parts()` before the Claude generation call
- Run `coherence_validator.check_mystery()` after — attach result as `_coherence` in the JSON
- The `_provenance` field makes incoherence traceable back to specific corpus parts

### 3. Does it drive down cost?
API calls are the primary cost driver. **Before any new API call, look for a cache hit.**

| Rule | Detail |
|---|---|
| Cache localization rulesets | `mystery_database/localization_cache/<era_key>.json` — derived on first use, reused forever |
| Skip modern-era localization | `_is_modern(setting)` → no API call |
| Compact mapping over full rewrite | Claude returns `[{old,new}]` only; Python substitutes |
| Cache extractions | Never re-extract a source text that already has a JSON result |
| Test on 6 | Use `extract_test_mysteries.py` (free) before running corpus pipeline |
| P1 first | Only escalate to P2/P3 if P1 quality is confirmed high |
| Dry-run first | All pipeline scripts support `--dry-run` |
| Coherence is free | `check_mystery()` / `check_parts()` make zero API calls |

**Active caching inventory:**

| Cache | Location | Key | What it stores |
|---|---|---|---|
| Localization rulesets | `mystery_database/localization_cache/<era_key>.json` | location+time_period slug | Name conventions, occupation map, forbidden titles |
| Part extractions | `mystery_database/extractions/*.json` | source filename | P1–P4 parts from source texts |
| Generated mysteries | `mystery_database/generated/*.json` | slug+timestamp | Full mystery dicts with `_coherence` |

Add a row here whenever you introduce a new cache.

---

## Core System Architecture

These four system categories are **essential** to the project. Every new feature
must account for at least one of them. Read the relevant subsection before
touching the corresponding layer.

### 1. Event Queuing System

**Status: Planned — not yet implemented.**

Currently all operations are synchronous: Streamlit handles UI events implicitly
at the framework level, and the CLI uses blocking I/O. There is no application-level
event queue.

When **multiplayer** is introduced (Session 9 design decision), an event queue will
be required to handle concurrent player actions — question submissions, accusations,
info-sharing triggers, and game-state transitions.

Design constraints when building this:
- Events must be serialisable to JSON (persisted to `mystery_database/` like all
  other state)
- Each event must carry a `player_id`, `mystery_id`, `timestamp`, and `event_type`
- Queue must support the 75% information-sharing mechanic: fan-out to all players
  except the originating player

**Do not implement until multiplayer invite mechanic is underway.**

---

### 2. Input Systems

Two parallel input surfaces exist. Add new inputs to **both** or clearly document
which surface handles them.

| Surface | File | Key functions / widgets |
|---------|------|------------------------|
| Streamlit UI | `app.py` | `st.text_input()`, `st.selectbox()`, `st.radio()`, `st.number_input()` |
| Rich CLI | `cli.py` | `_ask(prompt, default)`, `_ask_int(prompt, default)`, `_confirm(prompt, default)` |

**Pattern:** CLI wrappers detect Rich availability and degrade gracefully to plain
`input()`. Always follow this pattern — never call `input()` or `Prompt.ask()`
directly outside of these helpers.

---

### 3. Drawing Systems

Two parallel rendering surfaces. Add new UI to **both** or clearly document
which surface renders it.

| Surface | File | Key functions / components |
|---------|------|---------------------------|
| Streamlit UI | `app.py` | `st.title()`, `st.markdown()`, `st.metric()`, `st.expander()`, `st.balloons()` |
| Rich terminal | `cli.py` | `_panel()`, `_rule()`, `_print()`, `_banner()`, `_spinner()` |
| Validation output | `coherence_validator.py` | `rich_panels(report)` — yields Rich Panel content |

**Pattern:** Streamlit is declarative and re-runs top-to-bottom on each interaction.
Rich uses imperative print calls. Keep rendering logic out of business logic — pass
formatted strings/dicts into display helpers, not raw mystery objects.

---

### 4. Data Retrieval Systems

All retrieval is **file-based** from `mystery_database/`. No external database.
In-memory indexing is loaded once per session.

| Component | File | Entry point | What it retrieves |
|-----------|------|-------------|-------------------|
| Part corpus sampling | `part_registry.py` | `sample_for_generation(target_setting)` | Compatible atomised parts (1,469-part registry) |
| Scenario retrieval | `mystery_generator.py` | `_retrieve_relevant_scenarios(themes, limit=3)` | Similar past mysteries for RAG context |
| Mystery loader | `mystery_generator.py` | `_load_scenario(scenario_id)`, `_load_index()` | Full mystery JSON + database index |
| Database loader | `corpus_loader.py` | Module-level load on import | Mystery database from disk |

**Rules:**
- Always check the cache before any API call (see caching inventory above)
- `mystery_database/index.json` is the single source of truth for what mysteries exist
- Never write directly to `mystery_database/generated/` outside of the generation
  pipeline — always go through `mystery_generator.py`

---

## Current To-Do (as of March 27, 2026)

Full list in `SESSIONS.md`. Top priorities:

1. **[DONE]** ~~Add `ANTHROPIC_API_KEY` to HuggingFace Space secrets~~ — completed March 12, 2026
2. **[START HERE]** Play-test — generate 5–10 mysteries in the live Space, verify coherence passes, rate with viability widget
3. **Merge `claude/mystery-versioning-system-TPblK`** (CLI + part registry) into main
4. **Load saved mystery** — add dropdown to `app.py` to browse and reload past mysteries from disk
5. **Multiplayer invite mechanic** — shareable link + short game code (Jackbox model); global info sharing to start; see SESSIONS.md Session 9 design decision for full spec
6. **[LOW PRIORITY]** Feedback persistence — save viability rating + behavioral signals back to mystery JSON; defer until after play-testing

> **DO NOT re-run the corpus extraction pipeline.** Previous failures were due to source texts being too brief or not a mystery — re-running produces the same results. Expand the corpus only by adding new quality source texts.
