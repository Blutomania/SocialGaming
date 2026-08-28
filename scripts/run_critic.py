#!/usr/bin/env python3
"""Run the critic over generated mysteries. Prints the plan and spends nothing
unless you pass --go.

Same shape as scripts/upgrade_p1_to_p1p2.py, for the same reason: this is the
only script in the repo besides that one that can spend real money, and the
default has to be the one that does not.

WHAT THIS IS FOR, IN TWO PHASES.

  Phase A — VALIDATE THE CRITIC. Run it over the mysteries already on disk. We
  have ground truth on several of them: daggers_in_the_forum reasons about four
  people who are not in its cast, the Smurf mystery names two culprits in one
  field, and scripts/check_narrative.py says 7 of 17 have a phantom person. If
  the critic misses those, the critic is broken and nothing it says about a
  fresh mystery can be trusted. The old corpus is the critic's TEST SET, and
  that is the reason to spend money on mysteries nobody will ever play.

  Phase B — MEASURE THE FAILURE RATE. Generate fresh mysteries under the current
  prompt and critique those. Only Phase B answers "how often is the critic
  needed", because a rate measured on the old forwards-written corpus is a rate
  for a pipeline that no longer exists.

Reports are written next to the mystery as <slug>.critic.json so a run is
resumable and a second pass costs nothing for what is already done.

Usage:
    python3 scripts/run_critic.py                    # plan + price, spends nothing
    python3 scripts/run_critic.py --go               # run it
    python3 scripts/run_critic.py --go --limit 3     # a toe in the water first
    python3 scripts/run_critic.py --only daggers     # substring match on filename
    python3 scripts/run_critic.py --go --force       # re-critique what is done
"""

import argparse
import glob
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import critic  # noqa: E402

GENERATED = ROOT / "mystery_database" / "generated"

# claude-opus-5, per the Current Models table. Input $5.00 / output $25.00 per
# million. Kept next to the model constant it prices so the two cannot drift
# apart silently, which is how the "1,469-part corpus" claim survived.
PRICE_PER_MTOK = {"claude-opus-5": (5.00, 25.00),
                  "claude-opus-4-8": (5.00, 25.00),
                  "claude-sonnet-5": (2.00, 10.00),
                  "claude-sonnet-4-6": (3.00, 15.00),
                  "claude-haiku-4-5": (1.00, 5.00)}

# MEASURED, not guessed. The first real run (daggers_in_the_forum, Opus 5)
# returned 9,573 output tokens against an estimate of 1,200 -- eight times over,
# and the dry run under-priced the batch by 4x as a result.
#
# The reason is worth keeping: adaptive thinking is billed as OUTPUT. A rubric
# that says "enumerate every person, then every chain step, then every clue, and
# cite the text for each" is exactly the kind of work a model thinks hard about,
# so the thing that makes the critic good is also what makes it cost more than
# the "reads a lot, writes a little" argument suggests. That argument still
# holds -- $0.28 against $0.14 for a generation is a critic that costs twice a
# mystery, not a fifth of one -- but state it at the real number.
ASSUMED_OUTPUT_TOKENS = 9600


def _get_client():
    """Same two auth sources as the server, in the same order and for the same
    reason: an API key goes on x-api-key, a session ingress token is a Bearer
    token and goes on Authorization. Passing one as the other returns 401."""
    from anthropic import Anthropic

    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return Anthropic(api_key=key)
    token = Path("/home/claude/.claude/remote/.session_ingress_token")
    if token.exists():
        return Anthropic(auth_token=token.read_text().strip())
    raise SystemExit(
        "No credentials. Set ANTHROPIC_API_KEY, or run where a session ingress "
        "token exists.")


def _mysteries(only=None):
    out = []
    for path in sorted(glob.glob(str(GENERATED / "*.json"))):
        p = Path(path)
        if "batch_summary" in p.name or p.name.endswith(".critic.json"):
            continue
        if only and only.lower() not in p.name.lower():
            continue
        out.append(p)
    return out


def _report_path(path: Path) -> Path:
    return path.with_suffix(".critic.json")


def _price(model: str, input_tokens: int, output_tokens: int) -> float:
    inp, outp = PRICE_PER_MTOK.get(model, PRICE_PER_MTOK["claude-opus-5"])
    return input_tokens / 1e6 * inp + output_tokens / 1e6 * outp


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--go", action="store_true",
                    help="actually spend money. Without this, nothing is called")
    ap.add_argument("--limit", type=int, help="stop after this many mysteries")
    ap.add_argument("--only", help="substring match on the filename")
    ap.add_argument("--model", default=critic.DEFAULT_MODEL)
    ap.add_argument("--force", action="store_true",
                    help="re-critique mysteries that already have a report")
    args = ap.parse_args()

    files = _mysteries(args.only)
    if not files:
        print(f"No mysteries matched in {GENERATED}.")
        return 0

    todo = [f for f in files if args.force or not _report_path(f).exists()]
    done = len(files) - len(todo)
    if args.limit:
        todo = todo[:args.limit]

    print(f"\n{len(files)} mystery(s) found; {done} already critiqued; "
          f"{len(todo)} to do.")
    print(f"Model: {args.model}\n")

    if not todo:
        print("Nothing to do. Pass --force to re-critique.")
        return 0

    client = _get_client()

    # Price it before spending. count_tokens is free.
    print("Counting input tokens (free)…")
    total_in = 0
    for path in todo:
        mystery = json.loads(path.read_text(encoding="utf-8"))
        n = critic.count_input_tokens(mystery, client, args.model)
        total_in += n
        print(f"  {path.name[:46]:48s} {n:>7,} in")

    est_out = ASSUMED_OUTPUT_TOKENS * len(todo)
    est = _price(args.model, total_in, est_out)
    print(f"\n  input   {total_in:>8,} tokens  (measured)")
    print(f"  output  {est_out:>8,} tokens  (ESTIMATED at "
          f"{ASSUMED_OUTPUT_TOKENS:,}/mystery — adaptive thinking is billed here too)")
    print(f"  ESTIMATED COST  ${est:,.2f}  for {len(todo)} mystery(s)")
    print(f"  per mystery     ${est / len(todo):,.3f}")

    if not args.go:
        print("\nDry run. Nothing was called and nothing was spent.")
        print("Re-run with --go to spend it.\n")
        return 0

    print(f"\n--- running ---\n")
    spent = 0.0
    failures = 0
    for i, path in enumerate(todo, 1):
        mystery = json.loads(path.read_text(encoding="utf-8"))
        started = time.time()
        try:
            report = critic.critique(mystery, client, args.model)
        except Exception as exc:                       # noqa: BLE001
            failures += 1
            print(f"  [{i}/{len(todo)}] FAIL {path.name[:44]:46s} {exc}")
            continue

        usage = report["_usage"]
        cost = _price(args.model, usage["input_tokens"], usage["output_tokens"])
        spent += cost
        report["_usage"]["cost_usd"] = round(cost, 4)
        report["_source"] = path.name
        _report_path(path).write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"  [{i}/{len(todo)}] {path.name[:40]:42s} "
              f"{critic.summarise(report):<40s} "
              f"${cost:.3f}  {time.time() - started:.0f}s")

    print(f"\n  spent ${spent:,.2f} on {len(todo) - failures} report(s), "
          f"{failures} failure(s).")
    print(f"  Reports written beside each mystery as <name>.critic.json")
    print(f"  Summarise them with: python3 scripts/critic_report.py\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
