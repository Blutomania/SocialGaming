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
| `craft_grounding.py` | Retrieval layer over the craft-grounding docs — parses them into a confidence-tiered index and feeds relevant guidance into all five generation call-sites in `server/main.py`. See `docs/WIRING.md` → "Craft-grounding retrieval (RAG layer)" before touching this. |

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

## Current To-Do (as of Session 23, August 3, 2026)

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
   **[IN PROGRESS, Session 27]** The 22+-anthology ingestion is underway, not finished. Session 27
   was almost entirely git housekeeping (see `SESSIONS.md`) plus a duplicate-source triage: cross-
   referenced the owner's ~26 staged local files against the real corpus and caught two real
   near-misses — renamed duplicate PDFs of already-extracted books (*Leavenworth Case*, *Red House
   Mystery*), and, more seriously, the already-fully-extracted 63-story Hitchcock 1980 anthology
   itself still sitting in `new_sources/` (would have re-spent real API cost re-extracting 63
   already-owned stories). Owner removed both categories. Confirmed the extraction pipeline still
   has zero content-based dedup (`_slug()` keys purely off the input PDF's filename) — worth a
   pre-flight duplicate check on every future batch, not just this one; a standalone checker script
   was written for this (scratchpad-only, not committed to the repo).

   Remaining 21 anthology PDFs were `--dry-run`'d: **10 came back clean** (full-book page ranges,
   real per-story detection — the *Best American Mystery Stories* years 2005–2017/215/"4" plus
   *Years Best Mystery & Suspense 1993*, ~207 stories) and were moved to
   `mystery_database/new_sources/_anthologies/_ready/` with the real extraction command handed to
   the owner — **not yet run as of session close.** The other **11 have real detection problems**
   and are intentionally being held back, uncosted: 5 where the detector only caught back-matter and
   missed the entire body of stories, 3 where the whole book got detected as a single oversized
   "story" (459K–533K characters — a full anthology misattributed to one author, not a short story),
   and 3 broken/wrong-fit (one detected 0 stories; one nonfiction true-crime collection flagged for
   a separate taxonomy-fit decision). Full per-file breakdown in `SESSIONS.md` Session 27 — don't
   re-litigate it from scratch, the analysis is already done, just needs someone to act on the
   11 held-back files whenever there's appetite.

   Also unrun this session: the 4-file `_novels/` batch (*39 Steps*, *Behold Here's Poison*,
   *Mystery of the Chinese Ring*, *Whose Body?*) — never got even a `--dry-run` yet.

   **[CHECKED, Session 33 — August 20 2026]** That "next session should check" list is now
   answered, by measurement rather than by asking:
   - **The extraction runs happened.** `mystery_database/extractions/` holds **570 files**, of
     which **281 are `pdf_*`** — up from 75. So the `_ready/` anthology batch (and more) was run.
   - **The registry WAS regenerated — and still lost 13 sources.** Checked-in
     `part_registry.json` was **4,807 parts / 556 sources** against a fresh build's **4,952 /
     569**, so 13 sources and 145 parts were extracted, on disk, and never sampled.
     **Do not read this as "nobody remembered to regenerate" — an earlier draft of this note said
     that and it was wrong.** `20c3ee3` (owner, August 10) is titled "anthology extractions +
     regenerated part_registry" and did exactly that. The 20 extraction files missing from the
     index it produced were added *in that same commit*, and they cluster: ten stories from
     *Best American 2016 (Elizabeth George)* and three from *2007 (Hiaasen)* — the 13 that yield
     parts — plus 7 that yield none (see below). That is the signature of a regeneration run while
     those two books were still extracting, with everything committed together afterwards. Git
     cannot show the ordering (one commit, no intermediate timestamps), but nothing else explains
     the clustering.
     **Why this matters for the fix:** the failure was not neglect, it was a race between a long
     extraction run and a manual regeneration step. Doing the conscientious thing still silently
     lost 13 sources, which is precisely what an automatic check fixes and a reminder does not.
   - **[FIXED, Session 33]** Both halves done, no API calls: the registry is regenerated
     (4,952 / 569 committed), and `load_registry()` now has a real staleness check — see item 14.
   - **[OPEN, found in the same pass] 7 anthology extractions are all-null and contribute nothing.**
     `pdf_the_best_american_mystery_stor__story19_a_quiet_place_to_hide`,
     `__story21_remembering_the_rain`, `__story21_trip_to_reno_...`, `__story22_doggy_style`,
     `__story22_the_heroism_of_lieutenant_wills_...`, `__story22_the_women_s_room`,
     `__story22_these_two_guys_thuglit_november`. Every P1 field is `null` with `confidence: "low"`
     and **no `_meta.extraction_warnings`**, so by item 13's logic they read as a genuine "nothing
     found" rather than a caught parse failure — which is implausible for seven mystery short
     stories. They occupy filenames, so the dedup-by-filename rule means a re-run will skip them
     unless they are deleted first. Worth a look before the next batch; not diagnosed here.
