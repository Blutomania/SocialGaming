# Mind Your Friends — Playtest Questions

Questions to validate through playtesting (surveys, observation, or A/B testing).
Each item describes the tension, the current design choice, and what to watch for.

---

## PT-1: Card Resolution — FCFS vs. Stacking

**Current design:** Single FCFS slot. First card played claims the slot, all
others rejected.

**Alternative:** All played cards resolve and stack (RPG-style). Effects
multiply against each other. E.g. Double Down + Half-Off + Half-Off =
wager × 2 × 0.5 × 0.5 = 50% of original.

**Why it matters:** Stacking creates richer strategy — a ringer can be
counter-played by multiple opponents, and card interactions become emergent.
But it adds complexity (resolution order, interaction rules, cognitive load)
that may violate the Complexity Budget.

**What to watch for in playtesting:**
- Do players feel frustrated when their card is rejected under FCFS?
- Does FCFS create enough strategic depth, or does it feel too random/reflex-based?
- When explaining stacking to new players, do they get it immediately or need examples?
- Does stacking slow down the turn cycle noticeably?

---

## PT-2: Hot Take Round Rule — Salacious/Comedy Mechanic

**Removed from v1** — the concept has social energy but no clean scoring mechanic.

**The idea:** Players give "hot" answers — dirty wordplay, double entendres,
salacious corruptions of correct answers (e.g. "Andy Butthole" for Andy Warhol).
The table loves it, but how does the AI score "hotness"? Player voting was
explored but adds complexity.

**What to test:**
- Ask playtesters: "What round rule is missing?" — see if something like this
  emerges organically
- Survey: show the concept, ask if it's fun and how they'd score it
- Does player voting (thumbs up/down on "hotness") feel natural or like homework?

**Stretch idea — Player-Defined Round Rule ("Group Round"):**
Players could define their own round rule mid-game. Possible workflow:
1. Each player submits a one-line rule description
2. All submissions shown to the group
3. If everyone gives it a thumbs up, it becomes the rule for that turn
4. AI host adapts the question to fit the player-defined rule

This could be how Hot Take or similar comedy mechanics enter the game — the
players invent the mechanic themselves. Needs playtesting for feasibility
(do groups actually converge? does it kill pacing?).

---

## PT-3: Single-Player Inactivity — Group Dynamic Impact

**Current design:** Timers auto-advance on every player-action phase (category
pick, wager, answer). If a player goes AFK, the game doesn't stall — it
auto-picks a random category, sets a default wager, or submits an empty answer.

**The question:** Does one inactive player degrade the experience for the group,
or does the social dynamic self-correct ("dude, it's your turn")?

**What to watch for in playtesting:**
- Does auto-advancing feel jarring or natural when someone zones out?
- Do groups verbally nudge the inactive player, or do they silently resent it?
- Does repeated inactivity from one player make others want to quit?
- Is there a threshold (e.g. 3+ auto-advances) where the game should intervene
  (host callout, soft penalty, "are you still playing?" prompt)?
- Multi-player inactivity (2+ AFK) — does the game become pointless? Is this
  where an engineering solution is actually needed?

**Decision deferred until after playtesting.** Single-player AFK is likely a
social problem, not a technical one. Only build auto-kick or penalty mechanics
if testing shows it genuinely stalls games.

---

## PT-4: Open Answering — Does the Wager Still Mean Anything?

**ANSWERED BY DESIGN AND NOW BUILT, August 17 2026 — see GAME_DESIGN.md → "The
Round Loop". Still needs a table to confirm.** Built on both backends the same
day; nothing below has been validated by real players. Walking a three-player hypothetical
through the live rules made the failure concrete: if a faster player always
takes the question, the active player watches their own wager get claimed and
neither wins nor loses. Flow B gives the active player an exclusive ~8s window
first, so the wager is genuinely theirs, and buzzing becomes vulture rather than
race. The watch-list below still applies — it is now the list for testing Flow B
rather than for deciding whether a fix is needed.

**Changed August 12, 2026** (owner playtest note 9), replacing the
single-answerer model and retiring the Steal round rule with it.

**Current design:** every player gets one attempt at the same question and the
first correct answer wins. Only the **active** player has money on it — they
win or lose the wager that was set for them. Everyone else plays for a flat
`OPEN_ANSWER_POINTS` (100) and risks nothing. A wrong attempt locks that player
out of the question but costs a non-active player nothing. Not answering at all
costs the active player the same as answering wrong, so stalling isn't free.

**The question:** does the wager still carry tension when someone else can take
the question off you? "I cut, you choose" was built around one player being on
the hook; open answering keeps that hook but adds a way to be robbed of the
upside while keeping all of the downside.

**What to watch for:**
- Does the active player rush and lose points they'd have won with more time?
- Does the wager-setter play differently now — is a big wager still a threat, or
  has it become a gift to whoever reads fastest?
