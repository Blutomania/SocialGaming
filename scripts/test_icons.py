#!/usr/bin/env python3
"""Regression tests for the icon build and the picking rule. Zero API cost.

Run: python3 scripts/test_icons.py

Two halves, and the second is the interesting one.

The FLATTEN half checks the transform against the shapes real exports actually
take -- paint on attributes, paint in a CSS class, paint in an inline style --
because a pass that only walked attributes would silently leave an
Illustrator-exported icon fully coloured while reporting success.

The PICK half checks the owner's rule: which icon a clue gets must carry no
information. That is a claim about a distribution, not about a line of code, so
it is asserted as one -- the same key must draw different icons in different
games, and across many keys the draw must be close to uniform. A fixed mapping
would pass a naive "is it deterministic" test and fail both of these.

The picking itself lives in GDScript, so this reimplements Godot's String.hash
to test the RULE rather than the syntax. That is a real limitation and it is
stated in the file: this proves the design is sound, not that Icons.gd compiles.
"""

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_icons import NotVector, _assert_vector, recolour  # noqa: E402

failures = []


def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        failures.append(msg)


# ---------------------------------------------------------------------------
# The flatten
# ---------------------------------------------------------------------------

ATTR = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><linearGradient id="g"><stop offset="0" stop-color="#F5A623"/></linearGradient></defs>
<circle cx="26" cy="26" r="17" fill="none" stroke="url(#g)" stroke-width="4"/>
<path d="M20 24 l6 -8" fill="#F5A623"/></svg>'''

CSS = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<style>.st0{fill:none;stroke:url(#grad);stroke-width:4}.st1{fill:#4A90D9}</style>
<circle class="st0" cx="26" cy="26" r="17"/>
<path class="st1" d="M10 10 h4 v4 h-4 z"/></svg>'''

