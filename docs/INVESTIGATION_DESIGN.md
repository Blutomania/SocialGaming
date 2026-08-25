# The investigation model — locations, rounds, and provable solvability

**Status: design, agreed in conversation (owner + Claude, Session 35, August 25 2026). Nothing
here is built.** It supersedes item 20's "CLOUD" sketch in `CLAUDE.md` wherever the two differ,
and it exists because a UX question about drawing a map turned up three live defects in the
game underneath it.

Read `docs/PLAYTEST_FLOW.md` first for the screens as they stand today.

---

## 1. The crime scene is not a floor plan

`crime_scene_map.py` draws a **building**. `_grid_shape()` makes a near-square grid and
`_row_rects()` fills each row edge to edge — its own docstring says a gap "reads as a missing
room rather than as the shape of the building."

Run a Black Forest mystery through it and you get:

```
A1  Woodcutter's Hut       x= 24.0  y= 24.0  w=308.0  h=289.0
A2  The Ravine             x=346.0  y= 24.0  w=308.0  h=289.0
A3  Charcoal Kiln          x=668.0  y= 24.0  w=308.0  h=289.0
A4  Forest Track           x= 24.0  y=327.0  w=469.0  h=289.0
A5  Hunting Lodge Cellar   x=507.0  y=327.0  w=469.0  h=289.0
```

A forty-metre ravine as a 308×289 box, fourteen pixels from a hut.

**Where the assumption lives matters.** Generation is already setting-agnostic — the field is
`investigation_areas`, "named physical locations… plausible for the setting," and the word
"room" appears nowhere. The coherence engine has no spatial rule at all (all 26 codes are causal
chain, evidence variety, alibi anchoring). **Only the renderer assumes walls.**

### The decision: a connection map

Locations as nodes, connections as lines. Setting-agnostic by construction, because a line
claims only "these two relate" — true of a hallway, a footpath, and a companionway alike, while
a box always claims walls.

**The owner's argument is the strongest one and belongs on the record:** a Dick Francis mystery
spans a racetrack, training stables, a country estate and a lawyer's office. Rendering those
top-down is absurdist. Proximity is not the constraint; *access* is.

It also matches what the corpus actually holds. P3.F4 "setting as constraint" on *The Red House
Mystery* reads: *"an office reachable only through a passage of spring-hinged doors… door
movements are legible only as shadows on the passage wall."* That is a relation, not a floor
plan — and a relation is exactly what an edge is.

### Open: what does a line mean?

Three candidates, in ascending cost:

| Reading | Line means | Note |
|---|---|---|
| **Relationship** | "part of the same case" | Movement free. The map is a picture, not a mechanic. |
| **Provenance** | "this revealed that" | Falls out of §3's unlocking for free. Map becomes case history. |
| **Narrative access** | "reachable only once X is known" | A real mechanic. Most to build. |

**Owner is stewing on this.** Provenance looks like the natural fit given §3, and it costs
nothing extra.

### Correction (owner, later the same session): top-down is NOT rejected — rectangle-packing is

The first draft of this section generalised the defect from "packs rectangles" to "top-down."
**That was too broad, and the owner was right to push back.**

`_row_rects` fills each row edge to edge because its docstring reasons about *"the shape of the
building"* — it is drawing **interior architecture**. That is what breaks on a forest. The
overhead view is not the problem; the tiling is.

**Scale is what absorbs the Dick Francis case:**

| Story | Scale |
|---|---|
| Country house | floor plan |
| Antarctic station | site plan |
| Black Forest | terrain |
| Racetrack, stables, estate, lawyer's office | regional |

Same renderer, different zoom. *"Things placed in 2D space"* is true of all four; *"rooms tiled
into a rectangle"* is true of one.

It also removes the cost this document raised against the connection map — that a node graph
*"looks like a diagram, not a place."* A map at the right scale reads as somewhere.

**In APF the map is presentation, not mechanic** (`docs/PLAYTEST_FLOW.md`). With no traversal it
cannot deadlock, cannot gate anything, cannot lie about movement. It orients, and it gives the
game a place — which is exactly the "not just text" problem APF creates.

