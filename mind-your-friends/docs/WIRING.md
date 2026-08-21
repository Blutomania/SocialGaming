# Technical Wiring — Mind Your Friends (Godot Port)

How the Godot client and Python backend connect. Written the same day the port started
(session continuing from The Lineup round rule work) — see `CLAUDE.md` item 33 for status.

---

## Why this split (recap of the decision)

Both CYM and MYF target Steam/console distribution. Next.js/browser has no clean cert-friendly
path onto those platforms. CYM already paid the cost of a Godot client + planned GodotSteam
integration (`godot/` at repo root, CYM's `CLAUDE.md` Phase 4) — MYF converging onto the same
client stack reuses that investment instead of duplicating a second, incompatible distribution
path. It also resolves the coherence-engine unification question (see root `docs/WIRING.md` →
"Coherence validator" and `SESSIONS.md` Session 28): MYF's coherence logic is JavaScript today
and can't subclass the shared Python `coherence.engine.RuleSet` without a bridge. Once MYF's
backend is Python, it can.

**Done, August 20 2026 — and the name collision is the part to know about.**
`server_py/coherence_rules.py` (renamed from `coherence.py`) defines `QuestionRuleSet`, a real
`coherence.engine.RuleSet` subclass, so the shared framework has two consumers: this and CYM's
`coherence_validator.py`.

The rename was not tidying, it was the blocker. A top-level module named `coherence` and a
*package* named `coherence` cannot both live on `sys.path` — whichever is found first wins, and
`server_py/` is always first, so `from coherence.engine import RuleSet` resolved to MYF's own file
and raised `"'coherence' is not a package"`. Nothing about import order fixes that. **If you ever
add a module here whose name matches something at the monorepo root, this is what happens**, which
is also why the repo-root `sys.path` entry is *appended* rather than inserted: `server_py`'s own
modules must keep winning collisions.

`validate_question()` keeps its signature and returns a `coherence.engine.CoherenceReport` instead
of a `{"passed", "issues"}` dict. `server_py/test_coherence_engine.py` (zero API cost) proves both
the plumbing and that no rule changed in the rewire. `lib/coherence.js` is deliberately untouched —
the JS prototype is still the behavioural reference and is for retirement, not for a bridge.

## What CYM already proved, that this port reuses directly

Studied CYM's actual `main`-branch implementation (not the aspirational parts of its own docs)
before designing this. Two findings shaped every decision below:

1. **The transport is WebSocket, not ENet.** `godot/scripts/autoloads/NetworkManager.gd` is
   still a Phase-2 stub — CYM never built real ENet multiplayer client-side. What's actually
   shipped and working is `ApiClient.gd`'s `connect_ws(game_id, player_id)` → `/ws/{game_id}`,
   emitting one `ws_event(event_name, data)` signal that scenes subscribe to. `lobby.gd` wires
   entirely through this, never touching `NetworkManager`. MYF's port follows this pattern, not
   ENet — there's no open question here, CYM already answered it.
2. **Two channels, two jobs.** HTTP request/response for whatever *this* player just did
   (targeted reply, only to the actor). WebSocket push for anything caused by *someone else*, or
   that finishes async (broadcast to the room). This is a deliberate split from MYF's current
   Socket.io model, which resends the *entire* `playerView()` to everyone on every mutation —
   simpler, but chattier, and it doesn't distinguish "tell the asker" from "tell the room." The
   port adopts CYM's split because the round-loop dispatch pattern below (reused from CYM) is
   built on top of it.

## Layout

```
mind-your-friends/
├── server_py/              # NEW — FastAPI backend, replaces server.js + lib/*.js game logic
│   ├── main.py              # FastAPI app, room/lobby/WS endpoints
│   ├── game_state.py         # In-memory games dict + lock, ported from lib/gameState.js
│   ├── round_rules.py        # Port of lib/roundRules.js — ROUND_RULES dict, now round_type-keyed
│   ├── claude_client.py      # Port of lib/claudeClient.js — fact bank, question gen, evaluation
│   ├── cards.py               # Port of lib/cards.js
│   └── lineup_data.py         # Port of lib/lineupData.js (curated colors + decoy perturbation)
├── godot/                   # NEW — Godot client project, mirrors CYM's godot/ structure
│   ├── project.godot
│   ├── scripts/autoloads/
│   │   ├── ApiClient.gd       # Ported near-verbatim from CYM's — HTTP + WS wrapper
│   │   └── GameState.gd       # MYF-specific: round rule, hand, score, phase mirror
│   └── scenes/ui/             # Lobby, CategoryPicker, CardHand, GameBoard-equivalent, etc.
├── app/, components/, lib/, server.js   # EXISTING Next.js prototype — kept, not deleted.
│                                          Still the reference implementation for game logic
│                                          semantics while server_py/ is being built out.
```

**Decision, not yet confirmed with the owner:** directory names (`server_py/`, `godot/` nested
under `mind-your-friends/`) are a reasonable default, not a mandate — easy to rename if a
different convention is preferred once more of the port exists to look at.

**The Next.js prototype is not being deleted.** Per CYM's own precedent (`deprecated/` kept the
old Streamlit tooling around during its migration), the existing `server.js`/`lib/*.js`/React
client stays in place and working during the port — it's the executable spec for exact game
behavior (every rule's edge cases, every bug already fixed and documented in `CLAUDE.md`'s
to-do list) until `server_py/` + `godot/` reach parity and get playtested for real.

