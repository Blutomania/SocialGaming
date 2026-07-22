"""
Benchmark coherence_validator's check_parts()/check_mystery() latency.
========================================================================

Dimension-2 optimization (July 2026 session): before assuming validation
speed needs work, measure it. As of this writing:

    check_mystery: ~0.23 ms/call  (13-mystery real corpus average)
    check_parts:   ~0.05 ms/call  (real registry sample)

Both are roughly 1,000-10,000x faster than a single Claude API call (which
is the actual bottleneck in the generation pipeline) — validation latency is
not a real problem today. This script exists so that claim stays checked
rather than assumed as TAXONOMY_EXPANSION_CANDIDATES.md's ~40 candidate
rules get adopted over time; run it after adding new rules to catch a
regression before it ships, not after.

Usage:
    python3 scripts/coherence_benchmark.py
    python3 scripts/coherence_benchmark.py --iterations 500 --warn-ms 1.0
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from pathlib import Path

_repo_root = Path(__file__).parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

import coherence_validator as cv  # noqa: E402
import part_registry as pr        # noqa: E402


def benchmark_check_mystery(mysteries: list[dict], iterations: int) -> float:
    t0 = time.perf_counter()
    for _ in range(iterations):
        for m in mysteries:
            cv.check_mystery(m)
    t1 = time.perf_counter()
    return (t1 - t0) / (iterations * len(mysteries)) * 1000


def benchmark_check_parts(parts, iterations: int) -> float:
    t0 = time.perf_counter()
    for _ in range(iterations):
        cv.check_parts(parts)
    t1 = time.perf_counter()
    return (t1 - t0) / iterations * 1000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument(
        "--warn-ms", type=float, default=2.0,
        help="Print a warning if either benchmark exceeds this many ms/call (default: 2.0)",
    )
    args = parser.parse_args()

    mysteries = []
    for path in glob.glob(str(_repo_root / "mystery_database/generated/*.json")):
        with open(path) as f:
            mysteries.append(json.load(f))

    if not mysteries:
        print("No mysteries found in mystery_database/generated/ — nothing to benchmark against.")
        return

    registry = pr.load_registry()
    parts, _ = registry.sample_for_generation()

    mystery_ms = benchmark_check_mystery(mysteries, args.iterations)
    parts_ms = benchmark_check_parts(parts, args.iterations)

    print(f"check_mystery: {mystery_ms:.4f} ms/call  ({len(mysteries)} distinct mysteries, "
          f"{args.iterations} iterations)")
    print(f"check_parts:   {parts_ms:.4f} ms/call  ({args.iterations} iterations)")

    for name, ms in (("check_mystery", mystery_ms), ("check_parts", parts_ms)):
        if ms > args.warn_ms:
            print(f"WARNING: {name} exceeded --warn-ms threshold ({args.warn_ms} ms) — "
                  f"investigate before this compounds across many rules.")


if __name__ == "__main__":
    main()
