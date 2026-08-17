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

### The wager ladder

**Five tiers: 12 / 25 / 50 / 100 / 200** (decided August 17 2026). A doubling
ladder anchored so that **100 is the whole pie** — every rung is a fraction of
one, and the wager screen draws it that way: an eighth, a quarter, a half, all
of it, and more pie than there is.

This replaced a 50–500 slider in 10-point steps, which was arbitrary in a way
that mattered. It offered 46 values across a range whose ends were both wrong —
a 50 swung about 4% of a typical winning margin (noise), a 500 swung 43% (one
question deciding half the night) — at a resolution far finer than any decision
a person can actually make, and nothing on screen said what a big number was
supposed to mean.

The ladder spreads properly instead. Share of a typical winner-to-loser margin,
from `scripts/economy-sim.js`:

| Tier | Wager | Swings | Share of the margin | A buzz pays |
|---|---|---|---|---|
| Sliver | 12 | 24 | 3% | 10 |
| Slice | 25 | 50 | 6% | 20 |
| Half | 50 | 100 | 12% | 40 |
| Whole pie | 100 | 200 | 23% | 75 |
| DOUBLE | 200 | 400 | 47% | 150 |

Two consequences worth keeping:

- **Five buttons is a decision you can make in two seconds and say out loud**
  ("you're getting the whole pie"). A slider never was.
- **The wager is a real difficulty signal.** It becomes the difficulty
  instruction in the generation prompt *and* the filter on the fact bank, one
  rung per tier — so the question genuinely gets harder as the pie grows, and
  the question text is printed in a colour keyed to that tier.

Off-ladder values are **rejected, not clamped**: the screen offers five buttons,
so anything else is a stale client, and a wager of 137 is one no pie can draw.

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
- Each player holds Half-Off (universal) + 1 picked card + 2 random cards per round (see Card Mechanic below)
- **3–6 players per game** (hard cap enforced at join)

---

## The Round Loop — "Flow B"

**Status: BUILT August 17 2026** in the Next.js prototype and in `server_py`.
Not yet played by real people — see "Still needs a table" below. This supersedes
both the original single-answerer loop and the Aug 12 free-for-all. What changed
and why is in "Why the active player answers first" below.

Each question follows this phase order (server enforces):

1. **Active player picks a category** — from the six offered options.
2. **Next player (to their left) sets the wager** — one of five tiers, see
   "The wager ladder" below. Adversarial by design; see "I Cut, You Choose".
3. **Card window.** Anyone may play a sabotage or defence card at the active
   player (see Card Mechanic).
4. **Server calls Claude → generates the question**, modified by the active
   round rule.
5. **Reading window (`READING_SECONDS`, 5s).** The question is on screen and
   *nobody* can answer. Nobody should be racing a clock they haven't finished
   reading.
6. **The active player's exclusive window (`ACTIVE_WINDOW_SECONDS`, 8s).** Only
   they may answer. It is their wager, so they get first refusal on their own
   question.
7. **Active player answers correctly → they win the wager.** Question ends.
8. **Active player answers wrong → they lose the wager,** and the buzzer opens
   to the room immediately.
9. **Active player passes → the buzzer opens immediately and they lose
   nothing.** Passing is a real decision, not a forfeit: with 500 on a category
   you don't know, folding is legitimate play.
   **A pass is an explicit action. Running out of time is not.** If the active
   player neither answers nor passes and their window simply expires, they lose
   the wager exactly as if they'd answered wrong — the existing "stalling isn't
   free" rule (`expireAnswerWindow`) is preserved. The distinction is the point:
   folding is a decision and costs nothing, freezing is a failure and costs the
   wager. Without it, "pass" would just be a free opt-out of every hard question
   and the wager would stop mattering again — the exact problem Flow B exists to
   fix.
10. **Buzzer open to everyone else** for the remainder of the answer clock.
    One attempt each; the first correct answer wins `BUZZ_WAGER_SHARE` (0.75)
    of the wager. A wrong guess locks you out of this question and costs
    nothing.
