# Night File — the CYM style guide

**What this is.** The look of the Godot host screen and, for colour only, the phone client:
which colour means what, which face sets which text, and which parts every screen is built from.
Decided in Session 47 (item 36), from the owner's annotated screenshots of *Red Flags*
(predictredflags.xyz). The aim is to **emulate, not copy**: borrow the structure that makes that
game read from across a room, and replace its colour, its type and its voice with CYM's own.

**Where the values live.** Not here. `palette.py` decides every colour, size and width;
`scripts/build_palette.py` generates `godot/scripts/theme/Palette.gd` and `mobile.html`'s CSS
from it; `godot/scripts/autoloads/Style.gd` turns those into the Theme every screen wears. This
file says what the values are *for*. If it and `palette.py` disagree, `palette.py` is right and
this file is stale.

**The visual version** of this guide, with clickable components and three CYM screens mocked
up, is an artifact owned by the owner: *CYM Night File*.

---

## The one rule

**Outlined means "you could choose this". Filled means "chosen".**

Everything else follows from it. A tile, a row, a suspect card: at rest it is an outline; chosen,
it fills with steel and glows. Selection is carried by fill, border *and* halo together, never by
hue alone.

---

## Colour — two warm notes on a cold ground

| Role | Token | Value | Means |
|---|---|---|---|
| Ground | `GROUND` | `#0C1118` | Night. The room. Painted as the viewport clear colour, before any Control exists |
| Brand hue | `SLATE` | `#2F4459` | The tint: result bars, the wash behind a chosen row. Was the ground until Session 47 |
| Panels | `SURFACE` / `SURFACE_DEEP` / `SURFACE_RAISED` | | Rows and panels one step up; wells one step down; hover |
| **Chosen** | `STEEL` | `#46678A` | A chosen tile, a toggled row, a stamp, the investigation's progress |
| Accent as text | `STEEL_BRIGHT` | `#759BC8` | Counts, IDs, a "Sharing" state; the focus ring |
| **Act** | `BRASS` | `#C9A227` | The primary button, and the game's and the mystery's own name. Nothing else |
| Ink | `INK` | `#F0EADF` | Warm paper — a case file against the cold blue |

**Steel says "chosen", brass says "act".** That split is the owner's (Session 47): brass kept the
primary action rather than being retired to one reveal. Keeping the two meanings on two colours
is what lets a screen hold a row of chosen tiles *and* a call to action without either
competing.

**Why steel is slate lifted, not slate.** Slate at its own value reads at 1.89:1 against Night —
fine for a tint, invisible as a selection. `#46678A` is the same hue (210°) lifted until it
matched the reference accent's own ratios: 3.22:1 against the ground (that red: 3.36) and 4.92:1
for ink on top of it (that red: 4.96).

**Every pair is measured.** `scripts/test_palette.py` holds 33 ink/background pairs to their WCAG
floors. Re-pitch a colour and the consequence is a failing test, not a squint.

---

## Type — three faces, three jobs

| Face | Where | Why |
|---|---|---|
| **Cinzel Decorative Bold** | Every title: the game's name, a screen's title, a mystery's title, the verdict | The owner's face, and kept over a condensed gothic by the owner's call. `TitleLabel` joined it in Session 47 on the owner's markup |
| **Archivo Narrow** SemiBold/Bold | Buttons, choices, section headers, field labels, list rows | The reference's punch is condensed type on everything read at a glance. Added Session 47; OFL 1.1, static instances from the foundry's repo |
| **Nunito Sans** | Prose: witness statements, case briefs, transcripts | A paragraph set condensed is a chore from a sofa. Unchanged |

Cinzel Decorative has no true lowercase; lowercase renders as small caps. That is why free-typed
names and the room code stay out of it (see `Style.gd`).

---

## Shape

- **Square.** Every radius is 0 (`palette.RADIUS`), kept as a scale so a return to rounding is
  one edit.
- **Two line widths.** `BORDER_WIDTH` 2 for outlines, because in this look the outline *is* the
  affordance; `RULE_WIDTH` 1 for dividers, a rule the eye reads past.
- **The glow** is `StyleBoxFlat`'s own shadow: one draw call, no per-frame cost.

---

## The parts every screen is built from

Theme-level (done — every screen gets these with no `.tscn` edited):

| Part | How |
|---|---|
| **Choice tile** | Any `Button` with toggle mode. Its `pressed` box is the chosen state, so a `ButtonGroup` of plain buttons is a set of tiles |
| **Primary action** | `PrimaryButton`: brass, condensed, one size up. One per screen |
| **Progress** | `ProgressBar`: steel over a deep trough. Rounds in APF, the question budget in the gather loop |
| **List row, suspect card** | `BrowseRowButton`, `SuspectCardButton`: condensed, and chosen means steel |

