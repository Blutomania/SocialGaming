# Mind Your Friends — Interface Style Guide

**What this is.** The rules for how MYF's screens are built: boxes, hover and pressed states,
labels, headings and the small honesty rules that keep a social game trustworthy. They were
worked out on the studio's other title, *Choose Your Mystery* (CYM), over three playtest-driven
sessions in October 2026, and are written here so MYF can adopt them without re-deriving them.

**How to use it.** This file lives at `mind-your-friends/docs/STYLE_GUIDE.md`. Say which screen you are
working on. Every rule below says what to do, why, and how to do it in Godot 4. Where a rule
conflicts with something MYF's own `CLAUDE.md` has already decided, MYF's file wins: ask the
owner rather than overriding it.

**What carries over, and what does not.** The *structure* carries over: how a box behaves, what
a fill means, when a label may appear. CYM's *identity* does not. MYF keeps its own slate ground,
its own accents, its own typefaces and its own voice.

> **One CYM rule that must NOT come across:** CYM bans card-game words (*cards, decks, hands,
> deal, played*) because it is an investigation game and those words made it read like a
> board game. **MYF really is a card game** — sabotage cards and wagers — so in MYF those
> words are accurate and should be used.

---

## 1. Colour roles — name the job, then pick the colour

A colour is chosen for a **job**, never for a screen. Name the roles once, in one file, and have
every screen read from it. In CYM that file is `palette.py`, which generates the Godot constants
and fails a check if any copy drifts. MYF should have the same single source.

| Role | Job | MYF value |
|---|---|---|
| **Ground** | The page itself | Slate `#2F4459` (decided; MYF keeps slate) |
| **Surface** | A box sitting on the ground: rows, panels, buttons at rest | *to decide* — one step lighter than ground |
| **Line** | Outlines of available controls | *to decide* |
| **Ink** | Body text and labels on ground and surface | *to decide* — near-white |
| **Ink, faint** | Small labels, captions, disabled text | *to decide* |
| **Chosen** | "This is the selected one": a toggled choice, a chosen row, a settled stamp | *to decide* — a cool colour |
| **Act** | "Do this": the primary action, and the hover fill of any action | *to decide* — a warm colour |
| **Caution / negative / positive** | Owed, error, met | *to decide* |

**The rule that matters most: Chosen and Act are never the same colour, and never swap jobs.**
If hovering an action fills it with the Chosen colour, the player reads the action as already
selected. In CYM, Chosen is steel blue and Act is brass. MYF needs its own pair, but it needs
the split.

**Contrast floors** (WCAG), checked by a script rather than by eye:

- Body text on its background: **4.5 : 1** at least.
- Large text (about 24px and up) and the outline that *is* a control's affordance: **3 : 1**.
- Ink on the Act colour (text inside a hovered action): **4.5 : 1**. On a light Act colour the
  ink flips to the dark ground colour.
- A colour used only as a tint (a wash behind something, not a signal) has no floor, but **must
  not be the only thing carrying a meaning**.

**Why a script and not eyesight:** CYM's old slate-on-near-black brand colour measured
**1.89 : 1**. It looked fine to everyone and could not be read across a room.

---

## 2. Boxes — outlined means available, filled means chosen

Every interactive thing is a **box** with square corners and a heavy outline (CYM uses a 2px
border and a radius of 0). The box's *fill* is the whole vocabulary:

| State | Looks like | Means |
|---|---|---|
| **Available** | Outlined, surface fill | You can pick this |
| **Hover** | Outline brightens (a choice), or fills with Act (an action) | This is what a click will hit |
| **Chosen** | Filled with Chosen | This is selected |
| **Settled / locked** | Filled with Chosen, and not a button at all — a *stamp* | Done; cannot be changed |
| **Disabled** | Dim outline, deeper fill, faint text, **no hover change** | Not available yet |
| **Live status** | Outlined in ink, no fill, gentle motion | Still happening; will change |

### 2a. A choice is a set of adjoining boxes

Two or more options sit **side by side, touching**, and exactly one is filled. Name *every*
option. CYM had a single toggle that showed its current state as its label (*KEEPING*), and
players could not tell that clicking would change it. Two boxes, **SHARE | KEEP**, fixed it.

- **The default is what happens if the player does nothing.** In CYM, KEEP starts chosen,
  because not sharing is the passive outcome.
- **Godot:** toggle-mode `Button`s in one `ButtonGroup`, inside an `HBoxContainer` with
  `separation = 0`. The theme's `pressed` stylebox is the Chosen fill, so no per-screen styling
  is needed.
- **Gotcha:** a `ButtonGroup` refuses to un-press its pressed member. To flip a choice in code,
  press the *other* option; don't un-press this one.

### 2b. Actions fill with the Act colour on hover

An action button is outlined at rest and **fills with the Act colour on hover**, with its text
flipping to dark ink. It is the one place a fill appears without meaning "chosen", and that is
why it uses the Act colour and not the Chosen colour.