- Is 100 the right flat rate? Too low and nobody bothers buzzing in; too high
  and being the active player is strictly worse than not being one.
- Does the reading window (5s, PT-5) do enough to stop this becoming a
  reading-speed contest?
- Do wrong-but-free attempts create noise — people guessing instantly to burn
  the attempt before someone else answers?

**Known consequence, not yet resolved:** retiring Steal leaves **eight** round
rules where there were nine. Whether a ninth is wanted, and what it should be,
is a design call that hasn't been made. Steal itself can't come back as-is —
it was this mechanic rationed to one round in nine.

---

## PT-5: Reading Window — Is 5 Seconds Right?

**Added August 12, 2026** (owner playtest note 8), alongside doubling the
answer clock from 20s to 40s.

**Current design:** the question appears, the answer input stays visibly locked
for `READING_SECONDS` (5), then the buzzers open for the full answer clock.
Questions are generated at 8–20 words specifically so they fit inside it.

**The question:** does 5s cover reading for the slowest reader at the table
without deadening the pace for everyone else?

**What to watch for:**
- Do people spend the window reading, or does it just feel like a stall?
- Does anyone still get beaten to the buzzer purely on reading speed?
- Does it want to scale with question length rather than being fixed?
- Should the round rules move it — Lightning Round shortening it, Take Your
  Time lengthening it — or does a rule-independent reading window matter more
  as a fairness guarantee than as a pacing lever?

---

---

## PT-6: The Exclusive Window — Is 8 Seconds Right?

**Added August 17 2026, alongside building Flow B.** This is the number most
likely to be wrong in the whole design.

**Current design:** after the 5s reading window the answerer has
`ACTIVE_WINDOW_SECONDS` (8) alone with their own question, capped at 25% of the
round rule's clock so Lightning Round gets 5s rather than 8 of its 20.

**The question:** too short and first refusal is a formality — the answerer is
still reading the question when the room takes it. Too long and everyone else
is watching somebody think.

**What to watch for:**
- Does the answerer ever actually *use* the full window, or is it always
  answered/passed in the first three seconds?
- Does the room get bored during it, or does locking an answer in keep them busy
  (that is what pre-commitment is supposed to buy)?
- Is the Lightning Round cap right, or does a 5s exclusive window on a 20s clock
  feel like no window at all?
- **Spotlight interaction, flagged but not resolved:** the card shortens the
  clock to 5s, so the 25% cap gives a **1-second** exclusive window. The card's
  whole point is forcing the *active player* to answer immediately, and a 1s
  window arguably hands their question straight to the room instead. The spec
  was implemented literally rather than special-cased; if a table confirms this
  feels wrong, the fix is a floor on the exclusive window, not a Spotlight
  exception.

---

## PT-7: Pre-Committed Answers — Does Locking In Feel Good or Feel Like Homework?

**Added August 17 2026** (owner's change: everyone but the answerer commits an
answer during the exclusive window, and a buzz plays that committed answer).

**Current design:** you type an answer while the answerer has the question, you
lock it, and you cannot change it or type a new one later. No lock, no buzz.

**The question:** the mechanic is designed to close a lookup window and kill a
typing race. Does it read that way at a table, or does it read as being asked to
do paperwork while someone else plays?

**What to watch for:**
- Do people actually lock in, or do they sit out most questions? (`lockedCount`
  is on screen — watch whether it climbs.)
- Is the lock window long enough to type a real answer, or are people
  auto-locked mid-word by the deadline?
- Does "you HAD it and didn't buzz" land as the laugh it's designed to be, when
  the unplayed answers are revealed?
- Does anyone lock a joke answer purely to have the buzz available? (Free, and
  probably good, but worth knowing.)
- Does not being able to answer at all — because you didn't commit — feel fair,
  or feel like a rule you got caught by?

---

## PT-8: Is 0.75× the Wager the Right Buzz Payout?

**Added August 17 2026**, replacing a flat 100.

**Current design:** a buzz-in win pays `BUZZ_WAGER_SHARE` (0.75) of the wager.
`scripts/economy-sim.js` puts that at roughly 44% of a typical player's score
movement — nearly co-equal with the wager game.

**The question:** the wager is supposed to be the main event and buzzing the
vulture prize. Is 44% still "vulture", or have the two games become co-equal?

**What to watch for:**
- Does the answerer feel robbed when a fumble gets taken, or is that the joke?
- Does anyone deliberately pass on a big wager because handing the room 150 is
  cheaper than risking 200? (That would be a real exploit — worth watching.)
- Does a big wager still read as a threat to the answerer, or has it become a
  bounty the room is hoping for?
- The dial is one constant. 0.50× lands at 37%, flat 100 at 45%, 1.5× at 56%
  and is ruled out on principle (see GAME_DESIGN.md → "What a buzz is worth").
