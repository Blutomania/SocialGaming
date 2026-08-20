"""
background_field.py — the CYM BACKGROUND layout (root CLAUDE.md item 17).

Computes where the mystery's own title is strewn across the page: a faded,
rotated, randomly-sized field of the title, over the slate ground. It is
TEXTURE, NOT CONTENT — nothing in it is meant to be read.

WHY THIS IS PYTHON AND NOT A BUILD SCRIPT. MYF's equivalent
(mind-your-friends/scripts/build-question-field.mjs) runs once at build time
and commits a static SVG, because its motif — a question mark — is the same in
every game. CYM's motif is the mystery's TITLE, which does not exist until a
player types it, so this has to run per game at runtime.

WHY THE SERVER COMPUTES IT AND THE CLIENTS ONLY DRAW IT. CYM has two clients:
the Godot host screen and server/static/mobile.html, the phone client every
player actually looks at. One layout computed here, rendered by both, means the
television and every phone show the IDENTICAL field. Two independent
implementations would drift, and the drift would be visible in the same room.
So this returns plain JSON-serialisable dicts, not an image: Godot draws them
in _draw(), the phone as inline SVG. Shipping a rasterised image instead would
need one renderer per client anyway, plus a size penalty on every game.

Zero API calls. Pure and deterministic: the same (title, seed) always gives the
same field, which is what lets a reconnecting player rejoin to the wall they
left rather than a reshuffled one.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import List

# The tile is square and wraps, so a client can repeat it to fill any screen.
# 600 matches MYF's, which is not cosmetic — the two games' fields should have
# the same spatial rhythm even though the marks differ.
TILE = 600

# Below MYF's 10%, deliberately. MYF's mark is an abstract glyph; this one is
# WORDS, and words are read involuntarily — a background you keep accidentally
# reading is worse than no background. CYM's screens also carry far more text
# than MYF's (clue lists, interrogation transcripts, evidence).
#
# NOT SETTLED BY ARGUMENT. Item 17 flags this as the thing to check on a real
# screen, and item 40's rule still applies: if the field needs more presence,
# add density, not opacity.
MARK_STRENGTH = 0.07

# What fraction of the tile the title's ink should cover. This, not a mark
# count, is the density dial — and it is what makes the generator absorb title
# length automatically. The 16 real titles on disk run 8 to 39 characters, and
# a fixed count would make "Whiteout" sparse and "Daggers in the Forum: The
# Ides of March" a mat.
INK_RATIO = 0.5

# Type size, as a fraction of the tile — ABSOLUTE, not scaled to fit the title.
#
# The first version sized each mark so the whole title spanned a set fraction
# of the tile, which is the obvious approach and is wrong in both directions: a
# long title shrank to unreadable-as-texture 15px, and because thin strips
# carry less ink, the budget then asked for MORE of them. Forty characters at
# 15px, sixty times over, is a mat of grey lines, not a texture.
#
# So size ignores length, and long titles simply run past the tile edge and
# crop — which item 17 wants regardless ("rotation and edge-cropping so most
# instances are partial"). Ink per mark then rises with length, so a longer
# title appears FEWER times, which is the right direction and quietly rewards
# the short titles the design asks players for.
SIZE_MIN = 0.055
SIZE_MAX = 0.13

TILT = 24  # max rotation either way, degrees

# Average glyph advance as a fraction of font size, for a condensed uppercase
# face. The server has no font metrics — it is not the thing rendering — so
# extent is approximated. That is fine HERE and would not be fine for layout
# that must not collide: this is a texture where marks overlapping is expected,
# so an approximation that is a few percent out changes nothing anyone can see.
ADVANCE = 0.55

# Full-strength values, composited at MARK_STRENGTH by the client — never
# pre-multiplied against the ground. Same rule as MYF's field: pre-multiplying
# means the ground can never be re-tuned without re-deriving every mark.
# The brass share was 16% in the first pass and it was too much: rendered, the
# warm marks read as a different, louder element rather than as part of one
# texture, and the eye went to them. Cut to 8% — present as an accent, not as a
# second voice.
MARKS = [
    ("#B8C4CF", 0.36),  # cool light — dominant
    ("#8FA3B5", 0.24),  # steel
    ("#6E8398", 0.20),  # deep steel
    ("#DDE5EC", 0.12),  # near-white, the occasional bright one
    ("#C9A227", 0.08),  # brass — the one warm note, sparingly
]


@dataclass
class Mark:
    """One placement. x/y are the mark's CENTRE, in tile coordinates."""
    text: str
    x: float
    y: float
    size: float
    rotation: float
    colour: str

    def to_dict(self) -> dict:
        d = asdict(self)
        for k in ("x", "y", "size", "rotation"):
            d[k] = round(d[k], 2)
        return d


