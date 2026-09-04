#!/usr/bin/env python3
"""Report exonerations nothing reveals, and wire the ones a finding can honestly
carry. Free — no API call.

Three generations running failed the two-routes rule, and every time the short
suspect's exoneration was exactly the one no witness, lead or area pointed at.
This is the arrangement half of that fix: the model invents the clue, the game
decides what points at it. Full reasoning in arrangement.py's module docstring.

It refuses far more often than it acts, on purpose. A pointer has to be earned
lexically — the carrier must already be ABOUT that evidence — and every wiring is
re-verified against the full gate before it is kept, because a carrier that gains
one exoneration too many can start solving the case on its own.

Usage:
  python3 scripts/wire_pointers.py                    # report on everything
  python3 scripts/wire_pointers.py --coverage         # who has a person and a place
  python3 scripts/wire_pointers.py <file> --go        # wire one mystery in place
"""

import argparse
import glob
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))

import gate                                                   # noqa: E402
import arrangement as WP                                      # noqa: E402

DB = _ROOT / "mystery_database"


def _files(target):
    if target:
        return [Path(target)]
    out = []
    for sub in ("generated", "rejected"):
        for f in sorted(glob.glob(str(DB / sub / "*.json"))):
            if "batch_summary" not in Path(f).name:
                out.append(Path(f))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("target", nargs="?", help="one mystery file (default: all on disk)")
    ap.add_argument("--go", action="store_true", help="write the wirings that survive the gate")
    ap.add_argument("--coverage", action="store_true",
                    help="report which suspects have a witness and an investigable place")
    args = ap.parse_args()

    if args.go and not args.target:
        print("Refusing to rewrite every mystery on disk. Name one file with --go.")
        return 2

    touched = orphans = wired = 0

    for path in _files(args.target):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not any("exonerates" in e for e in (data.get("evidence") or [])
                   if isinstance(e, dict)):
            continue                                   # legacy schema; nothing to wire
        touched += 1

        proposals = WP.propose(data)
        coverage = WP.world_coverage(data) if args.coverage else {}
        if not proposals and not coverage:
            continue

        print(f"\n  {path.name}")

        if args.go:
            applied, withheld = WP.apply(data, proposals, path.name)
            for p in applied:
                print(f"     WIRED   {p.evidence_id} -> {p.carrier.label}   "
                      f"(shared: {', '.join(p.shared[:4])}"
                      f"{'; names the person it clears' if p.named_person else ''})")
                wired += 1
            for p in withheld:
                print(f"     GAP     {p.evidence_id} clears {p.clears}")
                print(f"             {p.reason}")
                orphans += 1
            if applied:
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                                encoding="utf-8")
                v = gate.evaluate(data, path.name)
                print(f"     saved. gate now: {v.summary()[:88]}")
        else:
            for p in proposals:
                if p.actionable:
                    print(f"     COULD WIRE  {p.evidence_id} -> {p.carrier.label}   "
                          f"(shared: {', '.join(p.shared[:4])}"
                          f"{'; names the person it clears' if p.named_person else ''})")
                    wired += 1
                else:
                    print(f"     GAP         {p.evidence_id} clears {p.clears}")
                    print(f"                 {p.reason}")
                    orphans += 1

        for who, cov in coverage.items():
            bare = not cov["witnesses"] and not cov["areas"]
            flag = "  <-- no person AND no place" if bare else ""
            print(f"     WORLD   {who[:26]:<26} witnesses={len(cov['witnesses'])} "
                  f"areas={len(cov['areas'])} leads={len(cov['leads'])}{flag}")

    print()
    print(f"  {touched} current-schema mystery/mysteries examined: "
          f"{wired} pointer(s) {'wired' if args.go else 'wirable'}, {orphans} gap(s) needing prose.")
    if not args.go and wired:
        print("  Dry run. Name one file with --go to write it.")
    if orphans:
        print("  A GAP cannot be wired — nothing there is about that evidence. It needs one\n"
              "  finding written for it, which is invention and costs a call.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
