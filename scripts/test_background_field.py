#!/usr/bin/env python3
"""Regression tests for the CYM BACKGROUND layout. Zero API cost.

Run: python3 scripts/test_background_field.py

Most of what is asserted here came from LOOKING at renderings, not from
reasoning about the code — which is the point of writing it down. The
coverage test in particular encodes a real defect: uniform random placement
at these mark counts reliably left a bare quarter of the tile, which reads as
a rendering failure rather than as a sparse texture.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from background_field import (  # noqa: E402
    ADVANCE, MARKS, TILE, field_layout, mark_count,
)

failures = []


def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        failures.append(msg)


SHORT, MED, LONG = "Whiteout", "Mystery on Mars", "Daggers in the Forum: The Ides of March"

print("--- deterministic, because a reconnecting player must rejoin the same wall ---")
check(field_layout(MED, seed="ABCD") == field_layout(MED, seed="ABCD"),
      "same title + same seed gives a byte-identical layout")
check(field_layout(MED, seed="ABCD") != field_layout(MED, seed="WXYZ"),
      "a different room gets a different field")
check(field_layout(MED, seed="ABCD") != field_layout(SHORT, seed="ABCD"),
      "a different mystery re-skins the same room (same-room replay)")

print("\n--- the pre-prompt state is empty, not broken ---")
for blank in ("", "   ", "\n\t "):
    check(field_layout(blank, seed="ABCD")["marks"] == [],
          f"no title ({blank!r}) yields a field with no marks")

print("\n--- title length is absorbed by the ink budget ---")
check(mark_count(SHORT) > mark_count(LONG),
      f"a long title appears fewer times ({mark_count(SHORT)} vs {mark_count(LONG)})")
sizes = [m["size"] for m in field_layout(LONG, seed="ABCD")["marks"]]
short_sizes = [m["size"] for m in field_layout(SHORT, seed="ABCD")["marks"]]
check(min(sizes) > TILE * 0.05 and max(sizes) < TILE * 0.14,
      "type size stays in range for a long title, rather than shrinking to fit")
check(abs(sum(sizes) / len(sizes) - sum(short_sizes) / len(short_sizes)) < TILE * 0.02,
      "mean type size is about the same whatever the title's length")

print("\n--- even coverage: the defect a rendering caught ---")
# Uniform random placement left a bare quarter of the tile; a jittered grid
# does not. Measured on mark EXTENT, not on centres: these marks are wide
# strips of text, so where a mark is centred says little about what it covers,
# and an earlier centres-based version of this check failed a layout that
# renders perfectly well. Wrap copies count, because the client draws them.
def covers(mark, x0, y0, x1, y1):
    half_w = len(mark["text"]) * ADVANCE * mark["size"] / 2
    half_h = mark["size"] / 2
    return (mark["x"] + half_w > x0 and mark["x"] - half_w < x1
            and mark["y"] + half_h > y0 and mark["y"] - half_h < y1)


for title in (SHORT, MED, LONG):
    for seed in ("ABCD", "WXYZ", "KRTP", "MNQS"):
        marks = field_layout(title, seed=seed)["marks"]
        bare = [
            (qx, qy)
            for qx in (0, 1) for qy in (0, 1)
            if not any(
                covers(m, qx * TILE / 2, qy * TILE / 2,
                       (qx + 1) * TILE / 2, (qy + 1) * TILE / 2)
                for m in marks
            )
        ]
        check(not bare,
              f"no bare quadrant ({title[:18]!r}/{seed}"
              + (f": {bare} empty)" if bare else ")"))

print("\n--- the tile wraps, or repeating it shows seams ---")
f = field_layout(LONG, seed="ABCD")
n = mark_count(LONG)
check(len(f["marks"]) > n, f"wrap copies are emitted ({len(f['marks'])} drawn vs {n} unique)")
for m in f["marks"]:
    half_w = len(m["text"]) * ADVANCE * m["size"] / 2
    on_tile = (m["x"] + half_w > 0 and m["x"] - half_w < TILE
               and m["y"] + m["size"] / 2 > 0 and m["y"] - m["size"] / 2 < TILE)
    if not on_tile:
        check(False, f"a drawn mark is entirely off-tile at ({m['x']}, {m['y']})")
        break
else:
    check(True, "every drawn mark, wrap copies included, touches the tile")

print("\n--- colour proportions hold, which a per-mark roll would not ---")
tally = Counter()
for seed in [f"seed{i}" for i in range(40)]:
    f = field_layout(SHORT, seed=seed)
    tally.update(m["colour"] for m in f["marks"][:mark_count(SHORT)])
total = sum(tally.values())
for hex_value, share in MARKS:
    actual = tally[hex_value] / total
    check(abs(actual - share) < 0.05,
          f"{hex_value} is {actual:.0%} of marks against a published {share:.0%}")

print("\n--- the ground is never baked into a mark ---")
check(all(m["colour"] != "#2F4459" for m in field_layout(MED, seed="ABCD")["marks"]),
      "no mark is painted the ground colour")
check(0 < field_layout(MED, seed="ABCD")["strength"] < 1,
      "strength ships as a separate value for the client to composite")

print("\n=== ALL PASSED ===" if not failures else f"\n=== {len(failures)} FAILED ===")
sys.exit(1 if failures else 0)