INLINE = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<circle cx="26" cy="26" r="17" style="fill:none;stroke:#BD10E0;stroke-width:4"/></svg>'''

print("--- every export shape flattens, not just the easy one ---")
for name, src in [("paint on attributes", ATTR), ("paint in a CSS class", CSS),
                  ("paint in an inline style", INLINE)]:
    out, seen = recolour(src, "#FFFFFF")
    body = out.split("</defs>")[-1]
    check("url(#" not in body, f"{name}: no gradient reference survives on a shape")
    check("#F5A623" not in body and "#4A90D9" not in body and "#BD10E0" not in body,
          f"{name}: no source hue survives")
    check("#FFFFFF" in out, f"{name}: the target paint is applied")

print("\n--- fill:none is never painted ---")
# This is the difference between an outline icon and a solid blob. Painting a
# `none` fill does not recolour the icon, it replaces it with its silhouette.
for name, src in [("attributes", ATTR), ("CSS class", CSS), ("inline style", INLINE)]:
    out, _ = recolour(src, "#FFFFFF")
    check('fill="none"' in out or "fill:none" in out,
          f"{name}: the transparent fill is left alone")

print("\n--- currentColor is a legal target, for the phone copy ---")
out, _ = recolour(INLINE, "currentColor")
check("currentColor" in out, "the phone copy defers its colour to CSS")

print("\n--- a raster in an SVG wrapper is refused, not passed through ---")
raster = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
          '<image href="data:image/png;base64,iVBORw0KGgo=" width="64" height="64"/></svg>')
try:
    _assert_vector(Path("icons/clue/fake.svg"), raster)
    check(False, "an embedded raster is rejected")
except NotVector:
    check(True, "an embedded raster is rejected")

out, _ = recolour(ATTR, "#FFFFFF")
try:
    _assert_vector(Path("icons/clue/real.svg"), out)
    check(True, "a real vector is accepted")
except NotVector:
    check(False, "a real vector is accepted")


# ---------------------------------------------------------------------------
# The pick
# ---------------------------------------------------------------------------

def godot_string_hash(text: str) -> int:
    """Godot's String.hash(): the classic djb2, over UTF-8, truncated to 32 bits.

    Reimplemented because the rule under test lives in GDScript and there is no
    engine here to run it. What this validates is therefore the DESIGN -- that
    seeding on (game, key) distributes and de-correlates -- and not that
    Icons.gd parses. Session 36's rule applies: necessary, not sufficient.
    """
    h = 5381
    for byte in text.encode("utf-8"):
        h = ((h << 5) + h + byte) & 0xFFFFFFFF
    return h


def mix32(value: int) -> int:
    """The murmur3 finalizer, mirroring Icons.gd's _mix32.

    Not optional. Without it the low bits of djb2 barely move between adjacent
    keys and the set cycles in order -- see the comment on _mix32 in Icons.gd
    for the sequence this test produced before it was added.
    """
    h = value & 0xFFFFFFFF
    h = ((h ^ (h >> 16)) * 0x7FEB352D) & 0xFFFFFFFF
    h = ((h ^ (h >> 15)) * 0x846CA68B) & 0xFFFFFFFF
    return (h ^ (h >> 16)) & 0xFFFFFFFF


def pick(set_size: int, key: str, salt: str) -> int:
    return mix32(godot_string_hash(salt + " " + key)) % set_size


KEYS = [f"clue_{i}" for i in range(400)]
SET = 4

print("\n--- stable within a game, so nothing flickers on redraw ---")
check(all(pick(SET, k, "GAME1") == pick(SET, k, "GAME1") for k in KEYS),
      "the same key in the same game always draws the same icon")

print("\n--- reshuffled between games, which is what makes it carry nothing ---")
# A fixed mapping -- hash(key) with no game in the seed -- would pass the test
# above and fail this one. That is the whole point of asserting it.
moved = sum(1 for k in KEYS if pick(SET, k, "GAME1") != pick(SET, k, "GAME2"))
expected = len(KEYS) * (SET - 1) / SET
check(abs(moved - expected) < len(KEYS) * 0.12,
      f"a different game re-draws {moved}/{len(KEYS)} keys "
      f"(chance alone gives about {expected:.0f})")

print("\n--- close to uniform, so no icon is quietly rare ---")
for salt in ["GAME1", "GAME2", "GAME3"]:
    tally = Counter(pick(SET, k, salt) for k in KEYS)
    check(len(tally) == SET, f"{salt}: all {SET} icons are reachable")
    worst = max(abs(c / len(KEYS) - 1 / SET) for c in tally.values())
    check(worst < 0.06,
          f"{salt}: the furthest icon is {worst:.1%} off an even share")

print("\n--- two keys that look related do not draw related icons ---")
# The failure this guards against is a hash that preserves ordering, which
# would make consecutive clue ids walk the set in order and become readable.
runs = [pick(SET, f"clue_{i}", "GAME1") for i in range(60)]
ascending = sum(1 for a, b in zip(runs, runs[1:]) if (a + 1) % SET == b)
check(ascending < len(runs) * 0.45,
      f"consecutive ids do not step through the set in order "
      f"({ascending}/{len(runs) - 1} steps are +1)")

print("\n--- the GDScript side stays in step with what is tested here ---")
gd = (Path(__file__).resolve().parent.parent
      / "godot" / "scripts" / "theme" / "Icons.gd").read_text()
check("_mix32(seed_text.hash())" in gd,
      "Icons.gd avalanches the hash before the modulus")
check("salt + _SEP + key" in gd, "Icons.gd puts the salt in the seed, not just the key")
check("set_paths.is_empty()" in gd, "Icons.gd handles the empty set")


# ---------------------------------------------------------------------------
# The suspect tag fallback chain
# ---------------------------------------------------------------------------
# Icons.gd's _suspect_candidates() decides WHICH pool _pick() then hashes
# into; the hash/uniformity tests above already cover the picking itself, so
# this section is only about that pool-selection logic. Reimplemented in
# Python for the same reason godot_string_hash() is above: the real thing is
# GDScript, so this proves the design, and the source-text checks at the end
# of this section prove Icons.gd actually contains the matching shape.

def suspect_by_tags(tags_by_path: dict, required: list[str]) -> list[str]:
    return [p for p, tags in tags_by_path.items() if all(t in tags for t in required)]


def gender_bucket(pronouns: str) -> str:
    # Tokenized, not raw substring matching -- "he" is a substring of "they"
    # and "them", so a naive `"he" in p` buckets "they/them" as masculine.
    # This mirrors Icons.gd's _gender_bucket()/_words_only() exactly, after
    # that exact bug was caught here and fixed in both places.
    tokens = re.findall(r"[a-z]+", pronouns.lower())
    if any(t in ("she", "her", "hers") for t in tokens):
        return "feminine"
    if any(t in ("he", "him", "his") for t in tokens):
        return "masculine"
    return "neutral"


def suspect_candidates(tags_by_path: dict, all_paths: list[str],
                        pronouns: str, presentation: str) -> list[str]:
    pres = presentation.lower().strip()
    if pres and pres != "human":
        species = suspect_by_tags(tags_by_path, [pres])
        if species:
            return species
        generic = suspect_by_tags(tags_by_path, ["non-human"])
        if generic:
            return generic
    matched = suspect_by_tags(tags_by_path, [gender_bucket(pronouns), "human"])
    if matched:
        return matched
    return all_paths


TAGS = {
    "m1": ["masculine", "human"], "m2": ["masculine", "human"],
    "f1": ["feminine", "human"], "n1": ["neutral", "human"],
}
ALL_PATHS = list(TAGS.keys())

print("\n--- suspect tag fallback chain ---")
check(set(suspect_candidates(TAGS, ALL_PATHS, "she/her", "human")) == {"f1"},
      "an exact gender+human match narrows to just that bucket")
check(set(suspect_candidates(TAGS, ALL_PATHS, "he/him", "human")) == {"m1", "m2"},
      "a bucket with more than one icon returns all of them, not just one")
check(set(suspect_candidates(TAGS, ALL_PATHS, "they/them", "human")) == {"n1"},
      "an unrecognised pronoun string buckets as neutral, not an error")
check(set(suspect_candidates(TAGS, ALL_PATHS, "she/her", "martian")) == {"f1"},
      "a non-human presentation with no matching species OR generic tag "
      "falls through to the gender-matched human bucket -- not the full "
      "pool, and not empty -- before the true floor is ever reached")
NOTHING_MATCHES = {"x1": ["masculine", "human"]}  # she/her+martian matches none of this
check(set(suspect_candidates(NOTHING_MATCHES, ALL_PATHS, "she/her", "martian"))
      == set(ALL_PATHS),
      "only when NO step matches at all -- no species, no generic non-human, "
      "no gender-matched human -- does it fall to the true floor: the full, "
      "unfiltered pool")
TAGS_WITH_NONHUMAN = dict(TAGS, alien1=["non-human"])
check(suspect_candidates(TAGS_WITH_NONHUMAN, list(TAGS_WITH_NONHUMAN), "", "martian")
      == ["alien1"],
      "a non-human presentation with no species-specific tag falls to the "
      "generic non-human bucket before falling to the human pool")
TAGS_WITH_SPECIES = dict(TAGS, martian1=["non-human", "martian"])
check(suspect_candidates(TAGS_WITH_SPECIES, list(TAGS_WITH_SPECIES), "", "martian")
      == ["martian1"],
      "an exact species tag beats the generic non-human bucket when both exist")
check(set(suspect_candidates({}, ALL_PATHS, "she/her", "human")) == set(ALL_PATHS),
      "an empty tag dict (no tags.json yet) falls through to the full pool")

check("_suspect_by_tags(required)" in gd or "_suspect_by_tags(" in gd,
      "Icons.gd has a tag-matching helper")
check('"non-human"' in gd, "Icons.gd's fallback chain names the generic non-human tag")
check("IconSet.SUSPECT" in gd and "SUSPECT_TAGS" in gd,
      "Icons.gd's fallback floor is the full, untagged SUSPECT pool")


# ---------------------------------------------------------------------------
# icons/suspect/tags.json is enforced, not advisory
# ---------------------------------------------------------------------------
import json
import tempfile
from build_icons import UntaggedIcon, load_suspect_tags  # noqa: E402

print("\n--- tags.json is refused, not silently accepted, when it drifts ---")
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    (d / "a.svg").write_text("<svg/>")
    (d / "b.svg").write_text("<svg/>")
    tags_path = d / "tags.json"

    import build_icons
    old_tags_json = build_icons.TAGS_JSON
    build_icons.TAGS_JSON = tags_path
    try:
        tags_path.write_text(json.dumps({"tags": {"a.svg": ["masculine", "human"]}}))
        try:
            load_suspect_tags([d / "a.svg", d / "b.svg"])
            check(False, "a file with no tag entry is refused")
        except UntaggedIcon:
            check(True, "a file with no tag entry is refused")

        tags_path.write_text(json.dumps({"tags": {
            "a.svg": ["masculine", "human"], "b.svg": ["feminine", "human"],
            "c.svg": ["neutral", "human"],
        }}))
        try:
            load_suspect_tags([d / "a.svg", d / "b.svg"])
            check(False, "a tag entry for a file no longer on disk is refused")
        except UntaggedIcon:
            check(True, "a tag entry for a file no longer on disk is refused")

        tags_path.write_text(json.dumps({"tags": {
            "a.svg": ["masculine", "human"], "b.svg": ["feminine", "human"],
        }}))
        result = load_suspect_tags([d / "a.svg", d / "b.svg"])
        check(result == {"a.svg": ["masculine", "human"], "b.svg": ["feminine", "human"]},
              "a fully-tagged set loads cleanly")
    finally:
        build_icons.TAGS_JSON = old_tags_json

print("\n=== ALL PASSED ===" if not failures else f"\n=== {len(failures)} FAILED ===")
sys.exit(1 if failures else 0)
