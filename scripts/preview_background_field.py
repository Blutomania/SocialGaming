#!/usr/bin/env python3
"""
Render the BACKGROUND field to SVG, with real UI text sitting on top of it.
Zero API cost.

Usage:
    python3 scripts/preview_background_field.py <out.svg> [title ...]
    python3 scripts/preview_background_field.py <out.svg> --sheet

WHY THIS EXISTS. CLAUDE.md item 17 says the field's mark strength is "NOT
SETTLED BY ARGUMENT -- test on a real screen", and background_field.py's own
comment agrees. Until something drew it, there was no way to take that
instruction: the module has been on disk since it was written, wired to
nothing, so nobody has ever seen the thing whose legibility is the open
question.

WHAT MAKES IT A USEFUL TEST RATHER THAN A PRETTY PICTURE. The field is not
being judged on its own; it is being judged on whether you can still read a
case brief through it. So this draws the field and then puts a real screen's
worth of text over it at the real sizes from palette.py -- a title, a heading,
body prose, a faint label. If the answer to "is 7% too strong" is yes, it will
be visible as prose you keep re-reading, and that is the only way this
question gets answered.

--sheet renders one page per title length (the shortest and longest of the 16
real titles on disk, plus a middling one), because the density generator
absorbs title length and the failure modes are at the ends: a short title
tiles densely, a long one runs off the edges and crops.

THE ONE THING THIS CANNOT TELL YOU. An SVG renders <text> in whatever font the
viewer has. Godot's _draw() will use the project font. So judge DENSITY and
STRENGTH here; do not judge the letterforms.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import background_field as bf  # noqa: E402
import palette  # noqa: E402

# A 16:9 page at the host screen's own viewport size, so the marks are the size
# a player will actually see them.
PAGE_W, PAGE_H = 1280, 720

# The shortest and longest of the 16 real generated titles on disk, plus one in
# between. Not invented examples: the ends are where mark_count() does its work.
SAMPLE_TITLES = [
    "Whiteout",
    "The Stolen Star of Smurf Village",
    "Daggers in the Forum: The Ides of March",
]


def esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_field(title: str, seed: str, strength: float,
                 x0: int = 0, y0: int = 0,
                 w: int = PAGE_W, h: int = PAGE_H) -> list:
    """The field itself, tiled to fill (w, h). Returns SVG fragments.

    Tiling here is the same repeat the clients do -- background_field.py's
    _wrapped() exists precisely so the seams do not show, and a preview that
    drew a single 600px tile would never exercise it.
    """
    layout = bf.field_layout(title, seed=seed, strength=strength)
    tile = layout["tile"]
    out = [f'<g opacity="{layout["strength"]}">']
    for ty in range(0, h + tile, tile):
        for tx in range(0, w + tile, tile):
            for mark in layout["marks"]:
                cx, cy = x0 + tx + mark["x"], y0 + ty + mark["y"]
                if cx < x0 - tile or cy < y0 - tile:
                    continue
                out.append(
                    f'<text x="{cx:.1f}" y="{cy:.1f}" fill="{mark["colour"]}" '
                    f'font-size="{mark["size"]:.1f}" text-anchor="middle" '
                    f'dominant-baseline="middle" '
                    f'transform="rotate({mark["rotation"]:.1f} {cx:.1f} {cy:.1f})" '
                    f'>{esc(mark["text"])}</text>'
                )
    out.append("</g>")
    return out


def render_page(title: str, seed: str, strength: float) -> str:
    marks = len(bf.field_layout(title, seed=seed)["marks"])
    body = (
        "The body was found in the observatory at ten minutes past midnight, "
        "the door bolted from the inside and the only key still in the "
        "victim's own waistcoat pocket."
    )

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PAGE_W} {PAGE_H}" '
        f'width="{PAGE_W}" height="{PAGE_H}">',
        '<style>text{font-family:ui-sans-serif,system-ui,sans-serif}</style>',
        f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="{palette.GROUND}"/>',
    ]
    out += render_field(title, seed, strength)

    # A real screen's text, at the real sizes, so the field is judged against
    # what it has to sit behind rather than against nothing.
    tx = 64
    out.append(
        f'<text x="{tx}" y="110" fill="{palette.BRASS}" '
        f'font-size="{palette.TYPE_SCALE["title"]}" font-weight="700">'
        f'{esc(title)}</text>'
    )
    out.append(
        f'<text x="{tx}" y="150" fill="{palette.INK_FAINT}" '
        f'font-size="{palette.TYPE_SCALE["label"]}">'
        f'{len(title)} characters · {marks} marks · '
        f'{strength:.0%} strength · ground {palette.GROUND}</text>'
    )

    # Prose directly ON THE GROUND -- the hard case. Any panel would cover the
    # field, so a preview that only showed text on panels would prove nothing.
    out.append(
        f'<text x="{tx}" y="215" fill="{palette.INK}" '
        f'font-size="{palette.TYPE_SCALE["heading"]}" font-weight="600">'
        f'The Case (on the ground — the hard case)</text>'
    )
    for i, line in enumerate(_wrap(body, 62)):
        out.append(
            f'<text x="{tx}" y="{252 + i * 26}" fill="{palette.INK}" '
            f'font-size="{palette.TYPE_SCALE["body"]}">{esc(line)}</text>'
        )

    # And the same prose on a panel, which is where it lives in the real
    # client. The two side by side are the argument for the surface ramp.
    px, py, pw, ph = 660, 190, 560, 200
    out.append(
        f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="{palette.RADIUS["card"]}" '
        f'fill="{palette.SURFACE}" stroke="{palette.LINE_SOFT}" stroke-width="1"/>'
    )
    out.append(
        f'<text x="{px + 20}" y="{py + 36}" fill="{palette.INK}" '
        f'font-size="{palette.TYPE_SCALE["heading"]}" font-weight="600">'
        f'The Case (on a panel)</text>'
    )
    for i, line in enumerate(_wrap(body, 46)):
        out.append(
            f'<text x="{px + 20}" y="{py + 72 + i * 26}" fill="{palette.INK}" '
            f'font-size="{palette.TYPE_SCALE["body"]}">{esc(line)}</text>'
        )

    # The three button weights, so the whole palette is on one page.
    _button(out, tx, 470, 210, "Interrogate Suspects", palette.BRASS, palette.SURFACE_DEEP, palette.BRASS)
    _button(out, tx + 230, 470, 190, "Investigate Area", palette.SURFACE, palette.INK, palette.LINE)
    _button(out, tx + 440, 470, 190, "Make Accusation", palette.SURFACE, palette.NEGATIVE, palette.NEGATIVE)

    out.append(
        f'<text x="{tx}" y="560" fill="{palette.CAUTION}" '
        f'font-size="{palette.TYPE_SCALE["label"]}">Not moderated for play testing</text>'
    )
    out.append("</svg>")
    return "\n".join(out)


def _button(out: list, x: int, y: int, w: int, label: str,
            fill: str, ink: str, border: str) -> None:
    out.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="44" rx="{palette.RADIUS["base"]}" '
        f'fill="{fill}" stroke="{border}" stroke-width="1"/>'
    )
    out.append(
        f'<text x="{x + w / 2}" y="{y + 28}" fill="{ink}" text-anchor="middle" '
        f'font-size="{palette.TYPE_SCALE["body"]}">{esc(label)}</text>'
    )


def _wrap(text: str, width: int) -> list:
    words, lines, line = text.split(), [], ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1

    out_path = Path(sys.argv[1])
    rest = sys.argv[2:]
    strength = bf.MARK_STRENGTH

    if "--sheet" in rest:
        written = []
        for i, title in enumerate(SAMPLE_TITLES):
            page = out_path.with_name(f"{out_path.stem}_{i + 1}{out_path.suffix}")
            page.write_text(render_page(title, seed="PREVIEW", strength=strength))
            written.append(page)
        for page in written:
            print(f"wrote {page}")
        print(f"\n{len(written)} pages at {strength:.0%} strength. "
              f"The question item 17 leaves open is whether the prose on the "
              f"LEFT of each page (on the ground, no panel) is still "
              f"comfortable to read.")
        return 0

    title = " ".join(rest) if rest else SAMPLE_TITLES[1]
    out_path.write_text(render_page(title, seed="PREVIEW", strength=strength))
    print(f"wrote {out_path}  ({title!r}, "
          f"{len(bf.field_layout(title, seed='PREVIEW')['marks'])} marks, "
          f"{strength:.0%} strength)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
