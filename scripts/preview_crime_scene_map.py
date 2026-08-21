#!/usr/bin/env python3
"""
Render a crime-scene layout to SVG so the aesthetic can be judged by looking
at it rather than argued about. Zero API cost.

The SVG is a preview only -- the real renderers are Godot's _draw() on the
host screen and (later) inline SVG on the phone. All three consume the same
dict from crime_scene_map.build_map(), so what this shows is the real layout.

Usage:
    python3 scripts/preview_crime_scene_map.py <out.svg> [mystery.json]

With no mystery.json it renders a representative 5-area example, which is what
the generation prompt asks for ("INVESTIGATION AREAS (exactly 5)").
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crime_scene_map as csm

GROUND = "#2b2f36"      # CYM slate
ROOM = "#363b44"
LINE = "#8b93a1"
INK = "#e8e6e3"
MUTED = "#9aa2b1"
WITNESS = "#6fb3d2"
BODY = "#c9584f"

EXAMPLE = {
    "title": "The Last Note at the Velvet Cage",
    "crime": {"initial_discovery": "found slumped in the dressing room",
              "what_happened": "strangled with a microphone cable"},
    "characters": [
        {"name": "Rosalind Vane", "role": "witness", "occupation": "coat-check girl"},
        {"name": "Bertie Cole", "role": "witness", "occupation": "bartender"},
        {"name": "Marcus Hale", "role": "victim", "occupation": "singer"},
    ],
    "investigation_areas": [
        {"id": "A1", "name": "Main Floor", "description": "tables and a low stage"},
        {"id": "A2", "name": "The Bar", "description": "brass rail, spilled gin"},
        {"id": "A3", "name": "Dressing Room", "description": "mirrors and cables"},
        {"id": "A4", "name": "Back Alley", "description": "one locked door"},
        {"id": "A5", "name": "Manager's Office", "description": "a forced drawer"},
    ],
}


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render(layout: dict) -> str:
    w, h = layout["width"], layout["height"]
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
        f'<rect width="{w}" height="{h}" fill="{GROUND}"/>',
        f'<style>text{{font-family:ui-sans-serif,system-ui,sans-serif}}</style>',
    ]

    for a in layout["areas"]:
        out.append(
            f'<rect x="{a["x"]}" y="{a["y"]}" width="{a["w"]}" height="{a["h"]}" '
            f'fill="{ROOM}" stroke="{LINE}" stroke-width="2"/>'
        )
        out.append(
            f'<text x="{a["x"] + 14}" y="{a["y"] + 30}" fill="{INK}" '
            f'font-size="19" font-weight="600">{esc(a["name"])}</text>'
        )
        out.append(
            f'<text x="{a["x"] + 14}" y="{a["y"] + 50}" fill="{MUTED}" '
            f'font-size="13">{esc(a["id"])} · click to search</text>'
        )

    b = layout["body"]
    out.append(f'<circle cx="{b["x"]}" cy="{b["y"]}" r="11" fill="{BODY}"/>')
    out.append(
        f'<text x="{b["x"] + 18}" y="{b["y"] + 5}" fill="{BODY}" font-size="14" '
        f'font-weight="600">BODY</text>'
    )

    for wit in layout["witnesses"]:
        out.append(f'<circle cx="{wit["x"]}" cy="{wit["y"]}" r="9" fill="{WITNESS}"/>')
        out.append(
            f'<text x="{wit["x"] + 16}" y="{wit["y"] + 5}" fill="{INK}" font-size="14">'
            f'{esc(wit["name"])}</text>'
        )
        if wit.get("occupation"):
            out.append(
                f'<text x="{wit["x"] + 16}" y="{wit["y"] + 22}" fill="{MUTED}" '
                f'font-size="12">{esc(wit["occupation"])}</text>'
            )

    out.append("</svg>")
    return "\n".join(out)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    out_path = Path(sys.argv[1])
    mystery = EXAMPLE
    if len(sys.argv) > 2:
        mystery = json.loads(Path(sys.argv[2]).read_text())

    layout = csm.build_map(mystery)
    if layout is None:
        print(f"{mystery.get('title','?')} has no investigation_areas — no map to draw.")
        return 1
    out_path.write_text(render(layout))
    print(f"wrote {out_path}  ({len(layout['areas'])} areas, "
          f"{len(layout['witnesses'])} witnesses)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
