# Mind Your Friends — Claude Code Instructions

## How to read this file

**This file says what is true now.** It is loaded into every MYF session, so it holds only what a
session needs before it starts: what the game is, how it is built, where it stands, and what is
open.

| Where | Holds |
|---|---|
| **`CLAUDE.md`** (here) | What is true now, and what is open. |
| **`docs/DECISIONS.md`** | Every numbered work item, 1–53, with its full reasoning. *Why is it like that? Has this been tried?* |
| **`SESSIONS.md`** (repo root) | What was decided when. MYF sessions are 29–33 and 50. Append-only. |
| **`GAME_DESIGN.md`** | The game's rules, in full. |
| **`PLAYTEST.md`** | PT-1 → PT-8: the questions only a real table can answer. |
| **`docs/STYLE_GUIDE.md`** | How a screen is built: boxes, states, honest labels. Read before touching any UI. |
| **`docs/WIRING.md`** | The Godot port's architecture and the `server_py` porting notes. |

**Item numbers are stable.** "Item 41" means Flow B everywhere — here, in `docs/DECISIONS.md`, in
`GAME_DESIGN.md` and in source comments. Never renumber one.

**When something here needs a "superseded" or "correction" note, it has become history.** Move it
to `docs/DECISIONS.md` and state the current truth here. This file reached 1,487 lines — about 90%
archive — because that rule was not followed, and was rewritten on October 19 2026.

---

## The game

Real-time multiplayer social trivia with sabotage cards, wagers, a rotating round rule and an AI
host who knows everyone's name. 3–6 players join with a 4-letter room code. **The social loop —
not the trivia — is the product.**

**Design thesis: casual-first.** Surprise, laughs and "oh no!" moments over strategic depth.
Randomness is a feature. A new player understands everything by the end of round 1 — which is why
round 1 has no rule. Design for the table, not the meta. Full text: `GAME_DESIGN.md`.

**MYF really is a card game.** Cards, hands, decks and *played* are the right words here. (CYM's
ban on card-game vocabulary does not apply to MYF.)

### How a turn works (Flow B, item 41)

4 rounds × 6 questions. One round rule per round, announced, kept on screen; round 1 is plain.

1. **Category** — the active player picks one of 6 from the shared pool, each credited to whoever
   submitted it ("swapped to Sarah's 90s Hip Hop!").
2. **Wager** — the *next* player sets the active player's stake on a five-rung ladder
   `12 / 25 / 50 / 100 / 200` (item 45). *I cut, you choose.* The wager also sets the question's
   difficulty, and the question is printed in a green keyed to the rung.
3. **Card window** — anyone may play a card; the first claims the single slot (FCFS).
4. **Question** — generated from the per-category fact bank, 8–20 words, shaped by the rule and
   any format card.
5. **Answer** — 5s reading window → the active player's **exclusive window** (8s, capped at 25%
   of the clock): right wins the wager, wrong loses it, an explicit **pass** costs nothing,
   **freezing** costs the wager. Meanwhile everyone else types and **locks** an answer; when the
   buzzer opens, a buzz plays that locked answer for **0.75× the wager**. No lock, no buzz.
6. **Result** — including the answers people locked and never played.

Answering never earns another turn. Worst Answer Wins (`submissionBased`) and The Lineup
(`lineupBased`) keep their own answer flows. **Post-game:** superlative voting, one award at a
time, and a shareable question card (answer withheld).

**The nine round rules:** Back It Up, One Word Only, Take Your Time, ELI5, Double Down, Lightning
Round, Worst Answer Wins, The Lineup, Rebus. Steal was retired by item 37.
**The cards:** a fixed hand of 1 picked + Half-Off (everyone has it), single-use. Sabotage:
Skip, Redirect, Whoa Nellie, 50% Off, Spotlight, Heckle, Language Barrier, Boxed In. Defence:
Insurance, The Fixer.

### Glossary (owner-defined — use these names)

| Term | Means |
|---|---|
| **Lobby** | The post-join screen: roster + 3-category picker → "Next — Pick Your Card". `components/Lobby.jsx`. **Not** the create/join screen (`app/page.js`). Godot's `lobby.tscn` merges both and must be split. |
| **Logo** | The three-emoji mark (brain / pointing finger / group). May appear on its own. |
| **Title treatment** (= text treatment) | The "Mind Your Friends" logotype — live type, two treatments 50/50 per game (item 52). |
| **Plate** | A rectangle of the ground colour with the texture switched off — for what must be *read* (item 40). |
| **Box** | An outlined, square control — for what must be *grabbed* (item 53, `docs/STYLE_GUIDE.md`). |