Scene-level (built on the screens named; each is drawn in that screen's script):

| Part | What it is | Where |
|---|---|---|
| *ID column* | Left of a row's text, split by a vertical rule. On ApfRound it holds a **kind icon** (Session 49): a witness portrait for a statement, a clue image for a clue or lead — the set says the kind, never which finding. ResultScreen still shows the ID (E3, L1, W) from `GameState.finding_display_id()` | ApfRound, ResultScreen |
| *Finding row* | ID column, the finding (title, kind — WITNESS STATEMENT / CLUE / LEAD — and its text, a statement in quotation marks), and adjoining **SHARE \| KEEP** choice tiles, KEEP chosen by default; a shared finding shows a locked SHARED stamp instead. The whole row is the hit target. Grouped newest first under ROUND N labels. `FindingRow`, `FindingRowChosen`, `FindingRowShared` | ApfRound; ResultScreen for findings kept back |
| *Progress* | Round progress, the bar alone. The caption row (*Cold trail*, *Closing in* …) was removed in Session 49: it said in words what the bar shows | ApfRound |
| *Step pair* | `StepButton`: adjoining outlined boxes that fill **brass on hover** — Share selected, then Open the next round. Disabled stays an unfilled dim outline, so a step not yet earned never lights up | ApfRound |
| *Stamp* | A steel block under the verdict: *Kept back — Sam sat on …*, or *Nothing kept back*. `StampPanel` | ResultScreen |
| *Notice* | The stamp's outline with no fill, in ink: a live state that will change, not a statement of record. The words shimmer while the state holds and stop when it changes. `NoticePanel` | Lobby (*Waiting for Players*) |
| *Ledger* | Label-and-value rows with hairlines: accusation, culprit, rounds, time, what you shared and kept back | ResultScreen |
| *Choice tiles* | `ChoiceTileButton`: Play / Create, Solo / With friends; Easy / Medium / Hard in place of the difficulty dropdown | MainMenu, MysteryGeneration |
| *Field label* | `FieldLabel`: white, condensed, caps via the Label's own `uppercase` flag — the label over a form field is the instruction, not a footnote | MysteryGeneration |
| *Roster rows* | A player as a finding row: seat number in the ID column, name as big as the room code | Lobby |
| *Brief* | Header band (the graphic logo, page count), the mystery's name at display size, one scrollable box of ID-column rows, and two boxes at the foot: BACK / NEXT, NEXT turning brass on the host's last page | CaseBrief |

Decided against (owner, Session 47):

| Part | Why not |
|---|---|
| *Result bar* | A slate fill inside a row, as wide as the share of the room that accused each suspect. Cut: it needed a server route, and a game ends at the first correct accusation, so most tables would have seen one or two bars |

---

## No label without content

A label with nothing beside it is never drawn (owner, Session 49). Generated mysteries do not all
fill the same fields, so a screen built from one must skip a row, a heading or a tag whose content
is empty — a shorter screen, never a blank. CaseBrief's rows, ApfRound's kind label and round
heading all follow it.

---

## Voice

Deadpan case report, not roast. The verdict names who you accused (*Not Cadan.*), not a
judgement. A heading reports what happened, and only what did: ApfRound's *Round 2 of 4: You Found a Clue*
names the kind of finding actually assigned — never one the mystery does not contain (item 37). And the vocabulary rule in `CLAUDE.md` holds here too: no cards, no decks, nothing is
*played*.

---

## What we took and what we left

| Taken from the reference | Left behind |
|---|---|
| Filled = chosen, outlined = available | Its red |
| Square corners, heavy outlines | Its typefaces |
| An ID column on every row | Its roast voice and its terms (karma, coward, flagged) |
| A one-line verdict with a stamp under it | The confidence slider — our bar measures the investigation, not a bet |
| The result bar inside the row | Its warm near-black |

---

## Still to do, and known gaps

- **ApplyTheme ran on the owner's machine (Session 47): 223 items across 51 types, two misses.**
  Both were a `hover_pressed` stylebox (on `Button` and `SuspectCardButton`), an item Godot 4.7's
  Button does not have — removed, so a chosen tile under the cursor simply stays chosen. Fonts:
  Nunito Sans and Cinzel Decorative reported loaded; the report now also checks Archivo Narrow,
  which it did not know about. Re-run after pulling to confirm `MISSES none`. `VerifyScenes.gd`
  and a full F5 walk are still to come.
- **Hard-coded colours that bypassed the theme** — all five fixed in Session 47. One deserves a
  note: the moderation notice carried a grey override from before the palette existed (Session 34)
  that masked the caution colour Session 37 gave it on purpose, so item 17's "visible" notice was
  rendering as a footnote. The override is gone. **Later the same session the owner set it white and
  all-caps** with the other form labels (`FieldLabel`) — 15.8:1 on the ground, so more visible than
  the amber was, which is what item 17 actually asks of it.
- **MYF no longer shares CYM's ground.** Accepted. `scripts/check_brand_contrast.py --myf` still
  grades a shared mark against slate.
- **The BACKGROUND field (item 17)** was pitched for slate and is untuned against Night. It is
  stage 3 and wired to nothing.