**The change is small.** Seven functions in `crime_scene_map.py`; only `_grid_shape` and
`_row_rects` are the offenders. `_seed_fraction` (determinism), `_point_in` (placing something
inside a region), `_best_area_for_crime` and `build_map`'s shape all survive. Most of the 193
assertions stay valid too — they test invariants a scattered layout must also satisfy (nothing
off-canvas, no overlaps, witnesses inside their area, identical run to run). Effectively only the
row-filling test goes.

**Simplest version that works:** labelled markers at seeded positions on a plain ground. No
terrain art, no walls, nothing to scale. Stable across reloads because the seed is the title.

Two things that do not change at any scale:

- **Do not claim precision you do not have.** A labelled marker is honest; a to-scale plan invites
  "but the hut overlooks the ravine" objections the data cannot back.
- **The witness fabrication is still a bug.** `area = placed[i % len(placed)]` is round-robin
  whether you draw rooms or a region. It still wants a real `area_id` from generation.

### Explicitly rejected

Teaching the floor plan about forests — i.e. per-setting rendering branches. Every new setting
would need new code, and the prompt box accepts anything. Scale generalises; special cases do
not.

---

## 2. A location is a container, not a single action

Today an area holds **exactly one** action: investigate it once, receive `discovery` +
`analysis` together, budget drops by one, and once anyone shares it the area is blocked for
everyone.

Worse, of the four content types only one is genuinely located:

| Content | Count | Located? | Actionable there? |
|---|---|---|---|
| Area discovery + analysis | 5 | yes, by definition | yes |
| Evidence items | 8 | **no field at all** | no |
| Witnesses | 3–4 | **fabricated by the renderer** | no |
| Leads | 4 | no | no |

**The witness placement is fiction.** `crime_scene_map.py` deals witnesses into areas
round-robin: `area = placed[i % len(placed)]`. Nothing in the mystery says where anyone is. So a
witness whose statement is "I was in the kitchen all evening" can be drawn standing in the
ravine — and there is no action attached either way, because interrogation is a separate phase
that picks from a list.

### The decision

- **Witnesses get a real `area_id`.** Generation already knows — it writes locations into alibis.
- **Evidence gets `area_id`.** Same reasoning.
- **Leads stay off the map**, in a panel beside it. An anonymous letter has no honest location.
- A location then shows what it holds, and multiple players can visit it for **different**
  business. The backend already supports this: `block_pool` is three pools with three
  granularities (`witness` per person-per-question, `investigation` per area, `lead` per lead),
  so "player 1 questions the witness at the Track, player 2 searches the Track" already blocks
  independently.

**Density becomes emergent, not allocated.** ~5 locations × ~3 affordance types is a *ceiling*
of ~15 actions, not a target. A thin mystery draws a thin map — a quality signal, and checkable
for free ("no location has any affordance" is a warning).

This removes the pressure to raise the area count, which was the previous plan. Do not spend
tokens on more rooms until this is settled.

---

## 3. The narrative hands out the options, and the pool grows

**Owner's design.** Round 1's options are not discovered — they are *stated*, in prose, by the
opening narration:

> "To start your investigation Hansel and the Gingerbread Man should be questioned. The
> gingerbread house should be investigated for clues, so should the front yard where Gretel
> died. Finally, that wolf in grandmother's clothing seems out of place, doesn't he?"

Round 2 = whatever nobody took, **plus** what round 1 unlocked. A hotel key found at the scene
opens the hotel room as a location and the receptionist as a witness. Car tracks in the mud.
Name tags in the wolf's clothing.

### What this fixes

- **Blind exploration is gone.** The owner's objection was that toiling while friends find things
  is neither fun nor social. It is also *structurally* the deadlock (§5): no findings means
  nothing to share, which means excluded from the social loop and unable to advance.
- **The deadlock cannot occur.** The pool grows faster than it is consumed. No player arrives at
  an exhausted board. That is a structural fix, not a patch.