def _seeded_random(seed: str):
    """A deterministic stream of floats in [0, 1) from a string seed.

    SHA-256 in counter mode rather than random.Random(seed): Python's Mersenne
    seeding is not guaranteed stable across interpreter versions, and this
    field must be reproducible for as long as a saved mystery is.
    """
    state = {"n": 0}
    key = seed.encode()

    def rand() -> float:
        digest = hashlib.sha256(key + state["n"].to_bytes(8, "big")).digest()
        state["n"] += 1
        return int.from_bytes(digest[:8], "big") / (1 << 64)

    return rand


def _colour_bag(count: int, rand) -> List[str]:
    """The published proportions, as a shuffled bag.

    Rolling a colour per mark instead misses the shares badly at these counts —
    a small share can vanish from a field entirely, which is visible.

    Apportioned by LARGEST REMAINDER, not by rounding each share
    independently. Independent rounding does not sum to `count`, and the
    obvious repair — build the bag then truncate it — silently deletes from
    whichever colour happens to be listed last. That is not hypothetical: the
    first version did exactly this, and because the 8% brass is declared last
    it was apportioned one slot and then had that slot truncated away, every
    single time. The field shipped with a published accent colour that
    literally never appeared, and it took a test over 40 seeds to see it.

    Floor every share, then hand the leftover slots to the largest fractional
    remainders. The total is exactly `count` by construction, so nothing is
    ever truncated, and no colour is systematically starved by its position in
    the list.
    """
    exact = [(hex_value, share * count) for hex_value, share in MARKS]
    bag: List[str] = []
    for hex_value, want in exact:
        bag.extend([hex_value] * int(want))

    # The leftover slots go out by WEIGHTED draw on the remainders, not to the
    # largest ones in order. Deterministic largest-remainder is right for a
    # single apportionment, but this one runs per game with a fixed share
    # table, so the same colours would win the leftovers in every field
    # forever — a systematic bias, not rounding noise. Measured over 40 seeds
    # that put one colour 7 points above its published share and another 5
    # below, permanently.
    #
    # Drawing each leftover with probability proportional to its remainder is
    # unbiased in aggregate while still favouring the colours that were closest
    # to earning a slot. A field of 13 marks can never be more accurate than
    # ±1/13 on its own; what this fixes is the average across games.
    remainders = [(want - int(want), hex_value) for hex_value, want in exact]
    while len(bag) < count:
        total = sum(r for r, _ in remainders)
        if total <= 0:
            bag.append(MARKS[0][0])
            continue
        pick = rand() * total
        for idx, (r, hex_value) in enumerate(remainders):
            pick -= r
            if pick <= 0:
                bag.append(hex_value)
                # Drawn without replacement: one colour cannot take every
                # leftover slot in a field.
                remainders[idx] = (0.0, hex_value)
                break
        else:
            bag.append(remainders[-1][1])

    for i in range(len(bag) - 1, 0, -1):
        j = int(rand() * (i + 1))
        bag[i], bag[j] = bag[j], bag[i]
    return bag


