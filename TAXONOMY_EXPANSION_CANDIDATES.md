# Choose Your Mystery — Taxonomy Expansion Candidates (July 22, 2026)

## Overview

This document stages candidate additions to the writer-grounded taxonomy in `RESEARCH_FINDINGS.md` /
`extraction_protocols.py`, produced by a comprehensive research pass across four parallel threads.
**Nothing here is adopted yet.** This is the "prioritized data" input to the next step — revisiting
the `Rule`/`RuleSet` shape in `coherence/engine.py` — not a change to the shipped taxonomy. Treat this
file as a candidate pool to select from, not a spec.

**Method note:** all four research agents had their `WebFetch` tool blocked (403s across every target
host tried this session — a tooling/environment issue, not a content problem) and fell back to
`WebSearch` synthesis, cross-checking claims across 2+ independent secondary sources. Every candidate
below carries an explicit confidence rating. Treat **High** as comparable rigor to the existing
Christie/Knox/Chandler citations already in the codebase; **Medium** as well-corroborated but
paraphrase/secondary-sourced, not verified against primary text; **Low-Medium** as genre-blog/consensus
knowledge with no single citable named authority — usable, but weaker grounding than the existing file's
standard.

---

## Two new structural axes (the most important finding — read before the tables)

The research didn't just surface more parts to add to P1–P4's flat depth ladder. It surfaced two
genuinely new **axes**, both of which should shape the `Rule`/`RuleSet` redesign more than any single
part below:

### Axis A — Subgenre Contract (gates/overrides existing parts, doesn't just add to them)

John Dickson Carr's locked-room lecture (*The Hollow Man*, Ch. 17) and Julian Symons' *Bloody Murder*
four-way subgenre split (Golden Age puzzle / hardboiled-noir / police procedural / inverted-psychological)
both argue that a mystery's **declared subgenre changes which rules even apply** — not just how deep to
extract. Concretely: a psychological-suspense mystery (Francis Iles/Flynn-style) can *legitimately leave
M1 Suspect Architecture empty*, because the culprit is revealed up front and there's no whodunit
architecture to build. A hardboiled mystery can *legitimately violate M3 Clue Fairness* by riding inside
a criminal narrator's head. These aren't bugs to catch — they're different, mutually exclusive contracts.

**Recommendation:** a `subgenre_contract` field, read alongside C3 (Closed World), that activates exactly
one of a small set of mutually-exclusive rule bundles and can suppress/override otherwise-universal parts.

### Axis B — P5: Interactive/Multiplayer (almost entirely type-conditional, none of it is in P1-P4 at all)

Every existing part in the file is grounded in **prose criticism** — a novel has one reader in the
author's chosen order with the author's chosen information. CYM is a live multiplayer game with
asymmetric, randomized information (the 75% clue-sharing mechanic). Prose criticism structurally cannot
address "is this fair across parallel competing investigators," and indeed nothing in the current
taxonomy does. This should be a genuine 5th top-level protocol, not folded into P1-P4.

**The single most actionable finding of the entire research pass** lives here: Robin D. Laws' **GUMSHOE
system** ("never leave clues to chance") and Justin Alexander's **(Inverted) Three Clue Rule** are both
named, durable, widely-cited authorities — on par with Knox/Christie — and translate directly into a
concrete, implementable, zero-API-call `coherence_validator.py` check:

> Every P1.C4 (culprit/motive) conclusion must be reachable via ≥3 independent evidence paths, **and no
> single clue flagged "core" may be subject to the 75% distribution roll.**

The research also concluded the 75% mechanic itself has **no direct precedent** in tabletop, social
deduction, or RPG design literature reviewed (closest analog: *Deception: Murder in Hong Kong*'s
constrained-channel truth-telling) — it should be validated empirically (playtesting/telemetry), not
defended by citing an external authority.

---

## Priority 1 — Validator-ready (High confidence, directly implementable as a free `coherence_validator.py` check)

| Candidate | Source | Tier | What it checks |
|---|---|---|---|
| **Core-Clue Guarantee** | Robin D. Laws, GUMSHOE system | New P5, universal-within-multiplayer | No clue flagged "core"/pivotal may be subject to the 75% distribution roll |
| **Three-Clue Redundancy** | Justin Alexander, "Three Clue Rule" / Node-Based Design | New P5, universal-within-multiplayer | Every pivotal (C4) conclusion has ≥3 independent supporting parts |
| **Retrospective Inevitability** | S.S. Van Dine Rule 15 (1928) | Universal | No other suspect's motive/means/alibi combination equally satisfies the evidence set |
| **No False-Crime Deflation** | S.S. Van Dine Rule 18 (1928) | Universal | If the crime framing (C1) reverses (murder→accident/suicide), the reversal must itself satisfy M3 clue-fairness, not be a bait-and-switch |
| **Naturalistic Causality Contract** | Ronald Knox Commandment 2 (1929) | Universal | No supernatural/preternatural mechanism anywhere in the causal chain, not just at the reveal (broader than C5) |
| **No-Coincidence Resolution** | Detection Club oath, 1930 (principally scripted by Dorothy Sayers; co-signed by Christie, Knox, Chesterton) | Universal | Every load-bearing fact in the resolution traces to a planted cause, never chance/timing — candidate to strengthen C5's citation rather than stand alone |

## Priority 2 — New parts, high confidence, needs scoping decision

