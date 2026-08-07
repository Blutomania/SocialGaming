# Mind Your Friends — Claude Code Instructions

## Project Overview
Real-time multiplayer social trivia game with sabotage cards, rotating round rules, and a
personalized AI host. Players join via 4-letter code, wager points, play cards against each
other, and answer AI-generated questions. The social loop — not the trivia — is the product.

**Priority note (added July 22, 2026, from a CYM-side session):** the current Next.js/browser
build is a design-validation prototype, not the shipping architecture. See **Current To-Do
item 31** — a Godot port is now the top priority before further web-only feature work.

**Studio engine framing (added same session):** the studio's product architecture rests on two
proprietary engine pillars across every title — **AI Generation** and **Coherence Engine** —
feeding four outputs: Avatars, Experiences, Social Loops, Gameplay. For MYF: `lib/coherence.js`
is this title's Coherence Engine instance (see item 6 and item 31 above for the real state of
the shared-framework question); `lib/claudeClient.js`'s question/fact-bank generation is AI
Generation; Social Loops = the sabotage-card/wager social layer; Experiences = round rules +
host personalization; Avatars has no MYF equivalent yet. This is the same "stress-free,
casual-first" design mandate already written up below as this file's own **Design Thesis:
Casual-First** section — nothing to add there, it already covers this.

