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

HOW THE COLOUR IS REMOVED. The alpha channel is the artwork; the RGB is thrown
away entirely. Every pixel becomes white at its original opacity, which makes
the result a coverage mask — Godot then multiplies it by any palette colour via
modulate, and CSS does the same with a filter. Converting the hues to greys
instead would keep the gradient's own light and dark, and the icons would arrive
with brightness variation nobody chose.
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

    # The alpha IS the artwork. White at the original opacity, so the result
    # multiplies cleanly against any colour. See the header.
    white = Image.new("RGBA", resized.size, (255, 255, 255, 0))
    white.putalpha(resized.getchannel("A"))

    canvas = Image.new("RGBA", (EDGE, EDGE), (255, 255, 255, 0))
    canvas.paste(white, ((EDGE - white.width) // 2, (EDGE - white.height) // 2))
    return canvas


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
        cut(sheet, left, right).save(out_dir / name)

    if dry_run:
        print("\n--dry-run: nothing written. Check the count and the widths above "
              "before running for real.")
    else:
        print(f"\nWrote {len(runs)} file(s) to icons/{icon_set}/. "
              f"Next: python3 scripts/build_icons.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
