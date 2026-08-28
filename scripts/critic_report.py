#!/usr/bin/env python3
"""Summarise critic reports, and grade the critic against what we already know.

Two jobs.

  1. AGGREGATE. One line per mystery, plus the totals that answer "how often
     would the critic fire" — which is the number the decision about whether to
     run it in the pipeline turns on.

  2. GRADE THE CRITIC. This is the more important one and it is why Phase A
     exists. scripts/check_narrative.py already knows, for free, which mysteries
     reason about a person absent from the cast — 7 of 17 at the time of
     writing, daggers_in_the_forum among them. Those are ground truth. So:

       critic found it too            -> agreement. The critic works.
       checker found it, critic did not -> a MISS. The critic is too lenient,
                                         and nothing it says can be trusted on
                                         a mystery we do not already have an
                                         answer for.
       critic found it, checker did not -> either a false positive, or a real
                                         fault only prose-reading can see.
                                         Read these by hand; they are the whole
                                         argument for paying for a critic.

     A critic that only agrees with the free checker is not worth $0.06 a
     mystery. The third row is what you are buying.

Zero API cost — it reads reports already on disk.

Usage:  python3 scripts/critic_report.py [--verbose]
"""

import argparse
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

GENERATED = ROOT / "mystery_database" / "generated"


def _checker_ground_truth():
    """Which mysteries the free checker says name a person absent from the cast."""
    from check_narrative import audit
    truth = {}
    for path in sorted(glob.glob(str(GENERATED / "*.json"))):
        p = Path(path)
        if "batch_summary" in p.name or p.name.endswith(".critic.json"):
            continue
        truth[p.name] = set(audit(p)["cast"])
    return truth


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verbose", action="store_true",
                    help="print every finding, not just the counts")
    args = ap.parse_args()

    reports = sorted(glob.glob(str(GENERATED / "*.critic.json")))
    if not reports:
        print("No critic reports yet. Run: python3 scripts/run_critic.py --go")
        return 0

    truth = _checker_ground_truth()
    rows, agree, miss, extra_only = [], 0, 0, 0
    total_cost = 0.0
    verdicts = {}

    for rp in reports:
        report = json.loads(Path(rp).read_text(encoding="utf-8"))
        source = report.get("_source", Path(rp).name)
        findings = report.get("findings") or []
        verdict = report.get("verdict", "?")
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        total_cost += (report.get("_usage") or {}).get("cost_usd", 0.0)

        blocking = [f for f in findings if f.get("severity") == "BLOCKING"]
        cast_findings = [f for f in findings
                         if str(f.get("code", "")).startswith("cast.")]
        known = truth.get(source, set())

        if known and cast_findings:
            status, agree = "agree", agree + 1
        elif known and not cast_findings:
            status, miss = "MISS", miss + 1
        elif not known and cast_findings:
            status, extra_only = "critic-only", extra_only + 1
        else:
            status = "—"

        rows.append((source, verdict, len(blocking), len(findings), status, known))

        if args.verbose:
            print(f"\n=== {source} — {verdict} ===")
            print(f"    {report.get('summary', '')}")
            for f in findings:
                print(f"    [{f.get('severity','?'):<8}] {f.get('code','?')}")
                print(f"       {f.get('claim','')}")
                cite = (f.get("citation") or "").replace("\n", " ")
                if cite:
                    print(f"       > {cite[:150]}")

    print(f"\n{'mystery':44s} {'verdict':<8s} {'block':>5s} {'all':>4s}  "
          f"{'vs free checker'}")
    print("-" * 88)
    for source, verdict, blocking, total, status, known in rows:
        note = f"{status}" + (f" ({len(known)} known)" if known else "")
        print(f"{source[:44]:44s} {verdict:<8s} {blocking:>5d} {total:>4d}  {note}")

    n = len(rows)
    would_fire = sum(1 for r in rows if r[2] > 0)
    print("-" * 88)
    print(f"\n  {n} report(s), ${total_cost:.2f} spent, "
          f"${total_cost / n:.3f} per mystery.")
    print("  verdicts: " + ", ".join(f"{k} {v}" for k, v in sorted(verdicts.items())))
    print(f"\n  {would_fire}/{n} have at least one BLOCKING finding — that is the")
    print(f"  regeneration rate if BLOCKING triggers a re-roll.")

    print(f"\n  GRADING THE CRITIC against scripts/check_narrative.py:")
    print(f"    {agree:>3d} agree      — critic found the phantom person the checker found")
    print(f"    {miss:>3d} MISSED     — checker found one, critic did not")
    print(f"    {extra_only:>3d} critic-only — critic flagged a cast fault the checker "
          f"could not see")
    if miss:
        print(f"\n  {miss} MISS(ES). The critic is too lenient on the one thing we can")
        print(f"  verify independently, so treat its judgement on motive and method")
        print(f"  — which nothing can verify — as unproven. Tighten the rubric before")
        print(f"  putting it in the pipeline.")
    elif agree:
        print(f"\n  No misses. The critic caught everything the free checker did,")
        print(f"  which is the minimum bar for trusting it on what the checker cannot see.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
