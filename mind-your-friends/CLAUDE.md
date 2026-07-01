# Mind Your Friends — Claude Code Instructions

## Project Overview
Real-time multiplayer social trivia game with sabotage cards, rotating round rules, and a
personalized AI host. Players join via 4-letter code, wager points, play cards against each
other, and answer AI-generated questions. The social loop — not the trivia — is the product.

## Current To-Do
1. ~~**Review Round variation types**~~ — 8 variations confirmed. See `GAME_DESIGN.md`.
2. ~~**Review card mechanic**~~ — FCFS card resolution, fixed 6-card hand (1 picked +
   5 random from pool of 10), single-use, 8 sabotage + 2 anti-sabotage. See `GAME_DESIGN.md`.
3. ~~**Resolve structural open questions**~~ — 4 rounds × 6 questions (24 total), 20s/question,
   common cards = Insurance + Skip, round rules assigned randomly, Boxed In = 1-2 word answers
   (baseline questions are >3 words). See `GAME_DESIGN.md`.
4. ~~**Resolve remaining open questions**~~ — Audience Poll out for v1; categories via
   registration pool (5/player, no DB) + random-6 pick each turn; scoring starts at 0,
   ties are shared wins. See `GAME_DESIGN.md`.
5. ~~**Build the first scaffold**~~ — `server.js`, `lib/gameState.js`, `lib/claudeClient.js`,
   `lib/cards.js`, `lib/roundRules.js`, `lib/constants.js`, Next.js app shell, and components
   (Lobby, CategoryPicker, CardHand, GameBoard, ScoreBoard) are in place. Syntax-checked but
   **not yet run** (`npm install` not done in this session).
6. ~~**Coherence Engine**~~ — `lib/coherence.js` integrated into game loop.
   Round-level constraints computed at turn start; turn-level constraints
   assembled after card resolution; post-generation validation checks answer
   format. Shared framework in `coherence/engine.py` (monorepo root).
7. ~~**Per-player views**~~ — `playerView()` filters state per socket. Hands,
   answers, and role-gated data hidden appropriately.
8. ~~**Steal round rule**~~ — FCFS buzz-in window (8s), half-wager penalty on
   wrong steal. Documented in `GAME_DESIGN.md`.
9. ~~**Redirect**~~ — random target (decided). No UI needed.
10. ~~**Category attribution**~~ — locked at registration, publicly visible,
    attributed in category options. Everyone sees who submitted what.