8. **[FUTURE]** Phase 4 — Steam integration (GodotSteam plugin)
9. **[ONGOING]** Repo-wide branch cleanup (Session 18) — 9 fully-merged branches identified as
   safe to delete, plus a further 21 stale unmerged branches the owner is triaging on their own
   schedule (see `SESSIONS.md` Session 18). **`dev/mind-your-friends` is a separate, real second
   project sharing this repo — do not touch it in any cleanup pass.**

   **`dev/cryptic-challenge` is NOT a third project (verified Session 29, August 17 2026).**
   The name has repeatedly been read — including by a Claude session, which cited it as evidence
   of a third studio title — as though it were a sibling of CYM and MYF. It is not. Verified
   against the actual refs, not the name:
   - It points at commit `ea5af2f`, and **`dev/choose-your-mystery` points at the exact same
     commit.** Two names, one ref.
   - That commit is a March 31, 2026 snapshot of the **pre-Godot Streamlit CYM tree** (`app.py`,
     `cli.py`, `corpus_loader.py`, `run_corpus_pipeline.py` — what now lives in `deprecated/`).
   - Zero unique commits vs `main`. Everything on it is already here.
   - Searched every branch's full history: **no file with "cryptic" in its name has ever
     existed**, and no commit message mentions it.

   So it is a stale duplicate pointer with a misleading name — nothing to archive, nothing to
   preserve. Owner cleared it for deletion; it needs the GitHub UI, since `git push --delete`
   hits the same 403 that blocks pushes to `main` and no branch-delete tool is exposed via the
   GitHub MCP server (a Session 29 attempt was also blocked by the permission classifier).
   Recreatable with `git branch dev/cryptic-challenge ea5af2f` if ever wanted.

   **Caveat that outlives the branch:** if a real "Cryptic Challenge" project exists, its work is
   **not in this repo** and deleting this pointer archives nothing. Don't treat the branch as
   that project's record.