**Composition rule:** the logo can appear without the title treatment; the title treatment must
never appear without the logo.

---

## Where it stands (October 19 2026)

**Two clients exist, and only one is playable.**

| | State |
|---|---|
| **Next.js prototype** (`app/`, `components/`, `lib/*.js`, `server.js`) | **The playable game, end to end**, Flow B, post-game and all. Every aesthetics pass was made here. It is the behavioural reference — **do not delete it** until Godot reaches parity and is playtested. |
| **`server_py/`** (FastAPI) | Full port of the game logic: Flow B (item 42), the question log and superlative voting (item 46). **At parity with the prototype.** |
| **`godot/`** client | `ApiClient.gd`, `GameState.gd`, and **one screen** — the lobby, unstyled, with stubbed registration (item 34). No round-loop screens. |

**Why Godot at all (item 31):** both titles target Steam and consoles, and a browser app has no
cert-friendly path there. It also let MYF's coherence rules subclass the shared Python engine
(item 51). The port is the strategic direction; the prototype is where design is still proven.

**Nothing in Flow B has been played on a correct clock.** The only Flow B table (August 18) ran on
the timer bug item 47 fixed, and the answer screen was rebuilt afterwards (item 50). Its timing
verdicts are not evidence.

---

## Open work, in order

**1. PLAY IT — top of the list since August 17, and still undone.** A fresh table on the fixed
build. Four numbers are guesses: the 8s exclusive window (PT-6), the 5s reading window (PT-5),
whether the lock window gives time to commit (PT-7), and whether 0.75× makes buzzing worth it
(PT-8). Short games: `NEXT_PUBLIC_MYF_ROUNDS=1` and `NEXT_PUBLIC_MYF_QUESTIONS_PER_ROUND=2` in
`.env.local`. **No further mechanic work should go in front of this.**

**2. Owner decisions waiting** — none blocking, all small:
- The three `#7c3aed` purples still in `LOGO_PALETTES` (`components/Logo.jsx`) — the purple the
  owner rejected in item 48 — and whether those palettes want a pass for slate (item 40). One
  decision, not two.
- Spotlight × the 25% cap gives a **1-second** exclusive window (PT-6). If wrong, the fix is a
  floor on the window, not a Spotlight exception.
- Whether `RoundLine` stays in the standings band (Session 33 moved it — item 50, one-line revert).
- Whether the lobby punchline stays the mark (item 49).
- **New (item 53):** the provisional Chosen / Surface / Line values in `lib/palette.js`, and
  whether fixed per-card art conflicts with hidden hands (style guide §4).
- Item 40's open three: does the shareable standings chart unpark the frozen share card; which cut
  of the chart gets shared; can a player skip a host moment.

**3. ~~`server_py`: `questionLog` + `postGame`~~ — done (item 46, Session 50).** The backend now
has everything a Godot end-of-game screen needs: `POST /games/{code}/postgame/vote` and `/skip`,
the question log at GAME_OVER only. Not yet in `ApiClient.gd` — add the two calls with the screen.
**One route is still missing on both sides of the port:** `main.py` exposes no disconnect-vote
endpoints, so a game cannot end by attrition there; when it can, call `_start_post_game` on it.

**4. Godot screens** — category picker (3 categories + the curated grid), card pick, then the round
loop WAGER → CARD → QUESTION → reading → ANSWER → RESULT, then GAME_OVER (after 3). Build them to
`docs/STYLE_GUIDE.md` from the start: a `Style.gd` autoload that builds the theme from a generated
palette, as CYM does. **Check first whether a Godot binary is reachable** — item 34 downloaded one;
CYM's Session 38 found the engine's hosts blocked.

**5. Live-test disconnect/reconnect and inactivity auto-advance against `server_py`** — ported,
never exercised.

**6. Tabled by the owner (item 44):** wager-tier simplification (12 and 25 barely differ —
`scripts/economy-sim.js`), and widening the difficulty ramp's hue toward blue-green / yellow-green
(edit `scripts/build-difficulty-colors.mjs`, never the generated hexes).

**7. Spec'd, not built:** the **Chain** round (`GAME_DESIGN.md`) — needs a call on round-level
category selection first. **Host video** as a centre-screen takeover with pre-packaged attitude
clips (item 40; cost estimate deferred).

**8. Proposed, not done:** rename "open answering" → "buzz-in" (item 43) as one atomic pass, and
rename `answerOpensAt` → `readingEndsAt` — **not** `buzzerOpensAt`, which collides with a real field.

**Parked by owner decision — do not re-prioritise without asking:**

