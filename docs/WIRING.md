# Technical Wiring — Choose Your Mystery

How the pieces connect. Written so you don't have to hold it all in your head.

---

## Data flow (end to end)

```
User prompt  ("1920s Harlem jazz club")
     │
     ▼
part_registry.py — sample_for_generation()
     │  Pulls compatible atomized parts from the 1,469-part corpus
     │  Returns: List[MysteryPart], Recipe
     │
     ▼
Claude API  (one call, structured JSON prompt)              ← call 1
     │  Parts act as hard constraints — Claude fleshes out prose
     │  Returns: mystery dict  (see Mystery JSON Schema below)
     │
     ▼
localize_mystery()                                          ← call 2 (always)
     │  Rewrites all character names, occupations, titles, and embedded
     │  text so they fit the setting's time period and culture.
     │  "Dr. Pemberton" in Ancient Athens → "Alexios the Physician"
     │  Minor characters may get playful period puns (e.g. "Vidiomnius")
     │  Preserves plot, culprit, evidence logic — surface text only.
     │
     ▼
coherence_validator.py — check_mystery()                    ← free, no API call
     │  Checks P1 causal chain + witness depth + evidence variety
     │  Returns: CoherenceReport  (passed, blocking_count, warning_count)
     │
     ├─── [opt-in] generate_cinematic_brief()               ← call 3 (opt-in)
     │         One extra Claude call
     │         Returns: cinematic_brief dict  (see Cinematic Brief Schema below)
     │         Stored at mystery_dict["cinematic_brief"]
     │
     ▼
mystery_dict  saved to  mystery_database/generated/<slug>_<timestamp>.json
```

### Call budget per generation

| Step | Calls | Condition |
|---|---|---|
| Mystery generation | 1 | always |
| Localization | 1 | always (quality fix, not opt-in) |
| Cinematic brief | 1 | opt-in only |
| Coherence check | 0 | free |
| **Total** | **2–3** | |

---

## Mystery JSON schema

Every generated mystery is a dict with these top-level keys:

```json
{
  "title": "string",

  "setting": {
    "location": "string",
    "time_period": "string",
    "environment": "string",
    "description": "2–3 sentences — MUST explain why suspects cannot leave"
  },

  "crime": {
    "type": "string",
    "what_happened": "string",
    "when": "string",
    "initial_discovery": "string"
  },

  "characters": [
    {
      "name": "string",
      "role": "victim | suspect | detective | witness",
      "occupation": "string  — explains their presence in the closed world",
      "motive": "string  — specific stake; never blank for suspects",
      "alibi": "string  — specific location, activity, and corroborating detail",
      "secret": "string  — 2-sentence concrete fact anchoring interrogation"
    }
  ],

  "evidence": [
    {
      "id": "E1",
      "name": "string",
      "description": "string  — what it is, where found, what it initially suggests",
      "type": "physical | testimonial | circumstantial | documentary",
      "relevance": "critical | supporting | red_herring"
    }
  ],

  "solution": {
    "culprit": "string",
    "method": "string",
    "motive": "string",
    "key_evidence": ["E1", "E2"],
    "how_to_deduce": "step-by-step logic chain (3+ steps)"
  },

  "gameplay_notes": {
    "difficulty": "EASY | MEDIUM | HARD",
    "estimated_playtime": "string",
    "key_twists": ["string"]
  },

  "_provenance": { ... },     // recipe dict — which corpus parts were used
  "_coherence": {             // written after check_mystery() runs
    "passed": true,
    "blocking": 0,
    "warnings": 2,
    "witness_gaps": []
  },
  "_meta": {
    "num_players": 4,
    "setting_input": "original user prompt"
  },

  "cinematic_brief": { ... }  // only present when opt-in was enabled
}
```

**Validation rules enforced by `coherence_validator.py`:**
- At least 2 physical evidence items
- At least 1 red-herring evidence item of type physical or documentary
- At least 2 critical evidence items
- Each suspect must have a non-blank alibi and motive
- Each suspect's secret must be ≥ 2 sentences
- `solution.key_evidence` must reference ≥ 2 evidence IDs
- `solution.how_to_deduce` must contain ≥ 3 reasoning steps
- `setting.description` must explain the isolation mechanic

---

## Localization pass

**Module:** `localization.py` — shared by `app.py` and `cli.py`

**Always runs** — it's a quality fix, not an opt-in. Anachronistic names are immersion-breaking.

### Three-tier caching strategy

| Tier | Condition | API calls | Token cost |
|---|---|---|---|
| **Skip** | Modern / contemporary setting | 0 | 0 |
| **Cache hit** | Era rules already on disk | 1 (compact) | ~900 tokens |
| **Cache miss** | First mystery for this era | 1 (derives + applies rules) | ~1,200 tokens |

vs. the old approach (full JSON round-trip): ~10,000 tokens every time.

**Compact mapping approach** — instead of asking Claude to rewrite the full mystery JSON
(~5,000 tokens in, ~5,000 tokens out), Claude returns only a name mapping:
```json
{"name_map": [{"old": "Dr. Pemberton", "new": "Alexios the Physician", "old_occ": "Doctor", "new_occ": "Physician"}]}
```
Python does the substitution (`localization._apply_name_map`), using word-boundary regex
and longest-name-first ordering to prevent substring collisions.

**Era ruleset cache** — stored in `mystery_database/localization_cache/<era_key>.json`:
```json
{
  "name_examples": {"male": ["Gaius", "Marcus"], "female": ["Livia", "Claudia"]},
  "occupation_map": {"doctor": "physician", "lawyer": "advocate"},
  "forbidden_titles": ["Mr.", "Ms.", "Dr."],
  "allowed_titles": ["Senator", "Tribune", "Consul"],
  "pun_style": "Latin-ified descriptive names (Vidiomnius, Mendaximus)",
  "notes": "Aristocrats: nomen+cognomen. Commoners: single name."
}
```
Generated on first use of a setting, loaded on all subsequent uses. The cache grows
automatically as more settings are explored — zero maintenance required.

