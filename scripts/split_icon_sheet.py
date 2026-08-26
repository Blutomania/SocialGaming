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


# ---------------------------------------------------------------------------
# The vector path
# ---------------------------------------------------------------------------

def _path_bounds(d: str) -> tuple[float, float, float, float] | None:
    """A path's bounding box, from its coordinates.

    Only correct for ABSOLUTE commands, which is why split_vector_sheet()
    refuses a sheet containing lowercase ones rather than quietly returning
    wrong boxes. Bezier control points are included, so the box can be slightly
    larger than the drawn curve -- which is the safe direction for a viewBox,
    and irrelevant for deciding which column a path belongs to.
    """
    numbers = [float(n) for n in re.findall(r"-?\d*\.?\d+(?:[eE][-+]?\d+)?", d)]
    if len(numbers) < 2:
        return None
    xs, ys = numbers[0::2], numbers[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def split_vector_sheet(path: Path, icon_set: str, dry_run: bool) -> int:
    """Cut a sheet of vector icons into one file each, by column.

    SPLIT AT SUBPATH LEVEL, NOT PATH LEVEL, and that is not a detail. These
    sheets hold 10 and 6 <path> elements for 4 icons each, because the export
    grouped by shape rather than by drawing: one element carries 180 subpaths
    spanning x=374..1202, i.e. pieces of three different icons. Grouping whole
    elements put all four icons in one file, which is what the first attempt
    did.

    Each output keeps its source element's ATTRIBUTES verbatim and only the
    subpaths belonging to its column, so paint, fill-rule and winding survive
    exactly. Nothing is re-fitted or re-encoded -- the geometry that ships is
    the geometry that was drawn, which is the entire reason vector was worth
    waiting for.
    """
    text = path.read_text()
    elements = list(re.finditer(r'<path\b([^>]*?)\bd="([^"]*)"([^>]*?)/?>', text))
    if not elements:
        raise SystemExit(f"error: {_rel(path)} has no <path> elements.")

    # (attrs, subpath_d, x0, x1) for every subpath in the sheet.
    pieces = []
    for index, match in enumerate(elements):
        attrs = (match.group(1) + " " + match.group(3)).strip()
        d = match.group(2)
        if any(c.islower() for c in re.findall(r"[A-Za-z]", d)):
            raise SystemExit(
                f"error: {_rel(path)} uses relative path commands.\n"
                f"       This splitter reads absolute coordinates only."
            )
        for sub in re.split(r"(?=M)", d):
            sub = sub.strip()
            if not sub:
                continue
            bounds = _path_bounds(sub)
            if bounds:
                pieces.append((index, attrs, sub, bounds[0], bounds[2]))

    if not pieces:
        raise SystemExit(f"error: {_rel(path)} has no usable subpaths.")

    # Find the gutters by interval coverage rather than by dividing the width:
    # the spacing in these sheets is uneven, exactly as it was in the rasters.
    right = max(piece[4] for piece in pieces)
    covered = [False] * (int(right) + 2)
    for _, _, _, x0, x1 in pieces:
        for x in range(max(0, int(x0)), min(len(covered), int(x1) + 1)):
            covered[x] = True

    bands: list[tuple[float, float]] = []
    start_x = None
    for x, ink in enumerate(covered):
        if ink and start_x is None:
            start_x = x
        elif not ink and start_x is not None:
            bands.append((start_x, x))
            start_x = None
    if start_x is not None:
        bands.append((start_x, len(covered)))
    bands = [b for b in bands if b[1] - b[0] >= MIN_RUN]

    print(f"{path.name}: {len(elements)} path(s), {len(pieces)} subpath(s) "
          f"-> {len(bands)} icon(s)")

    out_dir = ROOT / "icons" / icon_set
    for index, (band_left, band_right) in enumerate(bands, start=1):
        # A subpath belongs to the band its CENTRE falls in, so a piece that
        # grazes a boundary lands in one icon rather than both or neither.
        mine = [p for p in pieces if band_left <= (p[3] + p[4]) / 2 < band_right]
        if not mine:
            continue

        xs = [v for p in mine for v in (p[3], p[4])]
        ys = []
        for _, _, sub, _, _ in mine:
            bounds = _path_bounds(sub)
            if bounds:
                ys += [bounds[1], bounds[3]]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)

        side = max(x1 - x0, y1 - y0)
        pad = side * PAD
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        half = side / 2 + pad
        view = f"{cx - half:.2f} {cy - half:.2f} {side + 2 * pad:.2f} {side + 2 * pad:.2f}"

        # Regroup by source element so each keeps its own attributes.
        by_element: dict[int, list] = {}
        for element_index, attrs, sub, _, _ in mine:
            by_element.setdefault(element_index, [attrs, []])[1].append(sub)

        body = "\n".join(
            f'<path {attrs} d="{" ".join(subs)}"/>' if attrs
            else f'<path d="{" ".join(subs)}"/>'
            for attrs, subs in by_element.values()
        )

        name = f"{icon_set}_{index:02d}.svg"
        print(f"  {name}  {len(mine)} subpath(s) from {len(by_element)} element(s)  "
              f"x={x0:.0f}..{x1:.0f}")
        if dry_run:
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        # width/height as well as viewBox, deliberately. A viewBox-only SVG has
        # no intrinsic size, and Godot's importer has to invent one -- which it
        # may do at a scale that makes the icon a handful of pixels, with no
        # error to say so. Stating the size removes the guess. Square, matching
        # the raster path's EDGE, so both kinds of source import identically.
        (out_dir / name).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{EDGE}" height="{EDGE}" '
            f'viewBox="{view}">\n{body}\n</svg>\n'
        )

    if dry_run:
        print("\n--dry-run: nothing written.")
    else:
        print(f"\nWrote {len(bands)} file(s) to icons/{icon_set}/. "
              f"Next: python3 scripts/build_icons.py")
    return 0


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

    # A vector sheet is split by geometry; a raster one by pixels. Dispatch on
    # what the file actually contains rather than on its extension, because the
    # first upload was a .svg that held nothing but a PNG.
    if sheet_path.suffix.lower() == ".svg" and "base64," not in sheet_path.read_text():
        return split_vector_sheet(sheet_path, icon_set, dry_run)

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
