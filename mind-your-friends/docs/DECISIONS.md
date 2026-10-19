# Mind Your Friends — Decisions

**What this file is.** One entry per numbered MYF work item: what is true now, why, and what
was tried and rejected. `CLAUDE.md` says what to do next; this says why things are as they are.

**Every entry is current.** When an item changes, edit its entry here so it stays true, and put
the history in `SESSIONS.md`. The previous version of this file kept every item word for word as
first written, so a session landing on an old entry could act on something long since reversed.
It is kept, untouched, at `docs/archive/DECISIONS_to_2026-10.md`: open it for the full original
reasoning behind any item up to 53, by the same number.

**Numbers are stable and per game.** "Item 41" is Flow B here, in `CLAUDE.md`, `GAME_DESIGN.md`,
`PLAYTEST.md` and in source comments. CYM has its own list (`docs/DECISIONS.md` at the repo root);
both have an item 27. Never renumber; a dead item is marked, not deleted.
`python3 scripts/check_decisions.py` checks both lists.

## Index

| # | Topic | Status |
|---|---|---|
| 1 | Round-rule variations | Done — nine rules today |
| 2 | Card mechanic | Built |
| 3 | Game structure: 4 × 6 | Built |
| 4 | Scoring, ties, Audience Poll | Decided |
| 5 | First scaffold | Done |
| 6 | Coherence engine (JS) | Built; unwired to the shared engine by design |
| 7 | Per-player views | Built |
| 8 | Steal | Retired |
| 9 | Redirect targets | Decided |
| 10 | Category attribution | Built |
| 11 | 3–6 players | Decided |
| 12 | I cut, you choose | Decided |
| 13 | Whoa Nellie | Built |
| 14 | Post-game activations | Partly built |
| 15 | Question types | Designed, not built |
| 16 | Worst Answer Wins (rule) | Built — see 30 |
| 17 | Slow Burn → Take Your Time | Done |
| 18 | Question–rule coherence | Built |
| 19 | Complexity budget | Decided |
| 20 | Hot Take | Removed |
| 21 | Lobby → card pick | Built |
| 22 | Fact bank | Built (lazy since 37) |
| 23 | Question-from-fact builder | Built |
| 24 | First run: four crashes | Done |
| 25 | Disconnection handling | Built in JS; Python partial |
| 26 | Spotlight approximation | Open |
| 27 | Group splitting | Killed |
| 28 | Extended playtest: three bugs | Done |
| 29 | Voice input | Built; parked |
| 30 | Worst Answer Wins, real | Built |
| 31 | Why Godot | Decided |
| 32 | The Lineup | Built |
| 33 | `server_py` port | Done |
| 34 | Godot client foundation | Done — lobby only |
| 35 | Post-game social layer (JS) | Built |
| 36 | "Start Game does nothing" | Resolved |
| 37 | Owner playtest, eleven notes | Built; note 9 replaced by 41 |
| 38 | Rebus | Built |
| 39 | Visual identity exploration | Became 40 |
| 40 | Screen system and the host | Decided; three questions open |
| 41 | Flow B | Built; unplayed on a correct clock |
| 42 | `server_py` parity | Done |
| 43 | Rename "open answering" | Proposed |
| 44 | Wager tiers; colour hue | One declined, one tabled |
| 45 | Wager ladder and difficulty colour | Built |
| 46 | `server_py` post-game | Done |
| 47 | Turn-scoped timers | Fixed |
| 48 | Aesthetics pass 1 | Built |
| 49 | Aesthetics pass 2 | Built |
| 50 | Plate device and answer screen | Built |
| 51 | Coherence on the shared engine | Built |
| 52 | Live-type title treatment | Built |
| 53 | Interface style guide, tiles, layout | Built |

---

