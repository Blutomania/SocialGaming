#!/usr/bin/env python3
"""
Is a saved mystery actually winnable? Zero API cost, reads only local files.

A mystery can generate, save, serve and display perfectly while being
impossible to solve. The coherence validator already detects the main way
this happens -- P1.C4.culprit_not_in_characters, severity BLOCKING, "Chain is
broken; players can never identify them" -- but nothing in the pipeline acts
on that verdict: the mystery is saved and served anyway, and the failure
reaches the player as an ordinary "Wrong."

This is the pre-playtest version of that question, aimed at the accusation
screen specifically. Run it before handing a build to a playtester.

Checks per mystery:
  * solution.culprit resolves to at least one listed suspect, under the same
    matching rule accusation.gd uses (exact, else substring with a guard
    against a short name matching inside a longer one).
  * _coherence recorded a blocking failure.
  * the accusation dropdown will have something in it at all.

Usage:  python3 scripts/check_mystery_playable.py [slug-substring]
Exit:   0 = every mystery checked is winnable, 1 = at least one is not
"""
import json
import sys
from pathlib import Path

GENERATED = Path(__file__).resolve().parent.parent / "mystery_database" / "generated"


def is_culprit(accused: str, culprit_field: str, all_suspects: list) -> bool:
    """Mirror of accusation.gd's `_is_culprit`. Keep the two in step."""
    if accused == culprit_field:
        return True
    if not accused or accused not in culprit_field:
        return False
    for other in all_suspects:
        if other != accused and accused in other:
            return False
    return True


def check(path: Path):
    """Return (fatal_reasons, notes) for one saved mystery."""
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        return [f"unreadable: {exc}"], []
    if not isinstance(data, dict) or "characters" not in data:
        return [], []          # batch summaries and other non-mystery files

    fatal, notes = [], []
    suspects = [c.get("name", "") for c in data["characters"] if c.get("role") == "suspect"]
    culprit = (data.get("solution", {}) or {}).get("culprit") or ""

    if not suspects:
        fatal.append("no suspects — the accusation dropdown will be empty")

    matches = [s for s in suspects if is_culprit(s, culprit, suspects)]
    if not matches:
        fatal.append(f"culprit names no listed suspect: {culprit[:70]!r}")
    elif culprit not in suspects:
        notes.append(f"culprit is prose, resolves to {matches} by substring")

    coherence = data.get("_coherence", {})
    if coherence.get("blocking"):
        notes.append(f"coherence recorded {coherence['blocking']} blocking issue(s) and it was served anyway")

    return fatal, notes


def main():
    needle = sys.argv[1] if len(sys.argv) > 1 else ""
    files = sorted(p for p in GENERATED.glob("*.json") if needle in p.name)
    checked = unwinnable = 0

    for path in files:
        fatal, notes = check(path)
        if not fatal and not notes:
            checked += 1
            continue
        checked += 1
        print(f"{path.name}")
        for f in fatal:
            print(f"   ✗ {f}")
        for n in notes:
            print(f"   · {n}")
        if fatal:
            unwinnable += 1

    print(f"\nChecked {checked} saved mysteries. {unwinnable} unwinnable.")
    return 1 if unwinnable else 0


if __name__ == "__main__":
    sys.exit(main())