## Backend: room/lobby/WebSocket shape

Directly modeled on CYM's `server/main.py` connection-manager pattern:

- `_games: dict[str, dict]` — in-memory game-session store, keyed by room code.
- `_games_lock: threading.Lock()` — **new requirement, not in the JS version.** MYF's FCFS
  mechanics (card play, Steal, The Lineup) currently rely on Node's single-threaded event loop
  for correctness with zero explicit locking. FastAPI/Python doesn't give that guarantee for
  free — every state-mutating endpoint must acquire `_games_lock` around its read-modify-write,
  or two near-simultaneous "first correct tap" requests for The Lineup could both see themselves
  as first. This is the single most important correctness difference from the JS port and the
  first thing to get right, not an afterthought.
- `_ConnectionManager` — one WebSocket list per `game_id`, `broadcast(game_id, event, data)`.
  Same shape as CYM's, reused near-verbatim.
- `POST /games/create` → room code (reuse MYF's existing `generateGameCode()` alphabet:
  no I/O to avoid 1/0 confusion).
- `POST /games/{id}/join`
- `WS /ws/{game_id}?player_id=...`

## The round loop, generalized onto CYM's lockstep pattern

This is the part worth building carefully, because MYF's `submissionBased` (Worst Answer Wins)
and `lineupBased` (The Lineup) round rules already independently reimplemented, in ad hoc JS,
almost exactly the `stage: submitting → generating → revealed` shape CYM built generically for
its own witness-round rebuild (root `docs/WIRING.md` → "Multiplayer lockstep round system").
Porting MYF's 9 round rules onto that same generic dispatch, instead of re-inventing per-rule
phase juggling a second time in Python, is the actual point of doing this port carefully rather
than just transliterating `gameState.js` line-for-line.

### Round shape (`game["round"]`)

```json
{
  "round_type": "standard",           // one of the 9 round rule ids, see mapping table below
  "phase": "category",                // category -> wager -> card -> question -> answer -> result
  "active_player_id": "...",
  "answerer_id": "...",
  "category": null,
  "wager": null,
  "card_slot": null,
  "question": null,                    // {question, answer, hostQuip, lineup?}
  "submissions": {},                    // used by submission-based / lineup-based round types
  "opened_at": 1735689600.0,
  "result": null
}
```

