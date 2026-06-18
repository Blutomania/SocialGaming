# Mind Your Friends — Game Design Document

## Concept
Real-time multiplayer social trivia game. The social dynamics — sabotage, 
coalition-building, reading the room — are the product. The trivia is the vehicle.

---

## Design Thesis: Casual-First

This game targets casual, social players — not competitive optimizers. Every
mechanic should be evaluated through this lens:

- **Optimize for surprise, laughs, and "oh no!" moments** over strategic depth.
  A card play is a social event ("she used her Skip on ME?!"), not a chess move.
- **Randomness is a feature, not a bug.** Random hands create unique situations
  each game. Nobody is studying tier lists or drafting optimal loadouts — they're
  reacting in the moment and riffing off each other.
- **Minimal decisions, maximum expression.** When a player does get a choice
  (picking a card, choosing a category), it should be instant and gut-feel, not
  analysis paralysis. One fun decision beats three strategic ones.
- **No homework required.** A new player sitting down for the first time should
  understand every mechanic by the end of Round 1, without reading rules ahead
  of time. If a feature needs a subreddit to explain it, it's wrong.

Design for the table, not the meta.

### Category + Wager: "I Cut, You Choose"
The category/wager split follows the classic fair-division mechanism
([Yale SOM](https://insights.som.yale.edu/insights/better-way-to-divide-the-pie)):
Player 1 picks the category (the cut); Player 2 prices the risk (the choose).
This self-balances without additional incentive structures — Player 1 can't
pick an easy self-serving category without Player 2 slamming a high wager on
it, and Player 2 can't set a punishing wager without considering that Player 1
chose this category for a reason. The setter needs no skin in the game — their
power IS the balancing force.

---

## Game Structure

### Target Play Time
Under 30 minutes. Design goal: 25 minutes.

### Round & Question Structure
**4 rounds × 6 questions = 24 questions total.**

Back-of-envelope per-question cycle: ~8s category pick + ~8s wager + ~5s card
window + ~4s question generation + 20s answer timer + ~3s evaluation + 4s
result screen ≈ **~50-55s/question** (more with real players reading/typing,
say up to ~65s).
- 24 × 55s ≈ 22 min
- 24 × 65s ≈ 26 min

Lands comfortably inside the 20-30 min target with buffer under the hard cap.

### What is agreed:
- 4 rounds, 6 questions per round (24 total)
- 20 seconds per question
- Each player has a fixed hand of 6 cards for the entire game (see Card Mechanic below)
- **3–6 players per game** (hard cap enforced at join)

---

## The Round Loop
Each question follows this phase order (server enforces):
1. Active player picks a category
2. Next player sets the wager (50–500 pts)
3. All players may play cards (see Card Mechanic below)
4. Server calls Claude → generates question (modified by active round rule)
5. Active player answers within the timer
6. Claude evaluates answer (fuzzy match); points awarded or deducted
7. 4s result screen → next turn

---

## Card Mechanic

### Hand Dealing
- Pool of 10 cards total. Each player's hand is **fixed for the entire game** at 6 cards:
  - **1 player-picked card** — at game start, each player picks 1 card from
    the full pool. One gut-feel decision, no analysis paralysis (see Design
    Thesis above).
  - **5 randomly dealt cards** — server deals 5 from the remaining pool.
    Every player discovers a unique hand they react to in the moment.
- Dealt once at game start; no growth or redraw during the game.
- Duplicate cards across players are fine — if two players both have Skip,
  that's a social dynamic, not a bug.

### Card Resolution — First Come, First Served
**Replaces the old Two-Card Rule (June 2026).** Each question has a single
"card slot." The first player to play a card claims the slot and that card
resolves; everyone else's attempt is rejected (e.g. "too slow!").
- 0 cards played → normal question
- 1+ cards played → first one submitted resolves, all others rejected

**NOTE: this mechanic may need tweaking** — open concerns include reflex-speed
bias (fastest player always wins ties) and self-buff vs. sabotage cards
competing for the same slot (e.g. the active player could self-buff to block
an incoming sabotage). Revisit after playtesting.

### Card Usage Cap
**Single use per game.** Once a card is played (and claims the FCFS slot — see
Card Resolution above), it's removed from that player's hand for the rest of
the game. With only 6 cards per player across 4 rounds, this keeps cards scarce
and each play meaningful.

### The 10 Base Cards
8 sabotage + 2 anti-sabotage. All cards are single-use (see Card Usage Cap above)
and resolve via the FCFS slot (see Card Resolution above).

| # | Card | Type | Effect |
|---|---|---|---|
| 1 | Skip | Sabotage | Target player's turn is skipped entirely |
| 2 | Redirect | Sabotage | Changes who must answer (`effects.redirectedTo`) |
| 3 | Whoa Nellie | Sabotage | Swaps the category to a random different one from the pool (same difficulty). A category ambush. |
| 4 | 50% Off | Sabotage | Halves the active player's wager value |
| 5 | Spotlight | Sabotage | Active player must answer immediately, before seeing the timer/options |
| 6 | Heckle | Sabotage | Player who plays it submits a one-line heckle, read aloud by the AI host before the active player answers — pure social/comedy, no mechanical effect |
| 7 | Language Barrier | Sabotage | AI host phrases the question in a randomly-chosen silly register (Old English, pirate, corporate-legalese, Gen-Z slang, etc.) |
| 8 | Boxed In | Sabotage | Active player's answer must fit in one or two words (see Question Design Conventions below) |
| 9 | Insurance | Anti-sabotage | Question proceeds completely normally, as if no sabotage card had been played |
| 10 | The Fixer | Anti-sabotage | Same as Insurance (sabotage neutralized), plus the player who played it banks a small bonus (e.g. +50 pts) |

**Format-constraining cards are `generateQuestion()` prompt modifiers, not
post-hoc answer checks.** Because cards resolve in step 3 (before question
generation in step 4), Language Barrier and Boxed In feed into the prompt so
Claude designs the Q&A pair to satisfy the constraint by construction —
no risk of an unanswerable question, and no extra evaluation step. This is
the pattern for any future sabotage card that constrains the answer format.

### Question Design Conventions
**Baseline**: every generated question's correct answer should normally be
**more than 3 words** (a short phrase, not a single term). This gives "Back It
Up" (reverse the answer) something substantial to reverse, and gives Boxed In
a real bite.
- **Boxed In** overrides the baseline: the answer must be **one or two words**
  for that question — a meaningful reduction from the norm, not just a
  format quirk.

**Cut from earlier drafts**: Daily Double, Safety Net, Pinch Penny
(self-buff cards) — dropped in favor of an all-sabotage +
anti-sabotage theme (June 2026).


### The Pick Moment
At game start, each player sees the full pool of 10 cards and picks 1.
This is a social moment — players see each other picking, can react ("you
took Heckle? oh no"), and it sets the tone for the game. The remaining 5
are dealt randomly. No common/anchor cards — the randomness ensures variety.

---

## Round Rules (Variations)
Each question is modified by an active round rule. Rules rotate across the game.
Full rule list — 8 confirmed, 1 backburnered:

| # | Name | What changes | Input-agnostic? |
|---|---|---|---|
| 1 | Back It Up | Answer must be reversed | No — see below |
| 2 | One Word Only | Answer must be a single word | No — see below |
| 3 | Lightning Round | Timer halved | Yes |
| 4 | Slow Burn | Timer doubled; host quip escalates | Yes |
| 5 | ELI5 | Question phrased by a curious 5-year-old; Claude judges understanding | Yes |
| 6 | Hot Take | Opinion question; confidence beats correctness | Yes |
| 7 | Double Down | Wager auto-doubled, no backing out | Yes |
| 8 | Steal | Wrong answer opens a steal window for other players | Yes |
| 9 | Audience Poll | Others predict active player's answer *(out of v1 — backburnered)* | Yes |

### Steal — How It Works
When the Steal round rule is active and the answerer gets it wrong:
1. A "wrong" buzzer sound + visual fires for everyone.
2. The game enters a **STEAL phase** (8-second window). Every player except the
   original answerer sees a "STEAL!" button.
3. **First to buzz in claims it** (FCFS, same pattern as card play). They must
   submit their answer immediately.
4. Correct steal: stealer gains the full wager. Wrong steal: stealer loses
   half the wager. Either way, the window closes.
5. If nobody buzzes in within 8 seconds, the window expires and play continues.

**Redirect interaction**: if a Redirect card changed the answerer, the
redirected player is the one excluded from the steal pool — the original
active player can still steal.

### How round rules are assigned
**Random**, assigned each turn by the server.

---

## Categories

### Registration
At lobby join (no database — in-memory, per-game-session only), each player
submits **5 categories** they like (free-text tags, e.g. "Pop Music," "Marvel
Movies," "90s Sitcoms"). All players' submissions go into one shared pool for
that game.

### Category Pick
When it's a player's turn to pick a category, the server shows them **6 random
categories drawn from the shared pool** (their own or others' — no special
weighting). They pick one; it's passed to `generateQuestion()`.

### Parked for later
**AI-host-curated categories** (host persona influencing/adding category
options) — interesting, but depends on a host-persona system that doesn't
exist yet. Not part of v1; revisit once the host's voice/personality is
defined.

---

## Input Modes — Text and Voice

The MVP is text-driven. The intended final product is voice-driven (browser mic or phone).
Game logic is identical in both modes — `inputMode` (`"text"` | `"voice"`) lives on
session state and is passed into `transformAnswer()` and `evaluateAnswer()`.

Round rules that constrain the answer format define both variants:

| Rule | Text transform | Voice transform |
|---|---|---|
| Back It Up | Reverse characters: `htooB sekliW nhoJ` | Reverse word order: `Booth Wilkes John` |
| One Word Only | Trim to first word | First spoken word only |

Input-agnostic rules need no transform variants.
Never bake in text-only assumptions — voice is the destination.

---

## Social Loop Features
- **Host personalization** — AI host addresses players by name in every quip.
  `generateQuestion()` receives `activePlayerName` + `playerNames`.
- **Highlight Reel** — server logs memorable moments (sabotage plays, wrong answers
  with what the player actually said). Sent with `game:over`, rendered as a
  shareable end-game recap.

---

## Open Questions

All structural design questions are resolved as of June 2026:
- Audience Poll: out for v1 (backburnered)
- Categories: registration pool (5 per player, no DB) + random-6 pick each turn;
  AI-host-curated categories parked for later
- Scoring: start at 0 (can go negative), ties are shared wins (no tiebreaker)

No open design questions remain — ready to scaffold the codebase
(`CLAUDE.md` to-do item 5).
