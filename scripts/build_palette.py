#!/usr/bin/env python3
"""Generate the palette's GDScript and CSS forms from palette.py. Zero API cost.

    python3 scripts/build_palette.py          # write the generated files
    python3 scripts/build_palette.py --check  # fail if they have drifted

WHY GENERATE RATHER THAN IMPORT. GDScript cannot import Python and neither can
a stylesheet, so the same seventeen colours have to exist in three places no
matter what. The only question is whether the copies are derived or typed out,
and the product already ran the experiment: typed out, mobile.html drifted to
its own brass a digit-pair away from the brand's, and the Godot client never
got a palette at all.

WHY --check EXISTS. Generating is worthless if nobody notices when a generated
file is edited by hand, and hand-editing a generated file is exactly what
happens when someone is deep in a screen and wants one colour slightly darker.
--check is what turns that into a failure, and it is the form the pre-playtest
checker list calls: no separate wrapper script, because a wrapper that only
forwards its arguments is one more file to keep in step.

WHAT IS AND IS NOT GENERATED. Colours, and for Godot the type/space/radius
scales. Not the phone's type sizing — see the TYPE_SCALE note in palette.py
for why the two screens must not share pixel sizes. Not the Theme itself:
godot/scripts/autoloads/Style.gd builds that by hand from these constants,
because a theme is behaviour and this is data. Regenerating never touches it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import palette  # noqa: E402

GD_PATH = ROOT / "godot" / "scripts" / "theme" / "Palette.gd"
PROJECT_GODOT = ROOT / "godot" / "project.godot"
HTML_PATH = ROOT / "server" / "static" / "mobile.html"

BEGIN = "/* --- BEGIN GENERATED PALETTE (scripts/build_palette.py) --- */"
END = "/* --- END GENERATED PALETTE --- */"

BANNER = "scripts/build_palette.py from palette.py — DO NOT EDIT BY HAND"


def _gd_colour(hex_value: str) -> str:
    """A Color literal that is safe in a `const`.

    Color("#2F4459") reads better and is NOT usable here: a const initialiser
    must be a constant expression, and the String constructor is not one that
    GDScript will fold. Float components always are. The hex rides along as a
    trailing comment so the file is still greppable by colour.
    """
    r, g, b = palette.rgb(hex_value)
    return f"Color({r / 255:.6f}, {g / 255:.6f}, {b / 255:.6f}, 1.0)"


def render_gdscript() -> str:
    lines = [
        "## " + BANNER,
        "##",
        "## The CYM palette, as Godot sees it. Regenerate with:",
        "##     python3 scripts/build_palette.py",
        "##",
        "## Not an autoload and not a Theme. `class_name` makes every constant",
        "## reachable as `Palette.GROUND` from any script with no load-order",
        "## question to get wrong; the Theme that USES these is built in",
        "## scripts/autoloads/Style.gd, which is hand-written and is not",
        "## touched by regeneration.",
        "##",
        "## Every declaration states its type. Session 36 lost a whole screen to",
        "## an inferred Variant, and `:=` on a constructor call is exactly the",
        "## shape that went wrong.",
        "class_name Palette",
        "extends RefCounted",
        "",
        "",
        "## Colours. Float components rather than Color(\"#RRGGBB\") because a",
        "## const initialiser has to be constant-foldable and a String is not.",
    ]
    for name, value in palette.COLOURS.items():
        lines.append(f"const {name.upper()}: Color = {_gd_colour(value)}  ## {value}")

    lines += [
        "",
        "",
        "## Type sizes in pixels, for the 1280x720 host viewport. The phone",
        "## client deliberately does NOT share these — see palette.py.",
    ]
    for name, size in palette.TYPE_SCALE.items():
        lines.append(f"const TYPE_{name.upper()}: int = {size}")

    lines += ["", "", "## Spacing."]
    for name, size in palette.SPACE.items():
        lines.append(f"const SPACE_{name.upper()}: int = {size}")

    lines += ["", "", "## Corner radii."]
    for name, size in palette.RADIUS.items():
        lines.append(f"const RADIUS_{name.upper()}: int = {size}")

    lines += [
        "",
        f"const BORDER_WIDTH: int = {palette.BORDER_WIDTH}",
        "",
    ]
    return "\n".join(lines)


def render_css() -> str:
    """The custom-property block, without its sentinels."""
    lines = [
        f"  /* {BANNER} */",
        "  /* Colours only. The phone keeps its own em-based type sizing on",
        "     purpose — a phone and a television are not read from the same",
        "     distance. See palette.py's TYPE_SCALE note. */",
        "  :root {",
    ]
    for name, value in palette.COLOURS.items():
        lines.append(f"    --{name.replace('_', '-')}: {value};")
    lines.append("  }")
    return "\n".join(lines)


def _splice_css(html: str, block: str) -> str:
    """Replace the sentinel-delimited block, or fail loudly if it is missing.

    Deliberately not "append if absent": a missing sentinel means somebody
    restructured the file, and silently pasting a palette into a stylesheet
    that may already declare one is how you end up debugging cascade order.
    """
    if BEGIN not in html or END not in html:
        raise SystemExit(
            f"error: {HTML_PATH.relative_to(ROOT)} has no generated-palette sentinels.\n"
            f"       Add these two lines inside its <style> block, in this order:\n"
            f"         {BEGIN}\n"
            f"         {END}"
        )
    pattern = re.compile(
        re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL
    )
    return pattern.sub(lambda _: f"{BEGIN}\n{block}\n  {END}", html, count=1)


def check_clear_colour() -> str | None:
    """The ground is also declared in project.godot, and cannot be generated.

    project.godot is rewritten by the Godot editor itself — Session 36 recorded
    4.7.2 re-saving it just for being opened — so splicing generated content
    into it would fight the engine for ownership of the file. Checking it
    instead gets the same guarantee with none of that: this is the fourth place
    the ground appears, and the only one a human has to keep in step.

    Returns an error message, or None when it agrees.
    """
    r, g, b = (c / 255 for c in palette.rgb(palette.GROUND))
    wanted = f"environment/defaults/default_clear_color=Color({r:g}, {g:g}, {b:g}, 1)"
    text = PROJECT_GODOT.read_text()
    if wanted in text:
        return None
    return (
        f"{PROJECT_GODOT.relative_to(ROOT)} does not paint the ground {palette.GROUND}.\n"
        f"       Its [rendering] section needs exactly this line:\n"
        f"         {wanted}"
    )


def build(check_only: bool = False) -> int:
    targets = []

    gd = render_gdscript()
    targets.append((GD_PATH, gd, GD_PATH.read_text() if GD_PATH.exists() else None))

    html = HTML_PATH.read_text()
    spliced = _splice_css(html, render_css())
    targets.append((HTML_PATH, spliced, html))

    drifted = [path for path, wanted, current in targets if wanted != current]
    clear_colour_error = check_clear_colour()

    if check_only:
        for path in drifted:
            print(f"  DRIFTED  {path.relative_to(ROOT)}")
        for path, _, _ in targets:
            if path not in drifted:
                print(f"  in sync  {path.relative_to(ROOT)}")
        if clear_colour_error:
            print(f"  DRIFTED  {clear_colour_error}")
        else:
            print(f"  in sync  {PROJECT_GODOT.relative_to(ROOT)} (ground clear colour)")
        if drifted:
            print("\nRegenerate with: python3 scripts/build_palette.py")
        return 1 if (drifted or clear_colour_error) else 0

    for path, wanted, current in targets:
        if wanted == current:
            print(f"  unchanged  {path.relative_to(ROOT)}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(wanted)
        print(f"  wrote      {path.relative_to(ROOT)}")

    if clear_colour_error:
        print(f"\nwarning: {clear_colour_error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(build(check_only="--check" in sys.argv))
