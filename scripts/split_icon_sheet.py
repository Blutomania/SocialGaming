#!/usr/bin/env python3
"""Split a sheet of icons into individual files, and flatten them. Zero API cost.

    python3 scripts/split_icon_sheet.py icons/_sheets/clues_new.svg clue
    python3 scripts/split_icon_sheet.py <sheet> <set> --dry-run

WHY THIS EXISTS. The icon artwork arrived as two files, each holding a whole
row of four, and each one a PNG wrapped in an SVG — `<image href="data:image/png
;base64,…">`, zero <path> elements. So two separate things had to happen before
any of it could be used: the row had to become four icons, and the four had to
stop being a bitmap's worth of gradients.

WHAT THIS IS NOT. It is not a substitute for vector artwork, and it must not be
allowed to quietly become one. A bitmap cannot be re-cut, re-weighted, or scaled
past its own resolution, and CYM's host screen is a television. The output here
is a usable stopgap at UI sizes; the durable fix is re-exporting the originals
with paths instead of an embedded image, at which point build_icons.py handles
them directly and this script is not in the path at all.

HOW THE SPLIT IS FOUND. By column occupancy, not by dividing the width by four.
The icons are not evenly spaced in either sheet — the measured gaps run from 68
to 80 pixels — so an even division would clip some and off-centre the rest.
Scanning for columns with no ink finds the real gutters, and the run-length
floor rejects a stray antialiased pixel from being read as a fifth icon.

WHAT IT DOES NOT DO. It does not recolour. Splitting and flattening are separate
jobs, and this one stops at splitting so that what lands in icons/<set>/ is the
artwork as drawn — build_icons.py stays the single place any colour is decided,
exactly as it is for vector sources. Flattening here would bake an irreversible
choice into the file everyone thereafter treats as the original.
"""

from __future__ import annotations

import base64
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from PIL import Image
except ImportError:
    raise SystemExit("error: this script needs Pillow.  pip install Pillow")

SETS = ("clue", "witness")

# Output edge, in pixels. 256 is far above any size these are drawn at (a list
# row is 24-32px, a panel header maybe 64) and still small enough that four of
# them cost nothing. Going higher cannot recover detail the bitmap never had.
EDGE = 256

# Padding inside the square, as a fraction of the edge. Icons that touch their
# own bounding box look larger than ones that do not, and these four have very
# different aspect ratios, so a shared margin is what makes them read as a set.
PAD = 0.08

# A gap must be at least this many columns wide to count as a gutter rather than
# as a gap inside one drawing -- the magnifier handle leaves real vertical gaps.
MIN_GUTTER = 24

# And a run of ink must be at least this wide to be an icon rather than a speck.
MIN_RUN = 40

# Below this alpha a pixel is background. Antialiased edges sit well above it.
ALPHA_FLOOR = 12


def load_sheet(path: Path) -> Image.Image:
    """The sheet as RGBA, whether it is a PNG or a PNG hiding inside an SVG."""
    if path.suffix.lower() == ".png":
        return Image.open(path).convert("RGBA")

    text = path.read_text()
    match = re.search(r"base64,([A-Za-z0-9+/=]+)", text)
    if not match:
        raise SystemExit(
            f"error: {path} is an SVG with no embedded image.\n"
            f"       If it is real vector artwork, it does not need this script —\n"
            f"       put it straight into icons/<set>/ and run build_icons.py."
        )
    return Image.open(io.BytesIO(base64.b64decode(match.group(1)))).convert("RGBA")


def find_columns(sheet: Image.Image) -> list[tuple[int, int]]:
    """Left/right bounds of each icon, from the columns that carry ink."""
    alpha = sheet.getchannel("A")
    width, height = sheet.size
    pixels = alpha.load()

    occupied = []
    for x in range(width):
        ink = any(pixels[x, y] > ALPHA_FLOOR for y in range(height))
        occupied.append(ink)

    runs: list[tuple[int, int]] = []
    start = None
    gap = 0
    for x, ink in enumerate(occupied):
        if ink:
            if start is None:
                start = x
            gap = 0
        elif start is not None:
            gap += 1
            # Only close the run once the gap is wide enough to be a gutter;
            # otherwise a gap INSIDE a drawing would split it in two.
            if gap >= MIN_GUTTER:
                end = x - gap + 1
                if end - start >= MIN_RUN:
                    runs.append((start, end))
                start = None
                gap = 0
    if start is not None and width - start >= MIN_RUN:
        runs.append((start, width))
    return runs


