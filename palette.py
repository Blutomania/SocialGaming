"""
palette.py — the one CYM palette, and the only place a colour is decided.

WHY THIS FILE EXISTS. Before it, the product held three unrelated palettes and
none of them knew about the others:

  1. brand/README.md and scripts/check_brand_contrast.py declare the ground to
     be slate #2F4459, and call it "the one rule these assets must satisfy".
  2. server/static/mobile.html — the phone client every player actually looks
     at — was built on an invented navy #1a1a2e with its own blues and its own
     brass #c8a96e (note: not the brand's #C9A227, one digit-pair off and
     visibly warmer).
  3. The Godot host screen had no palette at all. Default engine grey, which
     is what "it ran, it's ugly, but it works" was describing.

So the two clients in the same room, at the same time, showed two different
games, and the documented standard was the one surface nobody rendered. That
is not a styling backlog, it is drift — and it is exactly the failure
brand/README.md predicts in its own opening paragraph, about why the source
artwork does not live inside either client's folder. The same argument applies
to the colours, so they live here, once.

WHAT IMPORTS THIS. Nothing renders from here directly, because two of the
three surfaces are not Python. scripts/build_palette.py generates
godot/scripts/autoloads/Palette.gd and the CSS custom-property block in
mobile.html from these values, and `--check` on that same script fails if
either has drifted from this file. Generated-then-checked rather than
imported, because GDScript and CSS cannot import Python and a comment asking
people to keep three files in step is how you get three palettes again.

ZERO API COST. Pure data and arithmetic.
"""

from __future__ import annotations

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# The ground
# ---------------------------------------------------------------------------

# Night — a blue-black in slate's own hue (210°). Owner's call, Session 45,
# taking the "Night File" direction (docs/STYLE_GUIDE.md): a loud, square,
# high-contrast party-game look in which ONE saturated accent does the work of
# selection, and an accent can only do that on a near-black ground.
#
# It REPLACES slate #2F4459 as the ground; slate itself survives as SLATE
# below, the brand hue, now used as a tint. What moved with it, so nothing is
# graded against a ground no client paints: brand/README.md's rule and
# scripts/check_brand_contrast.py's default both name this value. What did NOT
# move: MYF keeps slate as its ground, so the two titles no longer share one
# (accepted, Session 45), and background_field.py's five marks were pitched for
# slate and are untuned against this — item 17, stage 3, wired to nothing yet.
GROUND = "#0C1118"

# Slate, the brand hue. Lifted as a fill it is STEEL (the accent); at its own
# value it is the tint — result bars, the wash behind a chosen row. As a
# background on Night it reads at only 1.89:1, which is the point: a tint
# should be felt, not read.
SLATE = "#2F4459"


# ---------------------------------------------------------------------------
# The surface ramp
# ---------------------------------------------------------------------------
#
# Panels sit one step LIGHTER than the ground. On slate they had to sink,
# because slate was a mid-tone and ink on it tired the eye over a transcript
# (8.5:1); on Night ink is already 15.8:1, so that reason is gone and the
# conventional order returns. The steps are deliberately small: in this look a
# row is told apart by its 2px outline, not by its fill.
#
# Wells (transcripts, feeds) still sit BELOW the panel they are inset in, so
# the eye has an edge to hold — the one part of the old reasoning that was
# about reading, not about slate.

SURFACE = "#131B25"        # rows, panels — the default place text sits
SURFACE_DEEP = "#0F151D"   # inset wells: transcripts, feeds, evidence lists
SURFACE_RAISED = "#1E2B3A"  # hover, the row under the cursor

# Two border weights, and the split is a contrast requirement rather than a
# taste one. WCAG 1.4.11 asks 3:1 of anything that is the ONLY thing marking a
# control's boundary — which is true of a LineEdit, whose outline is its whole
# affordance, and false of a panel edge, where the fill change already does the
# separating. Holding both to 3:1 made every panel edge a bright rule the eye
# traced instead of reading past; holding neither to it made text fields
# invisible. So LINE is for controls and is measured; LINE_SOFT is decorative
# and deliberately carries no floor.
LINE = "#56789C"       # control boundaries: inputs, outlined buttons, focus
LINE_SOFT = "#3B5068"  # row and panel outlines, dividers — no contrast contract


