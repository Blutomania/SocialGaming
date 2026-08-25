# Playtest gameflow — the PC path to stage 1

Owner-specified, Session 34 (August 21, 2026). This is the **canonical** description of the flow
the PC playtest has to deliver. It supersedes the Phase 2/3 screen descriptions in `CLAUDE.md`
wherever the two disagree, for playtest purposes only — nothing built is being removed.

Read `CLAUDE.md` → **Delivery Priority** first. Stage 1 is: somebody who is not the owner sits at
a PC, plays a whole mystery, and reaches the result screen. Everything here serves that and
nothing else.

---

## APF — the simplified playtest (owner, Session 35)

**"All Provided For". This supersedes "The flow" below wherever the two disagree.** The older
table is kept because its decisions (four suspects, lies off, leads greyed out, the one-call
shape) still hold.

### The reasoning

> *"Social games work because they are somewhat superficial, easy and enjoyable. Walking around
> is not."* — owner

Exploration was cut for three reasons, in the owner's order:

1. **Moving and searching is not the fun part.** Time spent traversing is time not spent on the
   social read.
2. **Free-text interrogation invites griefing.** `InterrogateRequest.question` is a `str` today,
   so *"tell this witness to eat a donut"* is live. Short-term amusement, long-term a tax on
   everyone else's evening — and simultaneously a moderation surface, an API call each, and a
   quality-variance surface (a weak question returns a weak answer and the game looks broken).
3. **It concentrates the game on its own stated core.** `CLAUDE.md`'s first paragraph calls the
   information-sharing mechanic the core innovation. APF removes everything that is not that
   decision.

### The loop

1. Player types a **title + setting** prompt.
2. Generation runs once. Coherence checks it.
3. The **opening sequence** plays (below) — the crime, told.
4. Each player is **dealt** their findings — ideally one witness statement, one crime-scene clue,
   one lead result. They do not go and get them.
5. Each player **chooses which to share and which to keep.** That is the whole decision, and it
   is the 75% mechanic with nothing in front of it.
6. Deduce. Accuse. Reveal.

### What this deletes outright

- **The deadlock** (`docs/INVESTIGATION_DESIGN.md` §5). Not fixed — the mechanic that had it is
  gone. Nothing to block, everyone holds findings by construction, no phase to be trapped in.
- The block pool, the phase gates, traversal, the investigation budget.
- **Play-time API cost, to approximately zero.** `docs/AI_COST_PLAYBOOK.md` identifies writing
  fixed text at generation time rather than calling per action as the correct lever, measured at
  10.8× on a four-player game. APF is that lever pushed all the way.

### The deal is a separate step from generation, and it is free

Generate findings carrying elimination data (one call), **then deal them under constraints** —
pure computation, deterministic, and a failed deal is simply re-dealt at zero cost.

| Constraint | Why |
|---|---|
| the union of all dealt findings eliminates all but one suspect | otherwise nobody can win |
| no single player's hand does that alone | otherwise it is a lottery |
| it becomes solvable once the minimum share threshold is met | otherwise sharing is pointless |

This is a stronger guarantee than anything the engine does today, and it costs nothing. See
`docs/INVESTIGATION_DESIGN.md` §4 for the `exonerates` / `implicates` fields it needs.

### Path 2 — one interrogation — is a FLAG, not a fork

Owner: *"even if a pick list, it adds some user empowerment. That's important to confirm, but not
essential."*

If the pick-list is over pre-generated questions, the answers already exist in the mystery. So
Path 2 is not a different loop — it is *"one of your findings arrives chosen instead of dealt."*
Same generation, same deal, same share decision, same reveal. **Ship APF with the pick-list behind
a toggle and both get tested by one group in one evening**, everything else held constant.

One consequence: variable hands mean solvability must hold across *every* combination of picks.
4 players × 3 options is 81 combinations — checked exhaustively as set operations, zero API cost.
Do **not** take the shortcut of making all options eliminate the same thing; that is cosmetic
choice and players feel it.

---

## The opening sequence — text, paced, on the shared screen

No video for the playtest. The mystery is told.

**`opening_narration` already exists and is one boolean away.**
`_generate_cinematic_brief()` (`server/main.py:335`) returns two fields, and is gated behind
`cinematic_brief: bool = False` — off by default, which is why the one real generated mystery on
disk has neither key:

| Field | Its own spec | Use |
|---|---|---|
| `opening_narration` | *"3–5 sentences of atmospheric prose, written to be displayed or read aloud to players. No spoilers, no camera direction."* | **The playtest opening.** Turn the flag on. |
| `cinematic_brief` | *"technical shot/lighting/sound direction… prepared for future video generation"* | The eventual video's shot list. Stays hidden. |

One extra call **at generation time**, which is the right place to spend it.

**The beats, measured on the real generation:**