def cut(sheet: Image.Image, left: int, right: int) -> Image.Image:
    """One icon: cropped to its own ink, squared, padded, and flattened to white."""
    strip = sheet.crop((left, 0, right, sheet.height))

    # Crop to the ink rather than to the column band, so vertical position is
    # set by the drawing and not by where it happened to sit in the sheet.
    box = strip.getchannel("A").point(lambda v: 255 if v > ALPHA_FLOOR else 0).getbbox()
    if box:
        strip = strip.crop(box)

    inner = int(EDGE * (1 - 2 * PAD))
    scale = min(inner / strip.width, inner / strip.height)
    resized = strip.resize(
        (max(1, round(strip.width * scale)), max(1, round(strip.height * scale))),
        Image.LANCZOS,
    )

    # Colour is deliberately PRESERVED here. Splitting and flattening are two
    # different jobs, and keeping them apart makes the raster path behave the
    # same way as the vector one: what lands in icons/<set>/ is the artwork as
    # drawn, and build_icons.py is the single place that decides what colour
    # anything ends up. Flattening here instead would put an irreversible
    # decision in the file everyone treats as the source.
    canvas = Image.new("RGBA", (EDGE, EDGE), (255, 255, 255, 0))
    canvas.paste(resized, ((EDGE - resized.width) // 2, (EDGE - resized.height) // 2))
    return canvas


def detached_specks(icon: Image.Image, floor: float = 0.015) -> list[tuple[int, int, float]]:
    """Bands of ink that float free of the drawing, as (top, bottom, share).

    REPORTED, NEVER REMOVED, and the reason is in this very icon set: the
    figure with radiating emphasis lines has four legitimately detached
    components. Anything that deleted disconnected ink automatically would eat
    them. So this only looks for a band separated VERTICALLY from everything
    else and carrying almost none of the ink -- the shape a stray anchor point
    or a leftover mark takes -- and then says so rather than acting.
    """
    alpha = icon.getchannel("A")
    width, height = icon.size
    pixels = alpha.load()
    rows = [sum(1 for x in range(width) if pixels[x, y] > ALPHA_FLOOR)
            for y in range(height)]
    total = sum(rows) or 1

    bands: list[tuple[int, int, float]] = []
    start = None
    gap = 0
    for y, count in enumerate(rows):
        if count:
            if start is None:
                start = y
            gap = 0
        elif start is not None:
            gap += 1
            if gap >= 3:
                end = y - gap + 1
                bands.append((start, end, sum(rows[start:end]) / total))
                start = None
                gap = 0
    if start is not None:
        bands.append((start, height, sum(rows[start:]) / total))

    return [b for b in bands if len(bands) > 1 and b[2] < floor]


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    if len(args) != 2:
        print(__doc__)
        return 1

    sheet_path = Path(args[0])
    icon_set = args[1]
    if icon_set not in SETS:
        print(f"error: set must be one of {', '.join(SETS)}, not {icon_set!r}")
        return 1
    if not sheet_path.exists():
        print(f"error: {sheet_path} does not exist")
        return 1

    sheet = load_sheet(sheet_path)
    runs = find_columns(sheet)
    print(f"{sheet_path.name}: {sheet.width}x{sheet.height} -> {len(runs)} icon(s)")
    gaps = [runs[i + 1][0] - runs[i][1] for i in range(len(runs) - 1)]
    if gaps:
        print(f"  gutters: {gaps}  (even division would have been "
              f"{sheet.width // max(len(runs), 1)}px apart)")

    out_dir = ROOT / "icons" / icon_set
    for index, (left, right) in enumerate(runs, start=1):
        name = f"{icon_set}_{index:02d}.png"
        print(f"  {name}  from x={left}..{right}  ({right - left}px wide)")
        if dry_run:
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        icon = cut(sheet, left, right)
        for top, bottom, share in detached_specks(icon):
            print(f"      note: detached mark at rows {top}-{bottom} carrying "
                  f"{share:.2%} of this icon's ink — probably a stray point in "
                  f"the source artwork. Left alone; remove it in the original "
                  f"if it is not wanted.")
        icon.save(out_dir / name)

    if dry_run:
        print("\n--dry-run: nothing written. Check the count and the widths above "
              "before running for real.")
    else:
        print(f"\nWrote {len(runs)} file(s) to icons/{icon_set}/. "
              f"Next: python3 scripts/build_icons.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
