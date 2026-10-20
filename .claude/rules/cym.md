---
# Every pattern starts with "/", which anchors it to the repo root. Without it a
# pattern matches at ANY depth: "docs/**" also matched mind-your-friends/docs/,
# and "*.py" matched mind-your-friends/server_py/ — so MYF work loaded this
# whole file. Both tested with a fresh headless session, Session 50.
paths:
  - "/server/**"
  - "/godot/**"
  - "/docs/**"
  - "/scripts/**"
  - "/brand/**"
  - "/icons/**"
  - "/mystery_database/**"
  - "/deprecated/**"
  - "/*.py"
  - "/RESEARCH_FINDINGS.md"
  - "/SCREEN_CRAFT_FINDINGS.md"
  - "/PARTY_CRAFT_FINDINGS.md"
  - "/SOURCING_METHODOLOGY.md"
  - "/.claude/rules/cym.md"
---
# Choose Your Mystery — Claude Code Instructions

## How to read this file

**This file says what is true now, and what is open.** It loads only when a session touches CYM's
files (the `paths` above), so a Mind Your Friends session never pays for it. Until Session 50 it
WAS the root `CLAUDE.md`; code comments and older docs that say "CLAUDE.md" about CYM mean this
file. Two topics load only when a session needs them (Session 51):

| Where | Holds | Loads when |
|---|---|---|
| **`.claude/rules/cym.md`** (here) | What is true now, and what is open | any CYM file is touched |
| **`.claude/rules/cym-godot.md`** | The Godot client: autoloads, engine-side checks, how to run it | `godot/` is touched |
| **`.claude/rules/cym-checkers.md`** | Every checker, test and tool, with what it catches | `scripts/` is touched |
| **`docs/DECISIONS.md`** | Every numbered item, 1–38: what is true, why, what was rejected | read on demand |
| **`SESSIONS.md`** | What was decided when. Append-only; never edited to match a later truth | read on demand |

**Item numbers are stable.** "Item 17" means the same thing here, in `docs/DECISIONS.md`, in
`docs/`, and in source comments. Never renumber one. `scripts/check_decisions.py` confirms every
citation lands.

**When a statement here or in a decision entry stops being true, edit it to what is true now** and
put the history in `SESSIONS.md`. Do not stack a *[superseded]* note on top of it: that is how this
file reached 1,003 lines by Session 38, and how the decision record grew entries that contradicted
their own status labels until Session 51 cleaned them.

**The vocabulary is investigation, not card game.** No decks, cards, hands or deals, and nothing is
*played*. Findings are **assigned**, into a player's **casefile**. Owner's instruction, three times;
the first two fixed only the noun and the metaphor rebuilt itself from the verbs (item 34). **The
test: if a word would be at home on a box reading "2–6 players, ages 10+", it is the wrong word.**

**Backtick-quoting a string here or in `docs/` is a CLAIM that the product contains it**, enforced
by `scripts/check_doc_claims.py`. To mention a string without asserting it — a retired label, an
illustrative pattern — use italics, or add it to that script's `ALLOWED_LITERALS` with a reason.

---

## The product

AI-powered social murder mystery party game. Players join a room, are assigned findings about a
generated crime, decide which to share and which to keep, and race to accuse the culprit.

**Target:** multiplayer standalone, Steam. **Stack:** Godot 4.x desktop client (the host / TV
screen) + Python FastAPI backend; phones join through a browser page. All Claude calls are
server-side. HuggingFace is retired; the `hf-deploy` orphan branch is stale.

### The core mechanic

**Selective information sharing**: what you give away helps the room and costs you your edge.
Everything else exists to set up that decision. (There is no "75% random share" and there never
was — an old claim this file carried for many sessions; item 11.)

**The decision is a rhythm** (`apf.py`, item 23). Rounds = findings ÷ players, announced before
play. Each round assigns every player one finding; from round 2 there is a share checkpoint
against a per-difficulty minimum (`share_min`: EASY 0.70, MEDIUM 0.60, HARD 0.50). A shared finding
**stays in its holder's casefile** — what a player spends is exclusivity, not possession — so the
requirement is cumulative. Measured on the accepted mystery at four rounds, the private stash is
**1 at EASY, 2 at MEDIUM and HARD**, and that stash is the `hoard_allowance` the assignment uses.

**The assignment** (`casefiles.py`) guarantees the case is solvable from the union of casefiles,
that no single casefile solves it alone, and that nobody can withhold the proof away.
`REDUNDANCY_BY_DIFFICULTY` puts each exoneration in two casefiles on EASY, one otherwise; a third
rung needs a fifth suspect (item 33). Deduction is subtraction (exonerations) **plus** intersection
(`narrows`, the glove — item 27); the board greys a face only on an exoneration, never a narrowing.
The game ends in **full disclosure**: every held finding goes public with its holder's name
(item 32).