- **Godot:** one theme *variation* (CYM's is `StepButton`). `normal` is outline on surface,
  `hover` fills with Act-bright, `pressed` uses Act-dim, `font_hover_color` is dark ink.

### 2c. A disabled control never lights up

If a disabled button highlights under the cursor it looks clickable, and a player who clicks it
and gets nothing decides the game is broken. CYM's round screen had exactly that confusion.

- **Godot draws `disabled` over `hover`**, so give every button variation an explicit
  `disabled` stylebox (dim outline, deeper fill) and `font_disabled_color`. Then hover cannot
  leak through.

### 2d. Steps in order sit side by side, in order

Two actions that happen one after the other (CYM: *Share selected*, then *Open the next round*)
sit as an adjoining pair, left to right in the order they happen.

- **Two adjoining boxes usually read as "pick one".** The left-to-right order is what says
  "first this, then that"; keep it.
- **Host-only steps are hidden for everyone else**, and the remaining box takes the whole width
  of the pair. A half-empty pair looks broken.

### 2e. Anything irreversible keeps a confirm step

Choosing (SHARE) and committing (*Share selected*) are separate presses when the commit cannot
be undone. Revisit only after a real table has played it.

### 2f. Locked results are stamps, not buttons

A thing that is done and cannot change (an already-shared item, a verdict) is shown as a filled
**stamp**: a `PanelContainer` with the Chosen fill and a label. It is never shown as a disabled
button, which would suggest it might become available again.

### 2g. Live status: outlined, with gentle motion while it lasts

A status that is still happening (*Waiting for players*) is an **outlined notice in ink, with no
fill**, so it reads as open and not as a settled record. It may carry a slow, subtle motion (CYM
uses a shimmer: a slanted band of light crossing the words every four seconds).

- **Motion means "still live" and nothing else.** Remove it the instant the status changes
  (*Starting…*, an error). If nothing else on the screen moves, motion stays a signal.
- **Godot:** a tiny `canvas_item` shader on the one label, removed by setting
  `label.material = null`. No per-frame script work.
- **The colour of the outline is ink, not Act:** nothing here is to be pressed.

---

## 3. Words — honesty rules

A social game runs on trust in what the screen says. In a deduction or trivia game, **a wrong
label works as a wrong answer**: players reason from it.

### 3a. No label without content

A label, heading, tag or row with nothing beside it is **never drawn**. Generated content does
not fill every field every time, so a screen built from it must skip what is empty: a shorter
screen, never a blank with a label on it.

- **Godot:** check `text.strip_edges().is_empty()` before adding the row, rather than adding it
  and hiding it later. When joining parts (*place — date*), join only the non-empty ones, so a
  missing half leaves no stray dash.

### 3b. A label or heading says only what is true, and is built from the data

Before writing a label, check what the data actually contains. In CYM the owner asked for
*"Round 1: You Interviewed a Suspect"*, but every statement in the mystery came from a
**witness**, and no suspect spoke anywhere. The label would have contradicted the suspect list
on the same screen. It became *"You Interviewed a Witness / Found a Clue / Followed a Lead"*,
chosen from the kind of item that player actually received. The real idea (suspect interviews)
was logged as future work, not faked with a label.

- **Build headings from data with a lookup table** (`kind → phrase`). An unknown kind yields
  *no* phrase (rule 3a), never a guess.
- **Use the noun that covers everything the slot can hold.** CYM's *"1 of your 2 clues must be
  shared"* became *findings*, because what a player holds can be a statement or a lead as well.
  In MYF, check whether a slot can hold more than one kind of card before naming it.

### 3c. Quotation marks only around someone's actual words

Statements and quotes go in curly quotes (“ ”). Descriptions of things never do: quoting a
description puts words in nobody's mouth. Strip any quote marks the generator already added
before wrapping, or the text ends up double-quoted.

### 3d. Don't say it twice

If a bar shows progress, don't also caption it (*Cold trail → Warming up → Closing in*). CYM
removed that caption row: it repeated the bar in words and cost a line of screen.

### 3e. Plain headings over lists that grow

A list that accumulates (items held across rounds) gets a **plain heading** (*Your findings*)
with small **group labels inside** (*ROUND 3*, *ROUND 2*, …), newest first. A heading such as
*Round 3 Findings* above a list that also holds rounds 1 and 2 would be false.

### 3f. Name the person; that is the social layer

Attribution is the point of a social game: *Bardsley shared this*, not *1 item shared*. Keep
the **order** of public events (oldest first): the order is the record players read patterns
from (*"she's held back twice now"*). A round number on every line is optional once the order
is kept.

### 3g. A hint is shown only while it is true

*MORE BELOW ↓* appears only while there is more below, and disappears at the end. The same goes
for any "new", "waiting" or "your turn" marker: shown while true, removed the moment it isn't.

- **Godot:** drive it from the `ScrollContainer`'s `VScrollBar` (`changed` and `value_changed`
  signals): visible when `value + page < max_value - a few px`.
