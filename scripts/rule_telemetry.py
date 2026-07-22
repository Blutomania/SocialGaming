"""
Correlate coherence rule firings against owner viability ratings.
==================================================================

Dimension-4 optimization (July 2026 session): CLAUDE.md's design principles
already name this direction for part_registry ("part signal — which parts
appear in high-rated mysteries"). This script applies the same idea to
coherence_validator's rules: which rule codes actually predict a low- or
high-rated mystery, versus which just fire a lot without correlating to
anything the owner cares about.

Reads every mystery_database/generated/*.json, pulls each one's
_coherence.rule_hits (added by server/main.py's _run_coherence — see that
function's docstring) and _meta.viability_rating (populated by POST /rate),
and reports, per rule code, how it splits across rating buckets.

As of this writing NO mystery in the corpus has a real viability_rating yet
(POST /rate is wired up but has never been called) — this script is the
plumbing for when that data exists, not a report with real findings today.
Run it after a batch of mysteries has actually been rated to get something
meaningful back; until then it will (correctly, honestly) report that there's
no signal yet, not fabricate a trend.

Usage:
    python3 scripts/rule_telemetry.py
    python3 scripts/rule_telemetry.py --dir mystery_database/generated
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def load_corpus(directory: Path) -> list[dict]:
    mysteries = []
    for path in sorted(directory.glob("*.json")):
        try:
            with open(path) as f:
                data = json.load(f)
            data["_source_path"] = str(path)
            mysteries.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return mysteries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir", default="mystery_database/generated",
        help="Directory of generated mystery JSONs (default: mystery_database/generated)",
    )
    args = parser.parse_args()

    directory = Path(args.dir)
    mysteries = load_corpus(directory)
    print(f"Loaded {len(mysteries)} mysteries from {directory}")

    rated = [m for m in mysteries if m.get("_meta", {}).get("viability_rating") is not None]
    unrated_with_hits = [
        m for m in mysteries
        if m.get("_meta", {}).get("viability_rating") is None and "_coherence" in m
    ]

    print(f"  {len(rated)} have a real viability_rating (via POST /rate)")
    print(f"  {len(unrated_with_hits)} have coherence telemetry but no rating yet")

    if not rated:
        print()
        print("No rated mysteries yet — nothing to correlate against.")
        print("This is expected as of the July 2026 session: POST /rate exists and")
        print("writes _meta.viability_rating, but no one has called it yet. Re-run")
        print("this script once a batch of mysteries has been rated through the app.")
        if unrated_with_hits:
            print()
            print("Rule-firing frequency across the unrated corpus (informational only —")
            print("frequency alone does NOT mean a rule matters, only that it fires):")
            counts = defaultdict(int)
            for m in unrated_with_hits:
                for hit in m.get("_coherence", {}).get("rule_hits", []):
                    counts[hit["code"]] += 1
            for code, n in sorted(counts.items(), key=lambda kv: -kv[1]):
                print(f"    {n:>3}  {code}")
        return

    # Real correlation, once rating data exists.
    by_code: dict[str, list[int]] = defaultdict(list)
    for m in rated:
        rating = m["_meta"]["viability_rating"]
        codes_present = {hit["code"] for hit in m.get("_coherence", {}).get("rule_hits", [])}
        for code in codes_present:
            by_code[code].append(rating)

    print()
    print("Rule code -> average viability_rating when that rule fired (lower = more concerning):")
    for code, ratings in sorted(by_code.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
        avg = sum(ratings) / len(ratings)
        print(f"    {avg:5.2f}  (n={len(ratings):>2})  {code}")


if __name__ == "__main__":
    main()
