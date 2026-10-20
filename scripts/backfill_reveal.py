#!/usr/bin/env python3
"""backfill_reveal.py -- write solution.reveal for a mystery generated before it existed.

WHY. Since Session 51 the generation call writes the case's closing moment itself
(solution.reveal, the last field of the template), so winning makes no Claude
call. Mysteries generated earlier lack it and show the plain fallback -- the
culprit, method, motive and deduction joined together. This writes the reveal
once, offline, for a mystery already on disk: one call per mystery, paid once,
never at play time. Same rule as generation: generate, then never use AI again.

WHAT IT REFUSES. The reveal is put through check_narrative's RESOLUTION rules
before anything is written: it must name the culprit and at least one key
evidence item. A reveal that fails is printed and NOT saved -- re-run for
another attempt rather than keep a bad one.

    python3 scripts/backfill_reveal.py mystery_database/generated/<file>.json        # plan, free
    python3 scripts/backfill_reveal.py mystery_database/generated/<file>.json --go   # one call each

A mystery that already has a reveal is skipped. Needs the server's credentials
(ANTHROPIC_API_KEY, or the session token server/main.py also accepts).
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from check_narrative import audit_data  # noqa: E402

MODEL = "claude-sonnet-4-6"   # the generation model, so a backfilled reveal reads like a generated one
# Sonnet 4.6 list price per million tokens, for the printed estimate only.
PRICE_IN, PRICE_OUT = 3.00, 15.00

# The same rules the generation prompt's REVEAL section gives the model
# (server/main.py), minus the line about being the last field.
PROMPT = """\
Below is a complete murder mystery from a social deduction game, as JSON. Players have
already been given its findings; someone has just made the accusation.

Write the REVEAL: the moment the truth comes out, told to the whole table.
  - 4–6 sentences of prose, not a list and not a restatement of the solution fields, which
    the result screen already shows. Make it feel earned, not just correct: every clue was
    planted for this moment -- pay them off.
  - It MUST name the culprit, {culprit}, and it MUST name at least one of these key evidence
    items by its exact name, showing how it gave them away: {key_names}.
  - It must NOT say who solved it, who held which clue, or how the accusation went -- the game
    adds that live. Tell the story of the crime and its unravelling, not of the players.
  - It must not introduce any person, place or fact that is not already in the mystery.

Return ONLY the reveal text. No heading, no quotation marks, no commentary.

MYSTERY:
{mystery}"""


def plan(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    sol = data.get("solution") or {}
    if str(sol.get("reveal") or "").strip():
        return data, None
    by_id = {e.get("id"): e.get("name", "") for e in data.get("evidence") or []}
    key_names = [by_id[k] for k in sol.get("key_evidence") or [] if by_id.get(k)]
    visible = {k: v for k, v in data.items() if not k.startswith("_")}
    prompt = PROMPT.format(culprit=sol.get("culprit", "?"),
                           key_names="; ".join(key_names) or "(none listed)",
                           mystery=json.dumps(visible, ensure_ascii=False, indent=1))
    return data, prompt


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--go", action="store_true", help="make the call(s) and write")
    args = ap.parse_args()

    client = None
    failed = 0
    for path in args.files:
        data, prompt = plan(path)
        if prompt is None:
            print(f"  skip   {path.name} -- already has a reveal")
            continue
        if not args.go:
            print(f"  would  {path.name} -- one call, ~{len(prompt) // 4:,} input tokens")
            continue

        if client is None:
            from server.main import get_client   # deferred: a dry run needs no credentials
            client = get_client()
        resp = client.messages.create(model=MODEL, max_tokens=1200,
                                      messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        cost = (resp.usage.input_tokens * PRICE_IN + resp.usage.output_tokens * PRICE_OUT) / 1e6

        trial = json.loads(json.dumps(data))
        trial["solution"]["reveal"] = text
        report = audit_data(trial, path.name)
        if report["resolution"]:
            failed += 1
            print(f"  REFUSE {path.name} (${cost:.4f}) -- not written:")
            for msg in report["resolution"]:
                print(f"           {msg}")
            print(f"         the text was:\n{text}\n")
            continue

        data["solution"]["reveal"] = text
        # The generated files' own format -- indent 2, non-ASCII escaped, no final
        # newline -- so the diff is the new field and nothing else.
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"  wrote  {path.name} (${cost:.4f}, {resp.usage.output_tokens} output tokens):\n\n{text}\n")

    if not args.go:
        print("\nDry run -- nothing called, nothing written. Add --go to spend.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
