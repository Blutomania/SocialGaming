# Mind Your Friends — Claude Code Instructions

## Project Overview
Real-time multiplayer social trivia game with sabotage cards, rotating round rules, and a personalized AI host. Players join via 4-letter code, wager points, play cards against each other, and answer AI-generated questions. The social loop — not the trivia — is the product.

## Tech Stack
- Next.js 14 (App Router), React, Tailwind CSS
- Socket.io (custom Node.js server in `server.js` — wraps Next.js on port 3000)
- Claude API (`claude-sonnet-4-6`) — question generation + answer evaluation
- In-memory game state (no DB for MVP)

**Auth** — Use env var `ANTHROPIC_API_KEY` or the session token file; see `lib/claudeClient.js` for the pattern.

## Architecture
```
server.js          # Socket.io event hub + question generation orchestrator
lib/gameState.js   # In-memory state machine (8 phases: LOBBY→CATEGORY→WAGER→CARD→QUESTION→ANSWER→RESULT→GAME_OVER)
lib/claudeClient.js # generateQuestion(), evaluateAnswer()
lib/cards.js       # Card definitions + effect logic
lib/roundRules.js  # Rule definitions + answer transforms
components/        # React UI per phase
app/game/[code]/   # Game room page — Socket.io client, routes by phase
```

## Conventions
- **Branch**: always use a `claude/` prefixed branch — never commit directly to `main`
- ESM throughout (`"type": "module"`); Socket.io server owns all game logic, never the client
- Model: `claude-sonnet-4-6`
- No comments unless the WHY is non-obvious

## Game Design Context
**Round loop** (server enforces phase order):
1. Active player picks category
2. Next player sets wager (50–500 pts)
3. All players may play one card (sabotage or self-buff)
4. Server calls Claude → question (modified by round rule)
5. Active player answers within timer
6. Claude evaluates answer (fuzzy match); points awarded/deducted
7. 4s result screen → next turn; after max rounds → GAME_OVER

**Cards that matter architecturally**: Redirect changes who answers (`effects.redirectedTo`); Muted skips a player; Whoa Nellie re-triggers question generation; Safety Net / Pinch Penny modify point math in `submitAnswer()`.

**Social loop features (already built):**
- **Host personalization** — `generateQuestion()` receives `activePlayerName` + `playerNames`; the AI host addresses players by name in every `hostQuip`
- **Highlight Reel** — server logs memorable moments (sabotage card plays, wrong answers with what the player said); sent with `game:over` and rendered in `ScoreBoard` as a shareable end-game recap

## Common Tasks
**Run locally**
```bash
cp .env.local.example .env.local  # add ANTHROPIC_API_KEY
npm install
npm run dev   # starts on :3000
```

**Add a round rule** — edit `lib/roundRules.js`: add entry with `{id, name, emoji, description, promptInstruction, timerSeconds}`. If the answer needs transformation (e.g., BACK_IT_UP reverses the string), add a case to `transformAnswer()`.

**Add a card** — edit `lib/cards.js`: add definition. Apply the effect in `gameState.js → playCard()`. If it's a sabotage card, log a moment in `server.js → turn:playCard`.

## Current To-Do

1. **Review Round variation types** — audit `lib/roundRules.js`; Claude should suggest, edit, delete, or comment on existing rules so we end up with at least 8 well-defined, playable variations.
2. **Review card mechanic** — audit `lib/cards.js` and its integration in `gameState.js → playCard()`; confirm each card's effect is correctly wired, balanced, and clearly defined.

---

## What NOT to Do
- Never push directly to `main` (403). Always use a `claude/` branch.
- Never put Claude API calls in client-side React — only `server.js` touches the API.
- Don't add a database yet — in-memory state is intentional for MVP.