11. **Claude evaluates each attempt** (fuzzy match), serialised so that "first
    correct" means first *buzz*, never first API response.
12. **4s result screen → next turn.** Turn passes in fixed rotation regardless
    of who answered. **Answering never earns another turn.**

### Pre-committed answers — you buzz with what you already wrote

**Owner's call, August 17 2026.** Everyone except the answerer types their
answer **during the answerer's exclusive window** and locks it in. A buzz then
plays that committed answer. You cannot type one after the fumble.

Three things follow, and all three are the point:

- **It closes the lookup window.** The moment worth cheating in is the one
  *after* the answerer fails, with the whole remaining clock to search. That
  moment no longer accepts new answers.
- **Buzzing stops being a typing race.** It becomes one tap — a decision about
  whether to commit, not a test of words-per-minute. That is the right outcome
  for a game whose thesis is casual-first.
- **The room is busy during the exclusive window** instead of watching. No dead
  air, and everyone is invested in whether the answerer fumbles.

**No lock, no buzz.** A player who never committed sits the question out. That
is the whole mechanism — an escape hatch for the uncommitted would reopen the
lookup window it exists to close.

Two rules keep it fair:

- **The lock deadline never moves.** It is fixed at the *scheduled* end of the
  exclusive window. The answerer passing brings the **buzzer** forward but not
  the **lock deadline** — otherwise folding at second one would cut the room off
  mid-sentence and the question would die with nobody able to buzz.
- **A commitment is immutable.** One you can revise until the last instant is
  not a commitment, and the mechanic rests on having decided early.

**A question nobody can answer ends immediately** rather than running the clock
down. Once locking closes, if no eligible player holds a committed answer, there
is no way to resolve the question and no reason to make the room watch a buzzer
nobody can press.

**The unplayed answers are revealed at the result.** This is the loudest moment
the mechanic produces: *"you HAD it and sat on it"* is the line people shout at
each other, and it is invisible unless the room is shown the commitments.

### Why the active player answers first

The Aug 12 change opened every question to the whole room, which fixed the real
problem it was aimed at (two players sitting silent while a third floundered)
but created a quieter one: **if a faster player always takes the question, the
wager never bites.** The active player watches their own question get taken and
neither wins nor loses anything. That is PLAYTEST.md **PT-4**, and Flow B is the
answer to it.

Restoring first refusal (step 6) puts the wager back where "I Cut, You Choose"
needs it. The wager-setter's power only balances the category-picker if the
category-picker is the one exposed to it. If anyone can claim the wager, the
setter stops setting a punishment and starts setting **a bounty they might
collect themselves** — so they would always set maximum, and the most
interesting decision in the game collapses.

Buzzing survives, but its character changes from **race** to **vulture**: you
are pouncing on a fumble, not outrunning the person whose question it is. That
is a better fit for casual-first — the fast player still gets rewarded, but not
by taking anything away from someone who never got a turn to try.

### Parameters

| Parameter | Value | Note |
|---|---|---|
| `READING_SECONDS` | 5 | Nobody may answer. Already built. |
| `ACTIVE_WINDOW_SECONDS` | 8 | **New.** Carved *out of* the round rule's answer clock, not added to it, so total question length is unchanged. |
| Exclusive-window cap | 25% of the rule's clock | So Lightning Round (20s) gets a 5s exclusive window rather than 8s of its 20. Without this, halving the clock makes the round mostly-exclusive. |
| `BUZZ_WAGER_SHARE` | 0.75 | A buzz-in win pays this share of the wager, for anyone but the answerer. See "What a buzz is worth" below. |

The buzzer opens on **whichever comes first**: the active player answering, the
active player passing, or the exclusive window expiring. A pass must open it
*immediately* — making the room wait out a window the active player has already
declined is exactly the dead air this game keeps trying to remove.

**Does not apply to round rules with their own answer flow.** Worst Answer Wins
(`submissionBased`) and The Lineup (`lineupBased`) keep their existing
structures — everyone submits, or everyone taps. Rebus is ordinary free text and
does use Flow B.