10. **[DONE, Session 22; extended Session 26]** RAG (retrieval-augmented generation) for mystery
    best-practices — **wired into generation.** `craft_grounding.py` parses `RESEARCH_FINDINGS.md`,
    `SCREEN_CRAFT_FINDINGS.md`, and `PARTY_CRAFT_FINDINGS.md` into a retrievable, confidence-tiered
    index and injects relevant guidance into all five generation call-sites in `server/main.py`
    (`_generate_mystery_dict`, `_generate_witness_scene`, `_investigate_area_with_ai`,
    `_follow_lead_with_ai`, and — added Session 26 — `_generate_resolution_narrative`) — full design, rationale table, and extension guide in `docs/WIRING.md`
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
12. **[PARTIALLY FIXED, Session 22 audit / Session 23 fix]** Extraction-pipeline efficiency gap,
    found while auditing whether extraction actually supports the coherence engine's dialogue
    generation — two concrete, code-verified issues:
    - **[DONE, Session 23]** Even fully P1+P2-depth sources had craft-relevant fields
      (`clue_fairness`, `media_and_audience`, `investigator_wound`, `victim`, `resolution`,
      `investigator`) that the registry extracted and then never read, for any source, at any
      depth — confirmed against a real `ebook_*` extraction (14 populated fields, only 8 ever
      read). Fixed by extending `part_registry.py`'s `KEY_TO_IDX`; see item 14 below for the full
      fix (also resolved the pre-existing `evidence_type`/`alibi` axis mislabeling in the same
      pass). `media_and_audience` remains deliberately unmapped — no honest fit among the 8 axes.
    - **[STILL OPEN]** `part_registry.py`'s `_atomize_extraction()` still has no P3/P4-tier keys
      to read, so a P1-only source (all 12 novels + all 63 anthology stories) went from populating
      3 of the registry's 8 sampling axes to 5 of 8 after the Session 23 fix (gained `motive` via
      `victim`, `reveal_mechanic` via `resolution`, `social_dynamic` via `investigator`) — but
      `suspect_archetype`, `red_herring`, and `alibi` still require P2-tier fields
      (`suspect_architecture`, `red_herring`/`clue_fairness`, `alibi`) that a P1-only extraction
      never produces. Only fix: re-extract the 75 P1-only sources at `--protocol P1P2` (new API
      cost, backfills the remaining 3 axes specifically). Full detail in `SESSIONS.md` Session 22.