| Item | Why |
|---|---|
| Voice input | Text-only is fine for now. Keep honouring the `text`/`voice` transform split — voice is the destination. |
| Shareable Question polish | The canvas card + Web Share is the placeholder, frozen there. Don't extend it; don't rip it out. |

**Killed by owner decision — do not build, do not re-propose:** group splitting for 7+ players
(item 27). The 3–6 cap at join (item 11) is the whole answer to a big group.

**Known broken:** `scripts/coherence-test.js` imports `POINT_TIERS`, which no longer exists (the
ladder replaced it). Fixing it needs a call on which wager values to sample, and it spends real
API calls, so it is in no routine check.

---

## Architecture

```
mind-your-friends/
├── server.js            Socket.io hub + orchestration around Next.js, port 3000   (prototype)
├── lib/gameState.js     The phase state machine: LOBBY → CATEGORY → WAGER → CARD → QUESTION
│                        → ANSWER → RESULT → … → GAME_OVER, plus transient EVALUATING
├── lib/claudeClient.js  Fact bank, question, evaluation, lineup, superlatives, heckle moderation
├── lib/coherence.js     Round → turn constraints, validateQuestion, pickFactoid (JS; unwired to the engine on purpose)
├── lib/palette.js       THE colour roles — every screen reads from here (item 53)
├── components/          React UI per phase + chrome (BrandBar, Logo, Wordmark, HostStage, GameCard)
├── app/dev/answer/      Dev-only preview of every Flow B moment from fixtures; ?only=N
├── server_py/           FastAPI port: main.py, game_state.py, claude_client.py, coherence_rules.py …
└── godot/               Godot 4.6 client: ApiClient, GameState, lobby
```

**Transport.** The prototype resends the full per-player `playerView()` on every mutation. The
Godot pair splits it CYM's way: HTTP answers the actor, the WebSocket tells the room.
`server_py/main.py` captures the main event loop at startup and hands broadcasts to it with
`run_coroutine_threadsafe` — **keep it that way**: CYM lost a whole playtest when pushes from plain
`def` routes were silently dropped (style guide §7).

**Correctness Python does not give for free.** Node's one event loop made "first correct wins"
mean first *submission*. `server_py` uses a **ticket lock** (claim under `_games_lock`, evaluate
with it released) — a plain `threading.Lock` makes no FIFO promise. Item 42.

**Timers are scoped to a turn, not a phase** (`turnSeq`, item 47). Every turn walks the same
phases, so a phase guard alone lets one question's timer expire the next one.

**Coherence:** `server_py/coherence_rules.py`'s `QuestionRuleSet` subclasses the shared
`coherence.engine.RuleSet` at the repo root — the same class CYM's `coherence_validator.py` uses.
**It cannot be called `coherence.py`**: a module and a package of the same name cannot share
`sys.path`. The repo-root path entry is *appended* so `server_py` wins collisions. Item 51.

**Information hiding:** other players' hands, the answer and `correctOptionId` are withheld until
RESULT; `questionLog` (every correct answer) ships only at `GAME_OVER`.

---

## The look (items 40, 45, 48–50, 52, 53)

- **Ground:** slate `#2F4459` with a generated field of faded question marks at 10% strength
  (`scripts/build-question-field.mjs`). **If it needs adjusting, add density, not opacity.**
- **Plates** (what must be read) are the ground with the texture off — no border, radius or
  shadow — and need the `space-y-6` gap between them or two merge into one block.
- **Boxes** (what must be grabbed) follow `docs/STYLE_GUIDE.md`: square, 2px outline; **outlined
  = available, filled with Chosen = selected, Act fills on hover = "do this"**; an explicit
  disabled look that never reacts to hover; done things are **stamps**, not disabled buttons;
  live status is an outlined notice that shimmers until it stops being true. The classes are in
  `app/globals.css` (`.box`, `.choice`, `.act`, `.stamp`, `.live`).
- **In game: two columns, ⅔ game : ⅓ host slot**, the brand bar inside the game column and no
  title treatment there (item 53b). Choices whose selection is a lit border use `.tile`; an
  action that commits the selection beside it uses `.act-chosen` (blue), not `.act` (gold).
- **Cards stay objects** — saturated, rounded, shadowed, fixed art per card id.
- **Every colour is measured, never picked by eye**: `lib/palette.js` (roles,
  `scripts/palette-test.mjs`), the difficulty ramp (`scripts/build-difficulty-colors.mjs` refuses
  any step under 4.5:1), the player colours (item 40 — **assign by seat, never reorder**).
- **Title treatment:** live type, F1 Oswald / D1 Bebas Neue, deterministic per room (item 52).
  **Logo:** 73px everywhere, one of six palettes per room.