# ---------------------------------------------------------------------------
# Ink
# ---------------------------------------------------------------------------
#
# Three weights, not five. Every extra tier is a decision someone has to make
# at every label, and the ones below are already separated by enough contrast
# to be told apart at a glance.

INK = "#F0EADF"        # body and headings — warm paper against the cold blue
INK_MUTED = "#A9B6C3"  # secondary — supporting prose, inactive tabs
INK_FAINT = "#7D8B99"  # tertiary — field labels, timestamps, attribution
#
# INK is WARM on purpose: a case file's paper, and the one place the warm side
# of the palette shows outside brass. The two lower tiers stay cool so they
# recede into the blue rather than competing with the ink.
#
# On Night all three clear 4.5:1 on the ground itself, which on slate INK_FAINT
# could not (3.86:1). It stays "faint" by role, not by necessity: labels,
# never prose. contrast_report() below prints the whole matrix so this stays a
# measured decision rather than a remembered one.


# ---------------------------------------------------------------------------
# Accent
# ---------------------------------------------------------------------------

# Brass. The one warm note in the whole product, and it is rationed on purpose
# — background_field.py gives it an 8% share of the marks and its comment
# records why the first pass at 16% failed ("the warm marks read as a
# different, louder element rather than as part of one texture"). The same
# restraint applies here: brass means "this is the thing to act on" or "this
# is the mystery's own name". If it starts appearing on every panel it stops
# meaning anything.
BRASS = "#C9A227"
BRASS_BRIGHT = "#E3BC42"  # hover/focus only
BRASS_DIM = "#8A6F1B"     # pressed, and disabled-but-still-primary

# Steel — the selection accent, and the colour that does what red does in the
# look this palette borrows from. Brass says "act"; steel says "chosen": a
# filled choice tile, a toggled row, a stamp, the investigation's progress.
# Owner, Session 45: brass KEEPS the primary action, so the two never compete
# for one meaning.
#
# It is slate lifted to the reference accent's own contrast: 3.22:1 against
# Night (that red: 3.36) and 4.92:1 for ink on top of it (that red: 4.96).
STEEL = "#46678A"     # a FILL, so it is pitched dark enough for INK to sit on it
STEEL_BRIGHT = "#759BC8"  # the accent as TEXT and small marks; hover on fills


# ---------------------------------------------------------------------------
# Semantic
# ---------------------------------------------------------------------------
#
# Pitched into the slate family rather than taken off the shelf. mobile.html's
# #4caf50 and #e05050 are Material defaults; against this ground they read as
# stickers on the design rather than parts of it, because their saturation is
# far above anything else on screen.

# These are LIGHTER than a semantic colour usually looks. That was forced on
# the slate ground, where a saturated red could not reach 4.5:1 at all; on
# Night it no longer is (each clears 6:1 on every surface), and they were KEPT
# rather than re-saturated so that the phone and the host, and every screenshot
# from the slate era, read as one product. Each was tuned by walking lightness
# at fixed hue, so they stay in family rather than becoming three stickers.
POSITIVE = "#64AA7B"  # a clue that reached you, a connected socket
NEGATIVE = "#D58689"  # an error, a wrong accusation, a duplicate
CAUTION = "#CB8F44"   # a budget running out, an unmoderated-input notice
#
# NOT CARRIED BY HUE ALONE. POSITIVE/NEGATIVE mark things a player acts on —
# a shared clue against a duplicate one — and red/green is the one pair a
# common colour blindness collapses. mobile.html already pairs them with
# strikethrough and a border-side marker; anything new must carry a second
# signal too.


