# Mind Your Friends — Game Design Document

## Concept
Real-time multiplayer social trivia game. The social dynamics — sabotage, 
coalition-building, reading the room — are the product. The trivia is the vehicle.

---

## Game Structure

### Target Play Time
Under 30 minutes. Design goal: 25 minutes.

### Round & Question Structure
**UNDECIDED** — see Open Questions below. The tension is between:
- 5 rounds × 3 questions (fits 25 min, breaks card progression pacing)
- 3 rounds × 5 questions (fits 25 min, loses the full 10-card payoff)
- 5 rounds × 5 questions with ~60s per question (fits 25 min, more chaotic)

### What is agreed:
- 5 rounds
- Each player has a fixed hand of 6 cards for the entire game (see Card Mechanic below)
- Questions per round and time per question TBD

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
  - **2 common cards** — every player gets the same 2 cards. These double as the
    Round 1 anchor cards (see below) — chosen to be instantly understandable,
    funny, and not punishing.
  - **4 player-picked cards** — at game start, each player picks 4 of the
    remaining 8 cards for their hand.
- Dealt once at game start; no growth or redraw during the game.

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
the game. With only 6 cards per player across 5 rounds, this keeps cards scarce
and each play meaningful.

### The 10 Base Cards
8 sabotage + 2 anti-sabotage. All cards are single-use (see Card Usage Cap above)
and resolve via the FCFS slot (see Card Resolution above).

| # | Card | Type | Effect |
|---|---|---|---|
| 1 | Skip | Sabotage | Target player's turn is skipped entirely |
| 2 | Redirect | Sabotage | Changes who must answer (`effects.redirectedTo`) |
| 3 | Whoa Nellie | Sabotage | Forces server to re-generate the question |
| 4 | 50% Off | Sabotage | Halves the active player's wager value |
| 5 | Spotlight | Sabotage | Active player must answer immediately, before seeing the timer/options |
| 6 | Heckle | Sabotage | Player who plays it submits a one-line heckle, read aloud by the AI host before the active player answers — pure social/comedy, no mechanical effect |
| 7 | Language Barrier | Sabotage | AI host phrases the question in a randomly-chosen silly register (Old English, pirate, corporate-legalese, Gen-Z slang, etc.) |
| 8 | Boxed In | Sabotage | Active player's answer must fit a randomly-chosen format constraint (one word, exactly seven letters, no repeated letters, etc.) |
| 9 | Insurance | Anti-sabotage | Question proceeds completely normally, as if no sabotage card had been played |
| 10 | The Fixer | Anti-sabotage | Same as Insurance (sabotage neutralized), plus the player who played it banks a small bonus (e.g. +50 pts) |

**Format-constraining cards are `generateQuestion()` prompt modifiers, not
post-hoc answer checks.** Because cards resolve in step 3 (before question
generation in step 4), Language Barrier and Boxed In feed into the prompt so
Claude designs the Q&A pair to satisfy the constraint by construction —
no risk of an unanswerable question, and no extra evaluation step. This is
the pattern for any future sabotage card that constrains the answer format.

**Cut from earlier drafts**: Daily Double, Safety Net, Pinch Penny
(self-buff cards) — dropped in favor of an all-sabotage +
anti-sabotage theme (June 2026).


### Round 1 Anchor Cards
The 2 common cards (see Hand Dealing above) serve this role — every player has
them from the start, so they must be:
- Instantly understandable
- Creates a visible, funny moment
- Not punishing to the target
**Which 2 cards** — still TBD pending the full 10-card list (see Open Questions).

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
| 9 | Audience Poll | Others predict active player's answer *(backburnered — complex)* | Yes |

### How round rules are assigned
**UNDECIDED** — randomly assigned each turn, or active player chooses?

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

| # | Question | Leading candidates |
|---|---|---|
| 1 | Questions per round? | 3 or 5 |
| 2 | Time per question? | 90s or 60s |
| 3 | Which 2 cards are the common/anchor cards? | TBD — likely Heckle (low-stakes, funny) plus one more |
| 4 | How are round rules assigned? | Random or player choice |
| 5 | Boxed In's format constraint pool? | TBD — tune during playtest |
