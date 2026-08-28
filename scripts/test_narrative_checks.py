#!/usr/bin/env python3
"""Prove check_narrative.py's link checks actually fire.

No mystery on disk declares chain links yet -- the generation reorder that
produces them landed in the same session as the checker, and running generation
costs money. So the LINKS branch has no live input, and a branch with no input
is a branch nobody has run. These fixtures are that input.

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
             "produced_by": ["ACT1"],
             "exonerates": ["Boris Kell"], "implicates": ["Ada Vance"]},
            {"id": "E2", "relevance": "supporting", "supports": ["S2"],
             "produced_by": ["ACT1"],
             "exonerates": ["Cora Innes", "Dev Ortiz"], "implicates": []},
            {"id": "E3", "relevance": "red_herring", "supports": [],
             "produced_by": ["ACT2"],
             "exonerates": [], "implicates": []},
        ],
        "solution": {
            "culprit": "Ada Vance",
            "method": "She did it in the pantry.",
            "motive": "Money.",
            "how_to_deduce": "Because the log clears Boris Kell and the key clears the others.",
            "chain": [{"id": "S1", "claim": "The log clears Boris Kell."},
                      {"id": "S2", "claim": "The key clears Cora Innes and Dev Ortiz."}],
            "acts": [
                {"id": "ACT1", "by": "Ada Vance", "act": "She took the key.",
                 "guilty": True},
                {"id": "ACT2", "by": "Cora Innes", "act": "She dropped a glove.",
                 "guilty": False},
            ],
        },
    }
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

    ("a clue nothing caused",
     mystery(evidence=[{"id": "E1", "relevance": "critical", "supports": ["S1", "S2"],
                        "produced_by": [], "exonerates": ["Boris Kell", "Cora Innes",
                        "Dev Ortiz"], "implicates": ["Ada Vance"]}]),
     ["E1 has no produced_by"]),

    ("produced_by names an act that does not exist",
     mystery(evidence=[{"id": "E1", "relevance": "critical", "supports": ["S1", "S2"],
                        "produced_by": ["ACT9"], "exonerates": ["Boris Kell",
                        "Cora Innes", "Dev Ortiz"], "implicates": ["Ada Vance"]}]),
     ["E1 is produced_by ACT9"]),

    ("an act that left no trace",
     mystery(solution={**mystery()["solution"], "acts": [
         {"id": "ACT1", "by": "Ada Vance", "act": "She took the key.", "guilty": True},
         {"id": "ACT2", "by": "Cora Innes", "act": "She dropped a glove.", "guilty": False},
         {"id": "ACT3", "by": "Ada Vance", "act": "She wiped the handle.", "guilty": True},
     ]}),
     ["act ACT3 left no evidence"]),

    ("a red herring produced by a guilty act",
     mystery(evidence=[{"id": "E1", "relevance": "critical", "supports": ["S1", "S2"],
                        "produced_by": ["ACT1"], "exonerates": ["Boris Kell",
                        "Cora Innes", "Dev Ortiz"], "implicates": ["Ada Vance"]},
                       {"id": "E2", "relevance": "red_herring", "supports": [],
                        "produced_by": ["ACT1"], "exonerates": [], "implicates": []}]),
     ["red herring but ACT1 is a guilty act"]),

    ("an act performed by somebody not in the cast",
     mystery(solution={**mystery()["solution"], "acts": [
         {"id": "ACT1", "by": "Ada Vance", "act": "She took the key.", "guilty": True},
         {"id": "ACT2", "by": "Mysterious Stranger", "act": "He lurked.", "guilty": False},
     ]}),
     ["performed by 'Mysterious Stranger'"]),

    ("no guilty act belongs to the culprit",
     mystery(solution={**mystery()["solution"], "acts": [
         {"id": "ACT1", "by": "Boris Kell", "act": "He moved the key.", "guilty": True},
         {"id": "ACT2", "by": "Cora Innes", "act": "She dropped a glove.", "guilty": False},
     ]}),
     ["no guilty act is attributed to the culprit"]),

    ("the chain names somebody not in the cast",
     mystery(solution={**mystery()["solution"],
                       "how_to_deduce": "The ledger shows that Apolonios forged the seal."}),
     ["Apolonios"]),
]


def run(name, data, expected):
    with tempfile.TemporaryDirectory() as d:
        # Named so audit() reads it as a CURRENT-schema mystery (post 2026-08-21).
        path = Path(d) / "fixture_1790000000.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        report = audit(path)

    found = report["links"] + report["acts"] \
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
