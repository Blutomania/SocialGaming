# Choose Your Mystery — Party & Social Deduction Craft Findings

## Overview

Third companion document alongside `RESEARCH_FINDINGS.md` (novelist craft) and
`SCREEN_CRAFT_FINDINGS.md` (screen/TV craft). Those two ground narrative construction —
how a mystery's plot is built. This one grounds the thing neither novels nor screen media
actually do: **live, multiplayer, asymmetric-information play** — real murder mystery
parties and social deduction games (*Blood on the Clocktower*, Jackbox), which are the
closest real-world analogue to the 75% clue-sharing mechanic, the interrogation phase, and
a competitive first-to-solve accusation endgame.

## Two parts

- **Part 1 — Design & Mechanics Authority.** Designers/producers explaining what makes the
  live, asymmetric-info format actually work as a *game*, not just a story.
- **Part 2 — Player Experience.** Testimonials, host retrospectives, and psychology-of-
  enjoyment writing about what people say they love in practice. Treated as evidence of
  *reception*, not design authority — kept in a visibly different citation register than
  Part 1 (marketing-adjacent sourcing, not designer reasoning).

## Mapping convention (different from the other two documents)

This material doesn't map onto the P1–P4 literary taxonomy the way novelist/screen craft
does — it's about mechanics and player experience, not plot construction. Entries here map
instead to **game systems already in this project** (see `docs/WIRING.md`):

- **75% Sharing Mechanic** — the core asymmetric-info mechanic
- **Interrogation Phase** — player ↔ AI NPC dialogue
- **Investigation/Scene Phase** — evidence discovery
- **Accusation/Reveal Phase** — competitive, first-to-solve endgame
- **Replayability/Generation** — variety across sessions
- **Host/GM Function** — currently played by the backend (generation + `coherence_validator.py`)
- **Social Dynamics** — player-to-player interaction, not currently modeled by any file
- **Win Condition Design** — competitive-solve vs. cooperative-fun, a real design tension

## Status & sourcing caveat

Same caveat as `SCREEN_CRAFT_FINDINGS.md`: direct `WebFetch` to most article/interview hosts
is blocked by this session's egress policy (403 on CONNECT — confirmed via
`$HTTPS_PROXY/__agentproxy/status`, a policy denial not a site issue). Findings below are
built from `WebSearch`-returned attributed excerpts unless otherwise noted. Verify against
full source text before this feeds any generation prompt.

---

## Part 1 — Design & Mechanics Authority

### Jackbox Games

| Concept | Insight | Maps to game system | Source |
|---|---|---|---|
| Winning is secondary to the shared experience | "When you play a Jackbox game, winning is secondary; the true objective is to get the group to laugh." Their design formula (the "Jack Principles") strips games down to minimize friction and lower the barrier to entry. | **Win Condition Design** — direct tension worth naming: Choose Your Mystery is explicitly competitive (first to solve), whereas Jackbox deliberately deprioritizes winning in favor of collective enjoyment. Not a reason to change the win condition, but worth deciding consciously rather than by default. | [Built In Chicago](https://www.builtinchicago.org/articles/jackbox-games-design-party-pack) |
| Improv's "yes-and" as a design principle | Jackbox regularly hires Second City improv veterans; that training shows up as a house design philosophy — take a player's idea and build on it rather than shutting it down. | **Interrogation Phase** — a concrete prompt-design principle for NPC dialogue: an NPC's response to a player's theory/accusation should build on what the player offered (even to deflect it) rather than issue a flat non-sequitur | [Built In Chicago](https://www.builtinchicago.org/articles/jackbox-games-design-party-pack) |
| Social deduction requires constant rebalancing | "Social deduction games require a lot of balance, and just when you think you've got it figured out, somebody plays in a way you didn't think of and makes you rethink the rules." Identity/hidden-role games are popular with both the team and their audience. | **75% Sharing Mechanic** — a caution: emergent player strategies around a fixed information-sharing rule are likely, and the rule may need retuning after real playtesting rather than being treated as solved by initial design | [Built In Chicago](https://www.builtinchicago.org/articles/jackbox-games-design-party-pack) |

### Murder Mystery Co — "Why Murder Mysteries Are So Fun"

| Concept | Insight | Maps to game system | Source |
|---|---|---|---|
| Ownership through participation | "Every participant has a role to play, even guests without a scripted character still influence the outcome through questions, observations, and deductions" — being part of the story creates ownership, rather than passively consuming a plot. | **Investigation/Scene Phase**, **Social Dynamics** — reinforces that even non-central "witness"-type characters need enough material to meaningfully influence the group's deduction, not just flavor text | [Murder Mystery Co](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/) |
| Mysteries spark social connection without forced icebreakers | The format naturally sparks "conversation, laughter, and collaboration" — players "debate theories, share discoveries, and form alliances" organically. | **Social Dynamics**, **75% Sharing Mechanic** — the sharing mechanic's whole point (forcing collaboration) is validated as something players already do voluntarily in the real-world format when the structure invites it | [Murder Mystery Co](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/) |
| Clues framed as story, not raw data | "Humans are wired to enjoy problem-solving, especially when the clues come in the form of stories, relationships, and secrets" — the puzzle is more engaging when clues are relational/narrative rather than abstract facts. | **Investigation/Scene Phase** — supports `coherence_validator.py`'s existing bias toward evidence with "thin description" warnings; this is independent validation that narrative-framed clues aren't just nice-to-have polish | [Murder Mystery Co](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/) |
| Flexible participation styles, both valid | Some players love staying in character and delivering dramatic accusations; others prefer quietly observing and piecing together the puzzle — both are "equally valid," and no one is pressured to perform. | **Social Dynamics**, **Accusation/Reveal Phase** — a UX principle: the game shouldn't force performative interrogation on players who'd rather work the evidence quietly; both modes need a viable path to winning | [Murder Mystery Co](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/) |
| Shared failure is part of the fun | "Groups bond over shared failure too, as getting the wrong answer creates stories people retell for years, with mistakes becoming inside jokes." | **Accusation/Reveal Phase** — a wrong accusation shouldn't just be a fail-state; consider whether the reveal/resolution text can make a wrong guess entertaining in its own right, not just a loss | [Murder Mystery Co](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/) |

### New concepts flagged (Part 1)

1. **Win Condition Design as a live tension** — Jackbox's "winning is secondary" ethos vs.
   this game's competitive first-to-solve structure isn't a bug to fix, but a design choice
   worth being explicit about — e.g., does the game want *any* mechanism that rewards non-
   winners for a good session (memorable wrong guesses, social credit for good bluffing),
   the way real party mysteries seem to get that "for free"?
2. **Emergent-strategy retuning** — Jackbox's point that hidden-role game balance keeps
   breaking as players find new strategies suggests the 75% sharing rate itself may need
   playtesting-driven retuning post-launch, not just correctness-checking against
   `coherence_validator.py`.

---

## Part 2 — Player Experience

*(pending — parallel capture in progress: testimonials, host retrospectives, and the
psychology-of-enjoyment angle on social deduction games)*

---

## Sources

- Jackbox Games — [Built In Chicago](https://www.builtinchicago.org/articles/jackbox-games-design-party-pack)
- Murder Mystery Co — [Why Murder Mysteries Are So Fun](https://www.murdermysteryco.com/why-murder-mysteries-are-so-fun/)