- **Check the glyph exists in the font first.** CYM's prose face had no ↓ arrow and its
  condensed face did. A missing glyph renders as a box or as nothing. A ten-line `fontTools`
  script can check every font for a character.

### 3h. Lead with the event, then answer the questions

An opening screen starts on the thing that happened in one line, then answers the reader's
questions in their natural order. CYM's case brief went from *scene, crime, when, found* to
**CRIME, then WHO / WHAT / WHERE / WHEN**. Put the long atmospheric paragraph after the facts,
not before them.

---

## 4. Pictures and brand

- **An icon says what *kind* of thing something is, never *which* one.** Picking at random
  within a set (a portrait for a person, an object for a thing) is deliberate: a fixed icon per
  item would let a glance at someone's screen give away what they hold. In MYF, check this
  before giving a specific card a specific picture.
- **One brand mark, everywhere, from one file.** Every screen that shows the logo loads the
  *same* asset, so when the artist's version arrives it replaces all of them at once. Typing out
  the game's name where the mark should be was a CYM note.
- **Contrast-check the mark against the ground it sits on**, and against a header band if it
  sits on one (a band is a lighter surface, which lowers contrast).
- **Placeholders say they are placeholders.** An empty image slot is labelled *FPO* (for
  position only) rather than left blank, so nobody mistakes the gap for a bug.

---

## 5. Layout for a room, not a desk

- **The whole row is the hit target**, not just the small button at its end: people point at
  the text from a sofa.
- **Long text wraps; nothing pushes the column wider.** A label that cannot wrap sets its
  container's minimum width, and in Godot that silently overflows the window. Give long labels
  `autowrap_mode = TextServer.AUTOWRAP_WORD_SMART`, and measure a generated title rather than
  trusting its length.
- **Cap the reading column's width** (CYM: at most 1000px, centred), so a wide monitor gets
  margins rather than a metre-long line of prose.
- **Keep the brand mark's corner clear**: the column's side margin never drops below the mark's
  footprint.

---

## 6. Godot 4 failure modes that give no error

Each of these cost CYM a screen. None produces an error message.

| Failure | What you see | Guard |
|---|---|---|
| A GDScript parse error | The scene draws its static nodes and nothing responds | Run a parser (`gdparse` from `gdtoolkit`) over every changed script |
| A `#` comment line in a `.tscn` | The node declared after it silently disappears | Never comment a `.tscn`; put the reasoning in the script |
| A theme item name the engine does not have | The control keeps its default look | An editor script that applies the theme and reports misses (Godot 4.7's `Button` has no `hover_pressed`, for example) |
| `TextureRect` with the default expand mode | One large SVG sets the whole column's width and overflows the window | `expand_mode = TextureRect.EXPAND_IGNORE_SIZE` on every image added in code |
| `:=` inferring `Variant` from `Dictionary.get()` | A parse-time failure that kills the screen | State the type: `var x: String = str(d.get("k", ""))` |
| A triple-quoted string in GDScript | Parsed as a stray expression | Put shaders in a `.gdshader` file and `preload()` it |
| Opening the project in Godot 4.7 | `project.godot` is rewritten and its comments deleted | Discard that diff; keep documentation elsewhere |

Also keep theme building in one autoload (CYM's `Style.gd`) that builds a `Theme` from the
palette and sets it on the scene-tree root. Then every screen restyles with no `.tscn` edited,
and a screen's script adds only what is truly unique to it.

---

## 7. The live-update rule (server side)

A screen that only re-reads state after its **own** actions never sees what anyone else did. In
CYM this stalled a whole playtest: other players' shares never reached the host screen, because
every broadcast from a plain `def` FastAPI route was silently dropped. A worker thread has no
event loop, and the error was swallowed.

**MYF's `server_py/main.py` already does this right**: it captures the main loop at startup and
hands broadcasts to it with `run_coroutine_threadsafe`. Keep it that way, and keep **one test
that listens** on a player's socket while *other* players act over HTTP. A test that polls state
can never catch a dropped push.

---

## 8. Checklist for a new or reworked screen

1. Every colour comes from a named role, and no hex value is typed into the screen.
2. Choices are adjoining boxes with every option named and a sensible default chosen.
3. Actions fill with the **Act** colour on hover; nothing fills with **Chosen** on hover.
4. Every button variation has an explicit `disabled` look that does not react to hover.
5. Irreversible actions have a confirm step; locked results are stamps.
6. No label, heading or row is drawn without content.
7. Every label and heading was checked against the data it describes.
8. Quotation marks only around real speech.
9. Hints and live markers disappear the moment they stop being true; motion means "live".
10. Icons say kind, not identity; the brand mark comes from the one shared file.
11. Long text wraps and the column has a maximum width.
12. Parser run, theme misses checked, and the screen loaded in the engine before calling it done.
