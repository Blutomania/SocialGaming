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
- [~] `godot/` client — **foundation only, UNVERIFIED.** `project.godot` (no main scene set —
      none exists) + `ApiClient.gd` (HTTP+WS wrapper, adapted from CYM's proven version to MYF's
      actual endpoint paths) exist now. No Godot binary in this environment (root `CLAUDE.md`:
      "No Godot binary in repo"), so this is unverified by construction — written carefully
      against CYM's known-working reference rather than from scratch, but still needs a real
      Godot editor to confirm it even compiles before anyone trusts it. **No scenes exist.**
      `GameState.gd` (MYF's state mirror) is the next piece, before any UI.
- [ ] Voice input, disconnect/reconnect, inactivity auto-advance — **not started**, will need
      their own pass once the core loop is proven.

**Real-server testing note:** the first verification pass used FastAPI's `TestClient`, which
turned out not to reliably deliver WebSocket broadcasts originating from a `threading.Timer`
background thread (the card-window/answer-timer auto-resolve pushes) — the test hung waiting on
a push `TestClient`'s in-process lifespan silently dropped. Switched to a real `uvicorn` process
plus real `requests`/`websocket-client` — this is also more representative of what the Godot
client will actually talk to, so it's the right test shape going forward, not just a workaround.

Update the checkboxes above as work lands, in this same doc, rather than trusting `CLAUDE.md`'s
narrative summary alone to stay accurate — this table is the single source of truth for "what's
actually done" during the port.
