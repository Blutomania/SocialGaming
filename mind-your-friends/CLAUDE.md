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
21. **[START HERE] Lobby → card pick UI** — update `Lobby.jsx` / add
    `CardPicker.jsx` for the 1-pick-from-10 moment at registration.
22. **First run + playtest** — `npm install`, `npm run dev`, play through
    with 3+ browser tabs.
23. **Disconnection handling** — "Wait for our friend" pause screen. Players
    vote to keep waiting or continue without. No AI/bot takeover — dropped
    player's turns are skipped, score freezes. It's a party, not a ranked match.
24. **Known gaps / TODOs from the scaffold**:
    - **Spotlight** — approximated as 5s timer; UI doesn't skip a prep step.
    - **Heckle content moderation** — free-text read by AI host. Define
      boundaries (refuse? rephrase? host-reinterpretation?).
    - Game code collisions aren't checked.
    - Voice input mode (`inputMode: "voice"`) wired into signatures but
      UI is text-only.
25. **[FUTURE] Group splitting** — when 7+ players want to play together,
    design a splintering mechanic to auto-create balanced sub-games (e.g.
    4+3, 3+3+3). Parked until core game is proven.

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
lib/claudeClient.js # generateQuestion(), evaluateAnswer()
lib/cards.js        # Card definitions + dealHand()
lib/roundRules.js   # Rule definitions + answer transforms
lib/constants.js    # Shared constants (no Node-only deps — safe for client components)
components/         # React UI per phase (Lobby, CategoryPicker, CardHand, GameBoard, ScoreBoard)
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
1. `git checkout dev/mind-your-friends && git pull origin dev/mind-your-friends`
2. Read **Current To-Do** above — it has the exact next step.
3. Run `git log --oneline -5` to see what was last committed.
4. State your starting point in the first reply: branch, latest commit, what you'll do.

## What NOT to Do
- Never push directly to `main` (403). Always use `dev/mind-your-friends`.
- Never put Claude API calls in client-side React — only `server.js` touches the API.
- Don't add a database yet — in-memory state is intentional for MVP.
