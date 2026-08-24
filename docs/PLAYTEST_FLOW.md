# Playtest gameflow — the PC path to stage 1

Owner-specified, Session 34 (August 21, 2026). This is the **canonical** description of the flow
the PC playtest has to deliver. It supersedes the Phase 2/3 screen descriptions in `CLAUDE.md`
wherever the two disagree, for playtest purposes only — nothing built is being removed.

Read `CLAUDE.md` → **Delivery Priority** first. Stage 1 is: somebody who is not the owner sits at
a PC, plays a whole mystery, and reaches the result screen. Everything here serves that and
nothing else.

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