11. ~~**Player count**~~ — 3–6 players enforced. Hard cap at join.
12. ~~**Wager design principle**~~ — "I cut, you choose" documented.
13. ~~**Whoa Nellie**~~ — category ambush: swaps to a random different category
    from the pool at the same difficulty. Attributed ("swapped to Sarah's
    90s Hip Hop!").
14. ~~**Post-game activations**~~ — superlative voting, replay moments,
    shareable recap, "one more round" moments. See `GAME_DESIGN.md`.
15. ~~**Question types**~~ — three types: First Come First Serve, Open to All,
    Visual. Separate layer from round rules. See `GAME_DESIGN.md → Question Types`.
16. ~~**Worst Answer Wins round rule**~~ — submission-based, 3-axis scoring
    (factually wrong, creatively wrong, plausibility). Lowest total wins.
17. ~~**Rename Slow Burn → Take Your Time**~~
18. ~~**Question–rule coherence**~~ — generation-time constraint documented.
    See `GAME_DESIGN.md → Question–Rule Coherence`.
19. ~~**Complexity guardrails**~~ — "hear it and get it" test added to Design
    Thesis. See `GAME_DESIGN.md → Complexity Budget`.
20. ~~**Hot Take removed**~~ — moved to `PLAYTEST.md` (PT-2). Includes
    stretch idea: player-defined round rules ("Group Round").
21. ~~**Lobby → card pick UI**~~ — `Lobby.jsx` rewritten (two-step flow:
    categories → CardPicker). `CardPicker.jsx` added (40s timer, grid of 10).
22. ~~**Fact bank / batch question pipeline**~~ — `fetchFactsBatch()` in
    `claudeClient.js`. Five-bucket research prompt (Catalyst & Origins →
    Verified Trivia). Called once at game start via `buildFactBank()` in
    `gameState.js`. Stored on `game.factBank`. ~5-7 API calls vs 48.
23. ~~**Question-from-fact builder**~~ — `pickFactoid()` in `coherence.js`
    filters by difficulty + answer format. `generateQuestion()` uses factoid +
    random question angle. Falls back to original prompt if no bank.
24. ~~**First run + playtest**~~ — `npm install` + `npm run dev` succeeded. Ran an
    automated 3-player Playwright playtest (lobby → categories → card pick →
    Start Game → category → wager → card window → question → answer → result)
    and found/fixed 4 crash bugs uncovered only by actually running the app:
    - `claudeClient.js`: Claude sometimes wraps JSON replies in a ```` ```json ````
      fence; raw `JSON.parse` crashed on it. Added a fence-stripping `parseJson()`
      helper used by all 4 API call sites. Also wired the documented
      `ANTHROPIC_API_KEY` / session-ingress-token fallback that was never
      actually implemented.
    - `CategoryPicker.jsx`: rendered `categoryOptions` entries (which are
      `{category, submittedBy, submittedById}` objects per the attribution
      design) as if they were plain strings — fatal "Objects are not valid as
      a React child" crash the instant the CATEGORY phase appeared.
    - `CardHand.jsx` / `cards.js`: every hand always includes the universal
      `'halfOff'` card, but `CARDS` never included it (`HALF_OFF` was a
      separate constant) — `CARDS['halfOff']` was `undefined`, crashing every
      CARD-phase render. Added `CARD_INFO` (merged lookup) and switched
      `CardHand.jsx` to use it.
    - `GameBoard.jsx`: `AnswerPhase`/`ResultPhase` read `game.currentQuestion.*`,
      but `playerView()` never sends a nested `currentQuestion` — it flattens
      to `game.question` / `game.hostQuip` / `game.answer` (answer withheld
      until RESULT/GAME_OVER on purpose). Fixed the client to read the flat
      fields.
    After all 4 fixes, a full turn completes cleanly end-to-end with zero
    console/page errors (verified: category attribution, wager, card window,
    Claude-generated question honoring the active round rule, fuzzy answer
    evaluation, result screen). Next: extend playtesting to a full 24-question
    game, sabotage card plays (not just the auto-resolving card window),
    disconnect/reconnect, and voice input.
25. ~~**Disconnection handling**~~ — 45s grace period → vote to wait/continue.
    `disconnectPlayer()`, `reconnectPlayer()`, `startDisconnectVote()`,
    `castDisconnectVote()`, `resumeAfterDrop()` in `gameState.js`. Server
    wired with `game:rejoin`, `disconnect:vote` events. Future: AI host
    narrates disconnects with humor.
26. **Known gaps / TODOs from the scaffold**:
    - **Spotlight** — approximated as 5s timer; UI doesn't skip a prep step.
    - ~~**Heckle content moderation**~~ — host-reinterpretation via
      `moderateHeckle()` in `claudeClient.js`. Light trash talk encouraged,
      slurs/hate rewritten. `resolveCardSlot()` now async.
    - ~~Game code collisions~~ — retry loop in `server.js` `game:create`.
    - ~~Voice input~~ — `VoiceInput.jsx` component using Web Speech API.
      Server contract already supports `inputMode: 'voice'`. Wire into
      `GameBoard.jsx` answer input when ready for playtest.
27. **[FUTURE] Group splitting** — when 7+ players want to play together,
    design a splintering mechanic to auto-create balanced sub-games (e.g.
    4+3, 3+3+3). Parked until core game is proven.
28. ~~**Extended playtest**~~ — ran an automated 3-player Playwright game that
    actively plays a sabotage/anti-sabotage card every turn (rotating through
    the hand, deprioritizing the always-available Half-Off so real cards get
    exercised) and plays a full 24-question game to `GAME_OVER`. Found and
    fixed 3 more bugs beyond item 24's four:
    - **Missing STEAL phase UI** — `gameState.js`/`server.js` fully
      implement the FCFS steal mechanic (`claimSteal`, `expireSteal`,
      half-wager penalty) but `GameBoard.jsx`'s phase switch had no `STEAL`
      case, so the window silently auto-expired with no way to buzz in.
      Added a `StealPhase` component wired to `turn:claimSteal`, and a
      `result.stolen` headline in `ResultPhase`.
    - **Skip-card crash** — `resolveCardSlot()`'s `'skip'` case sets
      `game.skippedTurn = true` and skips `lastResult` entirely (there's no
      question to report), but `playerView()` never forwarded
      `skippedTurn` to the client. `ResultPhase`'s `if (game.skippedTurn)`
      guard was therefore always false and fell through to
      `game.lastResult.wager`, crashing every client the instant anyone
      played Skip, for the rest of the game. Fixed by adding
      `skippedTurn: !!game.skippedTurn` to the view.
    - **Silent hang on a failed Claude call** — `finishCardPhase()` (which
      calls `generateQuestion()`) was invoked fire-and-forget from
      `resolveCardWindow()`/`startCardWindow()` with no `.catch`; same gap
      in `startAnswerTimer`'s auto-submit path. Any thrown error (network
      blip, truncated JSON) left the turn hung forever in QUESTION/ANSWER
      phase with zero client feedback, and once it did eventually resolve,
      `scheduleNextTurn()` — the only phase-timeout helper with no guard —
      spammed `uncaughtException`s trying to re-advance an already-advanced
      game. Fixed with a shared `recoverFromFailedTurn()` (skips the turn)
      plus the missing phase guard. Also raised `generateQuestion`'s
      `max_tokens` 1024→2048 and loosened the JSON-fence regex to match
      a fenced block anywhere in the reply, not just when it wraps the
      whole response — both reduce how often a verbose round-rule prompt
      trips this path.
    After all fixes: a full 24-question game completes with zero
    console/page errors and zero server exceptions, exercising every
    sabotage/anti-sabotage card, Steal (both a successful and a failed
    steal, plus a no-one-stole expiry), and the inactivity auto-skip system
    (triggered incidentally when a card play left a player un-answered for
    a stretch). Remaining uncovered: voice input mode, disconnect/reconnect,
    and the `submissionBased` flag on Worst Answer Wins (declared on the
    round rule but never actually branched on in `gameState.js` — currently
    plays like a normal single-answerer turn).
29. **[START HERE] Remaining gaps from extended playtest** — pick one:
    voice input mode (wire `VoiceInput.jsx` into `GameBoard.jsx`'s answer
    input, playtest with `inputMode: 'voice'`), disconnect/reconnect
    (kill a browser tab mid-game, confirm the grace period + vote flow),
    or implement `submissionBased` for Worst Answer Wins (all players
    submit an answer, 3-axis scoring, lowest total wins — currently just
    a normal single-answerer turn with a different evaluation prompt).

## Design Thesis: Casual-First
This game targets casual, social players — not competitive optimizers. Every
mechanic must optimize for surprise, laughs, and "oh no!" moments over strategic
depth. Randomness is a feature. Minimal decisions, maximum expression. No homework
required — a new player should understand everything by end of Round 1. Design for
the table, not the meta. See `GAME_DESIGN.md → Design Thesis` for full detail.

## Tech Stack
- Next.js 14 (App Router), React, Tailwind CSS
- Socket.io (custom Node.js server in `server.js` — wraps Next.js on port 3000)
- Claude API (`claude-sonnet-4-6`) — question generation + answer evaluation
- In-memory game state (no DB for MVP)

**Auth** — Use env var `ANTHROPIC_API_KEY` or the session token file;
see `lib/claudeClient.js` for the pattern.

## Architecture
```
server.js           # Socket.io event hub + question generation orchestrator
lib/gameState.js    # In-memory state machine (8 phases: LOBBY → CATEGORY → WAGER → CARD → QUESTION → ANSWER → RESULT → GAME_OVER)
                    # Also: disconnect/reconnect, inactivity detection, fact bank
lib/claudeClient.js # fetchFactsBatch(), generateQuestion(), evaluateAnswer(), moderateHeckle()
lib/coherence.js    # Two-pass CE (roundConstraints → turnConstraints → validateQuestion) + pickFactoid()
lib/cards.js        # Card definitions, dealRoundCards(), buildRoundHand()
lib/roundRules.js   # Rule definitions + answer transforms
lib/constants.js    # Shared constants (no Node-only deps — safe for client components)
components/         # React UI per phase (Lobby, CardPicker, CategoryPicker, CardHand, GameBoard, ScoreBoard, VoiceInput)
app/game/[code]/    # Game room page — Socket.io client, routes by phase
```

## Conventions
- **Branch**: develop on `dev/mind-your-friends` — never commit directly to `main`
- ESM throughout (`"type": "module"`); Socket.io server owns all game logic, never the client
- Model: `claude-sonnet-4-6`
- No comments unless the WHY is non-obvious

## Game Design Context
**Input modes — text and voice:**
The MVP is text-driven. The intended final product is voice-driven (browser mic or phone).
Game logic and state machine are identical in both modes — input mode only affects the
answer surface. `inputMode` (`"text"` | `"voice"`) lives on the session state and is passed
into `transformAnswer()` and `evaluateAnswer()`.

Round rules that constrain the answer format must define both variants:
```js
BACK_IT_UP: {
  transform: {
    text: (answer) => answer.split('').reverse().join(''),   // "htooB sekliW nhoJ"
    voice: (answer) => answer.split(' ').reverse().join(' ') // "Booth Wilkes John"
  }
}
```
Rules with no answer constraint (Lightning Round, Double Down, etc.) are input-agnostic and
need no variants. Never bake in text-only assumptions — voice is the destination.

**Round loop** (server enforces phase order):
1. Active player picks category
2. Next player sets wager (50–500 pts)
3. All players may play a card; first one submitted claims the single FCFS
   "card slot" for the question, all others rejected (see `GAME_DESIGN.md` →
   Card Resolution)
4. Server calls Claude → question (modified by active round rule and any
   resolved format-constraining card — see below)
5. Active player answers within timer
6. Claude evaluates answer (fuzzy match); points awarded/deducted
7. 4s result screen → next turn; after max rounds → GAME_OVER

**The 10 cards (8 sabotage + 2 anti-sabotage, all single-use)** — see
`GAME_DESIGN.md` → The 10 Base Cards for full descriptions. Architecturally:
- **Redirect** changes who answers (`effects.redirectedTo`)
- **Skip** skips the active player's turn entirely
- **Whoa Nellie** re-triggers question generation
- **Spotlight** forces the active player to answer immediately
- **Language Barrier** and **Boxed In** are `generateQuestion()` prompt
  modifiers (register change / answer-format constraint) — resolved *before*
  question generation, not as post-hoc answer checks
- **Heckle** is a pure host-quip injection, no state change
- **Insurance** / **The Fixer** (anti-sabotage) neutralize whatever sabotage
  card would otherwise resolve; The Fixer additionally awards a small bonus
  to the player who played it

**Social loop features (already designed):**
- **Host personalization** — `generateQuestion()` receives `activePlayerName` + `playerNames`;
  the AI host addresses players by name in every `hostQuip`
- **Highlight Reel** — server logs memorable moments (sabotage plays, wrong answers with what
  the player said); sent with `game:over` and rendered in `ScoreBoard` as a shareable recap

## Common Tasks
**Run locally**
```bash
cp .env.local.example .env.local  # add ANTHROPIC_API_KEY
npm install
npm run dev   # starts on :3000
```

**Add a round rule** — edit `lib/roundRules.js`: add entry with
`{id, name, emoji, description, promptInstruction, timerSeconds}`. If the answer needs
transformation, add a case to `transformAnswer()` with both `text` and `voice` variants
(see Input modes above). Input-agnostic rules need no transform case.

**Add a card** — edit `lib/cards.js`: add definition (and to `COMMON_CARD_IDS` or
`PICKABLE_CARD_IDS`). Apply the effect in `gameState.js → resolveCardSlot()`'s switch
statement; log a highlight via `logHighlight()` if it's a notable sabotage moment.

## Session Start Protocol
1. `git checkout claude/continuation-r0mhfq && git pull origin claude/continuation-r0mhfq`
2. Read **Current To-Do** above — item #24 is the next step.
3. Run `git log --oneline -10` to see what was last committed.
4. Read `GAME_DESIGN.md` for the full game design.
5. Read `PLAYTEST.md` for open playtest questions (PT-1 through PT-3).
6. State your starting point in the first reply: branch, latest commit, what you'll do.

## What NOT to Do
- Never push directly to `main` (403). Use `claude/continuation-r0mhfq`.
- Never put Claude API calls in client-side React — only `server.js` touches the API.
- Don't add a database yet — in-memory state is intentional for MVP.