**Modern-era skip** — if `setting.time_period` contains "present day", "2020s",
"near future", etc., the localization call is skipped entirely (modern English names
are already appropriate). Detected by `localization._is_modern(setting)`.

**UI / CLI feedback** — the spinner label tells you which tier fired:
- `"Localization: modern setting — skipped"`
- `"Localizing names (era rules cached)..."`
- `"Localizing names and occupations (building era cache)..."`

**What it changes:**
- Character names → era/culture appropriate (no "Dr. Pemberton" in Ancient Athens)
- Occupations → period equivalents ("CEO" → "Merchant Prince", "Doctor" → "Healer")
- Honorifics and titles → era-correct ("Mr." has no place in Ancient Rome)
- All text fields that contain names: secrets, alibis, motives, evidence descriptions, title
- Minor characters may receive playful period puns (encouraged, not mandatory):
  - A Roman witness named "I Saw Everything" → "Vidiomnius"
  - A gossipy Harlem bystander → "Tells-It-All Thomas"
  - One or two per mystery maximum — witnesses and minor suspects only

**What it does NOT change:**
- Plot, culprit identity, evidence logic, solution
- Internal fields: `_provenance`, `_coherence`, `_meta`, `cinematic_brief`

**Setting-to-name conventions (guidance for the prompt):**

| Setting | Name style | Occupation examples |
|---|---|---|
| Ancient Greece/Rome | Single name or nomen+cognomen | Physician, Senator, Tribune, Merchant |
| Ottoman Empire | Arabic/Turkish given names | Kadi (judge), Bey, Effendi, Merchant |
| Medieval Europe | Given name + epithet | Blacksmith, Steward, Apothecary, Knight |
| Victorian Britain | Title + surname | Inspector, Dr., Rev., Lady |
| 1920s Harlem | Nickname-friendly | Numbers runner, Club owner, Doorman |
| Present day | No constraint | Modern titles fine |
| Sci-fi / future | Invent plausibly | Any era or invented culture |

---

## Cinematic brief schema

One `_generate_cinematic_brief()` call produces two separate outputs, stored as two
separate top-level keys on `mystery_dict` — not nested inside each other:

- **`mystery_dict["opening_narration"]`** — a string, 3–5 sentences of atmospheric prose.
  Player-facing: meant to be displayed or read aloud at the start of the game. No spoilers,
  no camera/shot direction — just the scene.
- **`mystery_dict["cinematic_brief"]`** — a dict, drop-in prompt for AI video generators
  (Sora, Runway Gen-3, Pika). Technical shot/lighting/sound direction. Hidden from
  players — prepared for future video generation, not something to show them directly.
  Covers the opening 15–30 second sequence only, no spoilers.

```json
{
  "logline": "One sentence. Visual, urgent, present tense. Under 20 words.",

  "opening_shot": "Establishing shot — lens, light, movement, no dialogue. 2–3 sentences.",

  "crime_reveal_shot": "The discovery moment — camera angle, reaction, sound. 2–3 sentences.",

  "atmosphere_tags": ["neon-soaked", "claustrophobic", "frozen silence"],

  "sound_design": "What the audience hears before any dialogue. One sentence.",

  "cast_visuals": [
    {
      "name": "character name",
      "appearance": "Clothing, posture, distinguishing detail. One sentence.",
      "first_seen_doing": "Their first on-screen action. One sentence."
    }
  ],

  "title_card": "The text overlay that ends the opening sequence."
}
```

Both outputs come from the same Claude call (one API call total, not two) — the point of
splitting them into two fields is presentation (one for players, one hidden for a future
video pipeline), not cost.

### How to use with a video API (future wiring)

```python
brief = mystery_dict["cinematic_brief"]

# Runway Gen-3 example
payload = {
    "prompt": f"{brief['opening_shot']} {brief['atmosphere_tags']}",
    "duration": 10,
}

# Sora example
payload = {
    "prompt": brief["opening_shot"],
    "style": ", ".join(brief["atmosphere_tags"]),
}
```

The schema is intentionally stable — wire once, use with any video provider.

---

## Where the cinematic brief is triggered

### In the UI (`app.py`)

```
user_prompt  text input
cinematic_on = st.checkbox("Generate cinematic brief", value=False)
                                                        ^^^^^^^^^^^
                                                        OFF by default

[Generate Mystery] button
  → generate_mystery()          # 1 Claude call always
  → check_mystery()             # free, always
  → if cinematic_on:
      generate_cinematic_brief() # 1 extra Claude call, opt-in only
```

The brief is shown in a collapsible expander "Cinematic Brief (video prompt)" below the
coherence badge in the left column.

### In the CLI (`cli.py`)

```bash
python cli.py generate --setting "..." --cinematic   # opt-in flag
```

---

## Room-first lobby flow (prompt suggestions before generation)

**Why it exists:** the old flow required a mystery to already exist before a room could be
created (`POST /games/create` took a `mystery_slug`, loaded from a file on disk) — someone had to
generate a mystery first, then create a room around it. That doesn't support "everybody suggests a
prompt while the lobby is waiting, and the host's pick is what the group actually plays" — by the
time the room existed, generation had already happened. The room-first flow inverts the order:
the room opens empty, players suggest prompts while they wait, and generation is deferred until
the host actually starts.

### Sequence

```
POST /games/create  {host_name, difficulty}      -- no mystery_slug -> room opens with mystery: None
   |
   v
POST /games/{id}/join                             -- other players join the empty lobby
   |
   v
POST /games/{id}/prompts/submit  {player_id, prompt_text}
                                                    -- each player (host included) suggests a prompt;
                                                       resubmitting overwrites that player's own entry
   |
   v
POST /games/{id}/start  {player_id}                -- host only. Reads the HOST's own submission from
                                                       submitted_prompts, kicks off generation in a
                                                       background thread, returns {status: "generating",
                                                       job_id}. Poll GET /jobs/{job_id} the same way
                                                       /generate/async already works, or just wait for
                                                       the WebSocket broadcast below.
   |
   v
"mystery_ready" broadcast (or "mystery_generation_failed" on error)
                                                    -- game["mystery"] is now attached; clients can call
                                                       GET /games/{id}/mystery-brief and GET /lobby
                                                       normally from here on
```

