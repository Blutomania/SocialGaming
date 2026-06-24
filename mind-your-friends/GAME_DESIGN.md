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
Player 1 picks the category (the cut); Player 2 picks the point tier (the
choose). Fixed tiers: **20 / 40 / 80 / 160 / 400**. This self-balances
without additional incentive structures — Player 1 can't pick an easy
self-serving category without Player 2 slamming a 400 on it, and Player 2
can't pick a punishing tier without considering that Player 1 chose this
category for a reason. The setter needs no skin in the game — their
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
2. Next player picks a point tier (20 / 40 / 80 / 160 / 400)
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
**Single use per game** for most cards. Once a card is played (and claims the
FCFS slot — see Card Resolution above), it's removed from that player's hand
for the rest of the game.

**Exception — 50% Off (Half-Off):** every player receives a Half-Off card at
the start of each round. If used during a round, it's gone until the next round
replenishes it. This gives everyone a baseline defensive tool against high
point tiers without making it feel precious.

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

## Design Principle: Every Game Is Complete

MYF is a party game, not a platform. Every session should be a self-contained
experience — the fun is in *this room with these people tonight*, not in
grinding toward a progress bar across 50 sessions.

This means:
- **No cumulative unlocks, levels, or lifetime stats.** The moment the game
  rewards you for *having played before* over *what just happened*, it stops
  being a party game and starts being a video game.
- **No collection mechanics.** Avatar cards and social graphics are souvenirs
  of a specific night, not entries in a Pokédex.
- **No returning-player advantage.** A first-timer and a 100-game veteran
  walk into the same lobby with identical chances. Experience helps you play
  cards better, but the game never mechanically rewards tenure.
- **The unit of fun is the session, not the account.** If someone plays once
  at a bachelorette party and never again, they had the full experience. If
  someone plays weekly, each game stands on its own.

Every feature proposal should be tested against this principle: does it make
*this game* better, or does it make *the 50th game* better? If only the
latter, it's wrong for MYF.

---

## Avatar Cards & Social Graphics

### AI Avatars
Every player has an AI-generated avatar created at registration. The avatar
appears on all social graphics produced during and after the game — it makes
cards *yours* without requiring a real photo.

### Card Minting — Notable Moment + Random Gate
Avatar cards are **rare by design.** They feel like lightning striking, not a
vending machine. Two ingredients are required to mint a card:

1. **Notable moment occurred** (deterministic). The highlight reel already
   flags these: steals, high-tier (400pt) swings, sabotage plays, comebacks,
   going negative. Boring correct answers on a 20pt question never produce
   cards.
2. **Random gate** (non-deterministic). Even when a notable moment happens,
   the card only mints with some hidden probability (~30–40%). The player
   never sees the threshold or the odds.

**Why this isn't gameable:**
- You can't force notable moments — you can't *choose* to be stolen from.
- Even when something notable happens, the random gate means chasing it
  doesn't reliably pay off.
- The odds are server-side and never exposed.

**Adaptive tuning:** the server targets ~2–3 mid-game cards per player per
game. If a game is running hot (many notable moments), the gate tightens
silently. If it's quiet, it loosens. Players experience natural variance,
not a formula.

**Superlative cards are guaranteed.** Everyone walks away with their
superlative(s). Mid-game avatar cards are the surprise on top.

### Spectacularly Wrong — Wrongness Badges
When `evaluateAnswer()` returns a wrong answer, Claude already has both the
correct answer and the player's answer. The coherence engine can assess the
**magnitude and category of wrongness** — and when the gap crosses into
comedy territory, it mints a social graphic. Not a punishment — a badge of
honor.

These are inherently rare. Most wrong answers are close misses or timeouts.
The truly absurd gaps are organic, unplannable, and unshareable-because-
embarrassing — they're shareable because they're *funny*.

**Wrongness archetypes:**

