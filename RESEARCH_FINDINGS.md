# Choose Your Mystery - Research Findings

## Overview

This document memorializes research conducted into the structural anatomy of mystery fiction, grounded in the words of major mystery writers. The goal is to establish a **writer-authoritative taxonomy** that can drive extraction protocols for the mystery database pipeline.

---

## Writer-Grounded Mystery Taxonomy

The taxonomy is organized coarse-to-fine, with writers as the source of authority.

### COARSE PARTS (C1–C6) — Structural Skeleton

Every writer, regardless of tradition, consistently names these as the load-bearing structure:

| # | Part | Who Names It |
|---|---|---|
| C1 | **The Crime** — type, method, and the question it poses | Christie (start with method), P.D. James (central mysterious crime), Knox (rule 4: method must be plausible) |
| C2 | **The Victim** — who they are and why they were killable | P.D. James explicitly: "I like to show what makes the victim the victim... there's got to be a motive for this appalling crime" |
| C3 | **The Closed World** — the bounded space of suspects and setting | James: "closed circle of suspects"; Rankin: Edinburgh as character; French: location as first decision |
| C4 | **The Culprit + Motive** — the real answer, constructed first | Christie: start with murderer and motive, then build outward; worked backward from the solution |
| C5 | **The Resolution** — how order is restored and by whom | James: "not by luck or divine intervention — by human intelligence"; Chandler: the detective as lone moral agent |
| C6 | **The Detective/Investigator** — the lens through which the reader moves | Chandler: "down these mean streets a man must go"; French: the detective's POV is not intrinsically heroic |

---

### MEDIUM-FINE PARTS (M1–M8) — Tactical Construction Elements

These appear consistently but require craft decisions at the story level:

| # | Part | Who Names It |
|---|---|---|
| M1 | **Suspect Architecture** — number, spread of means/motive/opportunity | James: "each with motive, means and opportunity"; Knox: criminal must appear early |
| M2 | **The Red Herring** — deliberate misdirection, not accidental | Christie: notebooks show she planned false trails explicitly before writing |
| M3 | **Clue Fairness** — every clue available to reader when detective sees it | James: "the detective can know nothing which the reader isn't also told"; Knox commandment 8 |
| M4 | **The Social World** — power structures, hierarchies, who owes whom | Rankin: Edinburgh class/institutional power; James: patronage networks |
| M5 | **The Alibi** — false or genuine, structural function in ruling suspects in/out | Christie notebooks: alibi construction is explicit planning step |
| M6 | **The Reveal Mechanic** — how the solution is demonstrated, not just stated | Christie: often a technical or psychological impossibility exposed; French: revelation timing (2/3 through) |
| M7 | **Media/Audience** — how the crime is perceived by the world around it | Flynn: "the packaging of tragedy... the need for a heroine and villain"; Chandler: corrupt institutions |
| M8 | **The Detective's Wound** — what the case exploits in the investigator | French: "the situation puts pressure on the character's weak spots"; Rankin: Rebus aging in real time |

---

### FINE PARTS (F1–F12) — Granular Craft Decisions

These are the things writers name when discussing specific books, not the genre in general:

| # | Part | Who Names It |
|---|---|---|
| F1 | **Victim's Enemies** — the specific web of people with grievance | James: "someone who has made enemies... important to show why" |
| F2 | **Suspect's Wound** — each suspect needs a plausible reason to look guilty | French (strongly implied): pressure on weak spots applies to suspects too |
| F3 | **The Unreliable Frame** — whose account of events can't be trusted and why | Flynn: "both narrators are consummate liars"; French: "we're all unreliable narrators" |
| F4 | **The Setting as Constraint** — how the physical/social world limits possible actions | Rankin: prison as structural constraint ("that was partly the fun of it"); Christie: closed environments |
| F5 | **The Evidence Type** — physical, testimonial, forensic, documentary | Christie notebooks: she classified evidence types as a planning step |
| F6 | **The False Suspect** — one character who bears maximum suspicion but is innocent | Christie: planted to protect real culprit; Knox: criminal must not be whose thoughts we know |
| F7 | **The Technical Detail** — the specific knowledge that makes the method possible | Knox commandment 4 (no unexplained science); Christie: expertise-as-alibi-builder |
| F8 | **The Moral Ambiguity** — why the culprit is understandable, not just evil | Chandler: "flexible conception of right and wrong"; James: "shift from who to why" |
| F9 | **The Sidekick/Foil** — the Watson function: slightly below reader intelligence, transparent thoughts | Knox commandment 9; Chandler: confidant who often perishes |
| F10 | **The Cascade of Deaths** — secondary crimes that follow the primary | Chandler formula: "deaths usually occur in a cascade" |
| F11 | **The Public Spectacle Moment** — when the crime enters a wider social stage | Flynn: media as Greek chorus; Rankin: institutional exposure |
| F12 | **The Inciting Image** — the single vivid scene the writer started from | Flynn: "a man coming home and the door is wide open"; French: the battered suitcase in the skip |

---

## Cross-Writer Consensus

These elements appear in 3+ writers and should anchor the extraction protocols:

1. **Victim construction** (James, Christie, French)
2. **Motive-first plotting** (Christie, James, Chandler)
3. **Closed world / setting as constraint** (James, Rankin, French, Christie)
4. **Clue fairness / evidence planting** (James, Christie, Knox)
5. **Character wound** (French, Rankin, Chandler)
6. **Red herring as planned architecture** (Christie, Knox, Flynn)
7. **Resolution as restoration of order** (James, Chandler, Knox)

---

## Proposed Four Extraction Protocols

| Protocol | Granularity | Parts Count | Grounded In |
|---|---|---|---|
| **P1: Skeleton** | Very coarse | C1–C6 (6 parts) | James's structural definition + Christie's backward method |
| **P2: Architecture** | Medium-coarse | M1–M8 (8 parts) | Christie notebooks + Knox commandments |
| **P3: Craft** | Medium-fine | F1–F8 (8 parts) | French, Flynn, Rankin interviews |
| **P4: Texture** | Very fine | F9–F12 + new (4–6 parts) | Chandler, Flynn on voice/atmosphere |

---

## Next Tasks

1. Update codebase docs/todo lists with the new extraction protocols (P1–P4)
2. Revise the HuggingFace Spaces UI to replace the generate button with a text input field

---

## Sources

- *How Christie Wrote* — Agatha Christie
- *Agatha Christie's Secret Notebooks* — Slate
- *P.D. James, Talking And Writing 'Detective Fiction'* — NPR
- *The Salon Interview* — P.D. James
- *Ronald Knox: 10 Commandments of Detective Fiction* — Gotham Writers Workshop
- *The Simple Art of Murder* — Raymond Chandler (PDF)
- *Tana French on Embracing Discomfort* — CrimeReads
- *Tana French: We're All Unreliable Narrators* — CrimeReads
- *Gillian Flynn* — BookPage
- *Interview with Ian Rankin* — Writers & Artists