1. **[DONE] Round-rule variations.** Nine rules today: Back It Up, One Word Only, Take Your
   Time, ELI5, Double Down, Lightning Round, Worst Answer Wins, The Lineup, Rebus. Eight were
   confirmed first; Steal was added and retired (8, 37); The Lineup (32) and Rebus (38) joined.
   Full rules: `GAME_DESIGN.md` → Round Rules.

2. **[BUILT] Card mechanic.** One shared card slot per question, first card played claims it
   (FCFS); every card is single-use. Eight sabotage cards (Skip, Redirect, Whoa Nellie, 50% Off,
   Spotlight, Heckle, Language Barrier, Boxed In) and two defence (Insurance, The Fixer). **A hand
   is Half-Off (everyone, every round) + your picked card until you use it + 2 random cards per
   round** (`buildRoundHand`, `RANDOM_CARDS_PER_ROUND`) — the original six-card hand is gone.
   *Rejected for now:* stacking every played card instead of FCFS — richer, but it breaks the
   complexity budget (19); kept as PT-1 for a table to judge.

3. **[BUILT] Game structure.** 4 rounds × 6 questions = 24. One round rule per round, announced,
   with round 1 deliberately plain (37). Answer clock 40s (was 20s; 37). Boxed In means a 1–2
   word answer, which works because baseline answers are longer than 3 words.

4. **[DECIDED] Scoring and the pool.** Scores start at 0; ties are shared wins everywhere
   (`getWinners`, superlatives, Worst Answer Wins). Each player adds 3 categories (37; was 5) and
   6 are offered per turn. *Rejected:* Audience Poll, out of v1.

5. **[DONE] First scaffold.** Next.js 14 + Socket.io custom server; game logic in `lib/`, never in
   the client.

6. **[BUILT] The coherence engine, in JS.** `lib/coherence.js`: round constraints → turn
   constraints → `validateQuestion`, plus `pickFactoid`. It is deliberately **not** wired to the
   shared Python engine — JS cannot subclass a Python `RuleSet`, and the prototype is for
   retirement, not a bridge. The shared engine became real on the Python side (51).

7. **[BUILT] Per-player views.** The server sends each player their own view. Withheld until it
   is safe: other players' hands, the answer and `correctOptionId` (until RESULT), the question
   log (until GAME_OVER — it holds every answer), other players' ballots (never).

8. **[RETIRED] Steal.** A wrong answer opened an 8s buzz window, with half the wager lost on a
   wrong steal. Retired by the August 12 playtest (37) because it was open answering rationed to
   one round in nine. It cannot come back as-is; Rebus took its slot.

9. **[DECIDED] Redirect** sends the question to a random other player. No targeting UI.

10. **[BUILT] Category attribution** is public and fixed at registration, and every option says
    whose it is ("swapped to Sarah's 90s Hip Hop!"). It is a designed social beat — a category
    credited to "Bob's Divorce" is the joke — which is why free-text entry survives beside the
    curated grid (37).

11. **[DECIDED] 3–6 players**, hard cap at join. This is the whole answer to large groups (27).

12. **[DECIDED] "I cut, you choose."** The active player picks the category; the next player sets
    the wager. The setter needs no stake — their power is the balancing force. Flow B (41) exists
    partly to protect this: if anyone could claim the wager, the setter would be setting a bounty
    they might collect, and would always set the maximum.

13. **[BUILT] Whoa Nellie** swaps to a random other category from the pool, at the same
    difficulty, attributed. In the Chain spec it restarts the chain.

14. **[PARTLY BUILT] Post-game activations.** Built: superlative voting and the Shareable
    Question (35; ported to Python in 46). Designed only, in `GAME_DESIGN.md`: replay moments and
    "one more round" moments — no code exists for either.

15. **[DESIGNED, NOT BUILT] Question types** — First Come First Serve, Open to All, Visual — as a
    layer separate from round rules. No code exists. Visual needs a licensed, tagged image pool
    and a legal review before launch. Spec: `GAME_DESIGN.md` → Question Types.