Non-host players' submissions are **not discarded** — they stay in `game["submitted_prompts"]` for
the post-game "vote for what to play next" round (design only, not built yet — ties into the
end-game resolution work).

### Quick-start / dev path (unchanged)

`POST /games/create` still accepts an optional `mystery_slug` — if given, it skips prompt
collection entirely and attaches an already-generated mystery immediately, exactly like the old
behavior. `POST /games/{id}/start` on a room created this way just broadcasts `game_started` with
no generation step, same as before this change. Useful for local testing without waiting on a full
lobby.

### Implementation notes

- `_run_generation_pipeline()` is the shared core (generate → localize → check coherence → optional
  cinematic brief → save) extracted out of the pre-existing `/generate/async` job runner. Both the
  plain job path (`_run_generation_job`) and the new game-attached path
  (`_run_game_generation_job`) call it — no duplicated pipeline logic.
- `_run_game_generation_job()` differs from the plain version only in what happens after the
  pipeline finishes: it attaches the result to `game["mystery"]` under `_games_lock` and broadcasts
  `mystery_ready` (or `mystery_generation_failed`) instead of just marking the job done.
- Any endpoint that reads `game["mystery"]` needs to handle `None` explicitly now — `mystery_brief`
  returns `400` with a clear "not yet generated" message rather than crashing; `get_lobby` returns
  `title`/`setting` as `null` and adds `submitted_prompt_count` / per-player `has_submitted_prompt`
  so lobby UIs can show waiting-room progress.

---

## Multiplayer lockstep round system

New synchronization layer alongside the original per-player async `phase` field on
each `game["players"][player_id]` — that field, and the endpoints that gate on it
(`/interrogate-witness`, `/investigate-area`, `/follow-lead`, `/share-phase`), are
still live and untouched. The lockstep system is additive: `game["stage"]` and
`game["round"]` are new top-level keys on the game session dict, currently used by
the witness interrogation flow only. Investigation and lead phases still run on the
legacy per-player system until they're ported (tracked as separate future work).

### Why it exists

The original witness flow answered each player's question in total isolation — no
memory of what the same witness had already told anyone else in the session, and no
bound on how many separate LLM calls a round could cost (N players × M questions
each). The lockstep model batches a whole round's questions into one generation call
per witness instead, which fixes both problems at once: one call has full visibility
into everything asked that round, and cost no longer scales per-question.

### Stage sequence

```
submitting -> generating -> revealed
```

- **submitting** — a round is open; players are POSTing their payload in.
- **generating** — every expected player has submitted (or the timeout fired);
  round-type-specific generation is running in a background thread.
- **revealed** — generation finished; `game["round"]["result"]` is populated and
  broadcast to everyone.

### Round shape (`game["round"]`)

```json
{
  "round_type": "witness",
  "expected_players": ["player_id", "..."],
  "submissions": {"player_id": {"...": "round_type-specific payload"}},
  "opened_at": 1735689600.0,
  "timeout_seconds": 90,
  "metadata": {"character_name": "Voss"},
  "candidate_questions": ["...", "..."],
  "result": null
}
```

`expected_players` is snapshotted when the round opens — a player who joins mid-round
is not included and picks up starting with the next round opened.

### Endpoints

| Endpoint | Who | What |
|---|---|---|
| `POST /games/{id}/round/open` | host only | Opens a round of a given `round_type`, with optional `metadata`. Rejects if a round is already open. |
| `POST /games/{id}/round/submit` | any player | Submits this round's payload. Once every expected player has submitted, auto-advances to `generating` and kicks off generation. |
| `GET /games/{id}/round/status` | any | Waiting-room view: stage, who's submitted, who's pending, seconds left. Also runs the lazy timeout check. |
| `POST /games/{id}/round/resolve` | server-side | Attaches a result and reveals it. Called by round-type generation code, not meant as a direct player action. |

Timeout handling is lazy, not a background sweep: `_check_round_timeout()` runs at
the top of `submit` and `status`, so an expired round with missing players
auto-advances to `generating` the next time anyone touches the round (missing
players are recorded in the `round_generating` broadcast, not silently dropped).

### WebSocket events

`round_opened`, `player_submitted`, `round_generating` (carries `timed_out` and
`missing_players`), `round_revealed` (carries the full `result`).

### Extending to a new round_type

Two dispatch points, both keyed by `round_type`:

- **`_ROUND_PREP`** — optional hook run when a round opens; returns extra fields to
  merge into the round dict (e.g. witness rounds attach `candidate_questions`).
- **`_ROUND_GENERATORS`** — required to actually produce a result; run in a
  background thread once the round reaches `generating`, then feeds straight into
  `_resolve_round()`. A round_type with no registered generator just never resolves
  past `generating` — nothing errors, but nothing happens either, so register one
  before wiring up a new round_type's endpoints.

### `round_type: "witness"` — the one built so far

- **Submission payload:** `{"questions": ["...", "..."]}` — up to
  `_DIFFICULTY_CONFIG[difficulty]["questions_per_round"]` (3/2/1 for EASY/MEDIUM/HARD),
  enforced in `submit_round`. Each question can be one of the `candidate_questions`
  pick-list (attached at round-open, role-aware — see `_CANDIDATE_QUESTIONS`) or free
  text — hybrid input, not validated against the candidate list.
- **Generation (`_generate_witness_scene`):** pools every submitted question across
  all players, deduping by normalized text so the same question asked by multiple
  players collapses into one entry with every asker attributed. One Claude call
  covers the whole pool and returns a scene bounded to 2–3 sentences regardless of
  how many questions were pooled, plus a private answer per pooled question. Carries
  the evasion/anti-spoiler instruction ("do NOT directly reveal the real culprit")
  that the old multiplayer witness endpoint was missing.
