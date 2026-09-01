#!/usr/bin/env python3
"""Prove check_narrative.py's link checks actually fire.

No mystery on disk declares chain links or reveals pointers yet -- the
generation reorder that produces links landed in the same session as the
checker, the `reveals` pointer one session later, and running generation costs
money. So the LINKS and REVEALS branches have no live input, and a branch with
no input is a branch nobody has run. These fixtures are that input.

Each case is a minimal mystery with exactly one fault planted, asserting the
checker names it and does not invent others.

Zero API cost. Exit: 0 = pass, 1 = failure.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_narrative import audit  # noqa: E402


def mystery(**over):
    """A minimal, fully correct mystery. Cases below break one thing."""
    base = {
        "title": "Fixture",
        "characters": [
            {"name": "Ada Vance", "role": "suspect"},
            {"name": "Boris Kell", "role": "suspect"},
            {"name": "Cora Innes", "role": "suspect"},
            {"name": "Dev Ortiz", "role": "suspect"},
            {"name": "Vic Tim", "role": "victim"},
        ],
        "evidence": [
            {"id": "E1", "relevance": "critical", "supports": ["S1"],
             "exonerates": ["Boris Kell"], "implicates": ["Ada Vance"]},
            {"id": "E2", "relevance": "supporting", "supports": ["S2"],
             "exonerates": ["Cora Innes", "Dev Ortiz"], "implicates": []},
            {"id": "E3", "relevance": "red_herring", "supports": [],
             "exonerates": [], "implicates": []},
        ],
        "solution": {
            "culprit": "Ada Vance",
            "method": "She did it in the pantry.",
            "motive": "Money.",
            "how_to_deduce": "Because the log clears Boris Kell and the key clears the others.",
            "chain": [{"id": "S1", "claim": "The log clears Boris Kell."},
                      {"id": "S2", "claim": "The key clears Cora Innes and Dev Ortiz."}],
        },
    }
    for k, v in over.items():
        base[k] = v
    return base


def pointered(**over):
    """The base fixture plus the witnesses and leads that carry `reveals`.

    Kept separate from mystery() on purpose: the base has no witnesses, leads
    or areas, so has_reveals is False there and the REVEALS branch stays off.
    That is deliberate -- it is how a pre-pointer mystery must behave, and the
    clean-fixture case above proves the branch does not fire on one.

    E1 exonerates Boris Kell and E2 exonerates the other two, so between them a
    witness and a lead must reach both for the pointered fixture to be clean.
    """
    base = mystery()
    base["characters"] = base["characters"] + [
        {"name": "Wilma Reed", "role": "witness",
         "statement": "The log was on the desk.", "reveals": ["E1"]},
        {"name": "Xan Pike", "role": "witness",
         "statement": "I saw the mud by the door.", "reveals": ["E3"]},
    ]
    base["leads"] = [
        {"id": "L1", "title": "The key register", "brief": "b", "reveals": ["E2"]},
        {"id": "L2", "title": "The muddy boot", "brief": "b", "reveals": ["E3"]},
    ]
    for k, v in over.items():
        base[k] = v
    return base


CASES = [
    ("a clean fixture reports nothing", mystery(), []),

    ("supports names a step that does not exist",
     mystery(evidence=[{"id": "E1", "relevance": "critical", "supports": ["S9"],
                        "exonerates": ["Boris Kell", "Cora Innes", "Dev Ortiz"],
                        "implicates": ["Ada Vance"]}]),
     ["E1 supports S9"]),

    ("a chain step nothing supports",
     mystery(evidence=[{"id": "E1", "relevance": "critical", "supports": ["S1"],
                        "exonerates": ["Boris Kell", "Cora Innes", "Dev Ortiz"],
                        "implicates": ["Ada Vance"]}]),
     ["chain step S2 is supported by no evidence"]),

    ("a red herring that supports the chain",
     mystery(evidence=[{"id": "E1", "relevance": "critical", "supports": ["S1"],
                        "exonerates": ["Boris Kell", "Cora Innes", "Dev Ortiz"],
                        "implicates": ["Ada Vance"]},
                       {"id": "E2", "relevance": "red_herring", "supports": ["S2"],
                        "exonerates": [], "implicates": []}]),
     ["red herring but supports"]),

    ("the culprit is exonerated",
     mystery(evidence=[{"id": "E1", "relevance": "critical", "supports": ["S1", "S2"],
                        "exonerates": ["Ada Vance", "Boris Kell", "Cora Innes", "Dev Ortiz"],
                        "implicates": ["Ada Vance"]}]),
     ["culprit (Ada Vance) is exonerated"]),

    ("elimination leaves more than one suspect",
     mystery(evidence=[{"id": "E1", "relevance": "critical", "supports": ["S1", "S2"],
                        "exonerates": ["Boris Kell"], "implicates": ["Ada Vance"]}]),
     ["leaves 3 suspect(s), not 1"]),

    ("nothing implicates anyone",
     mystery(evidence=[{"id": "E1", "relevance": "critical", "supports": ["S1", "S2"],
                        "exonerates": ["Boris Kell", "Cora Innes", "Dev Ortiz"],
                        "implicates": []}]),
     ["no evidence implicates anyone"]),

    ("the chain names somebody not in the cast",
     mystery(solution={**mystery()["solution"],
                       "how_to_deduce": "The ledger shows that Apolonios forged the seal."}),
     ["Apolonios"]),

    # --- REVEALS: the pointer that lets a witness or lead carry elimination ---

    ("a fixture with no witnesses or leads does not fire the REVEALS branch",
     mystery(), []),

    ("a clean pointered fixture reports nothing", pointered(), []),

    ("a reveals pointer naming no evidence item",
     pointered(characters=pointered()["characters"][:5] + [
         {"name": "Wilma Reed", "role": "witness", "statement": "s", "reveals": ["E9"]},
         {"name": "Xan Pike", "role": "witness", "statement": "s", "reveals": ["E1"]}]),
     ["witness Wilma Reed reveals 'E9', which is not in evidence[]"]),

    ("a witness that reveals nothing",
     pointered(characters=pointered()["characters"][:5] + [
         {"name": "Wilma Reed", "role": "witness", "statement": "s", "reveals": []},
         {"name": "Xan Pike", "role": "witness", "statement": "s", "reveals": ["E1"]}]),
     ["witness Wilma Reed reveals nothing"]),

    ("a lead that reveals nothing",
     pointered(leads=[{"id": "L1", "title": "t", "brief": "b", "reveals": ["E1", "E2"]},
                      {"id": "L2", "title": "t", "brief": "b", "reveals": []}]),
     ["lead L2 reveals nothing"]),

    ("an exoneration reachable only as a crime-scene clue",
     pointered(leads=[{"id": "L1", "title": "t", "brief": "b", "reveals": ["E3"]},
                      {"id": "L2", "title": "t", "brief": "b", "reveals": ["E3"]}]),
     ["E2 exonerates ['Cora Innes', 'Dev Ortiz'] but no witness, lead or area reveals it"]),

    ("an area pointer is checked the same way as a witness or lead",
     pointered(investigation_areas=[
         {"id": "A1", "name": "Pantry", "discovery": "d", "analysis": "a", "reveals": ["E7"]}]),
     ["area A1 reveals 'E7', which is not in evidence[]"]),
]


def run(name, data, expected):
    with tempfile.TemporaryDirectory() as d:
        # Named so audit() reads it as a CURRENT-schema mystery (post 2026-08-21).
        path = Path(d) / "fixture_1790000000.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        report = audit(path)

    found = report["links"] + report["reveals"] \
        + [f"CAST {c}" for c in report["cast"]] \
        + [f"ORPHAN {o}" for o in report["orphans"]]
    blob = " | ".join(found)

    if not expected:
        if found:
            return f"FAIL  {name}\n        expected nothing, got: {blob}"
        return None
    missing = [e for e in expected if e not in blob]
    if missing:
        return f"FAIL  {name}\n        expected {missing}\n        got: {blob or '(nothing)'}"
    return None


def main() -> int:
    failures = [f for f in (run(*c) for c in CASES) if f]
    for c in CASES:
        if run(*c) is None:
            print(f"  PASS  {c[0]}")
    for f in failures:
        print(f"  {f}")
    print()
    if failures:
        print(f"=== {len(failures)} FAILED ===")
        return 1
    print(f"=== ALL {len(CASES)} PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