**Correction (August 6, 2026, verified against CYM's actual `main` branch, not assumed):** this
note previously claimed CYM's `coherence/engine.py` was "substantially rebuilt" with richer
`Rule`/`Applicability`/`RuleSet` composition elsewhere — that was never actually checked against
CYM's real state and was wrong. In fact `coherence/` didn't exist on CYM's `main` **at all** until
today — it existed only on this MYF branch, unused by either project. Fixed today, CYM-side only:
`coherence_validator.py` now genuinely subclasses `coherence.engine.RuleSet`
(`MysteryPartsRuleSet`, `MysteryRuleSet` — see PR #14, `SESSIONS.md` Session 28 on `main`).
MYF's side is still not wired — `lib/coherence.js` is JS and needs this session's Python port to
land first (see item 31/33 below). When that happens, pull `coherence/engine.py` straight from
`main` (now the real source of truth) rather than this branch's copy, which is stale relative to
it in naming only — the classes are otherwise identical.

## Priority Queue (as of August 7, 2026)

The numbered list below is the full historical record and keeps growing. This is
the short version — what to actually work on next, in order. Items link to their
detail entries further down.

| # | Item | State |
|---|---|---|
| 1 | **Post-game social layer** — Superlative Voting + Shareable Question (item 35) | **START HERE** |
| 2 | Godot: category-selection + card-pick screens (replaces stubbed lobby registration) | Next |
| 3 | Godot: round-loop UI — WAGER → CARD → QUESTION → ANSWER → RESULT | Next |
| 4 | Godot: GAME_OVER screen, then port the post-game social layer once it's playtested | Blocked on 1+3 |
| 5 | Live-test disconnect/reconnect + inactivity auto-advance against `server_py` | Ported, never exercised |
| 6 | Voice input in the Godot client | Not started |
| 7 | Merge PR #14 (coherence unification) — now has a trivial docstring conflict | Open PR |
| 8 | Wire MYF's coherence to the shared Python engine — now possible, `server_py` is Python | Unblocked by the port |
| 9 | Retire the Next.js prototype — **only** once Godot reaches parity and is playtested | Do not do early |

## Current To-Do
1. ~~**Review Round variation types**~~ — 8 variations confirmed. See `GAME_DESIGN.md`.
2. ~~**Review card mechanic**~~ — FCFS card resolution, fixed 6-card hand (1 picked +
   5 random from pool of 10), single-use, 8 sabotage + 2 anti-sabotage. See `GAME_DESIGN.md`.
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
6. ~~**Coherence Engine**~~ — `lib/coherence.js` integrated into game loop.
   Round-level constraints computed at turn start; turn-level constraints
   assembled after card resolution; post-generation validation checks answer
   format. **Correction (July 22, 2026):** this originally claimed a shared
   `coherence/engine.py` framework — that file didn't actually exist on this
   branch's history until today's branch consolidation added it (see item 31).
   It exists at the monorepo root now, but `lib/coherence.js` still doesn't
   call it — treat "shared" as aspirational until item 31's Godot port makes
   the actual wiring worthwhile.
7. ~~**Per-player views**~~ — `playerView()` filters state per socket. Hands,
   answers, and role-gated data hidden appropriately.
8. ~~**Steal round rule**~~ — FCFS buzz-in window (8s), half-wager penalty on
   wrong steal. Documented in `GAME_DESIGN.md`.
9. ~~**Redirect**~~ — random target (decided). No UI needed.
10. ~~**Category attribution**~~ — locked at registration, publicly visible,
    attributed in category options. Everyone sees who submitted what.
11. ~~**Player count**~~ — 3–6 players enforced. Hard cap at join.
12. ~~**Wager design principle**~~ — "I cut, you choose" documented.
13. ~~**Whoa Nellie**~~ — category ambush: swaps to a random different category
    from the pool at the same difficulty. Attributed ("swapped to Sarah's
    90s Hip Hop!").
14. ~~**Post-game activations**~~ — superlative voting, replay moments,
    shareable recap, "one more round" moments. See `GAME_DESIGN.md`.
15. ~~**Question types**~~ — three types: First Come First Serve, Open to All,
    Visual. Separate layer from round rules. See `GAME_DESIGN.md → Question Types`.
16. ~~**Worst Answer Wins round rule**~~ — submission-based, 3-axis scoring
    (factually wrong, creatively wrong, plausibility). Lowest total wins.
17. ~~**Rename Slow Burn → Take Your Time**~~
18. ~~**Question–rule coherence**~~ — generation-time constraint documented.
    See `GAME_DESIGN.md → Question–Rule Coherence`.
19. ~~**Complexity guardrails**~~ — "hear it and get it" test added to Design
    Thesis. See `GAME_DESIGN.md → Complexity Budget`.
20. ~~**Hot Take removed**~~ — moved to `PLAYTEST.md` (PT-2). Includes
    stretch idea: player-defined round rules ("Group Round").
21. ~~**Lobby → card pick UI**~~ — `Lobby.jsx` rewritten (two-step flow:
    categories → CardPicker). `CardPicker.jsx` added (40s timer, grid of 10).
22. ~~**Fact bank / batch question pipeline**~~ — `fetchFactsBatch()` in
    `claudeClient.js`. Five-bucket research prompt (Catalyst & Origins →
    Verified Trivia). Called once at game start via `buildFactBank()` in
    `gameState.js`. Stored on `game.factBank`. ~5-7 API calls vs 48.
23. ~~**Question-from-fact builder**~~ — `pickFactoid()` in `coherence.js`
    filters by difficulty + answer format. `generateQuestion()` uses factoid +
    random question angle. Falls back to original prompt if no bank.
24. ~~**First run + playtest**~~ — `npm install` + `npm run dev` succeeded. Ran an
    automated 3-player Playwright playtest (lobby → categories → card pick →
    Start Game → category → wager → card window → question → answer → result)
    and found/fixed 4 crash bugs uncovered only by actually running the app:
    - `claudeClient.js`: Claude sometimes wraps JSON replies in a ```` ```json ````
      fence; raw `JSON.parse` crashed on it. Added a fence-stripping `parseJson()`
      helper used by all 4 API call sites. Also wired the documented
      `ANTHROPIC_API_KEY` / session-ingress-token fallback that was never
      actually implemented.
    - `CategoryPicker.jsx`: rendered `categoryOptions` entries (which are
      `{category, submittedBy, submittedById}` objects per the attribution
      design) as if they were plain strings — fatal "Objects are not valid as
      a React child" crash the instant the CATEGORY phase appeared.
    - `CardHand.jsx` / `cards.js`: every hand always includes the universal
      `'halfOff'` card, but `CARDS` never included it (`HALF_OFF` was a
      separate constant) — `CARDS['halfOff']` was `undefined`, crashing every
      CARD-phase render. Added `CARD_INFO` (merged lookup) and switched
      `CardHand.jsx` to use it.
    - `GameBoard.jsx`: `AnswerPhase`/`ResultPhase` read `game.currentQuestion.*`,
      but `playerView()` never sends a nested `currentQuestion` — it flattens
      to `game.question` / `game.hostQuip` / `game.answer` (answer withheld
      until RESULT/GAME_OVER on purpose). Fixed the client to read the flat
      fields.
    After all 4 fixes, a full turn completes cleanly end-to-end with zero
    console/page errors (verified: category attribution, wager, card window,
    Claude-generated question honoring the active round rule, fuzzy answer
    evaluation, result screen). Next: extend playtesting to a full 24-question
    game, sabotage card plays (not just the auto-resolving card window),
    disconnect/reconnect, and voice input.
25. ~~**Disconnection handling**~~ — 45s grace period → vote to wait/continue.
    `disconnectPlayer()`, `reconnectPlayer()`, `startDisconnectVote()`,
    `castDisconnectVote()`, `resumeAfterDrop()` in `gameState.js`. Server
    wired with `game:rejoin`, `disconnect:vote` events. Future: AI host
    narrates disconnects with humor.
26. **Known gaps / TODOs from the scaffold**:
    - **Spotlight** — approximated as 5s timer; UI doesn't skip a prep step.
    - ~~**Heckle content moderation**~~ — host-reinterpretation via
      `moderateHeckle()` in `claudeClient.js`. Light trash talk encouraged,
      slurs/hate rewritten. `resolveCardSlot()` now async.
    - ~~Game code collisions~~ — retry loop in `server.js` `game:create`.
    - ~~Voice input~~ — `VoiceInput.jsx` component using Web Speech API.
      Server contract already supports `inputMode: 'voice'`. Wire into
      `GameBoard.jsx` answer input when ready for playtest.
27. **[FUTURE] Group splitting** — when 7+ players want to play together,
    design a splintering mechanic to auto-create balanced sub-games (e.g.
    4+3, 3+3+3). Parked until core game is proven.
28. ~~**Extended playtest**~~ — ran an automated 3-player Playwright game that
    actively plays a sabotage/anti-sabotage card every turn (rotating through
    the hand, deprioritizing the always-available Half-Off so real cards get
    exercised) and plays a full 24-question game to `GAME_OVER`. Found and
    fixed 3 more bugs beyond item 24's four:
    - **Missing STEAL phase UI** — `gameState.js`/`server.js` fully
      implement the FCFS steal mechanic (`claimSteal`, `expireSteal`,
      half-wager penalty) but `GameBoard.jsx`'s phase switch had no `STEAL`
      case, so the window silently auto-expired with no way to buzz in.
      Added a `StealPhase` component wired to `turn:claimSteal`, and a
      `result.stolen` headline in `ResultPhase`.
    - **Skip-card crash** — `resolveCardSlot()`'s `'skip'` case sets
      `game.skippedTurn = true` and skips `lastResult` entirely (there's no
      question to report), but `playerView()` never forwarded
      `skippedTurn` to the client. `ResultPhase`'s `if (game.skippedTurn)`
      guard was therefore always false and fell through to
      `game.lastResult.wager`, crashing every client the instant anyone
      played Skip, for the rest of the game. Fixed by adding
      `skippedTurn: !!game.skippedTurn` to the view.
    - **Silent hang on a failed Claude call** — `finishCardPhase()` (which
      calls `generateQuestion()`) was invoked fire-and-forget from
      `resolveCardWindow()`/`startCardWindow()` with no `.catch`; same gap
      in `startAnswerTimer`'s auto-submit path. Any thrown error (network
      blip, truncated JSON) left the turn hung forever in QUESTION/ANSWER
      phase with zero client feedback, and once it did eventually resolve,
      `scheduleNextTurn()` — the only phase-timeout helper with no guard —
      spammed `uncaughtException`s trying to re-advance an already-advanced
      game. Fixed with a shared `recoverFromFailedTurn()` (skips the turn)
      plus the missing phase guard. Also raised `generateQuestion`'s
      `max_tokens` 1024→2048 and loosened the JSON-fence regex to match
      a fenced block anywhere in the reply, not just when it wraps the
      whole response — both reduce how often a verbose round-rule prompt
      trips this path.
    After all fixes: a full 24-question game completes with zero
    console/page errors and zero server exceptions, exercising every
    sabotage/anti-sabotage card, Steal (both a successful and a failed
    steal, plus a no-one-stole expiry), and the inactivity auto-skip system
    (triggered incidentally when a card play left a player un-answered for
    a stretch). Remaining uncovered: voice input mode, disconnect/reconnect,
    and the `submissionBased` flag on Worst Answer Wins (declared on the
    round rule but never actually branched on in `gameState.js` — currently
    plays like a normal single-answerer turn).
29. ~~**Remaining gaps from extended playtest — voice input mode**~~ — wired
    `VoiceInput.jsx` into both `AnswerPhase` and `StealPhase` in
    `GameBoard.jsx`. Each phase now tracks `inputMode` (`'text'` | `'voice'`)
    alongside the answer string: typing sets it back to `'text'`, a finished
    voice transcript sets it to `'voice'` and fills the same editable input
    (so a misrecognized word can still be corrected before Submit/Steal).
    `submit()` sends whichever mode was last used, unchanged wire format —
    no server changes needed since `server.js` already passed `inputMode`
    through to `submitAnswer()`/`claimSteal()`.
    Verified end-to-end with a real game (real Claude API calls for fact
    bank + question + evaluation) and a mocked `window.SpeechRecognition`
    (Playwright, no real mic in this environment): clicking the mic filled
    the answer box with the fake transcript, and the round rule's **voice**
    transform (not the text transform) was applied server-side — confirmed
    by the evaluator's feedback quoting back the voice-transformed string.
    Remaining: disconnect/reconnect and `submissionBased` Worst Answer Wins
    are still open (see item 26/28's notes) — pick one next.
    **Known platform caveat (not fixed, just documented):** Web Speech API
    is Chromium-only — Safari/iOS has no `SpeechRecognition`, so
    `VoiceInput.jsx` renders `null` there and those players fall back to
    text silently. Also requires a secure context (HTTPS or localhost) for
    mic permission — fine for local dev, but the deployed build needs TLS
    for phone players to get mic access at all.
30. ~~**Worst Answer Wins — real submission-based mechanic + transparent
    scoring**~~ — this was previously a fake: the round rule declared
    `submissionBased: true` but `gameState.js` never branched on it, so it
    played like a normal single-answerer turn with a tweaked prompt, and
    `evaluateAnswer()` never computed the 3 axes at all. Built the real
    thing per `GAME_DESIGN.md`:
    - `gameState.js`: new `game.submissions` map collects one answer per
      eligible (non-dropped-out) player during ANSWER. `submitGroupAnswer()`
      records each one and reports back once everyone's in;
      `autoFillMissingSubmissions()` fills blanks for stragglers when the
      timer expires. A new transient **EVALUATING** phase
      (`beginGroupEvaluation()`) flips synchronously the instant the last
      submission lands or the timer fires, so the two triggers can't race
      and double-evaluate. `resolveGroupAnswers()` then calls Claude once
      for the whole batch, computes each player's total (factually wrong +
      creatively wrong + plausibility), and awards the wager to whoever's
      total is lowest (ties share the win, same convention as
      `getWinners()`) — non-winners aren't penalized, since nobody "loses"
      a bit that landed.
    - `claudeClient.js`: new `evaluateWorstAnswers()` scores every
      submission in **one** call (not N) — cheaper, and lets Claude judge
      creativity/plausibility relative to the other answers in the batch.
    - `GameBoard.jsx`: new `SubmissionAnswerPhase` replaces the
      single-answerer view for this round rule — every player gets their
      own answer box + voice input, and sees "N/M submitted" while
      waiting. New `WorstAnswerResults` component is the transparency
      piece the user asked for: after scoring, every player sees
      **everyone's** submitted answer plus all three per-axis scores, the
      total, and Claude's specific feedback for that answer — not just who
      won.
    - `playerView()` exposes `roundRule.submissionBased`, `mySubmitted`,
      `submittedCount`/`totalToSubmit` (no leaking of other players'
      answers pre-reveal — those only appear once evaluation completes and
      phase is RESULT).
    Verified end-to-end with a real 3-player game (round rule temporarily
    forced via a local hack, reverted before commit) and a real batched
    Claude call: all 3 pages showed the simultaneous submission UI, the
    "waiting for N more" counter updated correctly, voice submission worked
    in this phase too, and the RESULT screen showed the complete transparent
    breakdown for all 3 players with the winner correctly identified by
    lowest total.
    **Open design call, not spec'd in GAME_DESIGN.md:** only the winner(s)
    gain the wager; everyone else's score is untouched (no penalty for
    non-winners). Worth revisiting if playtesting shows it needs teeth.
    Next: disconnect/reconnect is now the only item-29-era gap left open.
31. **[TOP PRIORITY] Godot port** — decided during a CYM-side session (July 22, 2026), reasoning
    backward from distribution, not from engineering preference:
    - Both CYM and MYF are intended for Steam, PlayStation, and other established platforms.
      Next.js/browser has no clean, cert-friendly path onto those (Electron-wrapping a web app
      is exactly the kind of friction console cert punishes). CYM already paid the cost of a
      Godot client + planned GodotSteam integration (`godot/`, Phase 4 in the CYM `CLAUDE.md`) —
      MYF converging onto the same client stack reuses that investment instead of duplicating a
      second, incompatible distribution path.
    - This also resolves the cross-language question for the shared **coherence engine** (see
      the studio pitch deck's "our engine" slide — Coherence Engine + AI Generation are named as
      the two proprietary pillars/moat across all titles, not incidental backend plumbing).
      Today MYF's `lib/coherence.js` (JS) and CYM's `coherence_validator.py` (Python) are
      separate implementations of the same concept, with no clean way for a Next.js app to call
      Python code directly. Once MYF's client is Godot talking HTTP JSON to a backend — same
      pattern as CYM — the engine can become one real shared Python service both games' backends
      call, instead of two languages needing a bridge. That's a stronger technical story for
      funding purposes too: one deployed asset both titles depend on, not a pattern implemented
      twice.
    - **Where this already stands, mechanically:** during today's branch-consolidation pass (four
      competing, never-merged MYF forks got reconciled onto `dev/mind-your-friends`), a real
      `coherence/engine.py` + `coherence/__init__.py` (a domain-agnostic `RuleSet`/`Issue`/
      `CoherenceReport` base class) got cherry-picked in from one of the losing forks and now
      exists at the monorepo root on this branch. **It is not yet wired to anything** — `lib/
      coherence.js` doesn't call it, and CYM's `coherence_validator.py` doesn't subclass it. Do
      that wiring as part of (or right after) the Godot port, not before — building the
      integration against a Next.js client that's getting replaced anyway is wasted work.
    - Scope not yet decided: full rewrite of `server.js`/`lib/*` game logic into GDScript +
      FastAPI endpoints (mirroring CYM's split) vs. some other division of client/server logic.
      That design pass hasn't happened — this item is "decide to do it and put it first," not
      a worked-out migration plan.
32. ~~**The Lineup round rule**~~ — new 9th round rule, owner-requested one more web feature
    before starting item 31's Godot port. Multiple-choice "spot the real one" mechanic, not
    free-text: 5 options (text list or color swatches), one correct, decoys deliberately close.
    Any player may tap any option any number of times — wrong taps fail silently, no penalty,
    no lockout — first correct tap (server-ordered, no real race) wins the wager. Full design in
    `GAME_DESIGN.md` → "The Lineup — How It Works" and the Question–Rule Coherence table.
    - Two flavors, chosen randomly per question: **text** (fact-bank-grounded multiple choice
      via new `generateLineupOptions()` in `claudeClient.js` — correct answer verified against
      the fact bank rather than trusted to live generation, same reliability fix as the rest of
      this file's fact-bank work; decoys are low-stakes creative generation) and **color** (a
      curated `{entity, label, hex}` table in new `lib/lineupData.js` + procedurally-perturbed
      near-miss swatches — no API call at all for this flavor, since a real hex code is a
      factual claim Claude shouldn't be trusted to invent).
    - `lib/roundRules.js`: new `theLineup` entry (`lineupBased: true`, no `transform` — a tap
      isn't free text).
    - `lib/coherence.js`: `roundConstraints()`/`turnConstraints()` propagate `lineupBased`;
      `validateQuestion()` checks the generated lineup has ≥2 options, unique ids, and a
      `correctOptionId` that references one of them.
    - `lib/gameState.js`: `buildLineupQuestion()` (flavor selection + content assembly),
      `attemptLineupPick()` (FCFS win check — deliberately returns `{correct:false}` instead of
      throwing for a late/invalid tap, since this mechanic invites genuinely simultaneous taps
      by design and a throw would hit the client's global `error` handler, which replaces the
      whole page, not just the answer widget), `expireLineup()` (timer-expiry, no winner).
    - `server.js`: new `turn:attemptLineup` handler using a Socket.io ack callback (not the
      `error` event) so a wrong tap gets local feedback without blowing up the page; timer
      branch mirrors the existing `submissionBased`/steal pattern.
    - `components/GameBoard.jsx`: new `LineupPhase` (ANSWER-phase tap UI, text or swatch grid)
      and `LineupResults` (RESULT-phase reveal, correct option highlighted).
    - `playerView()`: exposes `lineup.options` pre-reveal (safe — that's the multiple-choice UI
      itself) and withholds `correctOptionId` until RESULT/GAME_OVER, same pattern as the
      existing free-text `answer` field.
    Verified end-to-end with a real 3-player Playwright game (round rule temporarily forced via
    a local hack, reverted before commit, same convention as item 30's Worst Answer Wins
    verification) and real Claude API calls: 21 Lineup questions rendered across a full game,
    both flavors confirmed (color: "Which one is Starbucks green?", "Which one is Duke
    University blue?", etc.; text: real fact-bank-grounded questions with 5 well-formed options
    each), always exactly 5 options, 9 clean wins each correctly attributed to whichever
    player's tap landed first with correct scoring, zero client or server errors.
    **Known gap:** the timeout/no-winner path (`expireLineup`) wasn't exercised by this
    playtest — simulated players found the correct option well within the 20s timer every
    time — though the code path is a direct structural mirror of the already-proven
    `expireSteal`. Known limitations (color flavor ignores the picked category; Boxed In/
    Language Barrier cards have no effect on Lineup questions) are documented in
    `GAME_DESIGN.md` rather than fixed, matching this file's existing style for scoped-out
    edge cases.
    **Next: item 31, the Godot port** — this was the one explicitly-approved exception to
    starting it immediately.
33. **[IN PROGRESS] Godot port — Python backend built and verified; Godot client not started.**
    Same session as item 32, continued after a detour into `docs/WIRING.md` → the coherence
    engine unification (see root repo `SESSIONS.md` Session 28 on a separate branch,
    `claude/coherence-engine-unification`, PR #14 — that's CYM-side work, not part of this
    branch's history, done first because it needed real code sharing with `main` that this
    branch can't provide). Owner asked to keep working autonomously with incremental commits
    while away, in case of interruption — this item is written assuming exactly that happened.
    - Full architecture plan in `docs/WIRING.md` (new file, MYF's own — mirrors CYM's
      `docs/WIRING.md` naming): directory layout (`server_py/` + planned `godot/`, existing
      Next.js prototype kept as reference, not deleted), the WebSocket-not-ENet transport
      decision (verified against CYM's actual `main` branch — `NetworkManager.gd` there is
      still a dead Phase-2 stub, `ApiClient.gd`'s WebSocket path is what's actually shipped),
      and a mapping of all 9 round rules onto CYM's `round_type` lockstep dispatch concept
      (implemented via the same boolean-flag dispatch already proven in `lib/gameState.js`,
      not a new abstraction — see the doc for why).
    - `server_py/` — full Python port: `constants.py`, `cards.py`, `lineup_data.py`,
      `round_rules.py`, `coherence.py` (straight semantic ports, not a redesign),
      `claude_client.py` (all 6 Claude-calling functions, same prompts as the JS version
      verbatim), `game_state.py` (the complete phase state machine — every function from
      `lib/gameState.js`, including disconnect/reconnect and inactivity detection), and
      `main.py` (FastAPI app: REST endpoints + WebSocket, `threading.Timer`-based orchestration
      mirroring `server.js`'s `setTimeout` calls, `_broadcast_sync` bridge pattern borrowed
      directly from CYM's `server/main.py`).
    - **Real Python-vs-Node correctness difference, called out inline and in the doc:** every
      state-mutating call runs under one process-wide `_games_lock` (`threading.Lock`) — Node's
      single-threaded event loop gave the JS version's FCFS correctness (card play, Steal, The
      Lineup) for free; Python doesn't, so this is a genuine new requirement, not boilerplate.
      Coarser than per-game locking would be, flagged as a place to revisit if it becomes a
      bottleneck, not treated as good enough forever.
    - **Verification — real, not simulated:** first pass used FastAPI's `TestClient`, which
      turned out not to reliably deliver WebSocket broadcasts fired from a `threading.Timer`
      background thread (the test hung waiting on a push `TestClient`'s in-process lifespan
      silently dropped — a real finding, not a red herring, worth remembering if `TestClient`
      is reached for again later). Switched to a real running `uvicorn` process plus real
      `requests`/`websocket-client` — also more representative of what the Godot client will
      actually talk to. All 5 round-rule dispatch shapes verified end-to-end this way, with real
      Claude API calls and real WebSocket pushes confirming every phase transition (round rule
      forced via a `MYF_FORCE_ROUND_RULE` env-var hack, reverted before each commit, same
      convention as item 30/32's playtest sessions): **standard** (ELI5, Double Down, One Word
      Only, plus natural random runs), **steal** (full wrong-answer → STEAL phase → claim-steal
      → RESULT chain, not just phase detection), **worst_answer_wins** (3 players submit → group
      evaluation → RESULT with 3 scored entries), **the_lineup** (wrong taps failing soft,
      correct tap winning). `lightning_round` wasn't separately forced — it's pure config on top
      of `standard`, no distinct code path beyond what `standard` already proved.
    - **What's explicitly NOT done, stated plainly so nobody assumes otherwise:** the `godot/`
      client — zero scenes, zero GDScript — hasn't been started. No Godot binary exists in this
      environment (root `CLAUDE.md`: "No Godot binary in repo"), so writing GDScript here would
      mean shipping code nobody could verify even compiles, let alone runs — deliberately
      sequenced after the backend was proven instead. Also not started: voice input,
      disconnect/reconnect (ported to `game_state.py` but not exercised against a live game this
      session), inactivity auto-advance (same — ported, not live-tested). The Next.js prototype
      (`app/`, `components/`, `lib/*.js`, `server.js`) is untouched and still the reference
      implementation for exact behavior until `server_py/`+`godot/` reach parity and get
      playtested for real — do not delete it.
    - **Session was interrupted by container restarts more than once** (mid-test, twice) — each
      time, `git log` on this branch showed all prior commits intact and already pushed, so
      nothing was lost; work resumed by re-verifying git state and re-running whatever test had
      been killed. If a future session picks this up mid-stream, check `docs/WIRING.md`'s
      checkbox list first — it's the single source of truth for what's actually built, kept more
      current than this narrative summary by design.
    - **Next:** the `godot/` client. Start with `ApiClient.gd`, ported near-verbatim from CYM's
      (same WebSocket contract this backend already speaks), then a minimal Lobby scene talking
      to `POST /games/create` + `/ws/{code}` to prove the client/server pair end-to-end before
      building out the rest of the round-loop UI.
34. **[DONE] Godot client foundation built AND verified end-to-end** — completes the "Next" step
    item 33 left open. The headline finding: **"no Godot binary in this environment" was wrong.**
    The official Godot 4.6 Linux headless build downloads and runs here fine, so GDScript in this
    repo no longer has to be written blind. Full instructions in `docs/WIRING.md` →
    "Verifying the Godot client". Every future session should run the `--import` compile check
    before trusting any GDScript.
    - **`ApiClient.gd` did not compile as written.** Item 33 shipped it unverified with a caveat
      saying exactly that; the caveat was justified. `_post`'s `request_completed` lambda took
      untyped parameters, so `var text := response_body.get_string_from_utf8()` couldn't infer a
      type — a hard `Parse Error`, meaning the autoload failed to load and the client would not
      have started at all. Fixed by typing the callback signature.
    - **`GameState.gd`** — client-side mirror of `player_view()`, registered as the second
      autoload (after `ApiClient`, which it connects to in `_ready()`). Deliberately holds zero
      game logic: `server_py` broadcasts a complete per-player view after every mutation, so the
      correct client design is last-write-wins replacement, not delta patching — any client-side
      prediction would just be a second source of truth to drift. Exposes `state_updated` /
      `phase_changed` / `players_changed` / `game_over` signals plus typed accessors.
    - **Lobby scene** (`scenes/ui/lobby.tscn` + `scripts/ui/lobby.gd`) — create/join, live
      roster, ready-up, start. Follows CYM's `lobby.gd` pattern: fire the HTTP action, then
      drive all UI off the resulting WebSocket push, never off the HTTP callback.
      **Registration is stubbed** — it submits placeholder categories and a hardcoded
      `insurance` card, because the category-selection and card-pick screens don't exist yet.
      That's the next UI work, and it's the one thing in the lobby flow that is not real.
    - **Verified end-to-end against a real running backend, not mocks:** two headless test
      scenes. `lobby_smoke_test.tscn` — 18 assertions, all passing, **no API cost** (create → WS
      push → join ×2 → roster push → register ×3 → startable, plus confirming other players'
      hands stay withheld). `game_start_smoke_test.tscn` — all passing, but **spends real API
      calls** on the fact-bank build, so it's kept as a separate scene; it proves LOBBY →
      CATEGORY with 6 attributed category options, hands dealt, and a round rule assigned.
    - **Environment gotcha worth remembering:** a bare `pip install uvicorn` ships without
      WebSocket support, and the failure mode is misleading — the WS handshake 404s, which reads
      as a client routing bug. Install `uvicorn[standard]`/`websockets` or the client cannot
      connect. Cost real debugging time here; it is not a code defect.
    - **Next:** the CategoryPicker screen (replacing the lobby's placeholder registration), then
      the card-pick screen, then the round-loop UI (WAGER → CARD → QUESTION → ANSWER → RESULT).
      `GameState` already exposes accessors for all of those phases; none have UI yet.

35. **[IN PROGRESS — priority 1] Post-game social layer: Superlative Voting + Shareable
    Question.** Owner-chosen (August 7, 2026) as the next feature after the Godot port merged
    to `main` (PR #15). Two pieces, built **in the Next.js prototype first** — deliberately,
    because it's the only version that can be played end-to-end with real people today, and
    the whole point of a social feature is finding out whether it lands. Same validation
    convention as items 24/28/30/32. It gets ported to Godot after it's proven, not before.
    - **Superlative Voting** — after GAME_OVER, a short voting round on 3–4 AI-generated
      superlative categories drawn from what actually happened in the game ("Best Sabotage",
      "Worst Answer", "Most Targeted"). Ties are shared wins, same convention as `getWinners()`.
      Chosen over the cheaper alternatives because it's the only post-game option that
      **captures player signal** rather than just generating more content — which is the root
      `CLAUDE.md` design principle ("prefer code that captures signal over code that generates
      more content with no signal").
    - **Shareable Question** — owner's redesign of the spec'd "Shareable Recap", and a better
      idea: the shareable artifact is **a question from the game**, framed as a challenge to
      the sharer's own following, *not* a scoreboard. A scoreboard only means something to the
      people who were in the room; a hard trivia question travels, because guessing it drives
      replies. Optional per player, answer deliberately withheld from the card, no persistence
      required (client-side canvas → Web Share API, download fallback). Full design in
      `GAME_DESIGN.md` → "Shareable Question — the growth mechanic".
    - **Known prerequisite:** `game.highlightReel` logs prose strings, not structured data, and
      there is no record of the questions asked. Both features need a real `game.questionLog`
      (question, answer, category + attribution, who answered, right/wrong, wager) — that's the
      first build step, and it's also what makes the "4 of 5 friends got this wrong" hook line
      possible.

## Design Thesis: Casual-First
This game targets casual, social players — not competitive optimizers. Every
mechanic must optimize for surprise, laughs, and "oh no!" moments over strategic
depth. Randomness is a feature. Minimal decisions, maximum expression. No homework
required — a new player should understand everything by end of Round 1. Design for
the table, not the meta. See `GAME_DESIGN.md → Design Thesis` for full detail.

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
                    # Also: disconnect/reconnect, inactivity detection, fact bank
lib/claudeClient.js # fetchFactsBatch(), generateQuestion(), evaluateAnswer(), moderateHeckle()
lib/coherence.js    # Two-pass CE (roundConstraints → turnConstraints → validateQuestion) + pickFactoid()
lib/cards.js        # Card definitions, dealRoundCards(), buildRoundHand()
lib/roundRules.js   # Rule definitions + answer transforms
lib/constants.js    # Shared constants (no Node-only deps — safe for client components)
components/         # React UI per phase (Lobby, CardPicker, CategoryPicker, CardHand, GameBoard, ScoreBoard, VoiceInput)
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
2. Read **Current To-Do** above — item #31 (Godot port) is the next step.
3. Run `git log --oneline -10` to see what was last committed.
4. Read `GAME_DESIGN.md` for the full game design.
5. Read `PLAYTEST.md` for open playtest questions (PT-1 through PT-3).
6. State your starting point in the first reply: branch, latest commit, what you'll do.

> **Branch hygiene note (July 22, 2026):** four past sessions each independently forked MYF from
> the same old base commit (`claude/continuation-r0mhfq`, `brave-bohr-45istr`,
> `confident-franklin-250vxg`, `compassionate-cray-pu5ieu`) with no cross-awareness, so real work
> was scattered across competing branches with no PR and no single source of truth — the same
> failure mode CYM hit before its own July 9 reconciliation. These got compared and consolidated
> onto `dev/mind-your-friends` (built on `continuation-r0mhfq`, the most complete of the four,
> plus the coherence-engine files and a standalone API route cherry-picked from two of the
> others). The four source branches still exist on the remote but are superseded — don't resume
> work on them; `dev/mind-your-friends` is the one true branch now. This file's Session Start
> Protocol and "What NOT to Do" previously still pointed at `claude/continuation-r0mhfq` — fixed
> here so a future session isn't misdirected the way CYM's `CLAUDE.md` was before its own fix.

## What NOT to Do
- Never push directly to `main` (403). Use `dev/mind-your-friends`.
- Never put Claude API calls in client-side React — only `server.js` touches the API.
- Don't add a database yet — in-memory state is intentional for MVP.
