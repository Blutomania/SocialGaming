# Choose Your Mystery — Session Log

A running record of what each Claude Code session built or decided.
Use this file to onboard any new session without losing context.

---

## Session — March 18, 2026 at 18:04
**Branch:** `claude/setup-api-and-mysteries-LRLQK`
**Latest commit:** `fb8e533`

### Files changed this session
- `claude/settings.json` — Modified

### Commits this session
```
fb8e533 Fix session-start branch parsing (use grep -oP instead of greedy awk gsub)
c59f2f8 chore: auto-update SESSIONS.md with session summary [444ce35]
444ce35 Document HuggingFace deploy procedure in SESSIONS.md
782e698 Fix short_description length for HuggingFace (60 char limit)
fa0a6a8 chore: auto-update SESSIONS.md with session summary [badd150]
```

### Session notes
_No additional notes recorded_

### Resume from here
See **Consolidated To-Do List** above for next steps.
Check `CLAUDE.md` for project conventions and current priorities.

---

## Session — March 18, 2026 at 18:04
**Branch:** `claude/setup-api-and-mysteries-LRLQK`
**Latest commit:** `444ce35`

### Files changed this session
- `claude/settings.json` — Modified
- `.claude/hooks/` — Untracked

### Commits this session
```
444ce35 Document HuggingFace deploy procedure in SESSIONS.md
782e698 Fix short_description length for HuggingFace (60 char limit)
fa0a6a8 chore: auto-update SESSIONS.md with session summary [badd150]
```

### Session notes
_No additional notes recorded_

### Resume from here
See **Consolidated To-Do List** above for next steps.
Check `CLAUDE.md` for project conventions and current priorities.

---

## Session — March 12, 2026 at 23:09
**Branch:** `claude/setup-api-and-mysteries-LRLQK`
**Latest commit:** `badd150`

### Files changed this session
- `EADME.md` — Modified

### Commits this session
```
badd150 Improve HuggingFace Space discoverability metadata
9382fd7 Mark ANTHROPIC_API_KEY blocker as done
ec93ef8 Record multiplayer design decisions and corpus run clarification
6ea6b2a Update CLAUDE.md and SESSIONS.md for session 9
d66657d Note feedback persistence idea on backlog (low priority, do not implement yet)
f89b72e Surface evidence, gameplay notes, witnesses, crime timing; add viability rating
212fa64 Update page subtitle to show Ultimately/Currently dual-line caption
83e70ed Add scripts/browse_mysteries.py — rich terminal mystery browser
1d80e3d Clarify session-end merge: remote blocks direct push to main, use PR instead
a9b74e2 Update CLAUDE.md and GETTING_STARTED.md for current state
edf1fb8 Localization caching: 3-tier strategy cuts token cost ~11x
eab92af Add localization pass — character names/occupations adapt to setting
51ec30d Add docs/WIRING.md and rewrite README — institutional memory for the wiring
899c9d5 Add opt-in cinematic brief for video-gen engines
5b4e584 Wire check_mystery into app.py — structured JSON generation + coherence badge
37f8873 Add 9 more generated mysteries — all settings pass validator with 0 blocking issues
efa73b0 Wire bearer token auth into cli.py generate; fix max_tokens truncation; run first 9 real mysteries
7110dab Session 8 summary: coherence_validator + cli integration
1f11171 Add coherence_validator.py and wire into generation pipeline
330170a Update to-do: quality validation + P1 coherence validator as next priorities
be75c7f Session 7 summary — HuggingFace Space deployment
501641c Remove streamlit version pin from Space metadata
83af149 Add HuggingFace Space metadata to README
f205194 Wire part registry into app.py mystery generation
4f6c246 Ignore mystery-crime-books/ dir — parquet lives in GitHub LFS via user push
ce004c5 Remove parquet from this branch's index — already in GitHub LFS via user push
b80528f Ingest 284 corpus extractions into part registry: 48 → 1,469 parts across 294 sources
4b65d23 Allow corpus parquet through .gitignore (14MB, under GitHub limit)
8c0bade Remove SESSION_STATE.md — superseded by SESSIONS.md and CLAUDE.md
7662fe4 Sync full project state from upload-corpus branch: all 290 extractions, cli, app, part registry, research findings, session log
d1b5922 Add MysterySolver to .gitignore — third-party HF reference app, not our code
c63c789 Fix .gitignore — allow mystery_database/extractions/ JSONs in git
c8b7991 Add session scaffolding: test mysteries, state doc, and sync script
c50786a Add commit message template and contributing guide
```