- **It answers "what is a line"** — provenance.

The generation prompt already agrees with the no-toil principle: *"Every area must yield
something; an area that yields nothing wastes the only move a player gets there."* The interface
simply never surfaced it.

### Scope: this works as a list first

Round 1 shows five named options; you pick. **No map required.** The connection map earns its
place only once there are enough options that history matters. Build the growing pool, ship the
playtest as a list, add the map after — nothing is thrown away.

### What it requires

1. **The whole tree is generated up front**, round 2's car tracks included, each node tagged with
   what reveals it. Not invented mid-game: that is a new API call per unlock, and it can
   contradict a solution already written.
2. **The briefing may only name things that exist as data.** If the prose says "question the
   gingerbread man" and no such character exists, the game breaks on the first click. Free
   coherence rule.
3. **Playtime becomes variable.** More unlocks, more rounds, against a 30–75 minute target.
   Something must cap it — a round limit, or a budget that does not grow with the pool.

---

## 4. Solvability as arithmetic — the central idea

> *"How do we ensure the clues are actual clues that come together for the solution?"* — owner

**What cannot be checked cheaply:** that a serrated bolt-driver *implicates* Dr. Hale. That is
meaning, and meaning costs an API call.

**What can:** that the clues **eliminate**.

### Today the link does not exist

From the one real generation on disk (*Whiteout at Shackleton Base*):

```
suspects      : Hale, Tanaka, Larssen, Caron
culprit       : Dr. Marcus Hale
key_evidence  : [E1, E2, E3, E4, E6]

E1  critical     Dr. Solberg's USB Audit Drive
E2  critical     Serrated Bolt-Driver
E3  critical     Cold Storage Motion-Sensor Log
```

`relevance: critical` is a **label, not a relationship**. Nothing says E3 rules out Tanaka. The
claim that these five items prove Hale did it lives only in a paragraph of prose.

And `P1.C5.dangling_key_evidence` — the rule that is supposed to guarantee solvability — has the
message *"Resolution refers to evidence players can never find"* while checking only that the ID
appears in the evidence array. **Same failure family as Session 34's culprit bug: a rule whose
message states the real requirement and whose check is a weaker proxy.**

### The decision: make elimination a field

```jsonc
{ "id": "E3", "name": "Cold Storage Motion-Sensor Log", "exonerates": ["Tanaka"] }
{ "id": "E6", "name": "Keycard Access Log",             "exonerates": ["Larssen", "Caron"] }
{ "id": "E2", "name": "Serrated Bolt-Driver",           "implicates": ["Hale"] }
```

Then solvability is a set operation, free and deterministic:

> Take every suspect. Remove everyone exonerated by the key evidence.
> **Exactly one must remain, and it must be the stated culprit.**

Three BLOCKING conditions fall out, none of them detectable today, all of them producing a game
a player cannot win:

| Condition | Meaning |
|---|---|
| two or more survivors | no unique answer |
| zero survivors | the evidence contradicts itself |
| survivor ≠ stated culprit | prose and structure disagree |

### Paired with reachability

Elimination only matters if the evidence is obtainable. So: **every key evidence item must be
surfaceable by at least one player action** — which needs §2's `area_id`. Together the two rules
are a real proof: *the clues that eliminate all but one suspect are all obtainable.*

### A free interim check, available now

`how_to_deduce` already cites evidence IDs *and areas* inline —
*"the Cold Storage motion log **(E3, Area A1)** shows two separate entries…"*. Generation knows
all of this and writes it into prose instead of fields.

So before any schema change: **parse the evidence IDs out of `how_to_deduce` and confirm they
cover `key_evidence`.** If the solution's own reasoning never mentions E1, E1 is not load-bearing
and should not be listed as key. Zero cost, catches sloppy generations today.

### What is deliberately left to the playtest

Whether a clue is **fair** — whether a human could reasonably make the leap — is craft judgment,
not arithmetic. That answer comes from the feedback loop already designed: the viability rating,
plus accusation data (how many got it right, how long it took).

