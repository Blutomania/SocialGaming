# Mind Your Friends — Claude Code Instructions

## Project Overview
Real-time multiplayer social trivia game with sabotage cards, rotating round rules, and a
personalized AI host. Players join via 4-letter code, wager points, play cards against each
other, and answer AI-generated questions. The social loop — not the trivia — is the product.

## Current To-Do
1. ~~**Review Round variation types**~~ — 8 variations confirmed. See `GAME_DESIGN.md`.
2. ~~**Review card mechanic**~~ — FCFS card resolution, fixed 6-card hand, single-use,
   and the full 10-card list (8 sabotage + 2 anti-sabotage) are agreed. See `GAME_DESIGN.md`.
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
6. **[START HERE] First run + playtest** — `npm install`, add `ANTHROPIC_API_KEY` to
   `.env.local`, `npm run dev`, play through a full game with 2+ browser tabs. Expect rough
   edges — see TODOs below.
7. **Known gaps / TODOs from the scaffold**:
   - `broadcast()` sends the full game state to everyone — opponents' hands and the
     correct answer are visible before reveal. Needs per-player views.
   - **Redirect** targets a random other player (placeholder) — no design decision yet
     on how the target should be chosen.
   - **Whoa Nellie** is currently flavor-only (asks Claude for "a different question") —
     the actual "re-roll" mechanic isn't fully specified.
   - **Spotlight** ("no prep time") is approximated as a 5s timer — UI doesn't yet skip
     a distinct "prep" step.
   - **Steal** round rule has no steal-window implementation yet.
   - Voice input mode (`inputMode: "voice"`) is wired into `transformAnswer()`/
     `evaluateAnswer()` signatures but the UI is text-only.
   - Game code collisions aren't checked (`generateGameCode()` doesn't verify uniqueness
     against existing games).

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