---

## Where the project is now

**Stage 1: get one human through one whole mystery on one PC.** The build is item 23, **APF ("All
Provided For")** — findings assigned, not gathered: no traversal, no investigation budget, no phase
gates (`docs/PLAYTEST_FLOW.md`, `docs/INVESTIGATION_DESIGN.md` §5–§7).

**The stage-1 test is blunt:** can somebody who is not the owner start the game, play a whole
mystery and reach the result screen without a Godot error? Anything that fails that is urgent;
anything that does not, is not.

**Session 51: the F5 walk passed** — Lobby → CaseBrief → ApfRound, all four rounds → accuse →
ResultScreen, on the owner's machine, with `scripts/seat_players.py` filling the seats. **The next
step is a person other than the owner playing it cold**, and the owner's screen-by-screen markups.

### Delivery priority (owner, Session 34 — "obviously it can change")

| # | Stage | Means |
|---|---|---|
| 1 | **PC playtest** | The Godot desktop client is the **only** surface that has to work |
| 2 | **Funding** | The playtest is evidence for the pitch; the coherence engine and corpus are real |
| 3 | **Phone + robust gen AI** | `server/static/mobile.html`, the room-first prompt flow, moderation that survives Steam, item 17's BACKGROUND |

Before calling something a gap:
- **Phone-client gaps are not blockers.** `mobile.html` has no prompt box, no mystery list, no lobby
  suggestions, and cannot share under the rhythm. Fine until stage 3.
- **Saved mysteries:** the browse list opens one in `CaseDisplay.tscn` for solo reading;
  `MysteryGeneration`'s multiplayer section can open a **room** from one, so looking at the round
  screen costs no generation. `GET /mysteries` reports `apf_ready`; one mystery on disk qualifies,
  `the_neriin_in_the_pilchard_barrel`.
- **Moderation:** none, with the visible *Not moderated for play testing* disclaimer. A stage-1
  answer by construction; the Steam answer is stage 3.
- **Nothing already built gets removed**, and **new API cost needs a reason that serves stage 1.**

---

## Architecture

```
Godot 4.x desktop client (godot/) — the host / TV screen
  GDScript 2.0. Five autoloads, ten .tscn screens.  →  .claude/rules/cym-godot.md
        │ HTTP JSON (ApiClient.gd)
Python FastAPI server (server/main.py) — 37 routes
  Generation, game sessions, APF's rhythm, results. Wraps part_registry,
  coherence_validator, localization, craft_grounding, apf, casefiles, gate.
        │ WebSocket /ws/{game_id}
Phone client — server/static/mobile.html, served at /play
```

**Routes in `server/main.py`** (37 — check the file, do not assume): generation (`/generate`,
`/generate/async`, `/jobs/{job_id}`), saved mysteries (`/mysteries`), game lifecycle
(`/games/create`, `/join`, `/start`), **APF** (`/apf/open`, `/apf/round/next`, `/apf/state`,
`/apf/share`, `/apf/disclose`, `/apf/disclosure`) — the playtest path, and free to call — the
pre-APF gather loop (`/interrogate-witness`, `/investigate-area`, `/follow-lead`, `/share-phase`,
`/accuse`), lockstep rounds (`/round/*`), replay (`/prompts/submit`, `/prompts/tiebreak`,
`/next-mystery/start`), plus `/health`, `/rate`, `/play` and the WebSocket.

**One transport is live.** The FastAPI WebSocket carries every push, to the host and the phones.
Godot ENet (`NetworkManager.gd`) is registered as an autoload and called by nothing.
**Steam:** GodotSteam, deferred until the prototype is stable (item 8).

---

## Key files

| File | Purpose |
|---|---|
| `server/main.py` | FastAPI backend — every route and every Claude call site (`llm()`) |
| `server/static/mobile.html` | The phone client, served at `/play` |
| `godot/scenes/ui/` | Ten screens: MainMenu, MysteryGeneration, Lobby, **CaseBrief** (the room's opening), **ApfRound** (the play screen), ResultScreen; CaseDisplay (the author's view, solo), Interrogation, ShareSelection, Accusation (gather loop) |
| `apf.py` | The rhythm: round count, cumulative share checkpoint, suspect board, full disclosure. Owns the *cadence*; the share rule is injected, never recomputed |
| `casefiles.py` | The constrained assignment. `best_assignment()` picks the fairest of several seeds. Set arithmetic over `evidence[]`, reached through `reveals`. Deterministic from a seed |
| `gate.py` | Whether a generation may be served: routes it to `generated/` or `rejected/` on any failing check. Free (item 18) |
| `generation_ledger.py` | One JSONL row per generation attempt — cost, verdict, failure class, rule ids (item 28) |
| `arrangement.py` | Wires exonerations nothing reveals to a finding that honestly carries them. Repairs the arrangement, never the evidence (item 29) |
| `coherence_validator.py` | P1 causal-chain, witness and evidence checks. Free |
| `coherence/` | The shared engine (`Issue`, `CoherenceReport`, `RuleSet`) — CYM and MYF both subclass it (item 16) |
| `craft_grounding.py` | Retrieval over the craft docs into all five generation call sites. Zero added API calls (item 10) |
| `part_registry.py` | The corpus index — 5,990 parts across 573 sources; rebuilds when the corpus fingerprint changes (item 14) |
| `localization.py` | Era-appropriate names and occupations, 3-tier disk cache |
| `palette.py` | **The one place a colour is decided**, with its WCAG contrast contract. Read before changing any colour |
| `background_field.py` | The BACKGROUND layout (item 17). Tested, wired to nothing |
| `extraction_protocols.py` | P1–P4 taxonomy. Live dependency of `scripts/extract_from_pdfs.py` |
| `icons/` | Source art for clue, witness and suspect icons |
| **Documents** | |
| `docs/PLAYTEST_FLOW.md` | **APF and the playtest screens.** Read before touching a playtest-path screen |
| `docs/STYLE_GUIDE.md` | **Night File** — what each colour, face and part is for. Values live in `palette.py` |
| `docs/WIRING.md` | Canonical generation architecture — **read before touching generation, localization or coherence** |
| `docs/F5_CHECKLIST.md` | The hand-walk for the Godot client, and which steps have been walked |
| `docs/AI_COST_PLAYBOOK.md` | Measured economics. Read before adding a schema field, a play-time call or a re-extraction |
| `docs/INVESTIGATION_DESIGN.md` | The investigation model and solvability as set arithmetic |
| `docs/EXTRACTION_TROUBLESHOOTING.md` | Every extraction failure mode and its fix |
| `docs/COHERENCE_PRIMER.md` | The two kinds of coherence, in plain language |
| `RESEARCH_FINDINGS.md`, `SCREEN_CRAFT_FINDINGS.md`, `PARTY_CRAFT_FINDINGS.md` | Craft grounding — prose, screen, party-game; tiers and corroboration in `SOURCING_METHODOLOGY.md` |

**`deprecated/` — do not touch.** The pre-Godot Streamlit/HuggingFace tool, kept for provenance.
Several names look live: `deprecated/requirements.txt` is not `server/requirements.txt`, and
`deprecated/mystery_generator.py` is not where generation lives (`server/main.py`). **Never re-run
the frozen bulk corpus pipeline** (`deprecated/run_corpus_pipeline.py`); add sources one at a time
with `scripts/extract_from_pdfs.py`.

---

## Conventions

- **Session protocol** is the root `CLAUDE.md`'s. CYM adds: read `docs/WIRING.md` before touching
  generation; at the end, update **Open work** below and the item's entry in `docs/DECISIONS.md`.
- **Before handing anyone a build**, run `scripts/check_godot_wiring.py`, `scripts/test_apf.py`,
  `scripts/test_ws_push.py` and `scripts/build_palette.py --check`, and for doc edits
  `scripts/check_doc_claims.py` and `scripts/check_decisions.py`. The full list is
  `.claude/rules/cym-checkers.md`. Checkers passing is **necessary, not sufficient** — say whether
  a Godot change has been seen on the owner's machine.
- Python 3.8+ server-side, invoked as `python3`; GDScript 2.0 with types stated.
- **Models:** gameplay generation `claude-sonnet-4-6`; extraction `claude-haiku-4-5-20251001` with a
  Sonnet fallback; the corpus upgrade `claude-opus-5`.
- Mystery parts use `SOURCE(INDEX)` notation — `C(4)`, `F(2)`, `A(6)`. Protocols: P1 Skeleton
  (C1–C6), P2 Architecture (M1–M8), P3 Craft (F1–F8), P4 Texture (F9–F12). Every generated mystery
  carries `_provenance`.
- API auth is server-side only: the `ANTHROPIC_API_KEY` env var, else a Bearer token from
  `/home/claude/.claude/remote/.session_ingress_token`.

### Design principles — every feature answers at least one

1. **Does it close a feedback loop?** The 1–10 viability rating; accusations and time-to-solve; the
   ledger's rule firings.
2. **Does it preserve coherence?** The P1 chain — crime → victim → closed world → culprit/motive →
   resolution — unbroken. `check_parts()` before generation, `check_mystery()` after; both free.
3. **Does it drive down cost?** **Output tokens are ~95% of a generation call**, so prompt caching
   is the wrong lever; writing fixed text at generation time instead of calling per action is the
   right one (10.8× on a four-player game). Cost per *accepted* mystery is the number that decides
   — `python3 scripts/cpam.py`. Caches: localization rulesets
   (`mystery_database/localization_cache/`, by era; modern eras skip the call), extractions (never
   re-extract a source already in JSON), generated mysteries (`mystery_database/generated/`).

---

## Open work

Everything else is closed — see `docs/DECISIONS.md`.

**23. APF — built; what is left is a table.** All four build steps are in, and the accepted mystery
`the_neriin_in_the_pilchard_barrel` plays end to end over HTTP at all three difficulties. Open:
- **The F5 walk reached ResultScreen in Godot (Session 51)** — the stage-1 test passed on the
  owner's machine. Two defects found on the way, both fixed: a crash at OPEN THE CASE (an HTTP
  reply landing on a freed screen) and a pause after the accusation (the play-time resolution
  call, now removed — build step 5 for the critical path, so a game makes no Claude call).
