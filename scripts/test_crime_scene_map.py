#!/usr/bin/env python3
"""Tests for crime_scene_map.build_map. Zero API cost, no Godot needed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import crime_scene_map as csm

PASS = FAIL = 0


def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {label}" + (f" -- {detail}" if detail else ""))


def fake_mystery(n_areas=5, n_witnesses=2, title="The Test Case"):
    return {
        "title": title,
        "crime": {"initial_discovery": "found in the wine cellar", "what_happened": "poisoned"},
        "characters": (
            [{"name": f"Witness {i}", "role": "witness", "occupation": "porter"} for i in range(n_witnesses)]
            + [{"name": "Victim", "role": "victim"}, {"name": "Suspect", "role": "suspect"}]
        ),
        "investigation_areas": [
            {"id": f"A{i+1}", "name": f"Area {i+1}", "description": "a room"}
            for i in range(n_areas)
        ],
    }


def overlaps(a, b):
    return not (
        a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"]
        or a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"]
    )


def inside(px, py, r):
    return r["x"] <= px <= r["x"] + r["w"] and r["y"] <= py <= r["y"] + r["h"]


print("crime_scene_map")

# A mystery with no areas gets no map -- it must not invent rooms, because the
# playtest is testing whether generation produces usable areas.
check("no areas -> None", csm.build_map({"title": "x", "investigation_areas": []}) is None)
check("missing key -> None", csm.build_map({"title": "x"}) is None)

for n in range(1, 9):
    m = fake_mystery(n_areas=n)
    layout = csm.build_map(m)
    check(f"{n} areas -> {n} rooms", len(layout["areas"]) == n)

    for r in layout["areas"]:
        check(f"{n}: room in bounds",
              r["x"] >= 0 and r["y"] >= 0
              and r["x"] + r["w"] <= layout["width"]
              and r["y"] + r["h"] <= layout["height"],
              f"{r['name']} {r}")
        check(f"{n}: room has real size", r["w"] > 40 and r["h"] > 40, str(r))

    for i, a in enumerate(layout["areas"]):
        for b in layout["areas"][i + 1:]:
            check(f"{n}: rooms do not overlap", not overlaps(a, b), f"{a['name']} vs {b['name']}")

    # A row that does not fill the width leaves a hole that reads as a missing
    # room rather than as the shape of the building.
    rows = {}
    for r in layout["areas"]:
        rows.setdefault(r["y"], []).append(r)
    for y, row in rows.items():
        right = max(r["x"] + r["w"] for r in row)
        check(f"{n}: row fills width", abs(right - (layout["width"] - csm.MARGIN)) < 1.0,
              f"row at y={y} ends at {right}")

# Witnesses and the body must actually be in the room they claim.
m = fake_mystery(n_areas=5, n_witnesses=4)
layout = csm.build_map(m)
by_id = {a["id"]: a for a in layout["areas"]}
check("all witnesses placed", len(layout["witnesses"]) == 4)
for w in layout["witnesses"]:
    check("witness inside its area", inside(w["x"], w["y"], by_id[w["area_id"]]), str(w))
check("witnesses spread over distinct rooms",
      len({w["area_id"] for w in layout["witnesses"]}) == 4)
check("body inside its area", inside(layout["body"]["x"], layout["body"]["y"],
                                     by_id[layout["body"]["area_id"]]))

# Determinism: the host screen and the phone client must draw the same map.
check("same mystery -> identical layout", csm.build_map(m) == csm.build_map(m))
other = fake_mystery(n_areas=5, n_witnesses=4, title="A Different Case")
check("different mystery -> different placement",
      csm.build_map(other)["witnesses"][0]["x"] != layout["witnesses"][0]["x"])

# The body should land in the room the crime text points at, when one matches.
m2 = fake_mystery(n_areas=3)
m2["investigation_areas"][2]["name"] = "The Wine Cellar"
check("body follows the crime text",
      csm.build_map(m2)["body"]["area_id"] == "A3",
      str(csm.build_map(m2)["body"]))

# No match must not crash or guess wildly -- area 0 is a fine answer.
m3 = fake_mystery(n_areas=3)
m3["crime"] = {}
check("no crime text -> first area", csm.build_map(m3)["body"]["area_id"] == "A1")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