16. **[BUILT] Worst Answer Wins** as a round rule: everyone answers wrong on purpose, scored on
    three axes, lowest total wins. The real mechanic is item 30.

17. **[DONE] Slow Burn was renamed Take Your Time.**

18. **[BUILT] Question–rule coherence** is enforced at generation time, not checked afterwards:
    the rule shapes the prompt. Table: `GAME_DESIGN.md` → Question–Rule Coherence.

19. **[DECIDED] The complexity budget:** the "hear it and get it" test. A mechanic a new player
    cannot understand by the end of round 1 does not ship. `GAME_DESIGN.md` → Complexity Budget.

20. **[REMOVED] Hot Take** (salacious corruptions of correct answers): fun, but no clean way to
    score "hotness". Kept as PT-2, with the stretch idea of player-defined round rules.

21. **[BUILT] Lobby → card pick**, two steps: categories, then `CardPicker` (40s timer; the timer
    auto-picks if nobody chooses).

22. **[BUILT] The fact bank.** `fetchFactsBatch()` researches categories into facts (five
    buckets, three difficulties); questions are written from facts rather than invented, which is
    the reliability fix for answers. Since 37 it is **lazy**: a category is fetched when first
    picked, the rest prefetch in the background, unpicked ones are never paid for. *Rejected:*
    building the whole bank at start — 250s sequential, 50s concurrent (36).

23. **[BUILT] Question-from-fact builder.** `pickFactoid()` filters by difficulty and answer
    format; `generateQuestion()` writes from the factoid and a random angle, and falls back to a
    no-factoid prompt when the bank has nothing.

24. **[DONE] First run: four crashes**, all invisible until the app ran: Claude fencing its JSON
    (`parseJson`), category options rendered as strings, Half-Off missing from the card lookup
    (`CARD_INFO`), and the client reading a nested field the view never sends. The lesson stands:
    run it, don't trust a careful read.

25. **[BUILT in JS; PARTIAL in Python] Disconnection.** 45s grace, then the room votes to wait or
    continue. `server_py/game_state.py` has every function, but `main.py` exposes no
    disconnect-vote endpoint, so the Python backend cannot yet end a game by attrition — when it
    can, that route must also start the post-game (46). After GAME_OVER there is no grace period,
    and leaving no longer writes a false "waiting for reconnect" line (46).

26. **[OPEN] Spotlight is an approximation.** It forces the answer by cutting the clock to 5s,
    and the UI skips no prep step. Under Flow B's 25% cap that leaves a **1-second** exclusive
    window, which arguably hands the active player's question to the room — the opposite of the
    card's point. If a table confirms it, the fix is a floor on the exclusive window, not a
    Spotlight exception (PT-6). (The other gaps once listed here — heckle moderation, room-code
    collisions, voice input — are built.)

27. **[KILLED] Group splitting** for 7+ players. Owner, Session 50: *"I no longer think a use case
    of 7+ players is worth worrying about."* Nothing was built. Do not re-propose.

28. **[DONE] Extended playtest**, a full automated 24-question game: three more bugs — Skip
    crashing every client (`skippedTurn` never sent), a turn hanging forever on a failed Claude
    call (`recoverFromFailedTurn`), and a steal UI that no longer exists.

29. **[BUILT; PARKED] Voice input.** `VoiceInput.jsx` fills the same editable box, and
    `inputMode` (`text` / `voice`) picks which answer transform a rule applies. Chromium-only;
    phones need HTTPS for the mic. Parked by the owner — text is fine for now, and it is not in
    the Godot client. Keep the text/voice split in round rules: voice is the destination.

30. **[BUILT] Worst Answer Wins, for real.** Everyone submits; a transient EVALUATING phase
    stops the last submission and the timer from both triggering evaluation; one batched call
    scores every answer on three axes; lowest total wins, ties share; every player sees every
    answer and score. *Open design call:* non-winners lose nothing.