# ---------------------------------------------------------------------------
# Type scale
# ---------------------------------------------------------------------------
#
# Sized in pixels for the Godot host screen's 1280x720 viewport, and for that
# screen only. The phone client is NOT generated from this and keeps its own
# em-based sizing, which is a deliberate limit rather than an omission: the two
# surfaces are read at completely different distances, so 44px is barely a
# title on a television across a room and absurd on a handset. Colour is the
# thing that must agree between them — a player looking from phone to TV sees
# one game or two — and type size is the thing that must not.

TYPE_SCALE: Dict[str, int] = {
    # The main menu wordmark, and whatever else earns the same weight: the
    # room code, and a player's own name in the lobby (Session 43, owner --
    # "who you are playing with is high up in a hierarchy of import"). Not a
    # size for casual reuse; each addition has been a deliberate call that
    # something belongs at the top of the screen's hierarchy, not a default.
    "display": 44,
    "title": 30,    # one per screen, at the top
    "heading": 21,  # section headers within a screen
    "body": 18,     # the default; everything unlabelled is this
    "label": 13,    # field labels, attribution, timestamps
}

# Spacing, in the same spirit: a short scale people can hold in their head.
SPACE: Dict[str, int] = {
    "tight": 4,
    "small": 8,
    "base": 12,
    "wide": 16,
    "section": 24,
    "screen": 32,
}

# Square, everywhere (Session 45, Night File). Kept as a scale rather than
# deleted so Style.gd's call sites, and any return to rounding, stay one edit.
RADIUS: Dict[str, int] = {
    "small": 0,   # badges, inline chips
    "base": 0,    # buttons, inputs
    "card": 0,    # panels
}

# Two widths. Outlines are the affordance in this look — outlined means "you
# could choose this", filled means "chosen" — so they are 2px and read from a
# sofa. Dividers are 1px: a rule the eye should read PAST, not trace.
BORDER_WIDTH = 2
RULE_WIDTH = 1


# ---------------------------------------------------------------------------
# Contrast — the arithmetic, kept here because this file owns the colours
# ---------------------------------------------------------------------------

def _channel(value: float) -> float:
    return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4


def rgb(hex_value: str) -> Tuple[int, int, int]:
    """#RRGGBB -> (r, g, b). Accepts the leading # or not."""
    h = hex_value.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"not a 6-digit hex colour: {hex_value!r}")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def luminance(hex_value: str) -> float:
    """WCAG relative luminance."""
    r, g, b = (c / 255 for c in rgb(hex_value))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two colours, always >= 1."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# Every ink/background pair the UI can actually produce, and the floor each one
