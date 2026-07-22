# Choose Your Mystery — Session Log

A running record of what each Claude Code session built or decided.
Use this file to onboard any new session without losing context.

---

## Session — July 22, 2026 at 03:01
**Branch:** `claude/connection-check-lum47r`
**Latest commit:** `1280fe1`

### Files changed this session
- `TAXONOMY_EXPANSION_CANDIDATES.md` — Untracked

### Commits this session
```
_No new commits_
```

### Session notes
_No additional notes recorded_

### Resume from here
See **Consolidated To-Do List** above for next steps.
Check `CLAUDE.md` for project conventions and current priorities.

---

## Session 16 — July 22, 2026
**Branch:** `claude/session-wrapup-cleanup-blocker-3val9a`
**Starting commit:** `57575c1` (tip of `main`)
**Status:** Complete — no code changes; resolved a stale-request false alarm

### The problem
The owner pasted a leftover exchange from before Session 15's PR #1 merged, asking Claude Code
to "merge PR#1" into `main`. This looked like a live blocker but wasn't one.

### What was found
- PR #1 (`claude/mystery-pdf-extraction-0fisq0` → `main`) was already merged on 2026-07-14
  18:05 UTC (merge commit `faf52e0`, confirmed via GitHub). `main` and this session's branch are
  identical — no diff, clean working tree.
- Separately, the owner had tried running `scripts/session_summary.py` (the interactive,
  non-`--auto` mode used to type free-form session notes) directly instead of letting the
  `Stop` hook run it in `--auto --quiet` mode. That mode calls Python's `input()` in a loop —
  Claude Code's Bash tool has no live interactive stdin, so the process just blocks forever
  with no way to type a response. That's the actual "Claude Code cannot move forward" symptom.

### Decision
No merge action needed — PR #1 was stale news. Session closed with no code changes; this entry
exists so a future session doesn't re-open the same already-resolved question. If free-form
notes need to be added to `SESSIONS.md` interactively again, don't run
`scripts/session_summary.py` without `--auto` from Claude Code — dictate the notes to Claude Code
directly and have it edit this file instead.

---

## Session 17 — July 14, 2026 (design-only, no code)
**Branch:** `claude/phase-3e-avatar-design`
**Status:** Complete — Phase 3e avatar + player-profile design locked

> Numbering note: this session ran on July 14, concurrently with what became Session 16 above
> (both independently claimed "Session 16" since neither branch could see the other's log entry
> until this PR merged). Renumbered to 17 on merge to avoid a duplicate; no content changed.

### What was decided
Talked through Phase 3e (avatar pool + player history, designed-not-built since Session 14) end
to end and landed on a two-layer avatar model instead of either of the two originally-posed
options (persistent per-player identity vs. disposable per-mystery pool):

- **Base look** — era-appropriate portrait, shared/cached per `<era_key>`, same pattern as the
  existing localization cache. Solves the original concern (a jazz-age portrait showing up in an
  Ancient Rome mystery) since it was never actually possible under the era-keyed pool design —
  the real gap was that pools had no persistent-identity axis at all.
- **Signature accessory** — a small fixed prop (monocle, scarf, etc.) chosen once at registration
  and kept forever, deliberately anachronistic across eras. This is the persistence layer: cheap
  because it's drawn from a small fixed catalog (era × accessory stays a bounded, cacheable
  space), not freeform per-player generation.
- Combining the two is a prompt modifier on the existing pool mechanism, not a new pipeline —
  cached lazily under `<era_key>/<base_look_id>__<accessory_id>.png`.

Full spec — lobby-join flow, player-profile JSON schema, proposed 16-item accessory catalog,
cold-start fallback, and the five open questions each resolved to a default (registration
skippable; accessory permanent; pool sized for 8-player lobbies; static placeholder on cold
start; `localStorage` token now with `steam_id` reserved for Phase 4) — written up in
`docs/WIRING.md` under "Avatar system + player profiles (Phase 3e)".