14. **[DONE, Session 23]** Fixed the `evidence_type`/`alibi` axis mislabeling flagged as a known
    caveat in `craft_grounding.py`'s docstring (axis 8 was named `"evidence_type"` but actually
    held alibi content, since the extraction key `"alibi"` mapped there) — renamed the axis itself
    to `"alibi"` in `part_registry.py`, updated `craft_grounding.py`'s `PART_TYPE_TO_TAXONOMY` and
    `coherence_validator.py`'s hardcoded `"evidence_type"` string checks (4 call sites) to match.
    Done together with the item 12 field-mapping fix above, in the same commit, per the caveat's
    own instruction not to do one without the other. Also found and fixed a second, unrelated
    staleness bug while regenerating the registry to verify: `mystery_database/part_registry.json`
    is a checked-in cache with no staleness check (`load_registry()` only rebuilds if the file is
    *missing*, never if it's stale) — it had been silently frozen since March 11, missing ~75
    sources' worth of corpus growth (294 → 369 sources after regeneration; 1,469 → 2,833 parts).
    Regenerated and committed this time, but the root cause is **not** fixed — `load_registry()`
    still has no staleness check, so the next extraction run will silently go stale again until
    someone manually deletes `part_registry.json`. Worth a real fix (e.g. mtime comparison against
    `extractions/`, matching the pattern `craft_grounding.py`'s index cache already uses) as a
    follow-up, not done this session. Full detail in `SESSIONS.md` Session 23.
    **[RECURRED AND NOW FIXED, Session 33 — August 20 2026]** It went stale again exactly as
    predicted — 4,807 parts / 556 sources checked in versus 4,952 / 569 on a fresh build, i.e. 13
    sources extracted at real API cost and then never sampled. Regenerated, and the root cause is
    now closed:
    - **The check is a corpus fingerprint**, written to a sidecar `part_registry.meta.json`: the
      hashed set of extraction filenames plus a schema version. Filenames are the right unit
      because `load_extractions()` derives every `source_id` from the filename stem, so a change
      to that set is exactly a change to the sources covered.
    - **Not mtime-based, on purpose** — unlike `craft_grounding.py`'s index cache, which this item
      originally proposed copying. A fresh `git clone` stamps every file with the checkout time,
      so mtimes here carry no information about what was built when; comparing them would either
      miss real staleness or rebuild on every clone. **The cost of that choice, stated plainly:**
      an extraction file edited *in place* under the same name is not detected. `force=True` (or
      deleting the JSON) is the escape hatch.
    - **`REGISTRY_SCHEMA_VERSION` covers the other staleness mode**, which no amount of looking at
      the corpus can catch: Session 23 changed `KEY_TO_IDX`, so identical files produced different
      parts and the cache had no way to know. Bump it whenever `_atomize_extraction` / `KEY_TO_IDX`
      / `PART_TYPES` changes what a given extraction yields.
    - **`scripts/test_registry_staleness.py`** (new, zero API cost) asserts both halves — a
      moved-on corpus rebuilds, and an unchanged one does *not*, since the cheap way to pass the
      first is to rebuild unconditionally. The second is proved by corrupting the cached file and
      confirming the corruption survives.
13. **[DONE, Session 23]** Fixed a silent extraction-failure bug found while reviewing anthology
    output quality: `extract_pdf()`/`extract_pdf_anthology()` used to catch a malformed Claude
    response and silently save the same null-placeholder shape used for a genuine "nothing found"
    result — confirmed on `pdf_the_best_of_mystery_1980_antho__story05_pseudo_identity.json`
    (Lawrence Block's "Pseudo Identity"), which came back all-null with no trace of the failure.
    Fixed via a shared `_call_claude_for_protocol()` helper (retry once, then save-with-warning in
    `_meta.extraction_warnings` on parse failure; raise `ExtractionAPIError` and skip-without-saving
    on a pure API/network failure, preserving the dedup-by-filename retry on next run). Verified
    against the real failing case, not just stubs — owner re-ran extraction locally, the retry
    fired and fixed it, and the resulting file now has real high-confidence data across all 6
    fields. Full detail in `SESSIONS.md` Session 23.
15. **[DONE, Session 26]** Room-first lobby + prompt suggestions, end-of-game resolution reveal,
    and post-game voting + same-room replay — three-piece feature set, built and verified
    incrementally per explicit owner request. `POST /games/create` now opens an empty room;
    players suggest prompts while waiting; the host's own submission drives generation on
    `POST /games/{id}/start`. On a win, `GET /games/{id}/result`/`game_won` return `plot_reveal`
    (the mystery's own solution reformatted) + `winner_findings` (the winner's own findings,
    shown to the whole room) + `resolution_narrative` (one Claude call, craft-guidance-informed —
    the RAG layer's fifth call-site, tagged `C5`/`M6`/`"Accusation/Reveal Phase"` — generated once
    and cached, never regenerated on a later fetch). New `round_type: "prompt_vote"` lets the
    group pick what to play next from the leftover suggestions; ties go to the game's winner
    unless they also won the mystery immediately before this one, in which case it's random
    instead (`game["win_history"]` tracks this). `POST /games/{id}/next-mystery/start` resets the
    same room in place — same `game_id`, same players, nobody rejoins — which is the actual point:
    subtly encouraging the same group to keep playing together. Video generation stays explicitly
    tabled — client renders a static `"Video Scene Will Play Here"` placeholder. Full detail,
    including a real `_craft_guidance` leak this work found and fixed in `winner_findings` (private
    per-player audit citations were about to broadcast to the whole room), in `SESSIONS.md`
    Session 26 and `docs/WIRING.md`'s three new sections.
16. **[DONE, Session 28]** Coherence engine unification — CYM side, first of eventually every
    title. Owner priority: the "Coherence Engine" pillar in the studio funding pitch needs to be
    real, not aspirational, and CYM was the safe place to start (same language, same repo, no
    cross-language bridge — unlike MYF, which is JS today). Brought the `coherence/` package
    (`Issue`/`CoherenceReport`/`RuleSet` base classes) over to `main` — it previously existed
    **only** on the stranded `dev/mind-your-friends` branch, despite `docs/WIRING.md`'s prior
    phrasing implying it was already shared. Refactored `coherence_validator.py`'s two entry
    points into real `RuleSet` subclasses (`MysteryPartsRuleSet`, `MysteryRuleSet`); `CoherenceReport`
    here now extends the engine's base class, keeping the inherited `issues` field in sync as the
    union of CYM's categorized `p1_issues`/`scene_issues`/`part_issues`. `check_parts()`/
    `check_mystery()` kept as thin wrapper functions with unchanged signatures — zero call-site
    changes needed in `server/main.py` or `deprecated/cli.py`. Verified both the pass and fail
    paths against realistic mystery dicts, and confirmed `MysteryRuleSet().run(mystery)` called
    directly produces identical results to `check_mystery(mystery)`. Full detail in
    `docs/WIRING.md` → "Coherence validator — what it checks". **MYF's side is deferred until its
    own Python port lands** (see MYF's `CLAUDE.md` item 31/32) — its `lib/coherence.js` is
    JavaScript and can't subclass a Python `RuleSet` without a bridge, which is exactly the
    premature-integration mistake this sequencing avoids. Branch: `claude/coherence-engine-unification`.
    **[COMPLETED, Session 33 — August 20 2026] MYF's Python side is now wired, so the pillar has
    two real consumers.** `mind-your-friends/server_py/coherence_rules.py` (renamed from
    `coherence.py`, which it had to be — a top-level module named `coherence` and the `coherence`
    package cannot both sit on `sys.path`, and `server_py/` always wins, so the import resolved to
    MYF's own file) defines `QuestionRuleSet`, a real `coherence.engine.RuleSet` subclass.
    `mind-your-friends/server_py/test_coherence_engine.py` asserts that both titles use the
    **identical** `RuleSet` / `CoherenceReport` / `Issue` classes rather than two copies that
    merely share field names — the check that would actually catch the framework forking. Full
    detail in MYF's `CLAUDE.md` item 51.

17. **[DESIGNED, NOT BUILT — Session 33, August 20 2026] CYM BACKGROUND — the mystery's own title
    as the page texture.** Owner-initiated: bring MYF's look and feel across to CYM. Design is
    settled to the point of being buildable; **nothing has been written**. Two questions are still
    open (below) and both are the owner's.

    **Shared vocabulary (owner-defined — use these names).** MYF's `CLAUDE.md` glossary already
    defines two of the three; BACKGROUND is new and belongs in both files:
    | Term | MYF today | CYM equivalent |
    |---|---|---|
    | **BACKGROUND** | slate ground + strewn faded question marks | slate ground + the strewn mystery TITLE |
    | **LOGO** | the three-emoji mark, top centre | none yet — not part of this |
    | **TITLE TREATMENT** | the logotype, top left | none yet — not part of this |

    **What CYM gets, and what it does not.** CYM gets the *system* — a ground colour plus a faded,
    strewn, rotated, randomly-sized mark tile — **not the motif**. The question marks stay MYF's
    (owner, explicitly). CYM's marks are the mystery's own title, so the two titles read as
    siblings rather than as one game reskinned. This **reverses MYF item 39's** "scoped by owner to
    MYF only, do not generalise into a cross-title design layer" — knowingly, at the owner's
    direction. MYF item 39 needs that line rewritten when this is built.

    **The state machine.** Ground colour alone until a mystery is named; the field then builds in,
    and re-skins on same-room replay (`prompt_vote` → `next-mystery/start`), which is a free payoff
    of the same mechanism.

    **How the title arrives — the owner's answer, and it is the better one.** The first design
    routed around the fact that `title` does not exist until generation ends (112s–1992s, per the
    real batch summaries): stream the generation call, parse `title` out early since it is field #1
    in the schema, add a `short_title` beside it. That works and costs no extra API calls, but it
    changes the main generation path. **The owner's proposal supersedes it: prompt the player for a
    title alongside the setting, and use theirs.** No streaming, no schema change, nothing touching
    `llm()`, and the original spec ("plain until the prompt is entered, field after") becomes
    literally true. It is also closer to what players already do — `submit_prompt`'s own docstring
    examples are "Smurf murder mystery" and "Mystery on Mars", i.e. already title-shaped.
    Keep the streaming approach in the back pocket **only** as the fallback for a blank title.
    - "Encapsulated" = **as few words as possible** (owner). With a player-supplied title this is
      enforceable at the input (`maxlength` + placeholder) rather than hoped for from generation —
      which matters, because the 16 real titles on disk run 8 to 39 characters and a field of
      "Whiteout" behaves nothing like a field of "Daggers in the Forum: The Ides of March".
    - Free win: leftover suggestions already drive the post-game `prompt_vote`; if each carries a
      title, that screen becomes a list of *named* mysteries instead of raw setting text.
    - The change is small: one field on `SubmitPromptRequest` and on the stored
      `{name, prompt_text, ts}` dict in `submit_prompt` (`server/main.py`).

    **Architecture (decided): the server computes the layout, both clients render it.** CYM has
    **two** clients — the Godot host screen and `server/static/mobile.html`, the phone client every
    player actually looks at. The server emits a seeded layout (`{text, x, y, rotation, size,
    colour}`); Godot draws it in `_draw()`, the phone as inline SVG. One implementation, two
    surfaces, and the TV and every phone show the identical field. Shipping an image instead would
    mean rasterising for Godot and a data-URI for the phone — two renderers and two chances to
    drift.

    **Risks, in the order they will bite:**
    - **Moderation is the real one, and it is new.** A player-supplied string rendered large,
      repeated, on every screen, for a whole game, on a TV, in a Steam title. It is the
      highest-visibility user-generated content surface in the product. MYF already built
      `moderateHeckle()` for a far *smaller* surface. It cannot ride along on generation, because
      the background appears before any Claude call — so it needs handling at submit time, which is
      its own API call or a local filter.
      **[DECIDED, Session 34 — August 21 2026] None yet.** No filter and no moderation call: the
      room is people who chose to play together and can see who typed it. What ships instead is a
      **visible disclaimer under the prompt entry box — "Not moderated for play testing"** (live in
      `godot/scenes/ui/MysteryGeneration.tscn` as `VBox/ModerationNoticeLabel`). It does two jobs:
      it is cover during play testing, and it is a standing reminder that this is unresolved, so
      the decision cannot quietly become the status quo by being invisible. **It is not a Steam
      answer** — a TV-sized, whole-game, user-typed string still needs a real one before release.
      When the phone client finally grows a prompt-suggestion box (Session 26's room-first flow is
      server-only today — `server/static/mobile.html` has no prompt entry at all), the same line
      goes under it.
    - **Legibility.** MYF sits at 10% mark strength for an abstract glyph. Words are read
      involuntarily, and CYM's screens carry far more text (clues, transcripts, evidence). Expect
      to need *below* 10%, plus rotation and edge-cropping so most instances are partial. Test on a
      real screen; do not settle it by argument.
    - **Fonts:** OFL-licensed only (owner). One existing title is "Schatten am Checkpoint", so
      localisation means non-English titles and the set needs the glyph coverage. Note MYF draws
      its marks as **geometry, not font glyphs**, precisely because a background `<text>` renders
      in whatever font the machine has — that concern returns for the phone client, which needs the
      faces actually loaded or the two screens will not match.

    **The two open questions — question 1 is answered, question 2 is half-answered:**
    1. **Moderation** — **answered, Session 34: none yet, disclaimer instead.** See the risk entry
       above for what shipped and what it does not cover.
    2. **Does the player's title feed INTO generation, or only decorate?** Owner, Session 34:
       *"Title is just for generation, but should also be used in a drop down menu of reusable
       mysteries."* So the title **feeds generation** — it is not decoration-only — and it is the
       handle the saved-mystery list is browsed by. **Still to pin down before building:** whether
       "just for generation" also means the BACKGROUND field should be strewn with something other
       than the title, or with the title as well. Do not assume; ask.
       The slug wrinkle stands either way: the saved-mystery slug derives from
       `mystery_dict["title"]` (`server/main.py`), so decide whether the player's title *replaces*
       Claude's or sits beside it. Recommendation: replace, with Claude's as the blank-field
       fallback — the dropdown then lists what the player named, which is the point of question 2.

    **Reusable-mystery dropdown — it exists, and Session 34 fixed it.** Owner asked whether it was
    still in the build. It is, on the Godot host screen only: MainMenu's "Browse Saved Mysteries"
    → `GET /mysteries` → a popup `ItemList` labelled by each mystery's `title`. **It had been
    inert since it was written** — `main_menu.gd` connected its four buttons and none of the
    popup's own signals, so `_on_browse_item_selected` was dead code, clicking a row did nothing,
    and the window could not even be dismissed (a Godot `Window` does not hide itself on
    `close_requested`). Now wired. Two things it still is not:
    - **Single-player only.** Selecting a saved mystery goes straight to `CaseDisplay.tscn`. The
      server has supported multiplayer reuse all along — `CreateGameRequest.mystery_slug` is
      documented "skip prompt-collection, attach an already-generated mystery immediately" — but
      no UI reaches it, so a group cannot replay a saved case together. That is the version the
      owner's "reusable" almost certainly means, and it is a real next step.
    - **Absent from the phone client.** `mobile.html` has no mystery list.

    **Brand artwork — where it stands (Session 33).** `brand/` holds four files and a README.
    `negative_logo.svg` / `organic_logo.svg` were the first pass: raster PNGs in an SVG wrapper,
    not vector, and `organic_logo.svg` carries an export artifact of 22,445 opaque pixels outside
    its viewBox. `NEWnegative_CYM.svg` / `NEWorganic_cym.svg` are the owner's re-cut and are
    **genuine vectors** — 66 and 126 `<path>` elements, zero base64. That was the stated goal and
    it is met.
    - **The contrast problem is unchanged, and that is expected** — the re-cut converted format,
      not values. Measured on the slate ground by `scripts/check_brand_contrast.py`: the negative
      mark went 49% → 53% of ink at or below 2.5:1, the organic monogram 49% → 73%. The monogram's
      *outright invisible* band did drop from 22.7% to 0.1%, but it moved into "barely" rather
      than up the scale.
    - **Being vector now makes the fix cheap and safe**, which is the real payoff. A value
      re-pitch is a fill-colour rewrite across the paths, not a pixel filter. Worth knowing why
      that matters: the pixel filter tried in this session produced rainbow speckle on the
      negative mark, because its near-black regions have near-zero saturation with tiny hue noise
      and raising lightness amplified that noise into visible colour. On vector paths there is no
      noise to amplify.
    - **Neither mark is wired to any client.** No CYM screen references either file. They are
      artwork plus a measurement, not implemented chrome.
    - **The structural question is still open and is the owner's:** these are specified as
      *different marks per device* — negative mark upper-left on desktop/TV, organic monogram top-
      centre on phones. Unlike MYF, CYM's Godot host screen and its phone clients are in the same
      room at the same time, so the room would display two identities simultaneously. That may be
      wanted (a TV poster and a phone icon); it should be decided rather than arrived at.
    - Also unresolved: the negative mark reintroduces a question-mark motif to CYM, which item 17
      otherwise scopes to MYF. A noir question mark is a different object from a strewn field, so
      this may well be fine — but deliberately, not by drift.

    **Unrelated, noticed while checking and worth one look before building on generation:** an old
    batch summary in `mystery_database/generated/` shows **13 of 14 generations failing** on JSON
    parse errors (`Unterminated string`, `Expecting property name`). It is from March and 16
    mysteries have generated cleanly since, so it is probably long fixed — but a background keyed
    to the title inherits whatever the current failure rate is. Worth one real generation run to
    confirm before building on top of it.

> **DO NOT re-run the frozen bulk corpus pipeline** (`deprecated/run_corpus_pipeline.py`). Expand
> the corpus only via `scripts/extract_from_pdfs.py`, adding one quality source at a time.
> **DO NOT touch `deprecated/`** except the one restored exception noted above. It exists for
> historical reference only.