```
opening_narration        3–5 sentences   the scene
crime.initial_discovery      224 chars   a person, a moment
crime.when                    86 chars   the punch
crime.what_happened          421 chars   what was done
setting.description          531 chars   why nobody can leave
```

~1,300 characters over five beats with deliberately varied length — the 86-character `when` lands
hard between two longer passages. That is a sequence, not a wall.

**Pacing is free** — client-side timing, no API call. On the shared screen it is a group moment:
everyone reading at one rate, reacting together. The same text dumped instantly onto private
phones is homework.

### The video slot

Owner wants the expectation set. **Do not ship a grey box reading "Video Scene Will Play Here"** —
it announces unfinished software at the exact moment you want people absorbed.

Instead the slot holds the crime depicted as well as it currently can — the top-down map framed on
the crime location, or a title card over the background field (`background_field.py`) — with the
narration timed over it. Same real estate, same promise, no broken signal. A small caption
underneath can make the promise explicit without breaking the scene.

> **Correction, Session 35:** `CLAUDE.md` item 15 stated the client *"renders a static
> `Video Scene Will Play Here` placeholder."* It does not. That string appears in no `.gd`,
> `.tscn`, `.html` or `.py` file — nothing occupies that slot today. Fixed in `CLAUDE.md`.

### What the UI has to carry now

With exploration gone, the **hand** and the **share** are not part of the game — they are the
game, and they must feel like objects rather than paragraphs.

- **The data is already card-shaped**: a finding has a name, a description, a type, a relevance.
  Dealt, held, played. MYF has `GameCard.jsx` (155 lines), `CardHand.jsx` (67), `CardPicker.jsx`
  (104) — not portable to Godot, but straight into `mobile.html`, and the visual language carries
  either way.
- **The suspect board is where deduction becomes visible.** If evidence carries `exonerates`,
  playing a card **greys a suspect out for everyone, permanently, with your name on it.** Text
  cannot do that. It also makes withholding legible without a word of explanation: a face stays
  lit that you could have darkened, and everyone can see you didn't.

**One schema field does double duty** — `exonerates` is what proves the mystery solvable *and*
what drives the central UI moment. Usually correctness and fun are separate budgets.

**Build the hand, the board and the share to be satisfying with the placeholder still in the
slot.** If the playtest only works once the video lands, it has taught you nothing about the game
and cost stage-3 money to say so.

---

## The flow

| # | Screen | What happens | State |
|---|---|---|---|
| 1 | **Mystery picker** | Dropdown, **titles only**. No difficulty, no rating, no coherence badge. | Exists but shows extra columns |
| 2 | **Crime scene** | Top-down map. Areas are clickable regions; witnesses are marked where they stand. Simple to the point of plain. | **Layout built**, screen not |
| 3 | **Interrogate** | Pick a witness → get actionable information. | Exists, needs simplifying |
| 4 | **Search** | Pick an area → *"You searched the <AREA> and found <THIS>. Testing and research reveal <ANALYSIS>."* | Exists, needs reshaping |
| 5 | **Follow leads** | **Greyed out. Not in the playtest.** | Built; to be disabled |
| 6 | **"I've solved it"** | A deliberately clumsy button on the crime-scene screen → dropdown of **four** suspects. | Accusation screen exists |
| 7 | **Result** | Verdict + solution + viability rating. | Fixed Session 34 |

Steps 3, 4 and 6 are reachable from the crime-scene screen, not in a fixed order — "each player
able to choose whether to interrogate, look for clues, or follow leads".

