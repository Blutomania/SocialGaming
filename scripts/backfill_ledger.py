#!/usr/bin/env python3
"""Seed the ledger from the mysteries already on disk. Free — no API call.

WHY BACKFILL AT ALL. The four mysteries in rejected/ are the entire evidence base
for the rules the generation prompt now carries: a finding clears at most one
suspect, every innocent needs two independent routes, a narrowing must exclude
somebody, a narrowing's prose must not name who it leaves possible. Each rule
exists because one of those files broke first. Leaving them out of the ledger
would mean starting the failure corpus at zero while the counter-examples sit in
a directory nothing reads.

WHAT IT CANNOT RECOVER. Cost. Nothing read response.usage before Session 41, so
every backfilled row carries cost_usd null and says so. That is deliberate: an
estimate here would silently become the denominator of a number the owner may
one day put in front of an investor.

LEGACY MYSTERIES ARE RECORDED AS 'unjudged', NOT ACCEPTED. All 17 files in
generated/ predate the Session 38 schema, so the rules defined over exonerates /
narrows / reveals fire trivially on every one of them. They are not evidence of
anything except that the schema changed. Their findings are recorded as advisory
so the data exists; no verdict is invented for them. The one exception is
coherence, which has always run on every mystery -- so a legacy file with a
BLOCKING report is genuinely rejected, and exactly one is.

IDEMPOTENT. A file already in the ledger is skipped, so re-running adds nothing.

Usage:
  python3 scripts/backfill_ledger.py            # show what it would write
  python3 scripts/backfill_ledger.py --go       # write it
"""

import argparse
import glob
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import gate                                                    # noqa: E402
import generation_ledger                                       # noqa: E402
from check_narrative import SCHEMA_EPOCH                       # noqa: E402

DB = _ROOT / "mystery_database"


def _is_legacy(path: Path) -> bool:
    try:
        return int(path.stem.rsplit("_", 1)[1]) < SCHEMA_EPOCH
    except (IndexError, ValueError):
        return True


def _mysteries():
    for sub in ("generated", "rejected"):
        for f in sorted(glob.glob(str(DB / sub / "*.json"))):
            p = Path(f)
            if "batch_summary" in p.name:
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if "solution" not in data and "characters" not in data:
                continue
            yield sub, p, data


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--go", action="store_true", help="actually write the rows")
    args = ap.parse_args()

    already = {r.get("slug") for r in generation_ledger.load()}
    written = 0
    skipped = 0

    for sub, path, data in _mysteries():
        slug = path.stem
        if slug in already:
            skipped += 1
            continue

        legacy = _is_legacy(path)
        verdict = gate.evaluate(data, path.name, legacy=legacy)

        try:
            timestamp = int(path.stem.rsplit("_", 1)[1])
        except (IndexError, ValueError):
            timestamp = int(path.stat().st_mtime)

        row = {
            "attempt_id": f"backfill-{slug[:40]}",
            "timestamp": timestamp,
            "elapsed_s": None,
            # The originating prompt was never stored on the mystery, so it
            # cannot be recovered either. Recorded as empty rather than guessed
            # from the title.
            "prompt": "",
            "slug": slug,
            "calls": [],
            "cost_usd": None,
            "coherence": data.get("_coherence"),
            "verdict": verdict.verdict,
            "failure_class": verdict.failure_class,
            "violations": verdict.violations,
            "advisory": verdict.advisory,
            "destination": sub,
            "backfilled": True,
            "backfill_note": "generated before the ledger existed; cost unrecoverable",
        }

        moved = ""
        if verdict.destination != sub:
            moved = f"  -> belongs in {verdict.destination}/"
        print(f"  [{sub:<9}] {slug[:46]:<46} {verdict.summary()[:60]}{moved}")

        if args.go:
            generation_ledger.append(row)
        written += 1

    print()
    print(f"  {written} row(s) {'written' if args.go else 'to write'}, {skipped} already present.")
    if not args.go:
        print("  Dry run. Re-run with --go to write them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