### `_ROUND_TYPE_CONFIG` dispatch table — mapping MYF's 9 round rules

| round_type | timer_seconds | answer mode | Python module owning generation |
|---|---|---|---|
| `standard` (Back It Up / One Word Only / Take Your Time / ELI5 / Double Down — differ only by prompt/timer/wager modifier, not answer *mode*) | rule-specific | single answerer, free text, fuzzy-matched | `claude_client.generate_question()` |
| `lightning_round` | 10 | single answerer, free text | same as standard, `timer_seconds` halved |
| `steal` | 20 | single answerer → STEAL sub-phase on wrong | same as standard + `claim_steal()` |
| `worst_answer_wins` | 40 | all players submit, batch-scored | `claude_client.evaluate_worst_answers()` |
| `the_lineup` | 20 | all players may tap any option, FCFS correct-tap-wins | `claude_client.generate_lineup_options()` or `lineup_data` (color flavor, no API call) |

This collapses MYF's 9 round *rules* into effectively 5 round *type* handlers by answer-mode —
most of the JS `ROUND_RULES` entries differ only in `promptInstruction`/`timerSeconds`/
`wagerMultiplier`, which become config on `standard`, not separate dispatch branches. Only
`worst_answer_wins` and `the_lineup` need genuinely distinct submission/resolution logic, which
matches exactly what building both of those in JS this year already showed empirically.

### Endpoints (per round)

| Endpoint | Who | What |
|---|---|---|
| `POST /games/{id}/round/pick-category` | active player | Same as `turn:pickCategory` today |
| `POST /games/{id}/round/set-wager` | wager-decider | Same as `turn:setWager` |
| `POST /games/{id}/round/play-card` | any | FCFS card slot, same semantics as `playCard()` |
| `POST /games/{id}/round/submit-answer` | answerer (or all, if submission-based) | Dispatches by `round_type` |
| `POST /games/{id}/round/attempt-lineup` | any | Only valid when `round_type == "the_lineup"` |
| `WS` events | — | `round_category_picked`, `round_wager_set`, `round_card_played`, `round_question_ready`, `round_result` |

## What's actually built as of this session (be honest about scope)

**Do not read this doc as "the port is done."** As of this session:
- [x] `server_py/` FastAPI skeleton (rooms, lobby, WS) — built, verified against a real running
      uvicorn server with a real WebSocket client (not just TestClient — see note below)
- [x] Registration (categories + card pick) + game start (real fact-bank API call) — verified
- [x] `standard` round_type end-to-end (category → wager → card → question → answer → result) —
      verified with multiple real round rules (ELI5, Double Down, One Word Only) through the
      real server, real Claude calls, real WebSocket pushes confirming every phase transition