- **Result shape:**
  ```json
  {
    "scene": "shared dramatized text, same length regardless of pool size",
    "scene_covers": ["question text that made it into the scene", "..."],
    "answers": {"player_id": [{"question": "...", "answer": "..."}]}
  }
  ```
  No random cross-player distribution: a player always gets 100% of the answers to
  their own submitted questions, and the shared `scene` — covering whichever
  questions multiple players asked in common, plus one authored flourish — is what
  everyone sees together. Anything neither yours nor scene-covered simply isn't part
  of what you have; this was a deliberate simplification over the original "70% of
  the remaining answers, randomized" pitch, chosen for legibility.
- **Secondary witness:** same `round_type: "witness"`, just opened a second time
  with a different `character_name` in `metadata` — no separate mechanism needed.

### Accusation resolution

Not part of the lockstep round mechanism above — accusing is a race, not a
synchronized round, so it's a standalone always-available action rather than a
`round_type`. Two new fields on the game session: `game["winner"]` (`player_id` or
`None`) and `game["accusations"]` (full public history: `{player_id, accused_name,
correct, ts}`).

`POST /games/{id}/accuse` — `{player_id, culprit_name}`. Checked server-side against
`mystery["solution"]["culprit"]` (normalized the same way as question deduping —
case/whitespace-insensitive) — the solution is never sent to clients (see
`/mystery-brief`, which explicitly strips it), so this is the only way a client can
actually learn whether a guess was right. First correct accusation wins; the game is
rejected with `400` for any further attempt once `winner` is set. Race-safety: the
win is claimed inside `_games_lock`, re-checking that `winner` is still `None` at the
moment of the correct guess — so if two players guess correctly close together, only
the one that actually acquires the lock first wins, not just whichever request
arrived first. No elimination on a wrong guess — a player can keep trying.

Every attempt — right or wrong — broadcasts `accusation_made` to the whole room
(`{player_name, accused_name, correct}`); a winning guess additionally broadcasts
`game_won` (`{winner_player_id, winner_name, solution, plot_reveal, winner_findings}`).
`GET /games/{id}/result` gives the identical payload as a snapshot, for a client that
missed the broadcast (late join, reconnect) — `{"solved": false}` before anyone's won,
otherwise the same shape as `game_won` minus the broadcast-only framing.

### End-of-game resolution reveal (`plot_reveal` + `winner_findings`)

**Explicitly zero new AI calls** — the owner tabled all generative-AI video/text work for
this screen to save cost and get the UI's look-and-feel right first. Both fields are pure
reformatting of content that already exists by the time the game is won:

- **`plot_reveal`** (`_format_plot_reveal()`) — the mystery's own `solution` (already
  generated once, at mystery creation) reshaped for display: `culprit`, `method`, `motive`,
  `how_to_deduce` (the string reasoning chain), and `key_evidence` — resolved from
  `solution.key_evidence`'s bare evidence IDs into the full `{id, name, description}`
  objects, so the reveal can actually name what was found instead of citing `"E1"`.
- **`winner_findings`** (`_winner_findings_summary()`) — the winning player's own
  `witness_findings` / `investigation_findings` / `lead_findings`, exactly as collected
  during play. Deliberately shown to the **whole room**, not kept private to the winner —
  the point of this screen is the shared reveal of *how* they got there, not just *that*
  they won.

**Video stays a placeholder for now.** The client should render a static
`"Video Scene Will Play Here"` panel where a future resolution-video clip would go — no
backend field for it, since there's nothing generated to point to yet. When video work
actually gets picked back up, the natural shape (mirroring the opening scene's
`_generate_cinematic_brief()` two-output split — see "Cinematic brief schema" above) is a
`_generate_resolution_video_brief()` that reuses `plot_reveal`'s already-resolved content as
its prompt input, rather than re-deriving anything from `solution` a second time. Not built;
not scoped until the owner decides to un-table video generation.

### Post-game prompt voting and same-room replay (`prompt_vote`)

Closes the loop opened by the room-first lobby flow above: the prompts nobody used this game
(`game["submitted_prompts"]`, minus whoever's drove the mystery just played — tracked in
`game["used_prompt_player_id"]`) become the candidate list for what to play next. **Zero AI calls**
— tallying votes is pure Python, same cost discipline as the rest of this screen.