# has to clear. This is the palette's test surface: scripts/test_palette.py
# walks it, so a colour cannot be re-pitched without the consequence showing up
# as a failure rather than as a screen someone squints at later.
#
# Floors follow WCAG: 4.5 for body text, 3.0 for large text (>= 21px, i.e. the
# heading tier and up) and for the boundary of a control.
CONTRAST_CONTRACT: Tuple[Tuple[str, str, float, str], ...] = (
    (INK, GROUND, 4.5, "body text on the ground"),
    (INK, SURFACE, 4.5, "body text on a panel"),
    (INK, SURFACE_DEEP, 4.5, "body text in a well"),
    (INK, SURFACE_RAISED, 4.5, "body text on a hovered row"),
    (INK_MUTED, GROUND, 4.5, "secondary prose on the ground"),
    (INK_MUTED, SURFACE, 4.5, "secondary prose on a panel"),
    (INK_MUTED, SURFACE_DEEP, 4.5, "secondary prose in a well"),
    (INK_FAINT, SURFACE, 4.5, "field labels on a panel"),
    (INK_FAINT, SURFACE_DEEP, 4.5, "field labels in a well"),
    (INK_FAINT, GROUND, 3.0, "field labels on the ground (large only)"),
    (BRASS, GROUND, 3.0, "the mystery title on the ground (large only)"),
    (BRASS, SURFACE, 4.5, "brass text on a panel"),
    (BRASS, SURFACE_DEEP, 4.5, "brass text in a well"),
    # Semantics carry body-text weight on the two panel tiers, where prose
    # actually lives, and marker weight on the ground, where they appear as
    # borders and large status text. See the note above POSITIVE for why a
    # 4.5 floor on the ground is not reachable at any usable saturation.
    (POSITIVE, SURFACE, 4.5, "a shared-clue marker on a panel"),
    (POSITIVE, SURFACE_DEEP, 4.5, "a shared-clue marker in a well"),
    (POSITIVE, GROUND, 3.0, "a shared-clue marker on the ground"),
    (NEGATIVE, SURFACE, 4.5, "an error message on a panel"),
    (NEGATIVE, SURFACE_DEEP, 4.5, "an error message in a well"),
    (NEGATIVE, GROUND, 3.0, "an error marker on the ground"),
    (CAUTION, SURFACE, 4.5, "a budget warning on a panel"),
    (CAUTION, SURFACE_DEEP, 4.5, "a budget warning in a well"),
    (CAUTION, GROUND, 3.0, "a caution marker on the ground"),
    # LINE is measured because it is the whole affordance of a text field.
    # LINE_SOFT is decorative and appears here on purpose with no floor of its
    # own, so that its absence reads as a decision rather than an oversight.
    (LINE, SURFACE, 3.0, "a text field's outline on a panel"),
    (LINE, SURFACE_DEEP, 3.0, "a text field's outline in a well"),
    (LINE, GROUND, 3.0, "a text field's outline on the ground"),
    # Filled buttons: the pairing that matters is the LABEL against the fill.
    (SURFACE_DEEP, BRASS, 4.5, "the label on a primary button"),
    (SURFACE_DEEP, BRASS_BRIGHT, 4.5, "the label on a hovered primary button"),
    (INK, STEEL, 4.5, "the label on a chosen tile or toggled row"),
    # Steel as the selection signal. A chosen tile's fill against the ground is
    # the whole of its boundary when nothing else outlines it.
    (STEEL, GROUND, 3.0, "a chosen tile's fill against the ground"),
    (STEEL_BRIGHT, GROUND, 4.5, "accent text on the ground: counts, IDs"),
    (STEEL_BRIGHT, SURFACE, 4.5, "accent text on a row: a 'Sharing' state"),
    # Text that sits on a slate tint — a name inside a result bar.
    (INK, SLATE, 4.5, "ink over a result bar"),
    (INK_MUTED, SLATE, 4.5, "a sub-label over a result bar"),
)


def contrast_report() -> str:
    """The whole contract as a table. Printed by scripts/test_palette.py."""
    rows = ["  ratio  floor  pair"]
    for fg, bg, floor, why in CONTRAST_CONTRACT:
        ratio = contrast(fg, bg)
        mark = "ok " if ratio >= floor else "LOW"
        rows.append(f"  {ratio:5.2f}  {floor:5.1f}  {mark} {why}  ({fg} on {bg})")
    return "\n".join(rows)


# The full ordered mapping the generators walk. Ordered so the generated files
# read top-to-bottom the way this one does, rather than alphabetically.
COLOURS: Dict[str, str] = {
    "ground": GROUND,
    "slate": SLATE,
    "surface": SURFACE,
    "surface_deep": SURFACE_DEEP,
    "surface_raised": SURFACE_RAISED,
    "line": LINE,
    "line_soft": LINE_SOFT,
    "ink": INK,
    "ink_muted": INK_MUTED,
    "ink_faint": INK_FAINT,
    "brass": BRASS,
    "brass_bright": BRASS_BRIGHT,
    "brass_dim": BRASS_DIM,
    "steel": STEEL,
    "steel_bright": STEEL_BRIGHT,
    "positive": POSITIVE,
    "negative": NEGATIVE,
    "caution": CAUTION,
}


if __name__ == "__main__":
    print(f"CYM palette — ground {GROUND}\n")
    print(contrast_report())
