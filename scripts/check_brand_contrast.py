#!/usr/bin/env python3
"""Measure a brand asset's ink against CYM's ground. Zero API cost.

    python3 scripts/check_brand_contrast.py brand/organic_logo.svg [...]
    python3 scripts/check_brand_contrast.py --myf [...]   # MYF's slate instead

WHY. CYM's ground is Night #0C1118 (slate #2F4459 until Session 45, and
still MYF's), and on Night it is the DARK half of a mark that vanishes. On
slate, artwork drawn against white loses its
dark half on it — near-black lands around 1.9:1. That is not a hypothetical:
it is what happened to MYF's metallic title treatment, which shipped looking
"dim" because roughly two thirds of it was below 3.5:1 and simply was not
there. This turns "does this mark read on our ground?" into a number before
anyone builds a screen around it.

Reads .svg (including an SVG that is really a wrapper around an embedded
base64 PNG, which is what design tools often export) and .png.

Two things it does that a naive check would get wrong, both learned the hard
way on the first assets measured:

  * It crops to the SVG's viewBox. One asset carried 22,445 opaque pixels of
    export artifact OUTSIDE its viewBox — invisible in use, but they dragged
    the measured "invisible ink" figure from 49% to 62%. Measure what is
    displayed, not what is in the file.
  * It reports the DISTRIBUTION, not an average. These marks are bimodal: one
    is half near-white and half near-black, and its mean contrast is a number
    describing no pixel in it.
"""

import base64
import io
import re
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("needs pillow:  pip install pillow")

# Two grounds since Session 45: CYM moved to Night, MYF kept slate. A brand
# mark shared by both titles has to be measured against both — pass --myf to
# grade against slate. Default is CYM's, because that is what this repo paints.
CYM_GROUND = (0x0C, 0x11, 0x18)  # Night — palette.GROUND
MYF_GROUND = (0x2F, 0x44, 0x59)  # slate — palette.SLATE, still MYF's ground
GROUND = MYF_GROUND if "--myf" in sys.argv else CYM_GROUND
GROUND_NAME = "MYF slate" if GROUND == MYF_GROUND else "CYM Night"

BANDS = [
    (1.5, "invisible", "below 1.5:1 — not perceptible as a shape"),
    (2.5, "barely", "1.5-2.5:1 — a large solid form still reads, detail does not"),
    (3.5, "weak", "2.5-3.5:1 — under AA for anything but large graphics"),
    (5.0, "ok", "3.5-5:1 — reliable for a mark"),
    (float("inf"), "strong", "5:1+ — crisp at any size"),
]


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb):
    return 0.2126 * _lin(rgb[0]) + 0.7152 * _lin(rgb[1]) + 0.0722 * _lin(rgb[2])


def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def load(path: Path) -> Image.Image:
    """The displayed artwork, cropped to the viewBox when there is one."""
    if path.suffix.lower() == ".png":
        return Image.open(path).convert("RGBA")

    src = path.read_text(errors="replace")
    embedded = re.search(r"base64,([A-Za-z0-9+/=]+)", src)

    if not embedded:
        # A real vector SVG. Rasterise it and measure the pixels, rather than
        # counting declared fill colours: these marks are built from ~130 paths
        # approximating a gradient, so an unweighted colour census would treat
        # a hairline highlight and half the mark as one vote each.
        try:
            import cairosvg
        except ImportError:
            raise SystemExit(
                f"{path} is a real vector SVG; measuring it needs a rasteriser.\n"
                "  pip install cairosvg"
            )
        png = cairosvg.svg2png(url=str(path), scale=2)
        return Image.open(io.BytesIO(png)).convert("RGBA")

    img = Image.open(io.BytesIO(base64.b64decode(embedded.group(1)))).convert("RGBA")

    box = re.search(r'viewBox="([\d.\s-]+)"', src)
    if box:
        _, _, w, h = (float(v) for v in box.group(1).split())
        if (w, h) != img.size:
            print(f"  note: PNG is {img.size[0]}x{img.size[1]} but the viewBox shows "
                  f"{int(w)}x{int(h)} — measuring only what is displayed")
            img = img.crop((0, 0, int(w), int(h)))
    return img


def report(path: Path) -> None:
    print(f"\n=== {path} ===")
    img = load(path)
    ink = [p[:3] for p in img.get_flattened_data() if p[3] > 200]
    if not ink:
        print("  no opaque pixels"); return

    counts = {name: 0 for _, name, _ in BANDS}
    darker = 0
    for px in ink:
        ratio = contrast(px, GROUND)
        for limit, name, _ in BANDS:
            if ratio < limit:
                counts[name] += 1
                break
        if luminance(px) < luminance(GROUND):
            darker += 1

    total = len(ink)
    print(f"  {total:,} opaque pixels, against the {GROUND_NAME} ground")
    for _, name, blurb in BANDS:
        share = counts[name] / total
        print(f"    {name:10s} {share:6.1%}  {'#' * int(share * 34):34s} {blurb}")

    lost = (counts["invisible"] + counts["barely"]) / total
    print(f"  -> {lost:.0%} of the ink is at or below 2.5:1")
    print(f"  -> {darker / total:.0%} of the ink is DARKER than the ground")
    if lost > 0.25:
        print("  -> drawn for a light ground. Re-pitch the values into the light "
              "half of the scale, or give the mark a light plate to sit on.")


if __name__ == "__main__":
    targets = [a for a in sys.argv[1:] if not a.startswith("--")] or sorted(str(p) for p in Path("brand").glob("*.svg"))
    for t in targets:
        report(Path(t))
