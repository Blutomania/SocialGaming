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

Current phase: **Phase 3d — Lobby flow, room codes, QR display on host screen**.

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
| `part_registry.py` | 1,469-part corpus; sampling logic; `load_registry()` also loads every JSON in `mystery_database/extractions/` live at runtime |
| `coherence_validator.py` | P1 causal-chain + witness + evidence checks (free — no API call) |
| `localization.py` | Era-appropriate name/occupation localization with 3-tier disk cache |
| `extraction_protocols.py` | P1–P4 taxonomy definitions — still active, used by `scripts/extract_from_pdfs.py` |
| `scripts/extract_from_pdfs.py` | Sanctioned way to add a **single new source** (e.g. a PDF) to the live corpus — extracts P1 parts, writes to `mystery_database/extractions/`. Distinct from the frozen bulk pipeline below. Invoke with `python3`, not `python` (this environment has no `python` alias). Add `--anthology` for a short-story collection PDF (one novel-narrative sampling per file otherwise) — detects per-story boundaries and extracts each story as its own corpus source with its own full text; always `--dry-run` an anthology first to review the detected split before spending API calls. |
| `docs/WIRING.md` | **Canonical generation architecture** — read before touching generation |
| `SESSIONS.md` | Session-by-session history and full to-do list |
| `RESEARCH_FINDINGS.md` | Writer-grounded mystery taxonomy (C1–C6, M1–M8, F1–F12) — prose novelists |
| `SCREEN_CRAFT_FINDINGS.md` | Companion to above: film/TV directors & screenwriters craft grounding |
| `PARTY_CRAFT_FINDINGS.md` | Companion to above: live/social-deduction game mechanics grounding |
| `SOURCING_METHODOLOGY.md` | Shared sourcing discipline (confidence tiers, corroboration rule) for the three craft-grounding docs above, and the process for adding a new media type |
| `craft_grounding.py` | Retrieval layer over the craft-grounding docs — parses them into a confidence-tiered index and feeds relevant guidance into all four generation call-sites in `server/main.py`. See `docs/WIRING.md` → "Craft-grounding retrieval (RAG layer)" before touching this. |

**Deprecated (do not touch — kept for historical reference only):**
- `deprecated/` — all pre-Godot Streamlit/HuggingFace-era Python tooling (`app.py`, `cli.py`,
  `corpus_loader.py`, `run_corpus_pipeline.py`, `test_mysteries.py`, `mystery_generator.py`,
  `gameplay_validator.py`, `demo_acquisition.py`, `mystery_data_acquisition.py`,
  `mystery_database_plan.md`, `extract_test_mysteries.py`, `browse_mysteries.py`,
  `GETTING_STARTED.md`, `end_of_session.sh`, `requirements.txt`). This was the single-player
  Streamlit creator tool hosted on HuggingFace Spaces — superseded by the Godot client +
  FastAPI server above. Kept for provenance/history, not for use.
  - **Exception:** `extraction_protocols.py` was briefly moved here and has been **restored to
    root** — it's a live dependency of `scripts/extract_from_pdfs.py`, which is still how new
    corpus sources get added (see Key Files above). Everything else in `deprecated/` really is inert.

---

## Active Branch