### Session notes
_No additional notes recorded_

### Resume from here
See **Consolidated To-Do List** above for next steps.
Check `CLAUDE.md` for project conventions and current priorities.

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

### What is incomplete / next steps
1. **[DONE]** ~~Add `ANTHROPIC_API_KEY` to HuggingFace Space secrets~~ — completed March 12, 2026
2. **[START HERE]** Play-test — generate mysteries in the live Space, use the viability rating, verify full output looks right
3. ~~Full corpus run~~ — **DO NOT re-run**. Corpus run failures were caused by source material that is too brief or not a mystery — re-running will produce the same failures. The 1,469-part registry is the corpus; expand it only by adding new quality source texts.
4. Merge `claude/mystery-versioning-system-TPblK` (CLI + part registry) into main
5. Add "Load saved mystery" dropdown to `app.py`
6. **Multiplayer / invite mechanic** — see design decision below
7. **[LOW PRIORITY — do not implement until owner asks]** Feedback persistence: auto-save mystery to disk on generation, write `_feedback.viability_rating` back into the JSON. Extend to behavioral signals (time-to-solve, interrogation patterns, first-accusation accuracy) when ready. Consider HuggingFace Datasets API for multi-user deployment.

### Design decision — Multiplayer & invite mechanic
**Agreed direction (March 12, 2026):**
- The game is multi-player. The **initiator** creates and enters the mystery scenario.
- **Information sharing is global** — all players see the same 75% of information. Simple to begin with; no per-player asymmetry yet.
- **Invite mechanic:** use a **shareable link with a short game code** (e.g. `chooseyourmystery.com/game/XK7F2`). Host generates the mystery, gets a link/code, and shares it however they like (WhatsApp, text, email — host's choice). No email/SMS infrastructure needed on our side.
  - This is the Jackbox / Skribbl.io model — lowest friction, works in any group-chat context.
  - First-come-first-served on joining (no invite list to manage).
  - If a gated invite list is needed later it can be added, but start without it.
- **Do not implement yet** — design is captured here for the next session that picks up multiplayer work.

### Local sync steps (for owner)
```bash
cd ~/SocialGaming                                        # or wherever your local clone lives
git fetch origin
git checkout claude/setup-api-and-mysteries-LRLQK
git pull origin claude/setup-api-and-mysteries-LRLQK
```

### HuggingFace deploy procedure (discovered March 12, 2026)

The HF Space has two remotes on the owner's machine:
- `origin` → GitHub (`git@github.com:Blutomania/SocialGaming.git`)
- `hf` → HuggingFace (`git@hf.co:spaces/blutomania/SocialGaming`)

HF rejects pushes that contain binary files (PDFs) anywhere in git history.
The solution is an orphan branch (no history), which avoids the binary problem entirely.

**Standard deploy command (run from owner's machine after syncing main):**
```bash
git checkout --orphan hf-deploy
git add -A
git commit -m "Deploy to HuggingFace"
git push hf hf-deploy:main --force
git checkout main
git branch -D hf-deploy
```

**Constraints:**
- `short_description` in README.md YAML must be ≤ 60 characters
- PDFs must stay out of git tracking (covered by `.gitignore *.pdf`)
- Never `git push hf main` directly — the orphan workaround is required

---

## Session 8 — March 12, 2026
**Branch:** `claude/review-changes-mmmec1tknjh846kb-08C3q`
**Latest commit:** `1f11171`

### Files created
- `coherence_validator.py` — P1 chain + witness interrogation foundation + scene investigation checks; two entry points (`check_parts` pre-generation, `check_mystery` post-generation); all issues carry `repair_hint` pointing to registry re-sample rather than new API call

### Files modified
- `cli.py` — wired both validator entry points into `cmd_generate`: `check_parts` runs after sampling (auto-retries targeted re-samples for blocking part gaps), `check_mystery` runs after generation and attaches `_coherence` summary to saved JSON
- `cli.py` — tightened `_generate_with_claude` prompt with explicit quality requirements and concrete examples for `alibi`, `secret`, and evidence fields
- `CLAUDE.md` — updated current to-do list (item 2 and 3 now reflect quality-validation and coherence-validator work)

### Decisions made
- Validator is **two-phase**: pre-generation (free, catches weak sampled parts before API call) and post-generation (verifies the full mystery JSON)
- `BLOCKING` issues prevent gameplay use; `WARNING` degrades quality; `INFO` is cosmetic
- Witness interrogation check anchors three question types: Q-ALIBI, Q-WHY (secret), Q-MOTIVE (suspects)
- Scene investigation requires ≥1 red-herring evidence to be `physical` or `documentary` so players find misdirection during scene investigation, not only from dialogue
- All repair hints reference `part_type` re-sampling from registry (zero API cost)

### What is incomplete / next steps
1. **[START HERE]** Add `ANTHROPIC_API_KEY` to HuggingFace Space settings so app.py can call Claude in production
2. Run `python cli.py generate` with API key to generate 5–10 real mysteries and confirm they pass the new validator (especially confirm no Victorian template default)
3. Wire `check_mystery` into `app.py` — currently only integrated in `cli.py`
4. Full corpus run: `python cli.py extract --protocol P1P2` (359 books → ~700 new parts)
5. Merge `claude/mystery-versioning-system-TPblK` once quality items validated
6. Add "Load saved mystery" dropdown to app.py (browse mysteries generated via CLI inside the UI)
7. **[LOW PRIORITY — do not implement until owner has played with it]** Player/creator feedback persistence: auto-save generated mystery to disk on generation (same slug+timestamp pattern as CLI), then write viability rating + any future behavioral signals (time-to-solve, interrogation patterns, first-accusation accuracy) back into the mystery JSON as `_feedback.*`. The data co-locates with the mystery and feeds back into part-registry weighting (high-rated mysteries → their parts sampled more). Consider HuggingFace Datasets API when app goes multi-user.

---

## Session 6 — March 9, 2026
**Branch:** `claude/upload-corpus-extraction-3uTq5`
**Latest commit:** `037d7a2`
**Status:** Complete

### What was done

**Unblocked corpus extraction via surrogate pipeline:**
- HuggingFace corpus cannot be fetched in this environment (network 403); pivoted to Option 2
- Built `extract_test_mysteries.py` — runs P1+P2 extraction against the 6 built-in test mysteries (A–F) as a surrogate for the full corpus pipeline
- Resolved auth: environment has no `ANTHROPIC_API_KEY` but does have a Bearer OAuth token at `/home/claude/.claude/remote/.session_ingress_token`; script uses Bearer when no API key is set
- All 6 mysteries extracted successfully: ~8k tokens total, saved to `mystery_database/extractions/test_{a-f}_p1p2.json`

**Conceptual clarification (important for next session):**
- Resolved the "template vs. game engine" question: the 6 test scenarios are *validation samples*, not templates. Templates = constraint rules. The P1–P4 taxonomy already encodes the constraint space. Full corpus extraction (Step 7) is what builds real constraint knowledge.
- The test extraction results confirm the extractor works correctly: high confidence on fields present in source (crime, closed_world, alibi), low confidence on fields absent (resolution, investigator) — this is correct behavior.

**Updated CLAUDE.md** with three standing design principles:
1. Close feedback loops (player signal, quality signal, part signal)
2. Preserve mystery coherence (P1 chain must be causally consistent before P2 is added)
3. Drive down cost (cache, test on 6 first, protocol triage, batch before prompting, dry-run)

### Files created or modified
| File | Change |
|---|---|
| `extract_test_mysteries.py` | NEW — surrogate extractor for 6 test mysteries; Bearer token auth |
| `mystery_database/extractions/test_a_p1p2.json` | NEW — P1+P2 extraction for Mystery A |
| `mystery_database/extractions/test_b_p1p2.json` | NEW — P1+P2 extraction for Mystery B |
| `mystery_database/extractions/test_c_p1p2.json` | NEW — P1+P2 extraction for Mystery C |
| `mystery_database/extractions/test_d_p1p2.json` | NEW — P1+P2 extraction for Mystery D |
| `mystery_database/extractions/test_e_p1p2.json` | NEW — P1+P2 extraction for Mystery E |
| `mystery_database/extractions/test_f_p1p2.json` | NEW — P1+P2 extraction for Mystery F |
| `CLAUDE.md` | UPDATED — added Design Principles section (feedback loops, coherence, cost) |

### Key decisions
- **Test-first discipline**: always use `extract_test_mysteries.py` to validate extraction logic before touching the corpus pipeline
- **Bearer auth pattern**: `_get_token()` in `extract_test_mysteries.py` is the reference implementation for API calls without an explicit key in this environment
- **14MB parquet is small enough for GitHub** (under 100MB limit) — user should push `data/train-00000-of-00001.parquet` to unblock full corpus run

### Blockers
- **Corpus parquet not in repo**: user has it locally at `data/train-00000-of-00001.parquet` (14MB). To unblock Step 7: `git add mystery-crime-books/ && git push`
- **corpus_loader.py** expects parquet at `mystery-crime-books/train-00000-of-00001.parquet` or `mystery-crime-books/data/train-00000-of-00001.parquet`

### Resume from here
1. User pushes corpus parquet to repo → I fetch it → run `python cli.py extract --protocol P1P2 --end 10` → inspect quality
2. If quality OK → full run: `python cli.py extract --protocol P1P2` (359 books, ~700 new parts)
3. Wire `app.py` to `part_registry.py`
4. Deploy to HuggingFace Spaces

---

## Session — March 09, 2026 at 17:26 (auto-summary, superseded by Session 6 above)
**Branch:** `claude/upload-corpus-extraction-3uTq5`
**Latest commit:** `3cf2d54`

### Files changed this session
- `extract_test_mysteries.py` — Untracked
- `mystery_database/extractions/test_a_p1p2.json` — Untracked
- `mystery_database/extractions/test_b_p1p2.json` — Untracked
- `mystery_database/extractions/test_c_p1p2.json` — Untracked
- `mystery_database/extractions/test_d_p1p2.json` — Untracked
- `mystery_database/extractions/test_e_p1p2.json` — Untracked
- `mystery_database/extractions/test_f_p1p2.json` — Untracked

### Commits this session
```
3cf2d54 Remove Ellen G. White non-mystery books (Apocalypse, Armageddon) from corpus
105039f Retry extraction #326: rachel-davis-shard (API 500 resolved)
7927804 Add full corpus extraction: 285 books extracted, extractions + registry
eb66ac9 Add Session 4 wrap-up: API validated, data sync status documented
5e45b91 Add Session 3 summary: corpus loader fixes and extraction unblocked
fa19bec Fix corpus clone URL: point to HuggingFace, not GitHub
8f01231 Add automatic session summary system
358c706 Add SESSIONS.md: consolidated session log and master to-do list
2431ae4 Add Streamlit UI app with Claude integration and mystery taxonomy
f78a6ff Add writer-grounded mystery taxonomy research findings
fbf93de Fix extraction truncation: sample beginning+middle+end instead of head-only
fd0b320 Add .gitignore and commit mystery_database output
b78bfd6 Add CLI entry point and part-level atomization system
60d2379 Add corpus pipeline: loader, extraction runner, updated requirements
6281f71 Add extraction_protocols.py: four-level mystery part taxonomy
1019a27 Add canonical test mystery corpus (A-F)
```

### Session notes
_No additional notes recorded_

### Resume from here
See **Consolidated To-Do List** above for next steps.
Check `CLAUDE.md` for project conventions and current priorities.

---

## Session 4 — March 8, 2026
**Branch:** `claude/document-research-findings-LdlIV`
**Latest commit:** 5e45b91
**Status:** Wrap-up / housekeeping

### What was done
- Validated API key and Anthropic credit balance — pipeline is unblocked and ready
- Diagnosed "no credit" false alarm: was a terminal caching issue; restarting Terminal resolved it
- Confirmed working tree clean, branch up to date with remote — no code changes needed
- No corpus data locally (parquet corpus lives on HuggingFace, not cloned)
- `mystery_database/` is fully synced to git (1 generated mystery + 48-part registry committed)

### Data sync status
| Data | Location | Status |
|---|---|---|
| Code + registry | `claude/document-research-findings-LdlIV` | ✅ Pushed |
| Part taxonomy | `extraction_protocols.py`, `part_registry.py` | ✅ In git |
| Generated mysteries | `mystery_database/generated/` | ✅ Committed (1 file) |
| Corpus (359 books) | HuggingFace `AlekseyKorshuk/mystery-crime-books` | Remote-only, not cloned |
| Extraction outputs (--end 10 run) | Not saved — session ended before commit | ⚠️ Re-run needed |

### Next steps (resume here)
1. Re-run `python3 cli.py extract --protocol P1P2 --end 10` and inspect JSON output quality
2. If quality OK → full run: `python3 cli.py extract --protocol P1P2` (359 books, ~700 new parts)
3. Wire `app.py` to `part_registry.py` (replace freeform LLM generation with part registry RAG)
4. Deploy `app.py` to HuggingFace Spaces

---

## Session 3 — March 7, 2026
**Branch:** `claude/document-research-findings-LdlIV`
**Latest commit:** d39a3ca
**Status:** Complete

### What was done
- Fixed `corpus_loader.py` — two bugs blocking `python3 cli.py extract --protocol P1P2 --end 10`:
  1. Error message pointed to wrong clone URL (GitHub `Blutomania/mystery-crime-books` has no parquet); corrected to HuggingFace `AlekseyKorshuk/mystery-crime-books`
  2. HuggingFace clones nest the parquet under `data/` subdirectory; loader now checks `data/` first, falls back to repo root
- Extraction pipeline confirmed working — `--end 10` run completed successfully

### Next steps
- Inspect 10 extracted JSON files for P1/P2 field quality before full corpus run
- If quality is good: `python3 cli.py extract --protocol P1P2` (full 359-book run)
- Check API credit balance at console.anthropic.com before full run

---

## Session 2 — March 7, 2026
**Branch:** `claude/document-research-findings-LdlIV`
**Status:** Active

### What was done
- Committed `RESEARCH_FINDINGS.md` — the writer-grounded mystery taxonomy (C1–C6, M1–M8, F1–F12, cross-writer consensus, P1–P4 extraction protocols)
- Built `app.py` — Streamlit UI adapted from the MysterySolver HuggingFace Space:
  - Swapped Groq/Llama for Claude (`claude-sonnet-4-6`)
  - Replaced "Generate" button with free-text prompt input
  - Mystery generation structured around P1 Skeleton Protocol (C1–C6)
  - Suspect extraction and solution grounded in P2 Architecture Protocol (M1, M2, M5, M6)
  - Coming Soon panel: AI depiction scenes, multiplayer, clue sharing, Gen AI avatars
- Updated `requirements.txt`: `anthropic>=0.40.0`, `streamlit>=1.35.0`

### Sources for taxonomy
Christie, P.D. James, Ronald Knox, Raymond Chandler, Tana French, Gillian Flynn, Ian Rankin

---

## Session 1 — March 7, 2026
**Branch:** `claude/mystery-versioning-system-TPblK`
**Status:** Complete (4 commits, latest fd0b320)

### What was built

**`extraction_protocols.py`** — Four-level mystery part taxonomy (P1–P4)

**`test_mysteries.py`** — Canonical test corpus (Mysteries A–F), 6 mysteries × 8 part types = 48 parts

**`part_registry.py`** — Atomization layer (the core missing piece)
- `PART_CONTENT` — text of all 48 parts, keyed by `SOURCE(INDEX)` notation e.g. `C(4)`, `F(2)`, `A(6)`
- `SETTING_COMPAT` — per-part compatibility rules (motives/red herrings universal; biometric/data-log parts require `far_future`; maritime parts require `victorian` or `maritime`)
- `MysteryPart.is_compatible()` — filters candidates against a free-text setting string
- `PartRegistry.sample_for_generation(max_per_source=2)` — diversity-constrained sampling, no single source dominates
- `ProvenanceRecipe.format()` — auditable recipe string stored with every output e.g. `C(1) + C(2) + F(3) + B(4) + A(5) + B(6) + A(7) + E(8)`

**`corpus_loader.py`** — Loads and parses the mystery corpus

**`run_corpus_pipeline.py`** — Extraction runner; delegates to `cli.py extract`

**`cli.py`** — Terminal entry point, 5 commands:
| Command | What it does |
|---|---|
| `python cli.py generate` | Interactive mystery generation — setting/crime/players, RAG, mystery + provenance recipe |
| `python cli.py generate --demo` | Same, no API key needed |
| `python cli.py solve` | MysterySolver mode — paste mystery, get structured deduction (culprit, red herrings, next steps) |
| `python cli.py list` | Browse canonical corpus (A–F) and all generated mysteries with recipes |
| `python cli.py registry` | Part inventory: 48 parts, diversity health |
| `python cli.py extract` | Delegates to `run_corpus_pipeline.py` |

**`mystery_database/`** — Committed with initial `part_registry.json` (48 parts) and first demo mystery (`the_murder_at_ancient_athens_…json`) with provenance recipe

**`.gitignore`** — Added; excludes `__pycache__/`, `.env`, `venv`, parquet corpus files, pipeline checkpoints

**`requirements.txt`** — Added `rich>=13.0.0`

### Five gaps closed
| Gap | Solution |
|---|---|
| CLI entry point | `cli.py` with 5 subcommands |
| Explicit part-level decomposition with ID tracking | `MysteryPart` + `PART_CONTENT` in `part_registry.py` |
| Diversity constraint (no single source dominates) | `sample_for_generation(max_per_source=2)` |
| Setting compatibility filter | `SETTING_COMPAT` table + `_parse_setting()` + `is_compatible()` |
| Part provenance tracking | `ProvenanceRecipe` → `C(1) + F(3) + B(6) + …` stored in every JSON |

---

## Consolidated To-Do List

### Immediate (pre-full corpus run)
- [ ] **Step 6** — Run `python cli.py extract --protocol P1P2 --end 10` to validate extraction quality on 10 books before committing to full 359-book run
- [ ] **Step 7** — Full corpus run: `python cli.py extract --protocol P1P2` — adds ~700 parts to registry, expands setting diversity beyond 6 test mysteries

### UI
- [ ] Wire `app.py` (Streamlit) to `part_registry.py` and `mystery_generator.py` so generated mysteries use the part registry rather than freeform LLM generation
- [ ] Deploy `app.py` to HuggingFace Spaces with `ANTHROPIC_API_KEY` secret
- [ ] Revise HuggingFace Spaces UI: confirm text input field is in place (done in Session 2)

### Content & Quality
- [ ] Manual validation of first 10 extracted mysteries before full corpus run
- [ ] Confirm demo mystery output stops using generic Victorian template — requires Step 7 corpus parts for setting-accurate generation (e.g. "Ancient Athens")
- [ ] Update extraction prompts in `mystery_data_acquisition.py` to map to P1–P4 protocol structure

### Architecture
- [ ] Merge `claude/mystery-versioning-system-TPblK` into working branch once Step 6/7 validated
- [ ] Evaluate PostgreSQL + pgvector migration path (trigger: >1,000 mysteries in registry)

---

## Session 7 — March 11, 2026
**Branch:** `claude/review-changes-mmmec1tknjh846kb-08C3q`
**Latest commit:** `501641c`

### What was done
- Deployed `app.py` to HuggingFace Spaces at `huggingface.co/spaces/blutomania/SocialGaming`
- Resolved HTTPS git auth failure — switched to SSH (`git@hf.co`) after protocol errors
- Created clean `hf-deploy` orphan branch (no PDF history) to satisfy HF binary file restrictions
- Removed `MysterySolver/` embedded git repo from tracking; added to `.gitignore`
- Added HuggingFace Space YAML metadata block to `README.md`
- Removed `sdk_version` pin from metadata (was causing streamlit version conflict in build)

### Files modified
- `README.md` — Added HF Space metadata header; removed sdk_version pin
- `.gitignore` — Added `MysterySolver/`

### Decisions
- SSH over HTTPS for HF remote pushes (HTTPS protocol.version errors on this machine)
- `hf-deploy` orphan branch as the HF deployment branch (keeps PDF-free history)
- No `sdk_version` in metadata — let HF resolve streamlit version automatically

### Next steps
1. **Verify the Space builds and runs** — check `huggingface.co/spaces/blutomania/SocialGaming`
2. **Add `ANTHROPIC_API_KEY` secret** in HF Space settings (Settings → Variables and secrets)
3. Wire `app.py` to `part_registry.py` (marked in to-do above — partially done in `f205194`)
4. When pushing future fixes to HF: `git cherry-pick <commit>` onto `hf-deploy`, then `git push hf hf-deploy:main --force`
