# Color flavor for The Lineup round rule. Ported from lib/lineupData.js.
# No Claude call needed: the correct color is a curated real-world fact, and
# decoys are cheap to generate procedurally by nudging the real color's
# hue/saturation/lightness a small amount.

import colorsys
import random

LINEUP_COLORS = [
    {"entity": "the Philadelphia Eagles", "label": "green", "hex": "#004C54"},
    {"entity": "the Boston Celtics", "label": "green", "hex": "#007A33"},
    {"entity": "the Seattle Seahawks", "label": "green", "hex": "#69BE28"},
    {"entity": "the Green Bay Packers", "label": "green", "hex": "#203731"},
    {"entity": "Spotify", "label": "green", "hex": "#1DB954"},
    {"entity": "Starbucks", "label": "green", "hex": "#00704A"},
    {"entity": "Coca-Cola", "label": "red", "hex": "#F40009"},
    {"entity": "McDonald's", "label": "red", "hex": "#DA291C"},
    {"entity": "Facebook", "label": "blue", "hex": "#1877F2"},
    {"entity": "the Golden State Warriors", "label": "blue", "hex": "#1D428A"},
    {"entity": "Duke University", "label": "blue", "hex": "#001A57"},
    {"entity": "the LA Lakers", "label": "purple", "hex": "#552583"},
    {"entity": "the Minnesota Vikings", "label": "purple", "hex": "#4F2683"},
    {"entity": "Home Depot", "label": "orange", "hex": "#F96302"},
    {"entity": "the Tennessee Volunteers", "label": "orange", "hex": "#FF8200"},
]


def _hex_to_rgb01(hex_str):
    h = hex_str.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _rgb01_to_hex(rgb):
    r, g, b = (max(0, min(255, round(c * 255))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def _perturb_hex(hex_str):
    r, g, b = _hex_to_rgb01(hex_str)
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    def sign():
        return -1 if random.random() < 0.5 else 1

    h2 = (h * 360 + sign() * (4 + random.random() * 10)) % 360 / 360
    s2 = max(0.10, min(1.0, s + sign() * (2 + random.random() * 8) / 100))
    l2 = max(0.05, min(0.90, l + sign() * (2 + random.random() * 8) / 100))

    r2, g2, b2 = colorsys.hls_to_rgb(h2, l2, s2)
    return _rgb01_to_hex((r2, g2, b2))


def pick_color_lineup_entry():
    return random.choice(LINEUP_COLORS)


def build_color_options(entry, option_count=5):
    """Builds a shuffled option list for a color entry: the real hex plus
    option_count - 1 procedurally-perturbed decoys, none matching the real
    color or each other."""
    decoys = []
    guard = 0
    while len(decoys) < option_count - 1 and guard < 100:
        guard += 1
        candidate = _perturb_hex(entry["hex"])
        taken = {entry["hex"].lower(), *[d.lower() for d in decoys]}
        if candidate.lower() not in taken:
            decoys.append(candidate)

    all_hex = [entry["hex"], *decoys]
    random.shuffle(all_hex)
    options = [{"id": f"opt{i}", "hex": hexval} for i, hexval in enumerate(all_hex)]
    correct_option_id = next(o["id"] for o in options if o["hex"].lower() == entry["hex"].lower())
    return options, correct_option_id
