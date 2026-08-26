#!/usr/bin/env python3
"""Regression tests for the CYM palette. Zero API cost.

Run: python3 scripts/test_palette.py

WHAT THIS IS FOR. A palette is the easiest thing in a codebase to change
casually — one hex digit, in one file, and nothing complains until somebody
squints at a screen weeks later. These tests turn the parts of it that are
NOT taste into failures:

  - every ink/background pair the UI can produce clears its WCAG floor
  - the ground still matches the value brand/ and background_field.py were
    built against, so a re-pitch here cannot silently invalidate the artwork
  - brass is one colour, not two nearly-identical ones (the exact drift this
    palette was written to end)

It deliberately does NOT test that the colours are nice. That is the owner's
call and no assertion can hold it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import palette  # noqa: E402
from background_field import MARKS  # noqa: E402

failures = []


def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        failures.append(msg)


print("--- the contrast contract holds ---")
for fg, bg, floor, why in palette.CONTRAST_CONTRACT:
    ratio = palette.contrast(fg, bg)
    check(ratio >= floor, f"{why}: {ratio:.2f} >= {floor}")

print("\n--- the ground is the one the rest of the product already assumes ---")
# brand/README.md calls this "the one rule these assets must satisfy", and
# scripts/check_brand_contrast.py measures every mark against it. If the two
# ever disagree, the contrast script is grading artwork against a ground no
# client paints.
brand_checker = (Path(__file__).resolve().parent / "check_brand_contrast.py").read_text()
check("GROUND = (0x2F, 0x44, 0x59)" in brand_checker,
      "check_brand_contrast.py measures against the same slate")
check(palette.GROUND == "#2F4459", "palette.GROUND is that slate")
check("**CYM's ground is slate `#2F4459`.**" in (Path(__file__).resolve().parent.parent
                                                 / "brand" / "README.md").read_text(),
      "brand/README.md documents that slate")

print("\n--- brass is ONE colour ---")
# The drift this palette exists to end: mobile.html shipped #c8a96e while the
# brand and the background field used #C9A227. Near enough to look like a
# rounding difference, far enough apart to see side by side in one room.
field_brass = [hex_value for hex_value, _ in MARKS if hex_value.upper() == palette.BRASS]
check(len(field_brass) == 1,
      f"background_field.py's warm mark is palette.BRASS ({palette.BRASS})")

print("\n--- the field's marks read on the ground they are drawn on ---")
# background_field.py composites at 7% strength, so these are not text and do
# not owe 4.5:1. What they owe is being on the correct SIDE of the ground:
# a mark darker than the ground reads as a stain, not as a texture. This is
# the same failure check_brand_contrast.py runs on the logo artwork.
ground_lum = palette.luminance(palette.GROUND)
for hex_value, share in MARKS:
    check(palette.luminance(hex_value) > ground_lum,
          f"field mark {hex_value} ({share:.0%}) is lighter than the ground")

print("\n--- the scales are ordered, because a generator walks them ---")
sizes = list(palette.TYPE_SCALE.values())
check(sizes == sorted(sizes, reverse=True), f"type scale descends: {sizes}")
spaces = list(palette.SPACE.values())
check(spaces == sorted(spaces), f"spacing ascends: {spaces}")
radii = list(palette.RADIUS.values())
check(radii == sorted(radii), f"radii ascend: {radii}")

print("\n--- every colour is a well-formed 6-digit hex ---")
for name, value in palette.COLOURS.items():
    ok = value.startswith("#") and len(value) == 7
    try:
        palette.rgb(value)
    except ValueError:
        ok = False
    check(ok, f"{name} = {value}")

print("\n--- COLOURS covers every colour constant, so nothing escapes the generators ---")
# A colour defined at module level but left out of COLOURS would never reach
# Palette.gd or the CSS block — it would exist in Python and nowhere a player
# can see, which is the quiet way a fourth palette starts.
module_colours = {
    name for name, value in vars(palette).items()
    if name.isupper() and isinstance(value, str) and value.startswith("#")
}
# Catches both halves: a constant absent from COLOURS, and one present under
# its name but mapped to a different value.
missing = {n for n in module_colours if palette.COLOURS.get(n.lower()) != getattr(palette, n)}
check(not missing, f"every colour constant is in COLOURS at its own value (stray: {sorted(missing)})")

print("\n" + palette.contrast_report())

print("\n=== ALL PASSED ===" if not failures else f"\n=== {len(failures)} FAILED ===")
sys.exit(1 if failures else 0)