**`main`** — reconciliation is complete (PR #1 merged July 9, 2026, commit `faf52e0`). Start new
work from `main` directly; there is no other active branch right now.

> **Branch hygiene note (resolved July 9, 2026):** several past sessions had been auto-assigned
> fresh branches off older commits instead of continuing the active one, so multiple divergent
> "current states" of this repo existed in parallel (a Godot line, a since-abandoned
> pre-migration line, and a stranded PDF-ingestion line). All of that was reconciled into
> `claude/mystery-pdf-extraction-0fisq0` and merged into `main` via PR #1. The five superseded
> branches (`claude/review-godot-migration-GiLDz`, `claude/fix-godot-performance-QyXLQ`,
> `claude/start-godot-migration-mNrWD`, `claude/setup-api-and-mysteries-LRLQK`,
> `claude/mystery-versioning-system-TPblK`) were confirmed deleted the same day. If a future
> session gets auto-assigned a stale branch again, check this file on `main` first — don't trust
> whatever branch name the harness handed you until you've compared it against `main`'s
> `SESSIONS.md`.

---

## Session Start Protocol — MANDATORY

1. **Verify branch:**
   ```bash
   git fetch origin
   git checkout main
   git pull origin main
   ```
   Create a new feature branch off `main` for your session's work if it's more than a trivial
   change — don't accumulate unrelated work directly on `main`.
2. **Read the most recent block in `SESSIONS.md`** — exact next step, blockers, decisions.
3. **State your starting point:** branch, latest commit hash, what you'll do.
4. **Read `docs/WIRING.md`** if touching generation, localization, or coherence logic.

---

## Session End Protocol — MANDATORY

1. **Update `SESSIONS.md`** with new session block (files changed, decisions, next steps).
2. **Update `CLAUDE.md → Current To-Do`** to reflect completed and next items.
3. **Commit and push** on your session's feature branch.
4. **Tell the user to sync locally.**
5. The remote rejects `git push origin main` (HTTP 403). Use GitHub MCP tools to create a PR,
   and merge it once it's clean rather than leaving it to accumulate — that's what caused the
   July 9, 2026 branch-reconciliation mess documented above.

### NEVER end a session without updating SESSIONS.md.

---

## Godot Development Notes

- **Godot version:** 4.x (GDScript 2.0 — typed, class_name declarations)
- **Scene autoloads** declared in `project.godot`: `GameState`, `ApiClient`, `NetworkManager`
- **Backend URL:** Configured via `ApiClient.SERVER_URL` — default `http://localhost:8000`
  Change to production URL once deployed.
- **Testing single-player:** Run FastAPI server locally (`cd server && uvicorn main:app --port 8000`),
  then press F5 in Godot editor.
- **Testing multiplayer:** Run 2 Godot instances; both connect to same localhost server.
- **No Godot binary in repo** — developer must install Godot 4 separately.

### Phase session annotations (commit tags):
| Tag | Meaning |
|---|---|
| `phase1-backend-done` | FastAPI server + Godot scaffold complete |
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
| Adding one new source | Use `scripts/extract_from_pdfs.py <file-or-dir> --protocol P1` (`python3`, not `python`), not the frozen bulk pipeline |

**Active caching inventory:**

| Cache | Location | Key | What it stores |
|---|---|---|---|
| Localization rulesets | `mystery_database/localization_cache/<era_key>.json` | location+time_period slug | Name conventions, occupation map, forbidden titles |
| Part extractions | `mystery_database/extractions/*.json` | source filename | P1–P4 parts from source texts |
| Generated mysteries | `mystery_database/generated/*.json` | slug+timestamp | Full mystery dicts with `_coherence` |

---

## Multiplayer Architecture (decided Session 12)

**Jackbox model:**
- **Godot desktop** = host/TV screen, Steamworks-connected
- **HTML phone client** = thin browser page served by FastAPI at `/play`, no install
- **Transport** = FastAPI WebSocket (replaces HTTP polling); room per `game_id`
- **Room codes** = short alphanumeric, shown on host screen (QR code future)
- **ENet is desktop-only** — browsers block UDP; use `WebSocketMultiplayerPeer` if Godot web export ever needed

**Why keep Godot (not all-Python):**
GodotSteam is the best Steamworks path; Godot Linux export = Steam Deck support free; host screen can be cinematic while phone UI is minimal.

---

## Current To-Do (as of Session 22, July 31, 2026)

Full list in `SESSIONS.md`. Top priorities:

1. **[DONE]** Phase 1 — FastAPI server + Godot project scaffold
2. **[DONE]** Phase 2 — Single-player Godot prototype (all 5 screens functional)
3. **[DONE]** Phase 3 — Multiplayer investigation phases + clue sharing
   - **[DONE]** 3a: Mystery gen updated (investigation_areas + leads in JSON)
   - **[DONE]** 3b: Game session store + 8 server endpoints
   - **[DONE]** 3c: WebSocket upgrade + mobile.html phone client + .tscn wiring
   - **[DONE]** 3d: Lobby flow, room codes, host-screen display (Session 14)
4. **[START HERE]** Phase 3e — Avatar pool system + player history tracking. Design is locked and
   merged (PR #4, Session 17) — full spec in `docs/WIRING.md` under "Avatar system + player
   profiles (Phase 3e)" (two-layer model: shared era-keyed base looks + persistent per-player
   signature accessory from a fixed catalog). Nothing is built yet; see that section's
   "What still needs building" list. Sign off on the proposed 16-item accessory catalog first.
5. **[DONE]** PR #1 (branch reconciliation) merged into `main` — merge commit `faf52e0`, July 9 2026.
   `main` is now the source of truth: full Godot migration, `deprecated/` Streamlit archive, and
   the PDF-ingestion corpus work are all present.
6. **[DONE]** The five superseded branches were confirmed deleted (owner, July 9 2026):
   `claude/review-godot-migration-GiLDz`, `claude/fix-godot-performance-QyXLQ`,
   `claude/start-godot-migration-mNrWD`, `claude/setup-api-and-mysteries-LRLQK`,
   `claude/mystery-versioning-system-TPblK`
7. **[ONGOING]** Corpus growth — the anthology (`The_Best_of_Mystery_1980_Anthology`) is **[DONE]**:
   run for real, all 63/63 stories extracted (Session 21), source_id collision fix confirmed
   working on the real output. Corpus is larger than this list previously implied — besides the
   12 PDF-sourced entries via `scripts/extract_from_pdfs.py` (now 12 novels + 63 anthology
   stories = 75), there are **283 additional `ebook_*` entries** from an earlier bulk-pipeline run
   (bookrix.com sources, P1+P2 depth) already sitting in `mystery_database/extractions/` —
   confirmed present, not previously tracked in this file (Session 21).
   **Sourcing-ratio guideline (Session 21):** favor short-story anthology PDFs heavily over
   individual novels for new clearance decisions — roughly 3–5 anthologies cleared per 1 novel —
   since an anthology yields 15–63x the source_ids per single legal-clearance decision at
   currently-identical extraction depth (both the 12 curated novels and the 63 stories are P1-only;
   novels only earn a depth advantage once `--protocol P1P2`, or P3/P4, actually gets used on them).
   `mystery_database/new_sources/` still holds: three full novels (Stevenson ×2, Tana French)
   queued for later one-at-a-time ingestion; one `.html` file (`extract_from_pdfs.py` only reads
   PDFs — unsupported as-is); and **`The_Devotion_of_Suspect_X` (Higashino) — found untriaged in
   Session 21**, not one of Session 20's original 9 categorized files, confirmed NOT a duplicate of
   the existing Higashino extraction (different novel: *Miracles of the Namiya General Store*).
   Owner ruled out deleting it; still needs an actual triage call (queue / skip / other).
8. **[FUTURE]** Phase 4 — Steam integration (GodotSteam plugin)
9. **[ONGOING]** Repo-wide branch cleanup (Session 18) — 9 fully-merged branches identified as
   safe to delete, plus a further 21 stale unmerged branches the owner is triaging on their own
   schedule (see `SESSIONS.md` Session 18). **`dev/mind-your-friends` is a separate, real second
   project sharing this repo — do not touch it in any cleanup pass.**
10. **[DONE, Session 22]** RAG (retrieval-augmented generation) for mystery best-practices —
    **wired into generation.** `craft_grounding.py` parses `RESEARCH_FINDINGS.md`,
    `SCREEN_CRAFT_FINDINGS.md`, and `PARTY_CRAFT_FINDINGS.md` into a retrievable, confidence-tiered
    index and injects relevant guidance into all four generation call-sites in `server/main.py`
    (`_generate_mystery_dict`, `_generate_witness_scene`, `_investigate_area_with_ai`,
    `_follow_lead_with_ai`) — full design, rationale table, and extension guide in `docs/WIRING.md`
    → "Craft-grounding retrieval (RAG layer)". Read that section before touching any of it. Zero
    added API calls — retrieval is a local index lookup. Auditable by design: every call records
    which citations it used (routing differs by broadcast scope — see that doc section).
    Remaining open items, not part of this build:
    - Finish verifying `PARTY_CRAFT_FINDINGS.md` against full source text (Session 21's partial
      pass — Jackbox + 3 of 4 Medway posts pasted, findings sorted but not yet written into the
      doc itself) — the retrieval layer works fine on the doc as it stands today, but the
      verification pass is still worth finishing for citation accuracy.
    - True-crime podcast sourcing — the one media type not yet covered; becomes retrievable
      automatically the moment the doc exists, per `SOURCING_METHODOLOGY.md`'s process.
    - Human decision on the accumulated "new concepts flagged" candidates across all three docs
      (e.g. howcatchem structural mode, production-security-as-craft-practice) — whether any
      warrant a new `extraction_protocols.py` code. Explicitly kept separate from "wiring the
      retrieval mechanism" as its own decision (see Session 22's chat log) — not required for the
      RAG layer to work, only for the taxonomy itself to grow.
11. **[IN PROGRESS, Session 21]** Multiplayer lockstep redesign — a live "Murder on Mars" use-case
    walkthrough against the actual running code (not this file's aspirational description) found
    real gaps: the "75%-random-share" mechanic described above doesn't exist in the code (real
    mechanic: player-choice minimum-share threshold, 50/60/70% by difficulty); interrogation was
    free text, not a pick-list; and **there is no backend endpoint anywhere for resolving a
    multiplayer accusation** — the only accusation code (`accusation.gd`) is single-player-era,
    client-local. Full design in `docs/WIRING.md` → "Multiplayer lockstep round system". Built and
    verified so far: the lockstep round state machine (`stage`/`round`, additive alongside the
    legacy per-player `phase` — nothing existing broken), and the witness interrogation redesign
    (batched, deduped, shared-scene generation replacing N isolated per-question calls). Still
    open, in dependency order: accusation-resolution backend (independent, also unblocks the
    end-game resolution/summation scene); crime-scene investigation redesign and the "what I know
    vs. what's shared" comparison screen (both depend on the lockstep mechanism, now in place);
    lead-claim reservation + scaling lead count to max players (8, per item 4's Phase 3e decision).
12. **[ONGOING, Session 22]** Extraction-pipeline efficiency gap, found while auditing whether
    extraction actually supports the coherence engine's dialogue generation — two concrete,
    code-verified issues, neither fixed yet:
    - `part_registry.py`'s `_atomize_extraction()` expects P2-tier keys that a P1-only extraction
      never produces, so every P1-only source (all 12 novels + all 63 anthology stories) can only
      ever populate 3 of the registry's 8 sampling axes — confirmed directly against
      `story01_winter_run.json`.
    - Even fully P1+P2-depth sources have craft-relevant fields (`clue_fairness`,
      `media_and_audience`, `investigator_wound`, `victim`, `resolution`, `investigator`) that the
      registry extracts and then never reads, for any source, at any depth — confirmed against a
      real `ebook_*` extraction (14 populated fields, only 8 ever read).
    Two independent fixes, not mutually exclusive: extend `part_registry.py`'s field mapping to
    stop discarding the 6 unused fields (no new API cost, unlocks value already paid for); and/or
    re-extract the 75 P1-only sources at `--protocol P1P2` (new API cost, backfills their missing
    axes specifically). Full detail in `SESSIONS.md` Session 22.

> **DO NOT re-run the frozen bulk corpus pipeline** (`deprecated/run_corpus_pipeline.py`). Expand
> the corpus only via `scripts/extract_from_pdfs.py`, adding one quality source at a time.
> **DO NOT touch `deprecated/`** except the one restored exception noted above. It exists for
> historical reference only.
