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

**Both passed all 26 coherence rules.** That is the point worth keeping: the
coherence engine checks whether the story hangs together, and neither of these
failures is a story problem. They are game-structure problems, and they needed
their own checks.
