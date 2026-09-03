# rejected/ — generated successfully, failed structural validation

`mystery_database/generated/` is **served to players**: `/mysteries` in
`server/main.py` globs it directly, so anything sitting there can be picked at a
real table. A mystery that generation produced but that the structural rules
refuse therefore cannot stay in it.

It is moved here rather than deleted. Each of these cost a real API call, each
is the evidence that a rule was needed, and a rule with no counter-example is a
rule nobody can argue with later.

**Nothing reads this directory.** No route, no checker, no registry.

| Mystery | Coherence | Why it was rejected |
|---|---|---|
| `the_lantern_keeper's_last_light` | passed, 0 blocking, 0 warnings | `E4` "Bloody Palm Print" clears **all three** innocents at once, so whoever drew it won alone without anyone sharing. `deal.py` refuses it. This is why the prompt now carries Clue's rule that an item clears at most one suspect. |
| `the_vanishing_at_altheim_peak` | passed, 0 blocking, 0 warnings | Two suspects are clearable only **one** way, so a single player withholding one finding can make the case unprovable — and in 54 of 81 hoarding patterns only that one player could ever prove it. This is why the prompt now requires two independent routes. |
| `totality` | passed, 0 blocking, 1 warning | **Playable, but below standard — a different category from the two above.** Its deal is clean, it deals on the first attempt, and proof survives all 81 hoarding patterns. What it fails is quality: one innocent (Luz Fontaine) is clearable only one way, which leaves a monopoly on proof in 27 of 81 patterns; two exonerations are reachable only by drawing the clue itself; and its one narrowing finding — a rifle casing "consistent with" a bolt-action — names **all four** suspects, so it rules nobody out. That last one is why `narrows` must now exclude at least one person. |
| `the_light_that_went_out` | passed, 0 blocking, **0 warnings** | **Playable and spoiled in prose.** Mechanically the best generation to date — feasibility clean, proof surviving 81/81 hoarding patterns, a monopoly on proof in 0 of 81. Both narrowing clues carry honest data (2 of 4 suspects, culprit included) and then **name the culprit in their own description**: *"Morag Gillies wears size 5.5 walking boots with a herringbone sole"*. Whoever is dealt it wins without speaking to anyone. Nothing structural can see this — the fields are correct and the prose betrays them — which is why `check_narrative.py` reads the description as well as the links. |

**The two categories are worth keeping apart.** The first two here are *unplayable*: `deal.py`
refuses them outright. `totality` is *playable and not good enough*, which is progress — it is the
first mystery whose deal came out clean on the first attempt. `generated/` means fit to serve, and
a monopoly in a third of hoarding patterns is not.


**The four above all passed the coherence rules.** That is the point worth keeping: the
coherence engine checks whether the story hangs together, and none of those four
failures is a story problem. They are game-structure problems, and they needed
their own checks.

---

## A third category, and how files get here now

| Mystery | Coherence | Why it was rejected |
|---|---|---|
| `the_stolen_star_of_smurf_village` | **failed, 1 blocking** | **Incoherent, and served anyway for six months.** `P1.C4.culprit_not_in_characters` — its solution names two culprits, so `solution.culprit` is prose rather than a name in the cast, and under the accusation screen's original exact match *every* accusation on it was wrong, including both correct ones. The game could not be won and the player was told they were wrong. This is item 18's original case. |

**Nothing carried that file here.** Until Session 41 the pipeline wrote every generation to
`generated/` whatever the checks said, so the one mystery on disk that *fails* coherence was the
one being served, while all four that *passed* it had been moved out by hand. `gate.py` now decides
where a generation is written, and this is the only file already on disk that moved.

**The three categories, worst first:**

| | Means | Caught by |
|---|---|---|
| *incoherent* | the story does not hang together | `coherence_validator.py` |
| *unplayable* | the story is fine and the game cannot be dealt or won | `deal.py`, `check_narrative.py` |
| *spoiled_prose* | every field is correct and the text gives the answer away | `check_narrative.py` |
| *below_standard* | playable, winnable, not good enough to serve | `check_narrative.py` |

**This directory is no longer only an archive.** `mystery_database/ledger.jsonl` carries one row per
generation attempt — what it cost, what happened to it, and which rules it broke, by stable id.
Every rule the generation prompt now enforces was learned from one of these files; recording the
failure class and the offending evidence ids is what lets that loop be counted rather than
remembered. `python3 scripts/cpam.py` reads it.

**Still true: nothing SERVES this directory.** No route and no registry reads it. `/mysteries`
globs `generated/` only.