| Archetype | Trigger | Example badge |
|---|---|---|
| Geographic | Wrong hemisphere or continent | "Back to Geography Class 🌍" — avatar pointing at wrong continent |
| Temporal | Wrong century or millennium | "Time Traveler 🕰️" — avatar in the wrong era's clothing |
| Categorical | Entirely wrong domain (animal vs. mineral, fiction vs. reality) | "Wrong Universe 🪐" — avatar in a portal to the wrong genre |
| Scale | Orders of magnitude off on a number | "Just a Little Off 📏" — avatar next to a comically wrong scale |

**Implementation:** after `evaluateAnswer()` returns `correct: false`, a
follow-up Claude call (or structured output from the same call) classifies
the wrongness gap. If it matches an archetype and exceeds the comedy
threshold, the server mints the badge with the player's avatar, the wrong
answer, the right answer, and a one-liner. The graphic is revealed post-game
alongside avatar cards.

These badges reinforce the "Every Game Is Complete" principle — they're
souvenirs of *this moment* with *these people*, not lifetime achievements.

---

## Player Memory (Tentative)

*Half-baked — writing in pencil. This section captures cross-game data that
improves comfort and kindness, not progression or advantage. If any item
starts feeling like a level-up system, kill it.*

A lightweight player profile persists across sessions. It stores:

### 1. Preferred Categories
The 5 categories a player submitted last time, pre-filled at lobby
registration. They can change any or all — it's a convenience default, not a
lock-in. Saves the "ugh, type 5 things" friction on repeat plays.

### 2. AI Avatar
Generated once, reused across games. Players can regenerate anytime but don't
have to. The avatar is theirs — it shows up on their cards, badges, and
recaps without re-creating it each session.

### 3. Wrongness Badge Cooldown
The server tracks which wrongness archetypes a player has been hit with
recently. If someone got "Back to Geography Class" last game, that archetype
is suppressed for them for N games (TBD — maybe 3–5). The comedy threshold
for that archetype rises sharply so it only fires again on a *truly*
spectacular miss.

**Why this matters:** a wrongness badge is funny the first time. The same
badge hitting the same person repeatedly stops being a joke and becomes a
label. The cooldown protects players from feeling defined by a weak spot.
The game should punch up (celebrate absurdity) not down (expose ignorance).

### What This Is NOT
- Not a player account system. No login, no password. Could be as simple as
  a device-local cookie or a short code they remember.
- Not a progression mechanic. Nothing here makes the 10th game mechanically
  different from the 1st.
- Not a social profile. Other players never see your history, your badge
  cooldowns, or how many times you've played.

---

## Social Media Integration — DM-Based Answers

### The Core Mechanic
On certain questions, the active player **DMs their answer to an official MYF
account on Snapchat or Instagram** instead of typing it in-game. The MYF
account (bot or lightweight webhook listener) receives the DM, matches it to
the active game session via the player's linked handle, and forwards the
answer text back to the game server. Claude evaluates it normally.

### Why DM, Not Public Post
Public posting feels performative and contrived — it's homework, not gameplay.
A DM feels like passing a note. It's private, low-stakes, and native behavior
on both platforms. No one has to curate a post mid-game.

### Registration
During lobby join, each player links their Snap or IG handle (free text
input). This is the only friction — and it's the same friction as entering
a display name, which they're already doing.

### What This Gets Us
1. **Every player follows the MYF account to play.** Follower base grows as
   a side effect of gameplay, not a marketing ask.
2. **The MYF account can DM back.** Post-game recap cards, superlative cards,
   "you got sabotaged" moments — pushed directly into the player's DM thread.
   No share sheet friction, no "save and repost" dropout. It's already in the
   conversation.
3. **Story reshare from DMs is one tap.** If MYF sends you your superlative
   card via DM, resharing it to your story is native behavior on both
   platforms.
4. **Game code on every card.** Viewers who see a reshared card can join the
   next game.

### Open Design Questions (DM Integration)
- **Frequency**: every question is too much context-switching. Once per round?
  Triggered by a specific round rule or card? Player's choice?
- **Platform priority**: Snap or IG first? Support both from day one, or
  start with one?
- **Bot implementation**: Snap Kit / IG Messenger API, or a simpler
  webhook-based approach?
- **Fallback**: what happens if a player doesn't have Snap/IG? Skip the DM
  question and answer in-game normally?

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