Also fixed: `docs/WIRING.md`'s "Active branches" footer still named two branches from before the
July 9 reconciliation (`claude/setup-api-and-mysteries-LRLQK`, `claude/mystery-versioning-system-TPblK`).
Removed the duplicate tracking — `CLAUDE.md` is the single source of truth for branch status now.

### What is next
1. **Build Phase 3e** per the locked spec in `docs/WIRING.md` — nothing below exists yet:
   - `mystery_database/accessory_catalog.json`
   - Avatar pool generation script (fal.ai FLUX client, lazy-cache-on-request)
   - `server/main.py`: player registration/upsert, avatar fetch-or-generate, `mysteries_played` logging
   - Godot: registration screen, 3-candidate portrait picker in `Lobby.tscn`
   - Cold-start placeholder asset
2. Sign off on (or edit) the proposed 16-item accessory catalog before it's built
3. `docs/WIRING.md` still has broader staleness beyond the two things fixed this session — several
   sections reference `app.py`/`cli.py` as if still live (e.g. "Localization pass", "Where the
   cinematic brief is triggered", the `cli.py extract` commands under "Extraction protocols").
   Worth a dedicated pass, not done here since it wasn't this session's ask.

---

## Session 15 — July 9, 2026
**Branch:** `claude/mystery-pdf-extraction-0fisq0`
**Starting commit:** `84424e2` (tip of `claude/review-and-resume-1k0tP`)
**Status:** Complete — branch reconciliation + Streamlit deprecation cleanup

### The problem
Several past sessions had been auto-assigned fresh branches off older commits instead of
continuing the actual active branch. This left multiple divergent "current states" of the repo
existing in parallel with no single source of truth:
- `claude/review-and-resume-1k0tP` — the real Godot tip (Phase 3d, includes Session 14's
  `deprecated/` cleanup)
- `claude/fix-godot-performance-QyXLQ` and `claude/start-godot-migration-mNrWD` — earlier,
  now-superseded points in the same Godot lineage
- `claude/review-godot-migration-GiLDz` — a *stranded* branch (misleadingly named, contains no
  Godot code) that forked from the same pre-migration point and did one day of PDF-ingestion
  work (`scripts/extract_from_pdfs.py`, 8 new corpus extractions from Gilbert/Akunin/Higashino
  PDFs, a cast-of-characters text-sampling bug fix) that never got folded into the Godot line
- `claude/mystery-pdf-extraction-0fisq0` (this session's assigned branch) — itself just an empty
  fork of the old pre-migration point, with none of the above
- `CLAUDE.md` on `main` was stale, pointing at a fifth branch (`claude/setup-api-and-mysteries-LRLQK`)
  that predates the Godot pivot entirely

Root cause: no session was reliably merging its branch back before the next one started fresh.

### What was done
- Rebuilt this branch from `claude/review-and-resume-1k0tP` (the true Godot tip)
- Cherry-picked the stranded PDF-ingestion work from `claude/review-godot-migration-GiLDz`:
  `scripts/extract_from_pdfs.py` and the 8 extraction JSONs it produced
- Restored `extraction_protocols.py` from `deprecated/` to root — Session 14's deprecation sweep
  predated the PDF-ingestion work and didn't know it was still a live dependency
  (`scripts/extract_from_pdfs.py` imports it; `part_registry.load_registry()` reads every JSON
  in `mystery_database/extractions/` live, so the new PDF-derived corpus entries are active data)
- Rewrote `CLAUDE.md`: corrected Active Branch, added the corpus-expansion workflow
  (`scripts/extract_from_pdfs.py`, run with `python3` — this environment has no `python` alias)
  to Key Files and the caching-rules table, documented which branches are now safe to delete
- Rewrote `README.md` — it still had the original HuggingFace Streamlit metadata block and
  "`streamlit run app.py`" instructions at the top, missed by Session 14's cleanup. Now describes
  the Godot + FastAPI setup, with an explicit note that the Streamlit version is retired and
  archived under `deprecated/`.

### Decision (owner, this session)
**Godot is the confirmed, sole direction going forward.** All Streamlit/HuggingFace-era code
stays archived in `deprecated/` for provenance — not deleted, not resurrected.

### Follow-up within this session
- Opened **PR #1** (`claude/mystery-pdf-extraction-0fisq0` → `main`):
  https://github.com/Blutomania/SocialGaming/pull/1 — open, `mergeable_state: clean`, not yet merged
- Owner is deleting the five superseded branches manually via GitHub UI (git push --delete was
  blocked with the same 403 policy that blocks direct pushes to `main`; no delete-ref tool was
  available either) — **owner action, in progress, not yet confirmed done**
- Owner hit a real bug running `scripts/extract_from_pdfs.py` locally: `extract_pdf()` returned
  bare `None` (instead of the `(None, "")` tuple its signature promises) when the Claude API call
  raised — e.g. on an invalid key — so `main()`'s unconditional tuple-unpack crashed the whole
  batch with `TypeError: cannot unpack non-iterable NoneType object` instead of recording one
  clean failure and continuing. Fixed in commit `8967754` (single-line fix, `return None` →
  `return None, ""`), pushed to this branch/PR.
- Root cause of the original 401 was a stale/missing local `ANTHROPIC_API_KEY` — owner fixed by
  exporting a fresh key via `~/.zshrc`.
- Owner then successfully ran full ingestion end-to-end locally:
  `python3 scripts/extract_from_pdfs.py mystery_database/new_sources/ --protocol P1` —
  **4/4 processed, 0 failed** — and pushed the results directly to this branch (commit `00bca46`):
  - `pdf_the_circular_staircase_project_gutenberg.json` (Mary Roberts Rinehart)
  - `pdf_the_greene_murder_case_project_gutenberg.json` (S.S. Van Dine)
  - `pdf_the_leavenworth_case_a_lawyer_s_story_by_anna_katharine_gree.json` (Anna Katharine Green)
  - `pdf_the_red_house_mystery_by_a_a_milne.json` (A.A. Milne)
  - Also updated `pdf_smallbone_deceased_a_london_mystery_brit_michael_gilbert.json` — a
    `--fill-resolution` pass filled a previously-null resolution (confidence low → high)
  - Spot-checked `pdf_the_red_house_mystery_by_a_a_milne.json`: `crime` field quotes real
    Chapter III narration, not a table-of-contents artifact — extraction quality looks sound
- Corpus now has 12 PDF-sourced entries total (8 from the prior stranded-branch session + 4 new)

### What is next
1. **Confirm PR #1 merged into `main`** — was open and clean as of session end, not yet merged
2. **Confirm the five superseded branches were actually deleted** (owner was doing this manually
   when this session ended — verify, don't re-assume)
3. Resume Phase 3d work from Session 14 (avatar pool system, player history tracking — see
   Session 14 below)
4. Consider whether the corpus JSONs added this session should also get folded into
   `part_registry.json` itself, or whether relying on `load_extractions()`'s live directory scan
   at runtime is sufficient going forward (currently sufficient — no action required unless
   startup load time becomes a concern)

### Local sync steps (for owner)
```bash
git fetch origin
git checkout claude/mystery-pdf-extraction-0fisq0
git pull origin claude/mystery-pdf-extraction-0fisq0
```

---

## Session 14 — April 20, 2026
**Branch:** `claude/review-and-resume-1k0tP`
**Starting commit:** `403ba24`
**Status:** Complete — Phase 3d lobby flow built

### What was done

**Housekeeping:**
- Reset branch to Phase 3c-complete state (`claude/fix-godot-performance-QyXLQ`)
- Moved all pre-Godot Python tooling to `deprecated/` (app.py, cli.py, corpus pipeline, etc.)
- Updated CLAUDE.md: correct active branch, Phase 3c marked done, Phase 3d as next

**Phase 3d — Lobby flow:**

**`server/main.py`:**
- Added `StartGameRequest` Pydantic model
- `GET /games/{game_id}/lobby` — returns player list, mystery title, difficulty
- `POST /games/{game_id}/start` — host-only; broadcasts `game_started` WebSocket event

**`godot/scripts/autoloads/GameState.gd`:**
- Added `is_multiplayer: bool` flag (set by MainMenu, cleared on reset)

**`godot/scripts/autoloads/ApiClient.gd`:**
- Added `get_lobby()` and `start_game()` methods

**`godot/scenes/ui/MainMenu.tscn` + `main_menu.gd`:**
- Renamed "New Game" → "New Game (Solo)"
- Added "Multiplayer" button; sets `GameState.is_multiplayer = true` before routing to MysteryGeneration

**`godot/scenes/ui/MysteryGeneration.tscn` + `mystery_generation.gd`:**
- Added `MultiplayerSection` (hidden in solo): host name input + difficulty OptionButton
- After generation: if multiplayer → `create_game()` → `Lobby.tscn`; if solo → `CaseDisplay.tscn` (unchanged)

**`godot/scenes/ui/Lobby.tscn` + `godot/scripts/ui/lobby.gd`** — NEW:
- Displays room code and join URL (`SERVER_URL/play`)
- Live player list fed by `player_joined` WebSocket events
- "Start Game" button → `POST /start` → `game_started` broadcast → transitions to `CaseDisplay.tscn`
- "Cancel" returns to MainMenu and resets state

**`server/static/mobile.html`:**
- Added lobby waiting screen (shown after join, before host starts)
- localStorage persists player name across visits (zero friction on return)
- `game_started` WebSocket event triggers transition from lobby → investigation
- `player_joined` event adds player to lobby list

### Design decisions

**Player identity (decided):** `localStorage` token approach deferred to Phase 3e (avatar system).
For now, name is persisted in `localStorage` for convenience; no cross-device identity.

**Avatar system (designed, not built):**
- Setting-matched AI portraits (3 per player, era-styled, generated during lobby wait)
- Era-keyed pool in `mystery_database/avatar_pool/<era_key>/` — same key as localization cache
- Pre-generated pool + background replenishment; players' seen IDs tracked in localStorage
- Image API: FLUX via fal.ai recommended (~$0.003/image)
- Scheduled for Phase 3e, after lobby is confirmed working

### What is next

1. **[NEXT — Phase 3e]** Avatar pool system: seed pools per era, serve 3 portraits at lobby join, player picks one
2. **[NEXT — Phase 3e]** Player history tracking: localStorage token as persistent ID, `mystery_database/player_history/` JSON files, deduplication at generation time
3. **[FUTURE — Phase 3d test]** End-to-end playtest: host Godot + 1+ phones through full lobby → investigation → accusation
4. **[FUTURE]** Phase 4 — Steam integration (GodotSteam plugin)

### Local sync steps (for owner)
```bash
git fetch origin
git checkout claude/review-and-resume-1k0tP
git pull origin claude/review-and-resume-1k0tP
```

---

## Session 12 — April 4, 2026
**Branch:** `claude/fix-godot-performance-QyXLQ`
**Starting commit:** `4235c7c`
**Ending commit:** `a7a361c`
**Status:** Complete — Phase 3a/3b implemented; architecture decided

### What was designed (no code yet)

**Sharing mechanic (revised):**
- Old: fixed % of *players* receive all your findings
- New: you select 50–70% of your findings; **all** players receive what you chose
- Individual deduction is the skill — everyone works from the same shared pool
- Minimum share % is difficulty-gated: EASY 70%, MEDIUM 60%, HARD 50%
- Duplicate check on submission: if a clue is already in the pool, you must replace it

**Three-phase investigation structure:**
```
Witness Phase (X questions) → Investigation Phase (Y areas) → Lead Phase (2 leads) → Accusation
```
Each phase has a hard budget. When budget hits 0 → Share Selection screen → advance to next phase.

**Multiplayer architecture (confirmed):**
- **Godot desktop** = host/TV screen, atmospheric, Steamworks-connected (keep Godot)
- **HTML phone client** = thin browser page served by FastAPI, no download required
- **Pattern**: Jackbox model — host runs Godot, players open a URL on their phones
- **Transport**: FastAPI WebSocket (upgrade from current HTTP polling)
- **Room codes**: short alphanumeric (e.g. "A7FX2"), phone players type it in at the URL

**Why Godot over all-Python:**
- GodotSteam is the best Steamworks integration for indie; Python bindings are DIY
- Godot Linux export = Steam Deck first-class support for free
- Host screen can be cinematic and atmospheric; phones are deliberately minimal
- ENet (Godot's UDP networking) doesn't work in browsers — use WebSocket instead

### What was built (committed)

**`server/main.py`:**
- Mystery generation prompt updated: now requests `investigation_areas` (5) and `leads` (4)
- In-memory game session store (`_games` dict, same pattern as async job store)
- 8 new endpoints:
  - `POST /games/create` — create session from mystery slug + difficulty
  - `POST /games/{id}/join` — register player, get player_id + budgets
  - `POST /games/{id}/interrogate-witness` — budget-checked, hard-blocked, Claude AI call
  - `POST /games/{id}/investigate-area` — budget-checked, hard-blocked, Claude AI call
  - `POST /games/{id}/follow-lead` — max 2 per player, hard-blocked, Claude AI call
  - `POST /games/{id}/share-phase` — validates min %, checks dupes, broadcasts to all
  - `GET /games/{id}/block-pool` — current blocked questions/areas/leads
  - `GET /games/{id}/shared-clues` — all shared clues for polling

**Godot:**
- `MysteryData.gd` — added `InvestigationAreaData` and `LeadData` inner classes
- `GameState.gd` — full rewrite: `InvestPhase` enum, per-phase budgets, block pool, shared clues dict, helper methods (`is_witness_blocked`, `is_area_blocked`, `is_lead_blocked`, `current_phase_findings`, `reset`)
- `ApiClient.gd` — 8 new game API methods; single-player `/interrogate` preserved
- `interrogation.gd` — full rewrite: phase-aware Witness/Investigation/Lead sub-panels, block-pool polling, shared intel panel
- `share_selection.gd` — new: Share Selection screen with minimum enforcement, duplicate conflict highlighting
- `ShareSelection.tscn` — new: scene for share_selection.gd
- `case_display.gd` — added investigation areas, leads, Shared Intel panel with polling

### What still needs to be done

1. **`invest_phase` transition bug**: `_check_phase_complete()` in `interrogation.gd` transitions directly to `ShareSelection.tscn` but doesn't first set `invest_phase` to `SHARE_WITNESS`. Needs: set phase to `SHARE_WITNESS` before `change_scene_to_file`.
2. **`.tscn` wiring**: `Interrogation.tscn` needs new sub-panel nodes (WitnessPanel, InvestigationPanel, LeadPanel, SharedPanel). `CaseDisplay.tscn` needs AreasContainer, LeadsContainer, SharedIntelContainer nodes.
3. **WebSocket upgrade**: Replace HTTP polling with FastAPI WebSocket push. Server broadcasts `clues_shared` + `block_updated` events instead of clients polling.
4. **`mobile.html`** — phone client: simple HTML/JS page served by FastAPI, connects via WebSocket, handles all three phases + share selection.
5. **QR code or room URL display** on Godot host screen so players can join easily.

### Next steps (resume here)
1. Fix the `invest_phase` transition bug (1-line fix in `interrogation.gd`)
2. Wire the `.tscn` node trees to match `@onready` paths in scripts
3. Add `WebSocket /ws/{game_id}` endpoint to FastAPI + `ConnectionManager` class
4. Upgrade Godot `ApiClient.gd` to use `WebSocketPeer` instead of polling
5. Build `mobile.html` — phone client served at `/play`
6. End-to-end playtest: 2 players (desktop + phone) through all 3 phases + accusation

---

## Session 13 — April 4, 2026 (continuation)
**Branch:** `claude/fix-godot-performance-QyXLQ`
**Starting commit:** `389c154`
**Status:** In progress — Phase 3c

### What was built so far this session

**Bug fix — `interrogation.gd`:**
- `_check_phase_complete()` now sets `GameState.invest_phase` to the correct `SHARE_*`
  enum value before transitioning to `ShareSelection.tscn`. Without this, the share
  screen had no idea which findings to display.

**`.tscn` wiring:**
- `Interrogation.tscn` — full rewrite to match all `@onready` paths in `interrogation.gd`:
  `PhaseLabel`, `BudgetLabel`, `WitnessPanel` (with `SuspectDropdown`, `QuestionInput`,
  `AskButton`, scroll history), `InvestigationPanel` (with `AreasContainer`),
  `LeadPanel` (with `LeadsContainer`), `SharedPanel` (with `SharedContainer`),
  `StatusLabel`, `Spinner`, `AccuseButton`, `BackButton`.
- `CaseDisplay.tscn` — added `AreasContainer`, `LeadsContainer`, `SharedIntelContainer`
  nodes under `ScrollContainer/MainVBox`.
- `case_display.gd` — fixed `@onready` paths from `$MainVBox/...` to
  `$ScrollContainer/MainVBox/...` (the node is not a direct child of the root).

**FastAPI WebSocket (`server/main.py`):**
- Added `import asyncio` and `WebSocket, WebSocketDisconnect` to FastAPI imports.
- Added `fastapi.responses.HTMLResponse` and `fastapi.staticfiles.StaticFiles`.
- `ConnectionManager` class: async `connect`, `disconnect`, `broadcast` with per-room
  dict; `_broadcast_sync()` helper bridges sync endpoints to async WS sends.
- `GET /ws/{game_id}` WebSocket endpoint: accepts connection, broadcasts `player_joined`,
  listens for pings, cleans up on disconnect.
- `GET /play` — serves `server/static/mobile.html`.
- `app.mount("/static", ...)` — StaticFiles middleware for phone client assets.
- `share_phase` endpoint now calls `_broadcast_sync` for `clues_shared`,
  `block_updated`, and `player_phase_done` events on successful share.
- `join_game` endpoint now broadcasts `player_joined` to the room.

**Godot WebSocket upgrade:**
- `ApiClient.gd` — added `signal ws_event(event_name, data)`, `WebSocketPeer _ws`,
  `connect_ws(game_id, player_id)`, `disconnect_ws()`. `_process()` polls the peer and
  emits `ws_event` on each incoming JSON message.
- `interrogation.gd` — removed poll timer + `_poll_server()`. On `_ready()`, connects
  `ApiClient.ws_event` to `_on_ws_event()` (handles `block_updated`, `clues_shared`,
  `player_joined`). Disconnects signal in `_exit_tree()`.
- `case_display.gd` — same: removed poll timer, connects `ws_event` to `_on_ws_event`
  which calls `merge_shared_clues` + `_rebuild_shared_intel` on `clues_shared`.

### Still to do this session
- `server/static/mobile.html` — phone client (in progress)
- Commit and push
- End-to-end test: 2 players through all 3 phases + accusation

### If session ends before mobile.html is done
Resume by: write `server/static/mobile.html`.
It needs to: join by room code + name → WebSocket connect → three phase UIs
(witness: dropdown + text input; investigation: area buttons; lead: lead buttons) →
share selection checkboxes → shared intel feed. All via WebSocket + HTTP fetch calls
to the existing FastAPI endpoints.

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

# 2. Start backend
cd /path/to/SocialGaming && uvicorn server.main:app --port 8000

# 3. Smoke test
curl localhost:8000/health
# → {"ok":true}

# 4. Open godot/ in Godot 4 editor
# 5. Verify 3 autoloads appear in Project → Project Settings → Autoload
# 6. Press F5 — MainMenu should load
```

### Next steps (resume here — Phase 2)
1. Open `godot/` in Godot 4 editor and verify scenes load without errors
2. Run the FastAPI server locally; press F5 in Godot; generate a mystery end-to-end
3. If any `@onready` node paths are wrong (scene tree mismatch), fix them in the editor
4. Once full single-player loop works: tag `phase2-single-player-prototype`
5. Then: Phase 3 — lobby system, ENet multiplayer, 75% clue-sharing

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