- [x] `steal`, `worst_answer_wins`, `the_lineup` — **all verified end-to-end** through the real
      server (round rule temporarily forced via an env var for deterministic testing, reverted
      before commit — same convention as the JS version's own playtest sessions). Steal's full
      wrong-answer → STEAL phase → claim → RESULT chain was exercised, not just detected.
      `lightning_round` was not separately forced (it's config-only on top of `standard` — no
      distinct code path to verify beyond what `standard` already proved)
- [x] `godot/` client foundation — **now VERIFIED against a real Godot 4.6 binary.** The "no
      Godot binary in this environment" constraint turned out to be beatable: the official
      Linux headless build downloads and runs fine here (see "Verifying the Godot client"
      below). `ApiClient.gd` **did not compile** as written — `_post`'s `request_completed`
      lambda had untyped parameters, so `var text := response_body.get_string_from_utf8()`
      couldn't infer a type (`Parse Error` at line 147). Fixed by typing the callback
      signature. That's exactly the class of error the previous session flagged as
      unverifiable, and it was real.
- [x] `GameState.gd` — client-side mirror of `player_view()`. Holds no game logic: the server
      broadcasts a complete per-player view after every mutation, so the client does
      last-write-wins replacement, not delta patching. Turns the single `game:state` firehose
      into `state_updated` / `phase_changed` / `players_changed` / `game_over` signals, plus
      typed accessors so scenes never hand-parse raw dictionaries.
- [x] Lobby scene (`scenes/ui/lobby.tscn` + `scripts/ui/lobby.gd`) — create/join a room, live
      roster, ready-up, start. Registration currently submits **placeholder** categories and a
      hardcoded `insurance` card: the real category-selection and card-pick screens don't exist
      yet, and stubbing them keeps the lobby independently testable rather than blocked.
- [x] **Client/server pair proven end-to-end** — two headless test scenes drive the real
      autoloads against a real uvicorn backend:
      - `scenes/tests/lobby_smoke_test.tscn` — 18 assertions, **all passing**, zero API cost.
        Covers create → WS push → join ×2 → roster push → register ×3 → `can_start_game()`,
        plus the information-hiding guarantees (other players' hands stay withheld).
      - `scenes/tests/game_start_smoke_test.tscn` — **all passing**, but **costs real API
        calls** (fact-bank build), so it's a separate scene rather than part of the everyday
        test. Covers LOBBY → CATEGORY: `phase_changed` fires, 6 attributed `categoryOptions`
        arrive, hands get dealt, a round rule is assigned.
- [ ] Voice input, disconnect/reconnect, inactivity auto-advance — **not started**, will need
      their own pass once the core loop is proven.

## Verifying the Godot client

Previous sessions recorded "no Godot binary in this environment" as a hard blocker and wrote
GDScript unverified because of it. That is no longer true — the official build downloads and
runs headless here:

```bash
curl -sSL -o godot.zip \
  https://github.com/godotengine/godot/releases/download/4.6-stable/Godot_v4.6-stable_linux.x86_64.zip
unzip -q godot.zip && chmod +x Godot_v4.6-stable_linux.x86_64

# Compile-check every script + scene in the project:
./Godot_v4.6-stable_linux.x86_64 --headless --path godot --import

# Full end-to-end against a live backend:
cd server_py && python3 -m uvicorn main:app --port 8001 &
./Godot_v4.6-stable_linux.x86_64 --headless --path godot \
  res://scenes/tests/lobby_smoke_test.tscn    # exits 0 on pass
```

4.6 is what `project.godot` declares in `config/features`, so that's what these were verified
against. **Do not write GDScript in this repo without running at least the `--import` check** —
it catches parse errors in seconds and it already caught a real one.

**Server dependency gotcha:** a bare `pip install uvicorn` has no WebSocket support, and the
symptom is misleading — the WS handshake 404s and looks like a client bug or a routing mistake.
Install `uvicorn[standard]` (or `websockets`) or the Godot client cannot connect at all.

**Real-server testing note:** the first verification pass used FastAPI's `TestClient`, which
turned out not to reliably deliver WebSocket broadcasts originating from a `threading.Timer`
background thread (the card-window/answer-timer auto-resolve pushes) — the test hung waiting on
a push `TestClient`'s in-process lifespan silently dropped. Switched to a real `uvicorn` process
plus real `requests`/`websocket-client` — this is also more representative of what the Godot
client will actually talk to, so it's the right test shape going forward, not just a workaround.

Update the checkboxes above as work lands, in this same doc, rather than trusting `CLAUDE.md`'s
narrative summary alone to stay accurate — this table is the single source of truth for "what's
actually done" during the port.

---

## The August 12 playtest changes — what a porter needs to know

The owner played the Next.js prototype on August 12, 2026 and returned eleven
notes. All eleven landed **in the prototype only**. `server_py/` has not been
updated for any of them, which is the single most important thing to know
before touching the Godot client — the two backends now genuinely differ, and
`server_py` is the one the Godot client talks to.

### Mechanics that changed shape (these need porting, in this order)

| Change | JS | `server_py` today | Port note |
|---|---|---|---|
| **Open answering** — everyone gets one attempt at the same question, first correct wins | `submitAnswer`/`resolveOpenAnswer`/`expireAnswerWindow` in `lib/gameState.js` | still single-answerer + STEAL phase | The biggest one. Needs `answerAttempts`, the wager asymmetry, and a serialized evaluation path — see below |
| **Steal retired** | `steal` rule and the whole STEAL phase deleted | `round_rules.py` still has `steal`; `main.py` still has the claim-steal endpoint | Delete rather than port. Open answering *is* Steal, always on |
| **Reading window** | `answerOpensAt` timestamp; `getAnswerWindowMs()` covers reading + answering in one timer | no reading window | Do NOT add a phase for it. Every phase-timeout helper assumes the existing loop |
| **Round rules per round** | `beginRoundIfNeeded()`; round 1 is `NO_RULE`; `usedRuleIds` prevents repeats | rule redrawn every turn | Also needs `roundAnnouncement`, which the client renders as a banner for one turn |
| **Lazy fact bank** | `ensureCategoryFacts()` + `prefetchFactBank()`; `startGame` is synchronous | `start_game` still builds the whole bank inline | This is why `ApiClient.gd`'s start timeout stopped mattering — see below |
| **3 categories, curated list** | `CATEGORIES_PER_PLAYER = 3`, `lib/categories.js` | still 5 | The Godot category screen (priority-queue item 2) should be built against 3 and the curated grid, not 5 free-text boxes |
| **Question length** | hard 8–20 word rule in both prompts | old prompts | Straight prompt copy |

### Why evaluations are serialized

`submitAnswer` chains its Claude evaluations through `game._answerChain` rather
than running them concurrently. This is not incidental: with N players racing
the same question, "first correct wins" has to mean first *submission*, not
first *response*. Evaluating in parallel hands the win to whoever's API call
returns quickest — a coin flip — and lets two players both be paid for the same
question.

Node gets the ordering for free from its single-threaded event loop plus that
one promise chain. **Python does not.** `server_py` already runs every mutation
under `_games_lock`, but the evaluation itself is an I/O wait that must not hold
that lock for the whole call, or the room freezes for every answer. The port
needs a per-game answer queue, not just the existing lock.

### Start is instant now

`startGame` no longer builds the fact bank, so the `startProgress` push and
`ApiClient.gd`'s 300s `START_GAME_TIMEOUT` are both belt-and-braces rather than
load-bearing. Leave them: the timeout costs nothing and the progress field is
what `prefetchFactBank` reports through (`view.factPrefetch`). What matters for
the port is that facts arrive per-category, awaited in `runQuestionPhase` and
kicked off early on category pick — the correctness backstop and the latency
hiding are two separate calls on purpose.

### The logo split

`scripts/build-logo.mjs` turns the two-path source art into three
independently colourable emoji (`lib/logoPaths.js`, `public/brand/logo-split.svg`).
Its output is committed, so the Godot client can consume `logo-split.svg`
directly — three `<g>` elements, `emoji-1/2/3` — rather than re-deriving the
split. Re-run the script only if the source art changes; the two things that
make it work (real SVG command arities in the extent parser, and dropping the
artboard's hairline edge artifacts before finding gaps) are both documented in
its header, because both were wrong on the first attempt and failed silently.

### Regression suite

`scripts/mechanics-test.js` — 51 assertions, zero API cost, via the
`__setClientForTests` seam in `claudeClient.js`. It covers the race (two
correct answers genuinely in flight at once), the one-attempt lockout, the
wager asymmetry, timeout charging, fact-fetch de-duplication, and round-rule
assignment. **Port this alongside the mechanics** — a Python equivalent of
these assertions is what will prove the two backends actually agree, and the
race and de-dup ones are exactly where they're most likely to silently differ.
