# CLAUDE.md

## Project Overview
Two AI-powered social party games in one monorepo:

1. **Mind Your Friends** (`mind-your-friends/`) — Real-time multiplayer trivia with sabotage cards, rotating round rules, and a personalized AI host. Players join via 4-letter code, wager points, play cards against each other, and answer AI-generated questions. Built on Next.js + Socket.io.

2. **Choose Your Mystery** (root) — Multiplayer social deduction mystery game. AI generates coherent murder mystery scenarios from a 1,469-part corpus. Players join via shareable code; the 75%-information-sharing mechanic forces collaboration while preserving individual advantage.

---

## Tech Stack

**Mind Your Friends**
- Next.js 14 (App Router), React, Tailwind CSS
- Socket.io (custom Node.js server in `server.js` — wraps Next.js on port 3000)
- Claude API (`claude-sonnet-4-6`) — question generation + answer evaluation
- In-memory game state (no DB for MVP)

**Choose Your Mystery**
- Python 3.8+, Streamlit (`app.py`), CLI (`cli.py`)
- Claude API (`claude-sonnet-4-6`)
- JSON file store: `mystery_database/generated/`, `mystery_database/extractions/`

**Auth (both projects)** — Use env var `ANTHROPIC_API_KEY` or the session token file; see `lib/claudeClient.js` for the pattern.

---

## Architecture

**Mind Your Friends**
```
mind-your-friends/
  server.js          # Socket.io event hub + question generation orchestrator
  lib/gameState.js   # In-memory state machine (8 phases: LOBBY→CATEGORY→WAGER→CARD→QUESTION→ANSWER→RESULT→GAME_OVER)
  lib/claudeClient.js # generateQuestion(), evaluateAnswer()
  lib/cards.js       # Card definitions + effect logic
  lib/roundRules.js  # Rule definitions + answer transforms
  components/        # React UI per phase (Lobby, CategoryPicker, WagerModal, CardHand, QuestionCard, ScoreBoard)
  app/game/[code]/   # Game room page — Socket.io client, routes by phase
```

**Choose Your Mystery**
```
app.py              # Streamlit UI
cli.py              # Terminal entry (generate, extract, check, browse, solve)
part_registry.py    # 1,469-part corpus + sampling
coherence_validator.py  # Free P1 causal-chain check (no API call)
mystery_database/   # generated/, extractions/, localization_cache/
docs/WIRING.md      # Canonical generation architecture — read before touching
```

---

## Conventions

- **Branch**: `claude/compassionate-cray-pu5ieu` — all work goes here
- **Mind Your Friends**: ESM throughout (`"type": "module"`); Socket.io server owns all game logic, never the client
- **Choose Your Mystery**: Mystery parts use `SOURCE(INDEX)` notation (`C(4)`, `F(2)`); all generated mysteries include `_provenance` and `_coherence` fields
- **Model**: `claude-sonnet-4-6` everywhere
- **No comments** unless the WHY is non-obvious

---

## Game Design Context

**Mind Your Friends round loop** (server enforces phase order):
1. Active player picks category
2. Next player sets wager (50–500 pts)
3. All players may play one card (sabotage or self-buff)
4. Server calls Claude → question (modified by round rule)
5. Active player answers within timer
6. Claude evaluates answer (fuzzy match); points awarded/deducted
7. 4s result screen → next turn; after max rounds → GAME_OVER + Highlight Reel

**Cards that matter architecturally**: Redirect changes who answers (`effects.redirectedTo`); Muted skips a player; Whoa Nellie re-triggers question generation; Safety Net / Pinch Penny modify point math in `submitAnswer()`.

**Choose Your Mystery** P1 causal chain must be unbroken: crime → victim → closed world → culprit/motive → resolution. Run `coherence_validator.check_parts()` before Claude call, `check_mystery()` after.

---

## Common Tasks

**Run Mind Your Friends locally**
```bash
cd mind-your-friends
cp .env.local.example .env.local  # add ANTHROPIC_API_KEY
npm install
npm run dev   # starts on :3000
```

**Add a new round rule** — edit `lib/roundRules.js`: add entry with `{id, name, emoji, description, promptInstruction, timerSeconds}`. If answer needs transform (e.g., BACK_IT_UP), add case to `transformAnswer()`.

**Add a new card** — edit `lib/cards.js`: add definition. Apply effect in `gameState.js → playCard()`. Log as moment in `server.js → turn:playCard` handler if it's sabotage.

**Generate a mystery (Choose Your Mystery)**
```bash
python cli.py generate --setting "1920s Paris" --genre noir
```

---

## What NOT to Do

- Never push to `main` directly (403). Use the working branch and open a PR.
- Never run the corpus extraction pipeline again — source texts that failed were too brief; re-running produces the same results.
- Never put Claude API calls in client-side React — only `server.js` or Python backends touch the API.
- Don't add a database to Mind Your Friends yet — in-memory state is intentional for the MVP.
- Don't re-extract mysteries that already have JSON in `mystery_database/extractions/`.