**What the playtest is actually testing** (owner's framing, and it decides every trade-off below):
can we generate a mystery that, above all, **makes sense** — with witnesses worth questioning,
clues that help, and leads that lead somewhere. Everything on screen is in service of judging the
mystery, not of being a finished game.

---

## Decisions

### The map layout is derived, not generated

`crime_scene_map.py` computes the layout from the mystery. Claude is never asked for coordinates.

- **Cost.** Coordinates are the one part of the payload a computer can derive for free.
- **Reliability.** Every extra field is another chance for the response to fail to parse — and an
  old batch summary in `mystery_database/generated/` shows **13 of 14 generations failing** on
  exactly that.
- **Quality.** An LLM asked for rectangles produces overlapping rectangles.

The prompt owns *meaning* (which areas exist, who is where); this module owns *presentation*. Same
mystery in, same map out, seeded from the title, so the host screen and a future phone client draw
the identical map.

A mystery with no `investigation_areas` gets **no map**, reported as such. It does not get invented
rooms — the playtest exists to find out whether generation produces usable areas, so faking them
would defeat the point.

### Lies are switched off for the playtest

Witnesses give straight, actionable information. Deception is a real mechanic and it stays in the
design, but a playtester cannot tell "the mystery is incoherent" from "the witness lied to me",
and telling those two apart is the entire purpose of this playtest.

### Leads are greyed out, not deleted

Visible and disabled, so testers see the shape of the finished game and the code stays exercised.

### Four suspects

The accusation dropdown shows four. The generation prompt must therefore ask for exactly four —
see below; it currently does not, and produces three.

---

## The one-call shape (owner item 7: "as cheap as possible")

**This is the significant one, and the owner's own simplifications are what make it possible.**

Today, gameplay costs an API call per action: `_investigate_area_with_ai` fires per area per
player, witness interrogation fires per question. A four-player game across five areas is ~20+
calls on top of generation.

But steps 3 and 4 as specified are not conversations. *"User picks which witness, game just gives
them actionable info"* and *"You searched this AREA and found THIS"* are **fixed text per witness
and per area**. Fixed text can be written once, during generation, in the call that is already
being made.

**One generation call, then a whole game at zero further API cost, is the intended architecture**
(owner, Session 34: *"We never, ever planned for live calls. We want the prompt, we want to generate
off the prompt and never use AI again."*).

**The code does not currently do that.** Six live play-time call sites exist in `server/main.py` —
`_investigate_area_with_ai` (779), `_follow_lead_with_ai` (798), `_generate_witness_scene` (1135),
both `/interrogate` endpoints (2306, 2398) and `_generate_resolution_narrative` (707). They arrived
with the Session 21 lockstep redesign and the Session 26 reveal; nobody chose a per-action
architecture, it accumulated an endpoint at a time. **Single-player interrogation hits 2398 on every
question, so this is on the playtest path.** Build-order step 5 is what closes it.

Because there are then no play-time calls, a mystery's whole AI cost is fixed, one-time, and paid
before anyone plays — it does not scale with players or replays. **That makes generation the right
place to spend, and "more expansive" the cheapest improvement available.** Watch two limits as the
payload grows: output is 8,667 tokens against a 16,000 cap (1.85× headroom), and anything above
~16,000 must switch the generation call to streaming or risk an HTTP timeout.

Schema additions needed in `_generate_mystery_dict`'s prompt:

| Field | Where | Why |
|---|---|---|
| `discovery` | each `investigation_areas[i]` | the "and found THIS" half of step 4 |
| `analysis` | each `investigation_areas[i]` | the "testing and research reveal…" half |
| `statement` | each witness character | step 3's actionable info |
| exactly **4** suspects | `characters` | step 6's dropdown |
| **3–4** witnesses | `characters` | the map needs bodies to place; today it gets 1 |

The existing `investigation_prompt` fields stay: they are what the *dynamic* version uses, and
stage 3 will want them back.

---

## Blocker: no saved mystery can run this flow

Measured, not assumed — all 18 saved mysteries:

- **0 have `investigation_areas`.** The prompt has asked for exactly 5 since Phase 3a. Every saved
  file predates that change (March 12 / April 3, 2026).
- **0 have `leads`**, same reason.
- **1 witness each** (three have none). Step 2 needs several.
- **3 suspects each** (three have two). Step 6 wants four.

So the current generation prompt **has never been verified to produce areas or leads at all**, and
the mystery picker in step 1 currently offers eighteen mysteries that cannot support steps 2, 4
or 6.

**This is the first thing to fix, and it costs one real generation call.** Nothing downstream can
be tested against real data until a mystery exists in the current schema.

---

## Coherence validation (owner item 7.1)

The engine must be checked from more than one vector, because Session 34 found it succeeding at
detection and being ignored by the pipeline (`CLAUDE.md` item 18).

1. **Does it detect what it claims?** Feed it deliberately broken mysteries and assert each
   expected `Issue` code fires. Zero API cost.
2. **Does it pass what it should?** Feed it a real generated mystery and assert no false blocking
   issue. Needs one real generation.
3. **Does anything act on the verdict?** Currently no — a `BLOCKING` report is saved and served.
   Item 18.

New rules the added fields need: every area has a non-empty `discovery`; at least one
`discovery` or witness `statement` points at the culprit; no area's `discovery` names the culprit
outright (or the mystery is solvable in one click).

---

## Build order

1. **Generation prompt + schema** — the four field additions above. Zero cost to write.
2. **One real generation**, to prove the prompt returns what it claims. **Owner sign-off: it is
   real API spend.**
3. **Coherence rules** for the new fields, plus the deliberately-broken-mystery test set.
4. **Crime-scene screen** in Godot — draws `crime_scene_map.build_map()`, hosts the area clicks,
   the witness markers and the "I've solved it" button.
5. **Simplify interrogation and search** to read the pre-written text instead of calling out — this
   is what removes the six live call sites, not a cosmetic simplification.
6. **Grey out leads.**
7. **Mystery picker** — titles only.

Steps 1, 3, 4, 5, 6, 7 cost nothing. Only step 2 spends money, and everything after it depends on
what it returns.
