#!/usr/bin/env python3
"""Measure a brand asset's ink against CYM's slate ground. Zero API cost.

    python3 scripts/check_brand_contrast.py brand/organic_logo.svg [...]

WHY. CYM's ground is slate #2F4459, and artwork drawn against white loses its
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

GROUND = (0x2F, 0x44, 0x59)  # CYM/MYF slate

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
        raise SystemExit(
            f"{path}: real vector SVG — rasterise it first, this reads pixels.\n"
            "  (Worth knowing on its own: a true vector mark can be recoloured "
            "in place, which a raster cannot.)"
        )
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
    print(f"  {total:,} opaque pixels, against the slate ground")
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
    targets = sys.argv[1:] or ["brand/negative_logo.svg", "brand/organic_logo.svg"]
    for t in targets:
        report(Path(t))