def mark_count(title: str) -> int:
    """How many times the title fits the ink budget. See INK_RATIO."""
    chars = max(len(title), 1)
    mean_size = TILE * (SIZE_MIN + SIZE_MAX) / 2
    ink_per_mark = (chars * ADVANCE * mean_size) * mean_size
    # The floor is 8, not 3. A long title hits the ink budget with very few
    # marks, and a rendering showed what that actually looks like: large bare
    # regions with nothing in them, which reads as a bug rather than as a
    # sparse texture. Below about 8 the field stops being a field.
    return max(8, min(40, round(TILE * TILE * INK_RATIO / ink_per_mark)))


def field_layout(title: str, seed: str = "", strength: float = MARK_STRENGTH) -> dict:
    """The whole field for one mystery, ready to send to a client.

    `seed` should be stable for a game (the game_id) so every player sees the
    same wall and a reconnect does not reshuffle it. `title` is folded into the
    seed too, so the same room re-skins when it plays a second mystery.
    """
    clean = " ".join(title.split()).strip()
    if not clean:
        # No title yet — the pre-prompt state. An empty field, not a broken
        # one: the client paints the ground and nothing else, which is exactly
        # what item 17 specifies for every stage before a mystery is named.
        return {"tile": TILE, "strength": strength, "marks": []}

    rand = _seeded_random(f"{seed}\x00{clean}")
    count = mark_count(clean)
    colours = _colour_bag(count, rand)
    chars = max(len(clean), 1)

    marks: List[Mark] = []
    for i, (cx, cy) in enumerate(_scatter(count, rand)):
        marks.append(Mark(
            text=clean,
            x=cx,
            y=cy,
            size=TILE * (SIZE_MIN + rand() * (SIZE_MAX - SIZE_MIN)),
            rotation=(rand() * 2 - 1) * TILT,
            colour=colours[i],
        ))

    return {
        "tile": TILE,
        "strength": strength,
        "marks": [m.to_dict() for m in _wrapped(marks, chars)],
    }


def _scatter(count: int, rand) -> List[tuple]:
    """Positions on a jittered grid, not uniform random.

    Uniform random placement is the obvious choice and it looked wrong: at
    these counts (8-40, where MYF's field has 44) pure randomness reliably
    produces clumps beside bare patches, and a rendering showed both. Bare
    ground in a texture reads as a rendering failure rather than as sparseness.

    A jittered grid — one mark per cell, positioned randomly WITHIN its cell —
    keeps coverage even while staying organic. The jitter is the whole cell, so
    neighbours can still touch; what it removes is the empty quarter of a tile,
    not the irregularity.
    """
    cols = max(1, round(count ** 0.5))
    rows = max(1, -(-count // cols))  # ceil, so every mark gets a cell
    cell_w, cell_h = TILE / cols, TILE / rows

    cells = [(c, r) for r in range(rows) for c in range(cols)]
    # Shuffle so that when count < rows*cols the unused cells are spread around
    # rather than always being the last row.
    for i in range(len(cells) - 1, 0, -1):
        j = int(rand() * (i + 1))
        cells[i], cells[j] = cells[j], cells[i]

    return [
        ((c + rand()) * cell_w, (r + rand()) * cell_h)
        for c, r in cells[:count]
    ]


def _wrapped(marks: List[Mark], chars: int) -> List[Mark]:
    """Redraw anything crossing an edge on the opposite side.

    Without this the tile seams show as bands of bare ground when a client
    repeats it — and this field needs it far more than MYF's does, because a
    title is WIDE. A mark whose text is longer than the tile crosses both
    vertical edges at once, so a single mark can legitimately need copies on
    both sides.
    """
    out: List[Mark] = []
    for mark in marks:
        half_w = chars * ADVANCE * mark.size / 2
        half_h = mark.size / 2
        for dx in (-TILE, 0, TILE):
            for dy in (-TILE, 0, TILE):
                if dx == 0 and dy == 0:
                    out.append(mark)
                    continue
                x, y = mark.x + dx, mark.y + dy
                if (x + half_w > 0 and x - half_w < TILE
                        and y + half_h > 0 and y - half_h < TILE):
                    out.append(Mark(mark.text, x, y, mark.size, mark.rotation, mark.colour))
    return out