**Structure is provable for free. Fairness is empirical. Meaning is the expensive middle you
mostly do not need to buy.**

> For the funding pitch this is the strongest form of the coherence pillar: not "we check the
> story hangs together" — table stakes — but **"we prove the mystery has exactly one obtainable
> solution before anyone plays it."**

---

## 5. The deadlock (live today, stage-1 blocking)

Three facts in `server/main.py`:

1. **Sharing is the only exit from a phase.** `player["phase"]` advances in exactly one place,
   inside `share_findings`.
2. **You cannot share nothing.** `if not all_findings: raise HTTPException(400, …)`.
3. **Every area can be blocked before you act.** Sharing an investigation finding adds its
   `area_id` to `block_pool`; investigating a blocked area returns 409.

A player reaching the investigation phase with all five areas shared gets 409 on every room, 400
on share, and **cannot advance, ever.**

It is not an edge case:

```
EASY    4 players × 3 = 12 investigations wanted, 5 areas exist
MEDIUM  4 players × 2 =  8 investigations wanted, 5 areas exist
HARD    8 players × 2 = 16 investigations wanted, 5 areas exist
```

Every difficulty at every player count wants more investigations than there are rooms.

**The root cause is the phase gate**, not the block pool — lines 2076 / 2130 / 2363 lock a player
into one action type at a time. A player stuck in `investigation` cannot do the witness or lead
work sitting right there.

### Fixes, in order of preference

0. **[Session 35, owner] APF deletes the mechanic that has the bug.** With findings dealt rather
   than gathered there is nothing to block, every player holds findings by construction, and there
   is no phase to be trapped in. See `docs/PLAYTEST_FLOW.md` → "APF". This is the current plan for
   the playtest, and it is the cheapest correct outcome: the bug stops existing.
1. **§3's growing pool** — the deadlock stops being possible.
2. **Change the exit condition** to *"you are done acting,"* not *"you found something."*
   Spending a budget on three red herrings is a legitimate way to play a mystery badly; it should
   end a phase, not trap a player. Today, "found nothing useful" and "found nothing at all" are
   the same state to the code, and only one of them should be.
3. **The minimum patch**: advance when the player has no findings *and* no unblocked targets.

Owner's framing that made this clear: not every action needs to be vital — red herrings and
innocent bystanders are the point — so the fix is never "add just enough content."

---

## 6. Open questions — all owner's

1. **What a line means** (§1) — relationship, provenance, or narrative access.
2. **Affordance display** — show counts, or only presence? Counts turn blind exploration into
   informed allocation, and make an empty location visibly dead.
3. **Player position visibility.** Today only *shared* findings are public. Showing "the Track
   has been searched" is safe; showing "Priya is at the Track" gives away information the sharing
   mechanic never sold. Both defensible, not the same choice.
4. **Budget model** — one pool of N spendable anywhere, or the three separate allowances.
5. **Titles that spoil.** Player titles now feed generation, and *"Why did Hansel Grimm kill
   Gretel Grimm"* names the culprit. That is a whydunit — a legitimate form, a different game.
   Generation should treat such a title as premise or as misdirection **by decision, not by
   accident.**

---

## 7. Build order

| # | Step | Why here |
|---|---|---|
| 1 | Deadlock fix (§5, option 2 or 3) | Live stage-1 blocker, independent of everything else |
| 2 | `how_to_deduce` ID-coverage check (§4) | Free, no schema change, catches bad generations now |
| 3 | `area_id` on witnesses + evidence (§2) | One additive schema change, unblocks §4's reachability rule and kills the fabricated placement |
| 4 | `exonerates` / `implicates` + the set check (§4) | The solvability proof |
| 5 | Growing option pool, as a **list** (§3) | The playable shape; no map needed |
| 6 | Connection map (§1) | Presentation, once there is history worth drawing |

Steps 1–4 are stage 1. Steps 5–6 are the shape stage 3 grows into.

**Token cost of the schema additions is not a constraint.** A full generation measures ~7,200
tokens against a 16,000 ceiling; the fields above add a few hundred.
