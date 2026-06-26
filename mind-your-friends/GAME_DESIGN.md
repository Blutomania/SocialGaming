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

### Complexity Budget
The game has three modifier layers: **question types**, **round rules**, and
**cards**. That's already three things a player tracks. Each individual element
within those layers must pass the "hear it and get it" test:
- **Question types**: hearing the type name tells you exactly how to play.
  "First Come First Serve" — obvious. "Open to All" — obvious.
- **Round rules**: hearing the rule name tells you what's different this turn.
  "Lightning Round" — faster. "Worst Answer Wins" — be wrong on purpose.
- **Cards**: reading the card name tells you what it does. "Skip" — skip
  someone. "Redirect" — send it to someone else.

If any element needs a paragraph to explain, it's too complex for this game.
When in doubt, cut it.

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
- Each player holds Half-Off (universal) + 1 picked card + 1–2 random cards per round (see Card Mechanic below)
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

### Hand Composition
Each round, a player holds:
- **Half-Off** — universal card, always available, every round, never consumed
- **1 player-picked card** — chosen once at game start (single use for the
  entire game; once played, it's gone for remaining rounds)
- **1–2 randomly dealt cards** — fresh each round, single use for that round

Early game a player holds 3–4 cards; after the picked card is spent, 2–3.
Cards stay scarce, every play matters.
Duplicate cards across players are fine — that's a social dynamic, not a bug.

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

### Question–Rule Coherence
Every generated question must be **coherent with the active round rule**.
`generateQuestion()` receives the active round rule and must produce a Q&A
pair that the rule can meaningfully act on. Examples:

| Round rule | Question requirement |
|---|---|
| Back It Up | Answer must be a phrase worth reversing (not a single letter or number) |
| One Word Only | Answer must have a natural single-word form |
| Worst Answer Wins | Must have a clear factual answer so "wrongness" is measurable |
| ELI5 | Question must be rephrasable in simple language without losing meaning |
| Take Your Time | No special constraint — any question works |
| Lightning Round | No special constraint — any question works |
| Double Down | No special constraint — any question works |
| Steal | Must have a definitive correct answer (no opinion/subjective questions) |

This is a **generation-time constraint**, same pattern as format-constraining
cards: the round rule feeds into the prompt so Claude builds the question to
fit. No post-hoc filtering needed.


### The Pick Moment
At game start, each player sees the full pool of cards with **name +
one-line explanation** for every card (no matter how intuitive the name —
every card gets a description). Players have **40 seconds** to pick 1 card.

- Picks are **private** — you don't see what others are choosing
- When the timer expires (or all players have picked), all picks are
  **revealed simultaneously** — "Jake took Skip, Sarah took Insurance,
  Mia took Heckle, Tom took Redirect"
- If a player doesn't pick in time, they get a **random assignment** —
  no penalty, game keeps moving
- This is a social moment: reactions, trash talk, reading into each
  other's choices

---

## Question Types
Each question has a **type** that determines how players answer and how scoring
works. The type is announced before the question — a player should immediately
know what's expected of them just from hearing the type name. No rulebook
consultation, no "wait, what does that mean?" moments.

**Intuitiveness test**: if you can't explain the question type in ≤5 words to
someone mid-party, it's too complex. Rename or cut it.

| # | Type | How it works | Scoring |
|---|---|---|---|
| 1 | First Come First Serve | Speed — first correct answer wins | Only the first correct answer scores |
| 2 | Open to All | Everyone answers; no speed pressure | Anyone who gets it right scores points |
| 3 | Visual | Image-based prompt (logo, scene, clue) — identify what you see | Follows FCFS or Open to All scoring (server picks) |

Question types and round rules are **separate layers** — a round rule modifies
how the question plays out on top of whatever question type is active. E.g.
"Visual + Worst Answer Wins" or "Open to All + Lightning Round."

---

## Round Rules (Variations)
Each question is modified by an active round rule. Rules rotate across the game.
Full rule list — 9 confirmed, 1 backburnered:

| # | Name | What changes | Input-agnostic? |
|---|---|---|---|
| 1 | Back It Up | Answer must be reversed | No — see below |
| 2 | One Word Only | Answer must be a single word | No — see below |
| 3 | Lightning Round | Timer halved | Yes |
| 4 | Take Your Time | Timer doubled; host quip escalates | Yes |
| 5 | ELI5 | Question phrased by a curious 5-year-old; Claude judges understanding | Yes |
| 6 | Hot Take | Opinion question; confidence beats correctness *(needs rework — too amorphous, unclear what "winning" looks like to a player)* | Yes |
| 7 | Double Down | Wager auto-doubled, no backing out | Yes |
| 8 | Steal | Wrong answer opens a steal window for other players | Yes |
| 9 | Worst Answer Wins | Everyone submits; worst answer scores lowest (wins). Scored on 3 axes: factually wrong (1-10), creatively wrong (1-10), plausibility (1-10). Lowest total wins. | Yes |
| 10 | Audience Poll | Others predict active player's answer *(out of v1 — backburnered)* | Yes |

### Worst Answer Wins — How It Works
This is a **submission-based** round (not speed-based). All players get the
same question and a time window to craft their answer. Answers are revealed
simultaneously, then scored by the AI on three axes (1 = best/worst, 10 = most
correct/boring/implausible):
1. **Factually wrong** — how far from the truth? (1 = maximally wrong)
2. **Creatively wrong** — how inventive is the wrongness? (1 = most creative)
3. **Plausibility** — how convincing does it sound despite being false? (1 = most plausible)

Lowest total score wins. The sweet spot: completely false, wildly creative,
yet somehow sounds convincing.

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

## Post-Game Activations
Inspired by "For the Girls" party game energy — extend the social experience
beyond the last question so the game doesn't just *end*, it *lands*.

### Superlative Voting
After GAME_OVER, a brief voting round. Everyone votes on AI-generated
superlative categories drawn from what actually happened:
- "Best Sabotage" — based on logged card plays
- "Worst Answer" — based on logged wrong answers
- "Luckiest Steal" — if any steals occurred
- "Most Targeted Player" — whoever had the most cards played against them
The AI host announces each winner with a personalized quip.

### Replay Moments
The highlight reel is presented as a slideshow, not a flat list. Each moment
gets a card-style screen with AI host narration: "Remember when Jake played
Whoa Nellie and Sarah had to answer Marine Biology?" Players swipe/click
through together.

### Shareable Recap
A generated image or shareable link summarizing the game: final scores,
superlatives, 2–3 best highlights, player names. This is the growth mechanic —
"look at this game we just played." Designed for group chats and social media.

### "One More Round" Moments
Post-game dares or challenges based on what happened. The AI host generates
1–2 challenges tied to the game's narrative: "Jake, since you went negative,
you pick the restaurant tonight." Optional, social, no mechanical consequence.

---

## Disconnection Handling
**"Wait for our friend"** — when a player disconnects mid-game, the game
pauses. All remaining players see a waiting screen with two options:
1. **Keep waiting** — game stays paused.
2. **Continue without** — requires majority vote. The dropped player's turns
   are skipped for the rest of the game, their score freezes.

No AI takeover, no bot substitution. It's a party, not a ranked match.

---

## Open Questions

All structural design questions are resolved as of June 2026:
- Audience Poll: out for v1 (backburnered)
- Categories: registration pool (5 per player, no DB) + random-6 pick each turn;
  AI-host-curated categories parked for later
- Scoring: start at 0 (can go negative), ties are shared wins (no tiebreaker)
- Heckle content moderation: TBD — options are pass-through, host
  reinterpretation, tone-gating, or curated templates

No blocking design questions remain.