| Candidate | Source | Tier | Note |
|---|---|---|---|
| **Secret-Architecture Cap** | Knox Commandment 3 | Type-conditional (physically-sealed closed world) | At most one hidden room/passage per mystery |
| **Detective-Culprit Exclusion** | Knox Commandment 7 | Universal, but the most famously *deliberately broken* rule in the canon (Christie's own *Roger Ackroyd*) | Recommend: default constraint + explicit "intentional subversion" escape hatch, not a hard rule |
| **Twin/Double Foreshadowing** | Knox Commandment 10 | Type-conditional (identity-duplicate device used) | Directly applicable — existing corpus examples already use clone/identity devices (C1/C4/M6) |
| **Earned-Solution / No Lucky Break** | Knox Commandment 6 | Universal | Overlaps existing C5/M6 — likely best as an elaboration of those rather than a new part |
| **Impossibility Mechanism Category** + **Seal Reconstruction Trick** | John Dickson Carr, *The Hollow Man* Ch. 17 ("locked room lecture") | Type-conditional (C3 = physically sealed, not just socially bounded) | 7 death-mechanism categories + 5 seal-reconstruction tricks (see full breakdown below); wording is paraphrased/secondary-sourced, not a verified primary quote |
| **Fair-Play / Criminal-Eye / Procedural-Ensemble / Inverted-Certainty Contracts** (SG1–SG4) | Julian Symons, *Bloody Murder* (1972) | Type-conditional — the Axis A subgenre selector itself | See Axis A above; these four are mutually exclusive |

## Priority 3 — New parts, medium confidence (genre-consensus, recommend a second source before formalizing)

Procedural: Chain-of-Custody Integrity, Forensic Turnaround Realism, Jurisdictional Authority Constraint,
Bureaucratic Friction (Lee Lofland/*Howdunit*, Sue Coletta, Michael Connelly-paraphrase).
Cozy: Amateur's Standing, Off-Page Violence Rule, Community Restoration Resolution, Hobby/Occupation Hook,
Unmourned Victim (genre-blog consensus, no single named authority).
Hardboiled beyond Chandler: Mundane Means Principle (**High** — direct verified Chandler quote crediting
Hammett), Behaviorist/Objective Narration, Professional Detachment Code, Institutional Corruption as
Baseline (last one flagged lowest-confidence of the whole pass — recommend a second source).
Psychological suspense beyond Flynn's existing F3: Dueling Dual-Timeline Structure, Weaponized Evidence
(diegetic staged-clue device, distinct from M2's authorial red herring), Unlikability as Design (**High**
— direct verified Flynn interview quote).
Historical-mystery Period-Bounded Detection; general Chain-of-Custody Integrity (procedural).
Van Dine consolidated: Narratively-Significant Culprit, Single-Culprit Default (explicitly breakable —
*Orient Express* is the celebrated exception), Anti-Cliché/Device Freshness (**experience/polish tier**,
maps onto the part-signal feedback loop already in `CLAUDE.md`'s design principles), Romance-Subordinate-
to-Puzzle (dated in absolutist form, recommend soft tunable not hard rule).
Sayers: Self-Contained Logical Closure (overlaps existing F7, frames it as closure-of-system rather than
per-clue fairness).

Full interactive/multiplayer thread (Priority 1's P5 already covers the two best): tabletop party-game
redundancy floor and host-neutrality conventions, social-deduction compensating-asymmetry and
information-economy-explicitness principles (Secret Hitler, Blood on the Clocktower), escape-room
parallel-non-linear-solvability and fixed-session puzzle-density calibration — all **type-conditional on
multiplayer**, all Priority 3 (solid corroboration, no single named authority at Priority-1 tier).

## Explicitly rejected — contradicts the studio's own existing design, do not port

| Rule | Source | Why rejected |
|---|---|---|
| "There must be a corpse" | Van Dine Rule 7 | Existing C1 examples already include art theft, staged disappearance — no death required |
| "Only one detective" | Van Dine Rule 9 | Directly inverted by the core mechanic — every player is simultaneously an investigator |
| No dwelling on atmosphere/side issues | Van Dine Rule 16 | Contradicts the existing P4 Texture protocol (F13 Atmospheric Register, F14 Detective's Voice) outright — flagged as a genuine design-philosophy tension (Van Dine purism vs. this studio's Chandler/French-leaning texture layer), not an oversight to fix |
| "No Chinaman" (racialized stock villain) | Knox Commandment 5 | Period racial-stereotype artifact, not a structural craft principle — if anything, belongs in a content-safety generation guideline, not the craft taxonomy |

---

## Full Carr locked-room breakdown (for reference, Priority 2 item)

**Tier A — why the sealed-room murder isn't actually impossible (7 categories, paraphrased, moderate-high
confidence on structure, not verbatim):** (1) staged to look like murder, actually an accident; (2)
poison gas/fumes, sometimes causing a struggle misread as intrusion; (3) pre-planted mechanical trap; (4)
suicide staged as murder, often to frame someone; (5) killer kills then impersonates the victim for later
"sightings"; (6) remote kill from outside the sealed space (Carr's own example: bullets of ice that melt);
(7) victim only stunned — killer leaves, room is later broken into by others, killer is first through the
door and finishes the kill amid the confusion.

**Tier B — how the room was resealed after the fact (mechanical door/window tricks, ~5, lower detail
confidence):** bolt turned from outside via thread-and-pin, key-stem turned with pliers through the
keyhole, door lifted off and rehung on hinges, windowpane removed and reset, etc.

Robert Adey's *Locked Room Murders* (1979/1991) expands this into a ~20-category taxonomy — flagged as
existing and citable but **not independently verified this session**, a good next step if deeper
granularity is wanted.

---

## Next step

This feeds directly into revisiting the `Rule`/`RuleSet` shape in `coherence/engine.py` — specifically,
the applicability half of that hierarchy needs to express both Axis A (subgenre contract) and Axis B
(interactive/multiplayer conditionality), not just era/setting the way `part_registry.py`'s
`SETTING_COMPAT` already does for content parts.