### What a buzz is worth

**0.75x the wager, not a flat number** (decided August 17 2026, replacing a flat
100). Two reasons:

- **It is self-anchoring.** "Three-quarters of what they were playing for" needs
  no explanation. A flat 100 floats free of every other number on screen, which
  is exactly why nobody could tell whether 100 was a lot or a little.
- **It scales with the question's danger.** A big wager buys a harder question,
  so taking a hard one should pay more than taking an easy one.

**The share must stay below 1.** At 1.5x a buzzer would earn 300 on a question
the answerer could only win 200 on, while risking nothing — which inverts the
risk hierarchy of the whole game and makes being the active player something to
avoid. Under 1, that hierarchy stays the right way up.

It also barely disturbs "I cut, you choose". Any wager-linked payout gives the
setter — who is also a buzzer on that question — some interest in setting high,
but at 0.75x it moves their break-even from "will they get this?" at 50% to
about 55%. At 1.5x the whole decision starts to collapse.

`scripts/economy-sim.js` models this; re-run it after changing the share or the
ladder rather than arguing about it.

**Still needs a table.** Flow B is a reasoned answer to PT-4, not a validated
one. Two numbers are the guesses most likely to be wrong: the 8-second exclusive
window (too short and it is a formality, too long and the room is waiting), and
whether the lock window gives people enough time to commit an answer at all.

---

## Card Mechanic