31. **[DECIDED] Why Godot.** Both titles target Steam and consoles, and a browser app has no
    cert-friendly path there; CYM already paid for a Godot client and GodotSteam. A Python
    backend also let MYF's coherence rules join the shared engine (51). **The Next.js prototype
    stays until Godot reaches parity and is playtested** — it is the executable spec.

32. **[BUILT] The Lineup.** Five options, one correct; taps that miss fail silently with no
    penalty or lockout; first correct tap wins the wager. Two flavours: text (from the fact bank)
    and colour (a curated swatch table, no API call — a hex code is a fact Claude should not
    invent). Limits: the colour flavour ignores the category, Boxed In and Language Barrier do
    nothing to it, and the no-winner expiry has never been exercised live.

33. **[DONE] The `server_py` port.** A full Python port of the game logic. WebSocket, not ENet
    (CYM's ENet layer was never wired). Every mutation runs under one `_games_lock`, because
    Python does not give Node's single-thread ordering for free. Test against a real `uvicorn`:
    FastAPI's `TestClient` drops pushes made from timer threads.

34. **[DONE — lobby only] Godot client foundation.** `ApiClient.gd`, `GameState.gd` (a
    last-write-wins mirror of the server's view, no game logic) and a lobby with stubbed
    registration, with headless smoke tests. Its first `ApiClient.gd` did not compile — run
    `--headless --import` before trusting GDScript. A Godot binary was downloadable then; CYM later
    found the engine's hosts blocked, so check before relying on it. Use `uvicorn[standard]`.

35. **[BUILT] The post-game social layer** (prototype). `questionLog` is written once, from
    `nextTurn()`, the funnel every resolution path passes through; post-game lives *inside*
    GAME_OVER, not as new phases. Superlatives are grounded in what happened, generated in one
    call, voted one at a time. The **Shareable Question** shares a question, not the scoreboard —
    a question travels because guessing it drives replies — with the answer withheld. It is now
    parked and frozen (`CLAUDE.md`). Bugs worth remembering: failed steals logged as steals, and
    host quips keyed by title so every one silently dropped. Ported to Python in 46.

36. **[RESOLVED] "Start Game does nothing"** was a silent 250-second wait, not a bug: the fact
    bank built sequentially at start. Concurrency cut it to ~50s; the lazy bank (22, 37) to
    instant. Kept as the only real measurement of a sequential build.

37. **[BUILT] The August 12 owner playtest — eleven notes**, three with forks decided by the
    owner. Still true: questions are 8–20 words; a 5s reading window before a 40s clock, done as
    a timestamp, not a phase (every timer assumes the phase loop); one rule per round, announced,
    round 1 plain, no repeats; 3 categories from a curated grid plus your own; instant start; a
    brand bar with the logo recoloured per game, deterministic in the room code; a host slot held
    in the layout (now ⅔ : ⅓, 53); one card component everywhere, art fixed per card; superlatives
    one at a time, with a real abstention (`SKIPPED_VOTE`). **Note 9 — everyone races, first
    correct wins, flat 100 for anyone but the active player — was replaced by Flow B (41).**

38. **[BUILT] Rebus.** The answer spelled in emoji plus a one-line hint, the hint being the way
    in. **Curated, zero API calls**: a rebus whose pieces don't rebuild its answer is unsolvable,
    and a room cannot tell that from hard. Built as a library of pieces (113) composed into
    puzzles (82); literal puzzles must spell their answer exactly, enforced by tests; phonetic
    ones say so on screen. The reveal shows the decomposition. Ignores the picked category.
    `MYF_FORCE_ROUND_RULE=rebus` pins it for testing. *Rejected:* live generation.

39. **[BECAME 40] Visual identity exploration.** The owner's faded, strewn question marks as the
    ground. White was tried and dropped; slate won (40). The "MYF only" scope was later reversed
    by the owner so CYM could share the system with its own motif. *Rejected:* exporting the
    field as a raster — it is generated geometry (48).

40. **[DECIDED; THREE QUESTIONS OPEN] Screen system and the host.**
    - **Ground: slate `#2F4459`**, one token, with the question-mark field at 10% strength. If it
      needs adjusting, add density, not opacity.
    - **The plate** (built, 50): text sits on the ground with the texture switched off. **Plates
      are for what must be read; objects are for what must be grabbed** — cards stay saturated
      objects. Question type is light and centred.
    - **Player colours are validated, not picked:** a fixed eight in a fixed order. Assign by
      seat; never reorder.
    - **The host is a centre-screen takeover, not a window** (cost: zero when idle). One
      character whose attitude varies per game, so clips can be pre-packaged; names arrive as
      text under the clip. "Funny" needs far more variants than snark, because a joke dies on
      repeat and a posture does not. No answer timer runs during a host moment. While a clip
      loads, the hold screen is the standings plus a score-progression chart.
    - **Open:** does the shareable standings chart unpark the frozen share card; which cut of the
      chart gets shared; can a player skip a host moment. Host-video cost estimate deferred.

41. **[BUILT] Flow B — the active player answers first.** Reading window (5s) → the active
    player's exclusive window (8s, capped at 25% of the clock) → the buzzer. Answer right: win
    the wager. Wrong: lose it. **Pass: lose nothing; freeze: lose it** — that split is what stops
    "pass" becoming a free exit from every hard question. Meanwhile everyone else types and
    **locks** an answer; a buzz plays the locked answer for **0.75× the wager**. No lock, no buzz;
    a lock is immutable; the lock deadline never moves; a question nobody can still answer ends
    at once, and unplayed locks are revealed. Answering never earns a turn.
    *Rejected:* everyone racing (37's note 9 — the active player's wager stopped biting); Flow A
    (answering earns the next turn — runaway leader); a flat 100 buzz payout; 1.5× (being the
    active player becomes something to avoid). **None of its four numbers has been played on a
    correct clock** (PT-5 → PT-8).

42. **[DONE] `server_py` parity** with every August 12 change and Flow B. The hard part: "first
    correct wins" must mean first *submission*, and a plain Python lock makes no FIFO promise —
    so a **ticket lock**: claim under the game lock, evaluate with it released, served in ticket
    order. Running the port found what reading it missed: the 8–20 word rule had never been
    copied over.

43. **[PROPOSED] Rename "open answering" to "buzz-in"**, as one atomic pass, never mixed into
    other work. If it runs, `answerOpensAt` becomes `readingEndsAt` — **not** `buzzerOpensAt`,
    which would collide with the real `buzzOpensAt`.

44. **[ONE DECLINED, ONE TABLED] Two follow-ups to the ladder.** (1) Fewer wager tiers:
    **declined by the owner** (Session 50) — five stay, each named on its tile (53). (2) Widen
    the difficulty ramp's hue toward blue-green / yellow-green for separation: tabled. Change the
    generator, never the hexes.

45. **[BUILT] The wager ladder and difficulty colour.** Five tiers, `12 / 25 / 50 / 100 / 200`,
    a doubling ladder where 100 is the whole pie; off-ladder values are rejected, not clamped.
    The wager sets the question's difficulty (five rungs, mapped onto the fact bank's three) and
    the question is printed in a matching green. The ramp is **generated** and refuses any step
    under 4.5:1 on slate, so it deepens by saturation rather than darkness.
    `scripts/economy-sim.js` models the scoring. *Rejected:* the 50–500 slider (46 values, ends
    that were noise and a coin-flip); the owner's reference green `#26501A` (1.2:1, invisible).
    The pie survives only on the watchers' screen (53).

46. **[DONE] `server_py` post-game.** `questionLog` from `next_turn()`; superlative voting inside
    GAME_OVER (claim under the lock, call Claude without it); `POST /games/{code}/postgame/vote`
    and `/skip`; a 90s vote timer; a re-check when a departure completes the ballot, on a thread.
    Tallies publish before the host's quips arrive. `server_py/test_postgame.py`. Not yet in
    `ApiClient.gd`.

47. **[FIXED] Timers are scoped to a turn, not a phase.** Every turn walks the same phases, so a
    timer guarded by phase alone fired on the *next* question and expired it — compounding, and
    charging the next answerer a freeze. Fix: `turnSeq`, bumped at every turn start, checked by
    every timer. Python has a regression test; the JS fix has none, because `server.js` is not
    importable.

48. **[BUILT] Aesthetics pass 1.** The question-mark field on every page, **generated** (seeded,
    so a re-run is a no-op; the tile wraps; marks are geometry, not a font glyph; the ground is
    not baked in). The logo is 73px everywhere. Purple is gone; the accent is gold, a *light*
    colour, so text on it is dark. *Open:* the rejected purple is still in `LOGO_PALETTES`. (The
    metallic title treatment this pass installed was replaced in 52.)

49. **[BUILT] Aesthetics pass 2.** Card names sized to the card's longest word; cards a fixed
    98px everywhere; Half-Off shown, not offered. The join screen's four imperatives with the
    mark as the punchline. One `.panel` class, so every box changes at once. The round line is
    written once. (Its Easiest/Hardest end labels became five tile words, 53.)

50. **[BUILT] The plate device and the answer screen** ("I read, I answer"). One computed status
    line instead of four exclusive blocks; everything said once. `app/dev/answer` renders every
    Flow B state from fixtures and reports overflow — and taught two things: headless Chromium's
    `--window-size` does not set the layout viewport (use Playwright's `viewport`), and a flex
    input needs `min-w-0` to shrink.

51. **[BUILT] MYF's coherence rules on the shared engine.** `server_py/coherence_rules.py`'s
    `QuestionRuleSet` subclasses `coherence.engine.RuleSet`, the same class CYM uses, and a test
    asserts it is the identical class. **The file cannot be called `coherence.py`**: a module and a
    package of one name cannot share `sys.path`. The repo-root path is appended, so `server_py`
    wins any collision. Warnings are now logged, not just failures.

52. **[BUILT] The title treatment is live type.** The metallic SVG was drawn for a light ground;
    on slate two-thirds of it vanished. Now two treatments, 50/50 across games: F1 (Oswald 700)
    and D1 (Bebas Neue), self-hosted, measured within 0.12:1 of each other. Chosen by room code,
    through a bit-mixer: a naive second hash was perfectly correlated with the logo palette (12
    combinations became 6), caught by `scripts/wordmark-test.js`. Not shown in game (53).

53. **[BUILT] The interface style guide, the wager tiles and the in-game layout.**
    - **The guide** (`docs/STYLE_GUIDE.md`, owner-supplied) is MYF's rulebook, applied to the
      Next.js screens. Colour roles live in `lib/palette.js`, checked by
      `scripts/palette-test.mjs`. **Chosen (steel `#8EC5E8`) and Act (gold) never swap**; the
      surface is darker than the ground, because controls read as recessed (MYF's own call over
      the guide's). Honest labels: name who played a card, quotes only around real words, no
      label without content, hints only while true.
    - **Not changed, because MYF's decisions win:** borderless plates; cards as objects; fixed
      card art per id. The last is flagged — the guide says an icon must show a card's kind, not
      which one, so a glance cannot reveal a private hand.
    - **Wager tiles** (owner, from *Mob Rules*): a lit border marks the chosen tile; value on
      top, *Easiest / Easy / Medium / Hard / Hardest* beneath (`.tile`; the words live on
      `WAGER_TIERS` in both backends). This overrides "filled = chosen" for this control only.
    - **In-game layout** (owner's markup): two columns, ⅔ game and ⅓ host slot, the slot alone on
      the right; the brand bar inside the game column, with no title treatment there; the round
      status beside the scores; no big pie; "Lock in" blue (`.act-chosen`), because it commits
      the lit tile.
