#!/usr/bin/env python3
"""
browse_mysteries.py — human-readable summary of all generated mysteries.

Usage:
    python3 scripts/browse_mysteries.py            # list all
    python3 scripts/browse_mysteries.py --full     # full detail on every mystery
    python3 scripts/browse_mysteries.py burn_rate  # search by title keyword
"""

import json
import glob
import sys
import os
import textwrap

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "mystery_database", "generated")
WIDTH = 72


def divider(char="─"):
    print(char * WIDTH)


def wrap(text, indent=2):
    prefix = " " * indent
    return textwrap.fill(str(text), width=WIDTH, initial_indent=prefix, subsequent_indent=prefix)


def print_mystery(d, full=False):
    title = d.get("title", "Untitled")
    setting = d.get("setting", {})
    crime = d.get("crime", {})
    chars = d.get("characters", [])
    evidence = d.get("evidence", [])
    sol = d.get("solution", {})
    coh = d.get("_coherence", {})
    notes = d.get("gameplay_notes", {})

    status = "PASS" if coh.get("passed", True) else "FAIL"
    status_str = f"[{status}  {coh.get('blocking',0)} blocking  {coh.get('warnings',0)} warnings]"

    divider("═")
    print(f"  {title}")
    print(f"  {setting.get('location','')}  ·  {setting.get('time_period','')}")
    print(f"  Difficulty: {notes.get('difficulty','?')}  ·  {notes.get('estimated_playtime','?')}  ·  Coherence: {status_str}")
    divider()

    # Synopsis
    print("  SCENE")
    print(wrap(setting.get("description", "—")))
    print()
    print("  THE CRIME")
    print(wrap(crime.get("what_happened", "—")))
    print(wrap(f"Discovered: {crime.get('initial_discovery', '—')}"))
    print()

    # Cast
    print("  CAST")
    victim = next((c for c in chars if c.get("role") == "victim"), None)
    suspects = [c for c in chars if c.get("role") == "suspect"]
    witnesses = [c for c in chars if c.get("role") == "witness"]

    if victim:
        print(f"    VICTIM   {victim['name']} — {victim.get('occupation','')}")
    for s in suspects:
        print(f"    SUSPECT  {s['name']} — {s.get('occupation','')}")
    for w in witnesses:
        print(f"    WITNESS  {w['name']} — {w.get('occupation','')}")
    print()

    # Evidence — critical items always shown; all items if --full
    critical = [e for e in evidence if e.get("relevance") == "critical"]
    red_herrings = [e for e in evidence if e.get("relevance") == "red_herring"]
    print(f"  KEY EVIDENCE  ({len(evidence)} total · {len(critical)} critical · {len(red_herrings)} red herring)")
    items_to_show = evidence if full else critical
    for e in items_to_show:
        tag = {"critical": "★", "red_herring": "✗", "supporting": "·"}.get(e.get("relevance"), " ")
        print(f"    {tag} [{e.get('id','?')}] {e.get('name','?')}  ({e.get('type','')})")
        if full:
            print(wrap(e.get("description", ""), indent=6))
    print()

    # Solution — always shown (this is the GM view, not the player view)
    print("  SOLUTION")
    print(f"    Culprit:  {sol.get('culprit','?')}")
    print(wrap(f"Method: {sol.get('method','?')}", indent=4))
    print(wrap(f"Motive: {sol.get('motive','?')}", indent=4))
    print(f"    Key evidence: {', '.join(sol.get('key_evidence', []))}")
    if full:
        print()
        print("  HOW TO DEDUCE")
        print(wrap(sol.get("how_to_deduce", "—")))

    print()


def load_mysteries(keyword=None):
    files = sorted(glob.glob(os.path.join(DB_DIR, "*.json")))
    mysteries = []
    for f in files:
        try:
            d = json.load(open(f))
            if keyword:
                if keyword.lower() not in d.get("title", "").lower():
                    continue
            mysteries.append((f, d))
        except Exception as e:
            print(f"  [skip] {os.path.basename(f)}: {e}")
    return mysteries


def main():
    args = sys.argv[1:]
    full = "--full" in args
    keyword = next((a for a in args if not a.startswith("--")), None)

    mysteries = load_mysteries(keyword)

    if not mysteries:
        kw_msg = f' matching "{keyword}"' if keyword else ""
        print(f"No mysteries found{kw_msg}.")
        print(f"Directory searched: {os.path.abspath(DB_DIR)}")
        return

    print(f"\n  {len(mysteries)} mystery/mysteries\n")
    for _, d in mysteries:
        print_mystery(d, full=full)

    divider("═")
    print(f"  {len(mysteries)} total  ·  run with --full for evidence descriptions and deduction steps")
    print()


if __name__ == "__main__":
    main()
