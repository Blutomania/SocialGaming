# Choose Your Mystery — Screen & TV Craft Findings

## Overview

Companion to `RESEARCH_FINDINGS.md`. That document grounds the extraction taxonomy
(`extraction_protocols.py` P1–P4) in the words of prose mystery novelists. This document
extends the same grounding to **filmmakers, screenwriters, and showrunners** of successful
mystery films and television — feeding the RAG generation-grounding layer scoped in
`SESSIONS.md` Session 18 / `CLAUDE.md` Current To-Do item 10.

Purpose: give the mystery generator craft authority beyond structural completeness
(what `coherence_validator.py` already checks for free) — e.g. *how* a fair-play clue
should actually be planted, not just that a clue exists.

## Status & sourcing caveat

**Capture in progress.** Direct `WebFetch` of the source articles is blocked by this
session's egress policy (403 on CONNECT to hosts like theringer.com, scriptmag.com,
nofilmschool.com, aframe.oscars.org, cbr.com, freshfiction.tv — confirmed via
`$HTTPS_PROXY/__agentproxy/status`, not a site-side block). `WebSearch` is unaffected and
returns attributed excerpts/quotes from these same articles, so all entries below are
built from search-engine-returned snippets of the cited pages, not full-text fetches.

**Before this feeds any generation prompt**, verify quotes against full source text
(e.g. via a browser, archive.org, or a session without this egress restriction) — treat
everything below as accurately-attributed-per-search-snippet, not manually verified
verbatim.

---

## Rian Johnson — *Knives Out*, *Glass Onion*, *Poker Face*

| Concept | Insight | Maps to taxonomy | Source |
|---|---|---|---|
| Whodunit's structural weakness | Started from Hitchcock's critique that whodunits rely on one surprise at the end — a narrative weakness. His answer: a film that "begins as a traditional whodunnit and orients the audience very clearly, and then turns into a Hitchcock thriller where there's a character you care about." | Extends **C5 Resolution** / **M6 Reveal Mechanic** — the reveal isn't just a solved puzzle, it's earned emotional payoff | [ScriptMag](https://scriptmag.com/interviews-features/rian-johnson-talks-screenwriting-and-what-classic-movies-can-teach-us) |
| Visual fair play | "Feels like fair game to use the strength of cinema to do things visually that you cannot in books." Plays fair by hiding clues in **sound** — a technique with no prose equivalent. | Extends **M3 Clue Fairness** with a screen-specific corollary: fairness can be medium-native (visual/aural), not just textual | [No Film School](https://nofilmschool.com/rian-johnson-knives-out-screenplay) |
| Clues hidden in plain sight | Buries slighter clues inside jokes; prefers a visual clue the camera "zooms in on" that "was there the whole time because you could have seen it" — audience should be able to notice clues on first viewing even without knowing their relevance yet. | **M3 Clue Fairness**, **M2 Red Herring** (misdirection via comedic beat, not just plot) | [No Film School](https://nofilmschool.com/rian-johnson-knives-out-screenplay) |
| Reveal must feel earned, not just correct | Big dénouement is "only satisfying if it feels like audiences are connecting dots that they recognize" — not merely told the answer. | **C5 Resolution**, **M6 Reveal Mechanic** | [No Film School](https://nofilmschool.com/rian-johnson-knives-out-screenplay) |
| Mystery is underneath, not on top | Prioritizes the mystery being "visually engaged with great actor material and dialogue, with the mystery placed underneath all that stuff" — structure should feel invisible to a first-time viewer. | New concept, not in current taxonomy — candidate for a screen-specific "load-bearing but invisible structure" note | [PBS On Story](https://www.pbs.org/video/reinventing-the-classic-whodunnit-a-conversation-with-rian-johnson-7vtzs4/) |
| Character-first ensemble | Considers piecing together a fully-realized ensemble "one of the most rewarding aspects of the genre" — wants every actor to get material worthy of their talent, not just a suspect slot. | **M1 Suspect Architecture** — extends it: suspects need actorly material, not just means/motive/opportunity coverage | [PBS On Story](https://www.pbs.org/video/reinventing-the-classic-whodunnit-a-conversation-with-rian-johnson-7vtzs4/) |
| Theme drives structure | Starts from theme and uses the mystery's structure itself to engage deeper thematic material, rather than bolting theme onto a finished plot skeleton. | New concept — no direct P1–P4 analogue; candidate addition | [PBS On Story](https://www.pbs.org/video/reinventing-the-classic-whodunnit-a-conversation-with-rian-johnson-7vtzs4/) |
| Howcatchem vs. whodunit | On *Poker Face*: "as opposed to a whodunnit like *Knives Out* or *Glass Onion*, where you have an ensemble of eight or nine suspects and you have to juggle all of them," the benefit of the howcatchem format — audience sees who did it and how the detective catches them — "is that there's only one suspect." Term "howcatchem" (inverted detective story) coined by Philip MacDonald. | **New structural mode**, not covered by P1–P4 at all — the whole taxonomy currently assumes whodunit (culprit hidden from player until resolution). A howcatchem mode would need its own protocol variant if the game ever supports it. | [The Ringer](https://www.theringer.com/2023/01/25/tv/rian-johnson-interview-poker-face-peacock-natasha-lyonne) |
| Villain as full character | Cites *Columbo* as inspiration: the inverted format "allowed them to give screen time to the villain and to have them be built into a substantial character and play out the dynamic between them and Columbo." | **C4 Culprit + Motive** — extends it: even in a standard whodunit, the culprit benefits from being written with this much interiority, not just a motive line | [The Ringer](https://www.theringer.com/2023/01/25/tv/rian-johnson-interview-poker-face-peacock-natasha-lyonne) |

### New concepts flagged for taxonomy consideration

None of these exist in `extraction_protocols.py` P1–P4 yet — surfacing them here rather
than silently editing the taxonomy:

1. **Medium-native clue fairness** — fairness delivered through visual/aural information
   the player can *notice* (not just be told), distinct from prose's M3 definition.
2. **Invisible structure** — the mystery skeleton should not be visible as a skeleton to
   the player on first pass; craft is in the concealment as much as the construction.
3. **Howcatchem as a second structural mode** — currently out of scope (the game is
   whodunit-only), but worth a one-line note in `docs/WIRING.md` if genre variants are
   ever discussed.

---

## Steven Moffat — *Sherlock*

*(pending — parallel capture in progress)*

## John Hoffman — *Only Murders in the Building*

*(pending — parallel capture in progress)*

## Chris Chibnall — *Broadchurch*

*(pending — parallel capture in progress)*

## Nic Pizzolatto — *True Detective*

*(pending — parallel capture in progress)*

## Anthony Horowitz — *Magpie Murders*, *Foyle's War*, *Midsomer Murders*

*(pending — parallel capture in progress)*

---

## Sources

- Rian Johnson — [ScriptMag](https://scriptmag.com/interviews-features/rian-johnson-talks-screenwriting-and-what-classic-movies-can-teach-us), [No Film School](https://nofilmschool.com/rian-johnson-knives-out-screenplay), [PBS On Story](https://www.pbs.org/video/reinventing-the-classic-whodunnit-a-conversation-with-rian-johnson-7vtzs4/), [The Ringer](https://www.theringer.com/2023/01/25/tv/rian-johnson-interview-poker-face-peacock-natasha-lyonne)