### Hand Composition
Each round, a player holds:
- **Half-Off** — universal card, always available, every round, never consumed
- **1 player-picked card** — chosen once at game start (single use for the
  entire game; once played, it's gone for remaining rounds)
- **2 randomly dealt cards** — fresh each round, single use for that round

Early game a player holds 4 cards; after the picked card is spent, 3.
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
| Rebus | N/A — the puzzle comes from the curated bank, not from generation. The category still sets wager difficulty but does not shape the puzzle |
| The Lineup | Must resolve to exactly one unambiguous correct option from a small fixed set — no free-text answer, same category as Steal's "definitive correct answer" requirement |

This is a **generation-time constraint**, same pattern as format-constraining
cards: the round rule feeds into the prompt so Claude builds the question to
fit. No post-hoc filtering needed.


### The Pick Moment
At game start, each player sees the full pool of cards with **name +
one-line explanation** for every card (no matter how intuitive the name —
every card gets a description). The screen displays the instruction text:

> **Card Selection:** Please select a card you will have throughout the game.
> You can play your card one time every round.

Players have **40 seconds** to pick 1 card.

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
| 3 | Visual | Image-based prompt (logo, scene, clue) — identify what you see | Follows FCFS or Open to All scoring (server picks). **See trademark/copyright note below.** |

**Visual question type — image sourcing:**
Curated pool of freely licensed visual assets, tagged by category (logos,
landmarks, objects, symbols, etc.). `generateQuestion()` picks from the pool
based on the active category. No AI-generated images, no copyright gray areas.

**Asset sources:**
- **Wikimedia Commons** — logos, landmarks, historical images (Creative Commons / public domain)
- **The Noun Project** — icons and symbols for stylized visual puzzles
- **Open Game Art / OpenClipart** — public domain illustrations

Each asset must have clear licensing metadata before entering the pool.
**Legal review still recommended before launch** for trademark use in
trivia context.

Question types and round rules are **separate layers** — a round rule modifies
how the question plays out on top of whatever question type is active. E.g.
"Visual + Worst Answer Wins" or "Open to All + Lightning Round."

---

## Round Rules (Variations)
**One rule per ROUND**, not per question (changed Aug 12, 2026). The rule is
announced in a banner at the top of the round and stays on screen for its
duration — a rule you have to remember is one people forget mid-round and then
feel cheated by. **Round 1 has no rule at all**, deliberately: a new player
should learn the base game before a rule bends it. Rules don't repeat until
every rule has had a round.

Full rule list — 9 live, 1 spec'd, 1 retired, 1 backburnered:

| # | Name | What changes | Input-agnostic? |
|---|---|---|---|
| 1 | Back It Up | Answer must be reversed | No — see below |
| 2 | One Word Only | Answer must be a single word | No — see below |
| 3 | Lightning Round | Timer halved | Yes |
| 4 | Take Your Time | Timer doubled; host quip escalates | Yes |
| 5 | ELI5 | Question phrased by a curious 5-year-old; Claude judges understanding | Yes |
| 6 | Double Down | Wager auto-doubled, no backing out | Yes |
| 7 | Worst Answer Wins | Everyone submits; worst answer scores lowest (wins). Scored on 3 axes: factually wrong (1-10), creatively wrong (1-10), plausibility (1-10). Lowest total wins. | Yes |
| 8 | The Lineup | Pick the right one from a lineup of look-alikes — see below | N/A — no free-text answer at all |
| 9 | Rebus | The answer is spelled out in emoji — see below | Yes |
| — | Chain | Every answer in the round shares a theme — **spec'd, not built**, see below | Yes |
| — | ~~Steal~~ | **Retired Aug 12, 2026.** Open answering made this the default behaviour of every question, so the rule was one round in nine where the normal rules applied. See PLAYTEST.md PT-4 | — |
| — | Audience Poll | Others predict active player's answer *(out of v1 — backburnered)* | Yes |

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

### Rebus — How It Works
The question is a string of emoji that spell or sound out the answer, plus a
one-line hint of what kind of thing it is. 💯 + 🧑 → SURE + MAN → **Sherman**.
The hint is not decoration: without it a rebus is a guessing game with no way
in, which fails the casual-first test.

Two kinds, and the difference is marked in the data:
- **Literal** — the pieces spell the answer exactly (☀️ + 🌼 = SUNFLOWER).
- **Phonetic** — the pieces *sound* like it (🍩 + 🔑 = DOUGH + KEY = DONKEY).
  These get an on-screen nudge: "say the pictures out loud."

**Zero API calls.** Puzzles come from a curated bank (`lib/rebusData.js`),
for the same reason The Lineup's colour flavour uses a curated hex table: a
rebus whose pieces don't reconstruct its answer is *unsolvable*, and a room
can't tell "we're stupid" from "the game is broken". Decomposing a word into
sounds is among the things language models are least reliable at, so live
generation would produce exactly that failure at some rate. Curation removes
the failure mode rather than trying to catch it at runtime.

**Structure: pieces, not puzzles.** The bank is a library of reusable *pieces*
(`key -> {emoji, reads}`) plus puzzles that are just lists of piece keys. The
same atoms recur constantly — MAN appears in six puzzles, SUN in four — so
keying them means one emoji decision per concept instead of one per puzzle,
and improving a piece improves everywhere it's used. It also gives any future
generation path a fixed vocabulary to compose from, which is what makes an
AI-proposed rebus checkable: "pick from these 113 pieces" can be validated
mechanically, "invent a rebus" cannot.

`scripts/mechanics-test.js` asserts every non-phonetic puzzle reconstructs its
answer letter-for-letter, that every piece key resolves, and that no piece is
orphaned. A broken puzzle can't ship.

**The reveal shows the decomposition** (🟢 GREEN + 🏠 HOUSE = Greenhouse). A
player who missed it has to find out *why*, or it's a trick rather than a
puzzle.

**Known limitation:** the puzzle ignores the picked category, same as The
Lineup's colour flavour and for the same reason — the bank isn't categorized,
and forcing a match would mean either a far larger bank or falling back to
live generation. The category pick still happens; it sets wager difficulty and
keeps the turn loop's attribution beat intact.

### Chain — How It Works *(SPEC ONLY — not built)*
Every answer in the round shares a theme. "Every answer this round contains a
colour." "Every answer is a US state." The round announcement names the theme
up front.

**Why announce it rather than let the room discover it.** The obvious version
hides the theme so spotting it is the thrill — but under open answering, the
first player to spot it then wins every remaining question in the round. That
isn't a mechanic, it's a landslide. Announcing it inverts the effect: the
theme becomes a *hint*, which helps the players who need help, which is the
casual-first thesis. The "ohhh" moment moves from spotting the pattern to
seeing how each answer fits it.

**The variant NOT chosen:** last-word-of-answer-N becomes first-word-of-
question-N+1. It's brittle to generate and, more importantly, invisible to
players mid-round — a pattern nobody notices isn't a mechanic.

**The architectural cost, which is the real reason this is spec'd and not
built.** Questions are built from the pre-generated fact bank, and the
category is picked fresh each turn by the active player. Finding "a fact in
*90s Movies* whose answer contains a colour" is a filter over ten factoids
that will frequently come back empty. So a chain round needs one of:

1. **Generate without the fact bank** — the no-factoid fallback path exists,
   but it's the weaker one, and this rule would use it for a sixth of the game.
2. **Generate the round's questions up front, one category for the whole
   round** — defensible as design (a rule that changes the round's *structure*,
   not just the question) and *cheaper to run*: one Claude call per round
   instead of six. But it's the first round rule that would touch the turn
   loop rather than just question generation, and it removes the per-turn
   category pick for that round, which carries attribution and the Whoa Nellie
   card's whole reason to exist.

**Recommended shape if built:** option 2. One category for the round, chosen
by the round's first active player. Theme announced with the rule. Six
questions generated in a single call, each answer sharing the theme, validated
before use — a chain where one answer doesn't fit is worse than no chain.

**Whoa Nellie restarts the chain** (owner's call). The card keeps its identity
— it has always been the context ambush — and gains its most dramatic possible
version: the room is mid-pattern, and one card tears it up. New theme from this
question on.

That also resolves the announced-vs-hidden tension above, by splitting the
difference along the line the card draws:

- The round's **opening** theme is announced. Kind by default, no landslide.
- A theme installed by **Whoa Nellie is not announced.** The room has to spot
  the new one themselves.

So the base round helps the players who need help, and the sabotage makes the
rest of the round cruel — which is the right way round, and gives the card real
teeth without letting one sharp player run away with a whole round. The
landslide risk is bounded to whatever is left of the round.

Attribution works as it does today: "Bob tore up the chain — new theme, and
you're on your own."

**Mechanical consequences of the restart, to design against:**
- **Cost:** one extra generation call for that round. Acceptable — the card is
  single-use and there's one card slot per question, so it can fire at most
  once per round.
- **Latency:** regenerating six questions mid-turn is slower than the single
  question Whoa Nellie re-triggers today. Generate the *next* question
  immediately and the rest in the background — the same lazy-then-prefetch
  shape already built for the fact bank.
- **Only regenerate what's left.** Questions already played stay played; their
  scores stand.
- **Edge case:** played on a round's last question, a restart is pointless.
  Fall back to the normal category-swap behaviour there rather than building a
  one-question chain.

**Open questions still to settle before building:**
- If the opening theme is announced, is the round *easier* than a normal round,
  and should the flat buzz-in rate drop to compensate?
- Where does the theme list come from — curated (like the rebus bank and the
  category grid) or generated per round?

### The Lineup — How It Works
Not free-text at all — a multiple-choice "spot the real one" mechanic. 5
options render (text list or color swatches), exactly one correct, the rest
deliberately close near-misses.
1. The active player still picks a category and the wager-decider still sets
   the wager, same as any other round — the round loop doesn't change.
2. On QUESTION, one of two flavors is chosen at random:
   - **Text** — a fact-bank-grounded multiple-choice question (correct
     answer verified against the fact bank; decoys are real adjacent
     entities or believable invented look-alikes).
   - **Color** — a curated real color (sports team, brand) plus 4
     procedurally-perturbed near-miss swatches. No API call for this flavor.
3. **Any player may tap any option, at any time, any number of times.**
   Wrong taps fail silently — no penalty, no lockout, the round stays open.
   First correct tap (server-ordered — no real race) claims the full wager
   and ends the turn immediately.
4. If nobody taps the correct option before the timer expires, the question
   voids unclaimed — same shape as an unclaimed Steal window.

**Known limitation:** color flavor is category-agnostic — it draws from its
own curated color pool rather than the turn's picked category, since a real
color needs a verified hex value that can't be reliably tied to arbitrary
player-submitted category strings. The category pick still happens (keeps
the round loop and wager-sizing intact) but only shapes the question for
text flavor. Format-constraining cards (Boxed In, Language Barrier) also
have no effect on Lineup questions, since a "pick one" answer has no
free-text format to constrain — documented rather than special-cased, same
as this game's other scoped-out edge cases.

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

### Shareable Question — the growth mechanic
**Superseded "Shareable Recap" (August 7, 2026).** The original spec here was a
recap image: final scores, superlatives, best highlights. The problem with that
is who it's *for*. A scoreboard is interesting to the five people who were in
the room and nobody else — it's a souvenir, not a growth mechanic. It gets a
polite like from people who weren't there.

What actually travels is **the question itself**. Trivia already works online:
people repost hard questions, argue in the replies, and tag friends to test
them. So the shareable artifact is a question from the game, framed as a
challenge to the sharer's own following.

**How it works.** After the game, each player may optionally pick one question
from the ones actually asked and generate a share card for it. Optional by
design — most players won't, and the ones who do are self-selecting for a
question that struck *them* as funny or brutal, which is exactly the editorial
filter you want.

**What's on the card:**
- The question, as asked.
- The category and its attribution ("from Sarah's 90s Hip Hop") — credits a real
  person, which is itself a social hook.
- A hook line drawn from what actually happened: *"4 of 5 friends got this
  wrong."* This is the part that makes it a challenge rather than a flashcard.
- **Not the answer.** Withholding it is the whole mechanic — the follower has to
  guess, and guessing is what drives replies. A card with the answer on it is a
  fact; a card without one is an argument.

**Answer reveal** is a second card the sharer can post as a follow-up, or a
tap-to-reveal if the card is ever hosted rather than downloaded.

**No persistence required, deliberately.** MYF has no database by design (see
`CLAUDE.md` → What NOT to Do). So the card renders client-side to a canvas and
goes out via the Web Share API (`navigator.share` with a file) on mobile, with a
download fallback on desktop. No hosted link, no storage, no server round-trip.
If a hosted link is ever wanted for tap-to-reveal, that's a real infrastructure
decision to make separately — not a prerequisite for this.

**Caveat, unresolved:** questions are AI-generated per game, so a shared question
is only as good as that generation. A question that was funny *in context*
("remember Jake had to answer this in one word") may fall flat stripped of the
room. Worth watching in playtest whether the cards people actually share are the
ones the game would have predicted.

### "One More Round" Moments
Post-game dares or challenges based on what happened. The AI host generates
1–2 challenges tied to the game's narrative: "Jake, since you went negative,
you pick the restaurant tonight." Optional, social, no mechanical consequence.

---

## Disconnection Handling
**"Wait for our friend"** — when a player disconnects mid-game:

1. **45-second grace period** — game auto-pauses on phases that need the
   disconnected player. Other players see "Reconnecting…" next to their name.
   No vote prompt yet — most reconnects happen within this window.
2. **Vote prompt** — after 45s, remaining players vote "Wait" or "Continue."
   Simple majority to continue. A "wait" vote resets another 45s window.
3. **If continued without** — the dropped player's turns are skipped, score
   freezes. If they reconnect later, they rejoin as a spectator (frozen score)
   and can jump back in during "one more round" at game end.
4. **If reconnected during vote** — vote is dismissed, play resumes immediately.

No AI takeover, no bot substitution. It's a party, not a ranked match.

**[FUTURE] AI Host narration** — when the AI host is voice-enabled, it should
use humor to narrate disconnects ("Looks like Jake's phone just rage-quit…
giving him a moment to crawl back") and reconnects ("The prodigal son
returns!"). Keeps energy up instead of a sterile loading screen.

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