- **Nobody but the owner has played APF cold.** One outside player (Session 43) finished two
  mysteries, possibly on the gather loop.
- Owner's calls pending from Session 49: ApfRound's suspect board (placeholder squares vs
  CaseBrief's portraits); whether the share confirm step survives a real table; commit
  `cym_theme.tres` from the owner's machine.

**36. Night File — the host screen's look.** Theme landed, clean in the engine. Screen passes done:
MainMenu, MysteryGeneration, Lobby, CaseBrief, ApfRound, ResultScreen (Session 47). **Open:**
ResultScreen's newer markup, CaseDisplay, Interrogation, Accusation, ShareSelection; the brand mark
upper-left was not visible in the owner's Session 49 screenshots — unconfirmed. Session 49's
Lobby / CaseBrief / ApfRound pass has not been rendered.

**ApfRound's suspect board may do the deduction for the player** — it greys a face as soon as an
exoneration is shared. Owner's open worry, Session 51; see item 36. Not urgent.

**27. The glove (`narrows`) — built; one real generation's worth of evidence.** The accepted path
works; the one real generation since (item 35) leaked three narrowings in prose
(`NARR.NARROWS_PROSE_NAMES`). The rule that one finding may not reveal both a narrowing and the
exoneration completing it is in the prompt and unconfirmed.

**35. Pronouns + presentation.** Built and confirmed on one real generation. Open:
`coherence_validator.py` does not yet require both fields non-blank.

**33. A fifth suspect would give a third difficulty rung** — deferred until a mystery reliably
carries enough findings for both the alibi load and the round count. `APF_SUSPECT_COUNT` stays 4.

**17. BACKGROUND — one owner question, stage 3.** The layout is built and wired to nothing. Open:
whether the field is strewn with the mystery's title, something else, or both — ask, do not assume.
Also stage 3: the phone's chrome (organic monogram, top-centre) and the window icon. The Lobby's
logo is the owner's temporary placeholder pending an artist; measure any replacement with
`scripts/check_brand_contrast.py` before wiring it in.

**19. Corpus P1→P1P2P3 upgrade — blocked on API credits.** `python3 scripts/upgrade_p1_to_p1p2.py`
prints the plan; `--go` runs it. Seven stories are already upgraded. Not stage 1.

**7. Corpus growth — ongoing.** Anthologies over novels, roughly 3–5 to 1. Outstanding: 11
held-back anthology PDFs with detection problems, 7 all-null extractions occupying filenames, one
untriaged Higashino novel.

**38. The reveal is written at generation time** — built, and the accepted mystery backfilled.
Unconfirmed until a paid generation: bundle with items 27 and 35's open checks.

**37. Suspect interviews — stage 3.** Suspects never speak; a suspect-voiced, possibly lying
statement is a generation change. Until then ApfRound's heading names what really happened.

**4, 8. Avatars + player profiles, Steam** — both behind stage 3.

**Archived ideas** (Session 47 tagged every old branch *archive/<name>* and deleted it;
`dev/mind-your-friends` stays, item 9). Three hold work `main` lacks, each a decision, not a bug:
*archive/claude/connection-check-lum47r* (coherence rule-hit telemetry, a taxonomy research pool);
*archive/claude/pdf-ingestion-checkpoint-71qwb3* (the anthology filename-collision fix — port with a
rename step, since it renames outputs — plus Van Dine's 20 rules; item 7);
*archive/claude/brave-bohr-45istr* (MYF's ideas, MYF's call).