**`round_type: "prompt_vote"`** — a normal lockstep round (`POST /round/open` →
`POST /round/submit {vote_for_player_id}` → auto-resolves once everyone's voted or the round times
out), registered the same way `"witness"` is:
- **Prep** (`_prompt_vote_prep`) — candidates are every `submitted_prompts` entry except
  `used_prompt_player_id`'s. Attached to the round as `candidates: [{player_id, name,
  prompt_text}]`.
- **Generator** (`_tally_prompt_vote`) — counts `vote_for_player_id` across submissions. Majority
  wins outright (`{tie: false, chosen_player_id}`). On a tie, the rule is deliberately not "the
  game's winner always decides":
  - Winner is among the tied candidates **and didn't also win the mystery immediately before this
    one** → they get to pick, `{tie: true, tied_player_ids, awaiting_tiebreak_from: winner_id,
    chosen_player_id: null}` — the vote sits in this state until a human resolves it.
  - Winner also won the previous mystery in this room (checked against `game["win_history"]`), or
    isn't even one of the tied candidates → **auto-resolved randomly** instead,
    `{tie: true, auto_resolved: true, chosen_player_id, reason}`. This is the owner's explicit
    "I don't want the same winner to keep picking" rule — tie-break power doesn't compound onto
    whoever's already winning.

**`POST /games/{id}/prompts/tiebreak`** `{player_id, chosen_player_id}` — only usable while a
result has `awaiting_tiebreak_from` set and no `chosen_player_id` yet (the auto-resolved case needs
no human step and this endpoint rejects it). Restricted to whichever player the generator named as
the tie-break authority; `chosen_player_id` must be one of `tied_player_ids`.

**`POST /games/{id}/next-mystery/start`** `{player_id}` (host only) — once the vote has landed on a
`chosen_player_id` (clean majority or a resolved tie), this is the "same room persists across
mysteries" mechanic: `_reset_game_for_next_mystery()` records the concluded game's winner onto
`game["win_history"]`, clears everything scoped to a single mystery (`mystery`, `stage`, `round`,
`winner`, `accusations`, both pools, every player's phase/budgets/findings back to fresh), and kicks
off generation from the chosen prompt via the same `_run_game_generation_job()` piece 1 already
built — **same `game_id`, same players, nobody rejoins.** That persistence is the point: it's what
gives "vote for what to play next" any actual pull to keep the same group together, rather than
everyone having to re-form a new room from scratch.

---

## Coherence validator — what it checks

`coherence_validator.check_mystery(mystery_dict)` runs three check families:

| Family | What it checks | Cost |
|---|---|---|
| P1 causal chain | crime → victim → closed_world → culprit → resolution unbroken | free |
| Witness foundation | alibi / motive / secret depth per character | free |
| Scene investigation | physical evidence, red herrings, evidence variety | free |

Returns `CoherenceReport`:
- `passed` — True if zero blocking issues
- `blocking_count` — issues that must be fixed before gameplay
- `warning_count` — issues worth reviewing but non-blocking
- `witness_gaps` — list of characters with shallow interrogation anchors

`check_parts(parts)` is a cheaper pre-generation check (runs on the sampled parts
before the Claude call, catches missing part types early).

---

## Part registry — how parts are sampled

`part_registry.py` holds 1,469 atomized parts extracted from public-domain mystery fiction.

Each part has:
- `part_type` — one of the P1–P4 taxonomy types (crime_type, victim_profile, motive, etc.)
- `source_id` — which source text it came from (e.g. `C` for Christie corpus)
- `part_index` — position within that source
- `content` — the extracted text
- `setting_tags` — semantic tags used for compatibility matching

`sample_for_generation(target_setting=...) → (List[MysteryPart], Recipe)` picks one part
per required type, weighted toward setting-compatible parts.

The `Recipe` object serialises as `"C(4)+F(2)+A(6)+..."` — a reproducible fingerprint of
which parts were used. Stored at `mystery_dict["_provenance"]["recipe"]`.

---

## Extraction protocols (P1–P4)

| Protocol | Taxonomy | What it extracts |
|---|---|---|
| P1 Skeleton | C1–C6 | Crime, victim, closed world, culprit, motive, resolution |
| P2 Architecture | M1–M8 | Narrative structure, pacing, reveal mechanics |
| P3 Craft | F1–F8 | Prose technique, dialogue, atmosphere |
| P4 Texture | F9–F12 | Sensory detail, micro-tensions, period colour |

Run P1 first. Only escalate to P2/P3 if P1 quality is high. P4 is for corpus enrichment,
not for generation gating.

```bash
python cli.py extract --protocol P1      # cheapest, run first
python cli.py extract --protocol P1P2    # full corpus run (~359 books)
```

---

## Craft-grounding retrieval (RAG layer)

**Status:** Built and wired in (Session 22). This section is written for someone with zero
prior context on this repo — read it start to finish before touching `craft_grounding.py` or
any of its four call-sites in `server/main.py`.

### The problem this solves

`RESEARCH_FINDINGS.md`, `SCREEN_CRAFT_FINDINGS.md`, and `PARTY_CRAFT_FINDINGS.md` (see
`SOURCING_METHODOLOGY.md` for how they're built and how a new one gets added) ground this
project's mystery-writing taxonomy in real craft sources — novelists, screenwriters, and
party-game designers explaining, in their own words, *how* to plant a fair clue, build a red
herring, or keep a witness's answers consistent. Before Session 22, those documents were pure
research — real, carefully-sourced, and completely inert. Nothing in the running system ever
read them. Every generation call (the initial mystery, a witness's answers, a crime-scene
search, a lead follow-up) was writing dialogue and narration with zero craft guidance behind it
beyond whatever the underlying LLM already knew.

Separately, an audit of the extraction pipeline (`part_registry.py`) turned up two related
findings worth knowing as background:
1. Every P1-only-depth corpus source (all 12 curated novels, all 63 anthology stories from
   Session 20) can only ever populate 3 of the registry's 8 sampling axes, because the
   registry's atomizer expects P2-tier keys a P1 extraction never produces.
2. Even a fully P1+P2 source has craft-relevant fields (`clue_fairness`, `media_and_audience`,
   `investigator_wound`) that are extracted and then never read by the registry at all, for any
   source, at any depth.

Those two findings motivated *this* build but describe a different, still-open piece of work
(fixing `part_registry.py`'s field mapping / re-extracting at deeper protocol levels — not done
as part of this section). What follows is specifically the retrieval layer that makes the three
craft-grounding docs actually influence generation, independent of that other work.

### Design principles (read before "simplifying" anything)

These were explicit decisions made in discussion with the owner, not defaults an implementer
picked alone:

1. **The markdown is the only source of truth. The index is a disposable, regenerated cache.**
   `craft_grounding.build_index()` re-parses every `*_CRAFT_FINDINGS.md` / `RESEARCH_FINDINGS.md`
   file at the repo root into `mystery_database/craft_grounding_index.json`, automatically,
   whenever a source doc's mtime is newer than the cached index. **The index file is gitignored
   on purpose** — see `.gitignore` — because a committed copy could go stale across a fresh
   clone (`git checkout` doesn't preserve original file mtimes, which the staleness check relies
   on). Nobody should ever hand-edit that JSON file; it will just be silently overwritten.
2. **Retrieval is a local, zero-cost lookup — never an LLM call.** All the "intelligence" here is
   a plain dict filter over pre-parsed entries. Adding craft grounding to a generation call must
   never turn one API call into two — this was an explicit cost-consciousness requirement from
   the owner, given that `_investigate_area_with_ai` and `_follow_lead_with_ai` already fire live,
   repeatedly, per player, per area/lead, on `claude-sonnet-4-6` (not a cheap model).
3. **Not bounded, not immutable.** Paste new full-text findings into an existing doc, or drop a
   brand-new `*_CRAFT_FINDINGS.md` doc into the repo root following the same table convention
   (see "Adding a new craft doc" below), and the very next generation call picks it up
   automatically. No code change is needed for new *content* — only for a genuinely new *table
   shape* the parser hasn't seen before.
4. **Confidence tiers gate what reaches a live prompt.** The companion docs already tag entries
   by sourcing confidence (see `SOURCING_METHODOLOGY.md`'s confidence-tier discipline).
   `get_craft_guidance()` defaults to excluding the lowest tier (`secondary`) so a shaky or
   merely-anecdotal finding never silently governs what a witness actually says.
5. **Every retrieval is auditable.** This was the owner's specific ask, especially valuable
   during early playtesting: every call that injects craft guidance also records exactly which
   entries it used, in a structured citation form, attached to whatever that call produced. If a
   generated mystery or a witness's answer reads oddly, you can trace it back to the specific
   craft citation(s) that informed it — see "Where the audit trail lives" below.

### Data model

`craft_grounding.GuidanceEntry` — one row of craft guidance, parsed from a companion doc's table:

| Field | Meaning |
|---|---|
| `doc` | Source filename, e.g. `"SCREEN_CRAFT_FINDINGS.md"` |
| `section` | Nearest preceding markdown heading, e.g. `"Alfred Hitchcock"` |
| `concept` | Short label, e.g. `"Minimize actual lies; let circumstance do the misdirecting"` |
| `insight` | The full quote/explanation |
| `taxonomy_tags` | P1–P4 codes this maps to, e.g. `["M2"]` — pulled from a "Maps to taxonomy" column |
| `game_system_tags` | Fixed mechanics categories `PARTY_CRAFT_FINDINGS.md` uses instead, e.g. `["Interrogation Phase"]` — an entry can have either kind of tag, both, or neither |
| `confidence` | `"canonical"` (the taxonomy's own C/M/F definitions) \| `"verified"` (full text confirmed) \| `"primary"` (default) \| `"secondary"` (third-party analysis, or `PARTY_CRAFT_FINDINGS.md`'s explicitly-non-prescriptive "Player Experience" section — see below) |
| `source` | Raw citation text/URL from the doc |

### How parsing works, precisely

`craft_grounding._parse_doc()` walks a markdown file line by line, tracking the nearest heading
(for the `section` field) and the nearest **H2** heading separately (see the reception-evidence
rule below), and recognizes two table shapes via `_classify_columns()`:

1. **`RESEARCH_FINDINGS.md`'s taxonomy-definition table** — header exactly `# | Part | Who Names
   It`. Each row is one taxonomy code's own canonical definition (e.g. C1, M3, F8), tagged
   `confidence="canonical"` — the highest tier, since these are the taxonomy's own foundational
   text, not a secondary finding about it.
2. **A per-creator findings table** — header `Concept | Insight | Maps to taxonomy|game system |
   Source` (either "maps to" wording is accepted). `taxonomy_tags` are extracted from the "Maps
   to" column via the regex `\b([CMF]\d{1,2})\b`; `game_system_tags` are matched against the
   fixed list in `craft_grounding.GAME_SYSTEM_CATEGORIES` (kept in sync with
   `PARTY_CRAFT_FINDINGS.md`'s "Mapping convention" section — update both together if that list
   changes).

Any table whose header doesn't match one of these two shapes is **silently skipped**, not
treated as an error — so a reference table that isn't meant to be findings (there aren't any
today, but nothing stops one being added) doesn't pollute the index. If a future companion doc
introduces a genuinely new table shape, extend `_classify_columns()`.

**Confidence-tag detection** (`_infer_confidence()`) reads tags like `[full text verified]` or
`[third-party analysis]` from *any* of the Concept/Insight/Source columns — these tags have
shown up in different columns across the existing docs (e.g. McQuarrie's entries carry
`**[full text verified]**` inline in the Concept column itself), so all three are checked. The
tag markup is then stripped from the displayed `concept` text (`_clean_concept()`) — the tier is
already captured structurally in `confidence`, so leaving the raw bracket tag in would just be
noise in an injected prompt.

**The Part 1 / Part 2 reception-evidence rule.** `PARTY_CRAFT_FINDINGS.md` explicitly splits
"Part 1 — Design & Mechanics Authority" (designers explaining their own reasoning) from "Part 2
— Player Experience" (testimonials/reviews — that doc's own text says to treat these as
"data... not as prescriptions the way Part 1's entries are"). The parser respects that: any
table whose nearest **H2** ancestor heading matches `player experience|reception`
(case-insensitive) has every row in it forced to `confidence="secondary"`, regardless of that
row's own inline tag — which excludes it from a live prompt under the default `min_confidence=
"primary"` cutoff, while still keeping it in the index/audit trail for anyone who explicitly
lowers the bar. **If a future companion doc wants this same split, name its reception section's
H2 heading with "Player Experience" or "Reception" in it** — no code change needed.

### Retrieval API

```python
get_craft_guidance(
    taxonomy_tags: list[str] | None = None,
    game_system_tags: list[str] | None = None,
    min_confidence: str = "primary",
    max_items: int = 5,
) -> list[GuidanceEntry]
```

OR-matches on tags (an entry qualifies if it matches *any* requested taxonomy code or
game-system category), filters by confidence rank, then sorts highest-confidence-first with a
stable tiebreak (`doc`, `section`, `concept`) so the same call against the same index always
returns the same guidance — useful when debugging why a particular generation came out the way
it did.

`format_guidance_block(entries)` renders entries as a prompt-ready `"CRAFT GUIDANCE (...): - ..."`
text block, returning `""` (not a header with zero rows) when there's nothing to inject, so
callers can always concatenate it straight into a prompt without a conditional.

`guidance_provenance(entries)` returns the structured citation list (`concept`, `doc`,
`section`, `confidence`, `source` per entry) used for auditing — see below.

### The four call-sites, and why each gets the tags it gets

| Call-site (`server/main.py`) | Tag source | Tags | Why |
|---|---|---|---|
| `_generate_mystery_dict()` | Derived per-call from `craft_grounding.PART_TYPE_TO_TAXONOMY`, mapped from whatever `part_registry.py` actually sampled for this specific mystery (via `_craft_guidance_for_parts()`) | Varies — only the axes this mystery drew from | The one call whose relevant craft axes change every time, because the sampled recipe changes every time. Injecting a fixed tag set here would either miss what's relevant or inject irrelevant guidance for axes this mystery isn't using. |
| `_generate_witness_scene()` | Fixed, in `craft_grounding.CALL_SITE_TAGS["witness_scene"]` | `M2` (Red Herring), `M3` (Clue Fairness), `F3` (Unreliable Frame) + `"Interrogation Phase"`, `"Social Dynamics"` | These are the craft axes that govern *how a witness should mislead and stay fair* during interrogation — not plot-construction axes. Fixed because every witness-scene call needs the same kind of dialogue-craft guidance, regardless of which specific mystery is being played. |
| `_investigate_area_with_ai()` | Fixed, in `CALL_SITE_TAGS["investigate_area"]` | `F4` (Setting as Constraint), `F5` (Evidence Type) + `"Investigation/Scene Phase"` | Scene/evidence narration craft — e.g. Murder Mystery Co's "clues framed as story, not raw data" finding, which is specifically about *how to describe a found clue*, not about plot mechanics. |
| `_follow_lead_with_ai()` | Fixed, in `CALL_SITE_TAGS["follow_lead"]` | `M2` (Red Herring), `M5` (Alibi), `C4` (Culprit + Motive) + `"Investigation/Scene Phase"` | Lead-reveal craft — what a lead should actually disclose and how it should mislead when it's a red herring. |

**Resolved caveat (Session 23):** `part_registry.py`'s axis 8 used to be named `"evidence_type"`
despite holding alibi content — the extraction key `"alibi"` mapped there, not anything about
evidence type. Session 23 renamed the axis itself to `"alibi"`, so `PART_TYPE_TO_TAXONOMY` now
reads `"alibi": ["M5"]` directly, no name/content mismatch. Same session also extended
`_atomize_extraction()`'s `KEY_TO_IDX` to stop silently discarding `victim`, `resolution`,
`investigator`, `investigator_wound`, and `clue_fairness` (previously extracted, never sampled —
see the Session 22 efficiency audit above for how that was found). `media_and_audience` remains
deliberately unmapped — it's meta/format information, not a fit for any of the 8 crime-mechanic
axes. Full detail in `SESSIONS.md` Session 23.

### Where the audit trail lives

Craft guidance is never silently applied — every call that uses it records exactly what it used,
but *where* that record lands differs by call-site, deliberately:

- **`_generate_mystery_dict()`**: stored in `mystery_dict["_provenance"]["craft_guidance"]`,
  alongside the existing part-sampling recipe. Already covered by the existing stripping in
  `GET /games/{game_id}/mystery-brief` (which drops the whole `_provenance` key before sending to
  clients) — so this never leaks to players, with no new code needed for that.
- **`_generate_witness_scene()`**: the generator returns a `"_craft_guidance"` key alongside
  `scene`/`scene_covers`/`answers`, but `_resolve_round()` pops it off *before* storing
  `round_["result"]` (the dict that gets broadcast to every player over WebSocket) and stashes it
  instead on `round_["_craft_guidance"]` — server-side only. This one needed explicit handling
  (unlike the mystery dict) because round results are broadcast to the whole room, not returned
  to a single requester, and craft-guidance citations are internal tooling, not player content.
- **`_investigate_area_with_ai()` / `_follow_lead_with_ai()`**: both now return
  `(findings_text, craft_guidance_provenance)` tuples. The citation list is stored in the
  player's own `investigation_findings` / `lead_findings` entry **and** included directly in the
  HTTP response (`"craft_guidance"` key). This is safe to expose to the calling client, unlike
  the witness-round case, because these are private per-player HTTP responses, never broadcast to
  the room — there's no other player who could see it.

During early playtesting, this means you can always answer "why did this narration/dialogue turn
out this way?" by reading the relevant `_craft_guidance` / `craft_guidance` field next to
whatever it produced — no separate logging system needed.

### Extending this system

- **Adding a new craft-grounding doc** (e.g. the still-open true-crime-podcast sourcing from
  `CLAUDE.md`'s to-do): write it as `SOMETHING_CRAFT_FINDINGS.md` at the repo root, following the
  `Concept | Insight | Maps to taxonomy` (or `Maps to game system`) table convention already used
  by `SCREEN_CRAFT_FINDINGS.md` / `PARTY_CRAFT_FINDINGS.md`. Nothing else to do — the glob in
  `craft_grounding._SOURCE_DOC_GLOBS` picks it up automatically, and the index rebuilds itself on
  next use.
- **Adding a new call-site**: add an entry to `craft_grounding.CALL_SITE_TAGS` with the taxonomy
  and/or game-system tags that describe what that call is actually generating (not just "more
  guidance is better" — pick tags the way the table above reasons through each existing one), call
  `get_craft_guidance(**CALL_SITE_TAGS["your_new_site"])`, inject the formatted block into the
  prompt, and decide where the provenance should land (broadcast to everyone? private to one
  player? — follow the reasoning in "Where the audit trail lives" above, don't default to
  broadcasting it).
- **Adding a new taxonomy code**: if a "new concept flagged" entry in one of the companion docs
  (see each doc's own "New concepts flagged" sections) ever gets formalized into a real
  `extraction_protocols.py` code, it becomes retrievable automatically the next time the index
  rebuilds — no `craft_grounding.py` change needed, since taxonomy tags are extracted from doc
  text at parse time, not hardcoded.

### Verifying it's working

```bash
python3 -c "
import craft_grounding as cg
entries = cg.build_index(force=True)
print('total entries:', len(entries))
for name, tags in cg.CALL_SITE_TAGS.items():
    print(name, '->', len(cg.get_craft_guidance(**tags)), 'entries')
