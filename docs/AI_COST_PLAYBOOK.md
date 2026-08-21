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

## Lever 1 — one call per mystery, then never again  *(the architecture, not an optimisation)*

**State this correctly, because an earlier draft of this document got it wrong.** One generation call
per mystery and no AI at play time is not a saving discovered by analysis — it is, and always was,
the intended design (owner, Session 34: *"We never, ever planned for live calls. We want the prompt,
we want to generate off the prompt and never use AI again."*). There is no per-action baseline to
have saved money against.

**What the analysis actually found is a divergence: the shipped server does make live play-time
calls.** Six sites in `server/main.py`:

| Line | Function | Fires |
|---|---|---|
| 779 | `_investigate_area_with_ai` | every area a player searches |
| 798 | `_follow_lead_with_ai` | every lead a player follows |
| 1135 | `_generate_witness_scene` | every witness round |
| 2306 / 2398 | the two `/interrogate` endpoints | every question asked |
| 707 | `_generate_resolution_narrative` | once at end of game |

These arrived with the Session 21 lockstep redesign and the Session 26 resolution reveal. Nobody
decided to build a per-action architecture; it accumulated one endpoint at a time. **The
single-player playtest path hits line 2398 on every interrogation question today.**

So the number below is not a saving. It is the size of the gap between the design and the code:

| | Calls/game | Cost/game |
|---|---:|---:|
| Intended: one generation, no play-time calls | 1 | **$0.14** |
| What the code does now, 4 players × 5 areas + 6 questions each | 45 | **$1.48** |

Closing that gap is what the `discovery` / `analysis` / `statement` fields are for: they make the
pre-written answer exist, so the client can read it instead of calling out. The fields landed in
Session 34; **the call sites above have not been removed yet.**

Rule going forward: **anything a player will see that doesn't depend on what they chose is written at
generation time.** Dynamic interrogation would reverse this and is not planned — if it is ever
wanted, price it as "per player per question, scaling with room size".

### The corollary: spend *more* on generation, not less

Because there are no play-time calls, a mystery's entire AI cost is **fixed, one-time, and paid
before anyone plays**. It does not scale with players, session length, or replays — and saved
mysteries are replayable from the browse list, so the cost amortises further every time one is
reused.

That makes generation the *right* place to spend. A more expansive generation (owner's stated
direction) is the cheapest kind of improvement this architecture can buy.

Two practical limits to watch as the payload grows:

| | Now | Limit |
|---|---:|---|
| Output tokens per mystery | 8,667 | `max_tokens` is 16,000 — **1.85× headroom** |
| Cost per mystery | $0.14 | scales linearly: ~$0.26 at 2×, ~$0.39 at 3× |

`claude-sonnet-4-6` can return up to 128K output tokens, but **anything above ~16,000 must use
streaming** (`.stream()` + `.get_final_message()`) or the request risks an HTTP timeout. So the next
real expansion of the schema is also the moment the generation call needs to become a streaming call.
Worth doing before the payload forces it, not after — a truncated response bills in full (Lever 3).


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