---

## Checks — run before handing anyone a build

All zero API cost unless marked.

| Command | Covers |
|---|---|
| `node scripts/mechanics-test.js` | Flow B, the race, lockout, wager asymmetry, round rules, rebus bank integrity (105 assertions) |
| `node scripts/postgame-test.js` | `questionLog`, superlatives, the answer-leak guard (**2 real Claude calls**) |
| `node scripts/wordmark-test.js` | The two treatments are 50/50 *and* independent of the logo palette |
| `node scripts/palette-test.mjs` | Every colour role against its WCAG floor; `--ground` drift |
| `node scripts/economy-sim.js` | Not a test — the scoring economy. Re-run after touching the ladder or the buzz share |
| `npm run build` | Compiles; catches what a test cannot |
| `cd server_py && python3 test_mechanics.py` | The Python port, incl. the ticket-lock thread race (63) |
| `python3 server_py/test_turn_timers.py` | Item 47's regression test (12) |
| `python3 server_py/test_coherence_engine.py` | Both titles share one engine (23) |
| `cd server_py && python3 test_postgame.py` | The question log, superlative voting, and `main.py` opening and closing it on a short clock (58). Mutation-tested six ways |
| `/dev/answer` in a browser | Every answer-screen state. **Use Playwright's `viewport`** — headless `--window-size` lays out at 500px |

---

## Godot rules (for when the screens get built)

- Godot 4.6 declared. **Run `--headless --import` before trusting any GDScript** — item 34's
  `ApiClient.gd` did not compile as first written.
- `uvicorn[standard]`, not bare `uvicorn` — without WebSocket support the handshake 404s and looks
  like a client bug.
- FastAPI's `TestClient` drops WebSocket pushes from `threading.Timer` threads; test against a real
  `uvicorn` process.
- The style guide §6 table — every one of these failed silently in CYM: a GDScript parse error
  (static nodes draw, nothing responds); a `#` line in a `.tscn` (the next node vanishes); a theme
  item name the engine lacks (no-op); `TextureRect`'s default expand mode (one SVG overflows the
  window); `:=` from `Dictionary.get()` (a `Variant`); triple-quoted strings; Godot 4.7 rewriting
  `project.godot` and deleting its comments — which this project's `project.godot` still has.

---

## Conventions

- **Branch:** MYF lives on `main`. Work on a feature branch; `git push origin main` is rejected
  (403) — open a PR. **`dev/mind-your-friends` is stale** (July 22, no Godot client, no common
  history with `main`); never start from it.
- ESM throughout. The server owns all game logic; clients never call Claude.
- Model: `claude-sonnet-4-6`. Auth: `ANTHROPIC_API_KEY` or the session-ingress token file.
- `.env.local` is loaded by `lib/env.js`, imported **first** in `server.js` — Next.js doesn't load
  env files for a custom server, and `claudeClient.js` builds its client at import time.
- **Prose British, identifiers American:** `colour` in anything a person reads, `color` in
  anything a parser reads.
- Comments explain *why*. A rule a test enforces says so beside it.
- Generated files say so in their header — `lib/logoPaths.js`, `lib/difficultyColors.js`,
  `public/brand/question-field.svg`, `server_py/rebus_data.py`. Regenerate; never hand-edit.
- **A test that cannot fail is decoration.** Prove a new one fails with the fix reverted.
- No database — in-memory state is intentional.

**Common tasks.**
- **Run:** `npm install`, `cp .env.local.example .env.local` (set the key), `npm run dev` → :3000.
- **Force a round rule:** `MYF_FORCE_ROUND_RULE=rebus npm run dev` (overrides round 1 too).
- **Add a round rule:** `lib/roundRules.js` (`id, name, emoji, description, promptInstruction,
  timerSeconds`); a format-changing rule needs both `text` and `voice` transforms. Mirror it in
  `server_py/round_rules.py`.
- **Add a card:** `lib/cards.js` (+ `COMMON_CARD_IDS` / `PICKABLE_CARD_IDS`), effect in
  `resolveCardSlot()`, art in `GameCard.jsx`'s `CARD_ART`. Mirror in `server_py/cards.py`.

## Session protocol

**Start:** `git fetch origin && git checkout main && git pull`; branch off it. If the harness
hands you a branch, compare it against `main` first (Session 33 was handed a stale one). Read the
latest MYF block in `SESSIONS.md` and **Open work** above. State branch, commit and plan.

**End:** append a block to `SESSIONS.md`; update **Open work** here and the item in
`docs/DECISIONS.md`; commit, push the feature branch, open a PR.