"
```

If a doc was just edited and the count looks wrong, delete
`mystery_database/craft_grounding_index.json` and re-run — that file is a disposable cache (see
above), never the source of truth.

---

## Avatar system + player profiles (Phase 3e)

**Status:** Design locked (Session 16). Not yet implemented — see "What still needs building" below.

### Two-layer avatar model

Every player-facing portrait is the product of two independent, both-cacheable layers:

1. **Base look** — an era-appropriate portrait style/pose, generated once per `<era_key>`
   (same key as the localization cache) and shared across every mystery in that setting.
   10–15 base looks per era; floor of 12 to comfortably cover an 8-player lobby without repeats.
2. **Signature accessory** — a small, fixed prop (monocle, red scarf, pocket watch, ...) that
   persists with a *player*, not a mystery. Deliberately allowed to be anachronistic — the same
   monocle shows up whether they're a Roman senator or a 1920s jazz-club regular. It's the
   player's visual signature across every game they ever play, not part of the setting.

Combining the two is a prompt modifier, not a separate generation pipeline:
`base_look_prompt + accessory_clause`. The resulting portrait is cached under a compound key:

```
mystery_database/avatar_pool/<era_key>/<base_look_id>__<accessory_id>.png
```

Generated **lazily on first request** — same caching philosophy as the localization ruleset
cache. Nothing is pre-rendered for combinations nobody has asked for; a brand-new era crossed
with a brand-new accessory is the only case that pays full generation cost, and every later
player who shares either axis hits a cache.

**Image API:** FLUX via fal.ai (~$0.003/image), decided Session 14. Prompt-driven, not
photo-driven — avoids the moderation/liability surface of accepting user photos, and is what
makes a pre-generated shared pool possible at all (you can't pre-generate from photos nobody's
uploaded yet).

### Lobby-join flow

1. Player joins → if returning (`localStorage` token recognized), skip to step 4 with their
   existing `signature_accessory_id`.
2. New player → optional registration step: display name + one-time accessory pick from a fixed
   catalog (grid UI). **Skippable** — declining gets a random accessory and no persistent
   profile write, consistent with the existing zero-friction return-visit pattern.
3. Server upserts `mystery_database/player_history/<player_id>.json` (schema below).
4. Server offers 3 candidate portraits: 3 distinct `base_look_id`s for the mystery's `era_key`,
   each combined with the player's `accessory_id`. The player picks one; the chosen
   `base_look_id` is recorded on that game's `mysteries_played` entry.

Within one lobby, `base_look_id` assignment must avoid duplicates across players (visual
distinctness at the table) — `accessory_id` duplicates are fine and expected; it's identity,
not a lobby-unique slot.

### Cold start

The first lobby ever run in a brand-new `era_key` has an empty pool. Rather than blocking lobby
start on a live FLUX call, serve a static placeholder portrait (silhouette + accessory icon, no
AI call) for that one lobby while a background job seeds the pool — same async-job pattern
already built for mystery generation (`4235c7c`, "async job system + timeout + live progress").

### Player profile schema

`mystery_database/player_history/<player_id>.json`:

```json
{
  "player_id": "localStorage token, generated on first registration",
  "display_name": "string, player-chosen",
  "signature_accessory_id": "key into the fixed accessory catalog, e.g. \"monocle\"",
  "steam_id": null,
  "created_at": "ISO timestamp",
  "mysteries_played": [
    {
      "mystery_slug": "...",
      "era_key": "...",
      "base_look_id": "which of the 3 offered portraits they picked",
      "played_at": "ISO timestamp",
      "accused_correctly": true,
      "time_to_solve_seconds": 1830
    }
  ]
}
```

`steam_id` is reserved and unused until Phase 4 (GodotSteam) — the schema is forward-compatible
so the identity layer doesn't need a migration later.

### Accessory catalog (proposed — needs a sign-off pass, not final)

Static, curated, 16 entries to start (clean 4×4 grid in the picker UI). Expand the same way the
corpus grows — one addition at a time, no bulk churn:

```
monocle, red_scarf, pocket_watch, flower_crown, bow_tie, cracked_spectacles,
pipe, brooch, fedora, pearl_necklace, walking_cane, feather_boa,
signet_ring, eye_patch, silk_gloves, pinstripe_tie
```

### Open decisions resolved this session (defaults chosen — flag if wrong)

| Question | Default chosen | Reasoning |
|---|---|---|
| Mandatory or skippable registration? | Skippable | Matches existing zero-friction return-visit design; party games shouldn't gate on signup |
| Accessory permanent or editable? | Permanent | Identity/joke value, not a settings toggle |
| Max concurrent players sized for? | 8 | Jackbox-range lobby size; pool floor set at 12 base looks/era for headroom |
| Cold-start behavior? | Static placeholder, never block lobby start | Matches "no API call blocks a live game" principle used elsewhere |
| Identity scope | `localStorage` token now, `steam_id` reserved | Avoids a schema migration when Phase 4 lands |

### What still needs building (design only — none of this exists yet)

- `mystery_database/accessory_catalog.json` — the static catalog file
- Avatar pool generation script (fal.ai FLUX client, lazy-cache-on-request logic)
- `server/main.py` endpoints: player registration/upsert, avatar-pool fetch-or-generate,
  `mysteries_played` logging
- Godot: registration screen (name + accessory grid), 3-candidate portrait picker in `Lobby.tscn`
- Placeholder silhouette asset for the cold-start fallback

---

## API authentication

Priority order:
1. `ANTHROPIC_API_KEY` environment variable (local dev, HuggingFace Secrets)
2. Bearer token from `/home/claude/.claude/remote/.session_ingress_token` (CI / hosted runner)

See `extract_test_mysteries.py:_get_token()` for the reference implementation.

---

## Active branches

Branch status lives in `CLAUDE.md` (Active Branch section), not here — this file drifted out of
sync with reality once before (July 9, 2026 reconciliation) by duplicating that tracking.
Single source of truth: `CLAUDE.md`.
