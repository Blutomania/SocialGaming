#!/usr/bin/env python3
"""Cost per accepted mystery, and the numbers that explain it. Free — reads disk.

WHY CPAM AND NOT COST PER CALL. Cost per call is the number that is easy to get
and it answers the wrong question. A model at a third the price with a third the
pass rate is a wash, and one with a worse pass rate is a loss disguised as a
saving. What a mystery actually costs is everything spent to get one that can be
served -- the rejected attempts included, because those are a real and recurring
cost of every accepted one.

That makes CPAM the number that decides the questions the owner is actually
asking: whether a cheaper or self-hosted model is worth moving to, and what a
generation costs when someone asks in a funding meeting.

IT CANNOT BE COMPUTED RETROACTIVELY. Nothing read response.usage before Session
41, so the four mysteries in rejected/ have no recoverable cost and are backfilled
with cost_usd null. `unpriced` below counts them. This report never spreads a
guess over them -- see generation_ledger.PRICES.

Usage:
  python3 scripts/cpam.py            # the summary
  python3 scripts/cpam.py --rows     # one line per attempt
  python3 scripts/cpam.py --json     # machine-readable
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generation_ledger import LEDGER_PATH, load, summarise  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", action="store_true", help="one line per attempt")
    ap.add_argument("--json", action="store_true", help="machine-readable summary")
    args = ap.parse_args()

    rows = load()
    if not rows:
        print(f"No ledger yet at {LEDGER_PATH}.")
        print("It is written by the generation pipeline; run one generation to start it.")
        return 0

    s = summarise(rows)
    if args.json:
        print(json.dumps(s, indent=2, sort_keys=True))
        return 0

    if args.rows:
        print(f"{'when':<12} {'verdict':<10} {'class':<15} {'cost':>9}  slug")
        print("-" * 78)
        for r in rows:
            cost = f"${r['cost_usd']:.4f}" if r.get("cost_usd") is not None else "  —"
            when = str(r.get("timestamp", ""))[:10]
            print(f"{when:<12} {r.get('verdict', '?'):<10} "
                  f"{(r.get('failure_class') or '') :<15} {cost:>9}  {r.get('slug', '')}")
        print()

    cpam = f"${s['cpam_usd']:.4f}" if s["cpam_usd"] is not None else "undefined (no accepted mysteries yet)"
    print("=" * 78)
    print(f"  attempts        {s['attempts']}")
    print(f"  accepted        {s['accepted']}")
    print(f"  rejected        {s['rejected']}")
    if s.get("unjudged"):
        print(f"  unjudged        {s['unjudged']}   (legacy schema — never put to the gate)")
    rate = f"{s['pass_rate']:.0%} of {s['accepted'] + s['rejected']} judged" \
        if s["pass_rate"] is not None else "— (nothing judged yet)"
    print(f"  pass rate       {rate}")
    print(f"  measured spend  ${s['total_cost_usd']:.4f}"
          + (f"   ({s['unpriced_rows']} row(s) unpriced, excluded)" if s["unpriced_rows"] else ""))
    print(f"  COST PER ACCEPTED MYSTERY   {cpam}")
    print("=" * 78)

    if s["by_failure_class"]:
        print("\n  rejections by class")
        for cls, n in sorted(s["by_failure_class"].items(), key=lambda kv: -kv[1]):
            print(f"    {n:>3}  {cls}")
    if s["by_rule"]:
        print("\n  rules fired (a rejection usually trips several)")
        for rule, n in sorted(s["by_rule"].items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"    {n:>3}  {rule}")

    if s["unpriced_rows"]:
        print(f"\n  {s['unpriced_rows']} attempt(s) carry no cost — generated before the ledger "
              f"existed, or on a model absent from generation_ledger.PRICES.")
        print("  They are counted in the pass rate and excluded from spend. Not estimated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
