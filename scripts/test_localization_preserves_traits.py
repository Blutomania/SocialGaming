#!/usr/bin/env python3
"""pronouns/presentation must survive the localization pass untouched.

Run: python3 scripts/test_localization_preserves_traits.py

_apply_name_map() (localization.py) rewrites the WHOLE mystery dict as one
JSON string and does a word-boundary regex substitution of old name -> new
name and old occupation -> new occupation across all of it -- not a
field-by-field walk. That means pronouns/presentation survive by
CONSTRUCTION, not because anything was written to protect them specifically:
nothing in a "she/her" or "human" value is ever a whole-word match for a
character's own name or occupation. This test proves that holds rather than
assuming it, and would catch it if _apply_name_map's approach ever changes
to something that walks fields by key instead.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from localization import _apply_name_map  # noqa: E402

failures = []


def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        failures.append(msg)


mystery = {
    "characters": [
        {
            "name": "Dr. Pemberton",
            "occupation": "Doctor",
            "pronouns": "she/her",
            "presentation": "human",
            "bio": "Dr. Pemberton has practiced medicine as a Doctor for years.",
        },
        {
            "name": "Zyx the Wanderer",
            "occupation": "Trader",
            "pronouns": "xe/xem",
            "presentation": "martian",
            "bio": "Zyx the Wanderer works as a Trader among the outposts.",
        },
    ]
}

name_map = [
    {"old": "Dr. Pemberton", "new": "Alexios the Physician", "old_occ": "Doctor", "new_occ": "Physician"},
    {"old": "Zyx the Wanderer", "new": "Vek the Trader", "old_occ": "Trader", "new_occ": "Merchant"},
]

result = _apply_name_map(mystery, name_map)
chars = result["characters"]

print("--- names and occupations actually get rewritten (sanity, not the point of this test) ---")
check(chars[0]["name"] == "Alexios the Physician", "old name is replaced")
check(chars[0]["occupation"] == "Physician", "old occupation is replaced")
check("Alexios the Physician" in chars[0]["bio"] and "Physician" in chars[0]["bio"],
      "the rewrite reaches free-text fields too, not just the name/occupation keys")

print("\n--- pronouns and presentation are untouched by the same pass ---")
check(chars[0]["pronouns"] == "she/her", "human character's pronouns survive unchanged")
check(chars[0]["presentation"] == "human", "human character's presentation survives unchanged")
check(chars[1]["pronouns"] == "xe/xem", "invented-pronoun character's pronouns survive unchanged")
check(chars[1]["presentation"] == "martian", "non-human character's presentation survives unchanged")

print("\n=== ALL PASSED ===" if not failures else f"\n=== {len(failures)} FAILED ===")
sys.exit(1 if failures else 0)
