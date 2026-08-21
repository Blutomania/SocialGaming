# The cost of a mystery — AI call economics

Measured 21 August 2026 on this repo's own pipeline, generating *Whiteout at Shackleton Base*.
Every figure below is measured, not estimated: token counts come from the token-counting endpoint,
prices from `claude-sonnet-4-6` at $3.00 / $15.00 per million.

Shareable version: published as an artifact ("The Cost of a Mystery").

---

## The one number that reorders everything

| | |
|---|---|
| Input — the whole prompt, corpus parts and craft guidance included | **2,457 tokens** = $0.0074 |
| Output — the mystery it returned | **8,667 tokens** = $0.1300 |
| **One generation call** | **$0.1374** |

Output is priced 5× input, *and* this pipeline sends a short prompt to get a long answer. The two
multiply: **output is 95% of every generation call.**

**Therefore, the optimisation to skip: prompt caching.** It discounts cached *input* by up to 90%,
but input is $0.0074 of a $0.1374 call — perfect caching on every call saves about $0.0066, or 5%.
It is the first thing anyone reaches for and it is the wrong lever here. Revisit only if the prompt
grows dramatically (a much larger corpus block, or conversation history).

---

## Lever 1 — move work from play time to build time  *(biggest; done Session 34)*

The playtest's simplifications ("pick a witness, the game gives them actionable info"; "you searched
the area and found this") are **fixed text per witness and per area**, not conversations. Fixed text
can be written during the generation call already being paid for.

| Design | Calls/game | Cost/game |
|---|---:|---:|
| Pre-written at generation *(now)* | 1 | **$0.14** |
| Live call per area search, 4 players × 5 areas | 21 | $0.75 |
| Live calls for searches *and* interrogation | 45 | **$1.48** |

**10.8× cheaper** — and the saving compounds with players. A live-call design gets more expensive the
more people are in the room, which is the wrong direction for a party game; the pre-written design
costs the same for two players or eight. It is also faster, and cannot fail on the network in front
of a room.

Rule: **anything a player will see that doesn't depend on what they chose can be written before they
choose.** Dynamic interrogation is a real feature for a later version — but buy it deliberately.

## Lever 2 — don't buy what a computer can derive

The crime-scene map needs rectangles and marker positions. Asking for them in the generation JSON
would cost tokens on every generation forever, for numbers a twenty-line packer produces free — and
would produce overlapping rooms, because that is what an LLM does when asked for rectangles.

Before adding a schema field, ask whether it is **meaning** (worth paying for: which rooms exist, who
is where, what the forensics say) or **presentation** (arithmetic).

## Lever 3 — make the ceiling taller than the answer

`max_tokens` was **8,192**. The measured response is **8,667**. The model was being cut off mid-JSON,
and a truncated response is not a discount: **you are billed for every token generated and receive
something that will not parse.**

The old batch summary in `mystery_database/generated/` shows **13 of 14 generations failing** with
`Unterminated string` / `Expecting property name` — the error messages of a JSON document that stops
in the middle. On those numbers one usable mystery cost roughly fourteen times list price.

Measure the real answer with `count_tokens` (free), then set the cap comfortably above it. **Never
tune `max_tokens` down to save money** — it destroys output already paid for.

## Lever 4 — validate with things that cost nothing

`coherence_validator.py`, `scripts/check_mystery_playable.py`, `scripts/check_godot_wiring.py` and
`scripts/test_registry_staleness.py` make zero API calls. A defect caught before a generation is a
generation not wasted; one caught after is a re-generation avoided.

The cheapest lever, and the one most likely to be skipped, because free tools never appear on an
invoice. Live example: a mystery whose culprit matched no suspect was detected by the engine, saved
anyway, and shipped unwinnable (item 18). Detection cost nothing. Ignoring it cost a playtest.

## Lever 5 — batch anything nobody is waiting for

The Batch API runs asynchronously at **half price**. Wrong for generation (a room is watching a
spinner); right for every corpus job, which is where the bulk spend actually lives.

| Job | Latency matters? | Surface |
|---|---|---|
| Mystery generation | Yes | Messages API |
| Localization | Yes — same call chain | Messages API, cached per era |
| Corpus extraction, P1→P2 re-runs | No | **Batch API — 50% off** |
| Re-extracting the 7 all-null anthology stories | No | **Batch API — 50% off** |

The held-back P1→P2 re-extraction of 75 sources (item 12) is the largest uncommitted spend on the
books. Whenever it happens, it should happen in batch.

## Lever 6 — right-size the model per job

Model choice is per call, not per project. Extraction is mechanical — read a text, fill named fields.

| Model | In / Out per 1M | Fits |
|---|---:|---|
| `claude-sonnet-4-6` *(pinned today)* | $3 / $15 | Mystery generation — this is the product |
| `claude-haiku-4-5` | $1 / $5 | Extraction, classification, field-filling |

Extraction on Haiku is a **3× cut on the corpus line**; stacked with batching, ~6×. Generation stays
on Sonnet — it is the one call whose quality a player experiences, and the wrong place to save a
dollar.

---

## What will reintroduce cost, in the order it will arrive

- **Dynamic interrogation** — reverses Lever 1. Price it as "per player per question, scaling with
  room size", not as "one more feature".
- **Moderation on a player-typed title** — currently none by decision. A Claude pass adds a call to a
  lobby action in front of a waiting room; a local filter costs nothing and catches less. That trade
  is about latency and product risk more than money.
- **Re-generation on a failed coherence check** — genuinely open (item 18). Retrying doubles the cost
  of the mysteries that need it; shipping an unwinnable one costs a playtest.

**The habit underneath all six: measure before you spend.** `count_tokens` is free, the coherence
engine is free, and the pipeline will tell you what it costs if you ask. Nearly every finding here
came from asking rather than assuming — including the one quietly destroying 13 of 14 generations.
