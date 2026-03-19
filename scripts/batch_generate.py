#!/usr/bin/env python3
"""
Batch mystery generator — runs N mysteries non-interactively and captures output.

Usage:
    python scripts/batch_generate.py
    python scripts/batch_generate.py --db-dir ./mystery_database --players 4
    python scripts/batch_generate.py --demo   # no API calls
"""

import argparse
import json
import sys
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

# Ensure repo root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

import cli  # noqa: E402  (must be after sys.path tweak)

# ---------------------------------------------------------------------------
# The 14 mysteries to generate
# ---------------------------------------------------------------------------
MYSTERIES = [
    {
        "setting": "France, 1917 — the Western Front, a muddy sector of trenches near the Somme",
        "crime_type": "disappearance",
        "theme": "An entire battalion vanishes overnight without a trace, no bodies, no equipment left behind",
    },
    {
        "setting": "North Sea, 1952 — aboard a commercial fishing trawler found drifting forty miles off the Scottish coast",
        "crime_type": "murder",
        "theme": "The crew is missing; the engine is running, the nets are out, breakfast is still on the stove",
    },
    {
        "setting": "Prague, 1612 — the laboratory and apartments of a Royal Alchemist in the Hradcany district",
        "crime_type": "theft",
        "theme": "A coded manuscript containing the formula for the Philosopher's Stone has been stolen the night before its presentation to the Emperor",
    },
    {
        "setting": "Yucatan jungle, 1887 — a remote cenote considered sacred and secret by a local Maya community",
        "crime_type": "theft",
        "theme": "An ancient jade idol has been removed from the cenote floor; the community claims the cenote itself whispered the thief's name to the high priest",
    },
    {
        "setting": "Russian steppe, 1888 — the Trans-Siberian postal express, three days east of Ekaterinburg",
        "crime_type": "murder",
        "theme": "A government courier is found dead in a locked mail compartment; the diplomatic pouch he carried is intact but the sealed letter inside has been read and resealed",
    },
    {
        "setting": "Rome, 1st century AD — the Circus Maximus, during the most lucrative chariot race of the year",
        "crime_type": "sabotage",
        "theme": "A veteran charioteer renowned for stoic integrity deliberately crashes his own team at full speed, nearly killing himself — investigate why",
    },
    {
        "setting": "A small English village, 1963 — a quaint house on Unicorn Lane, just off Teddy Bear Close",
        "crime_type": "disappearance",
        "theme": "A mother of three vanished twenty years ago and was never found; her youngest child has now returned as an adult to uncover the truth",
    },
    {
        "setting": "Deep space, 2187 — a research vessel in orbit around Pluto, crewed by an order of 'data-monks' who maintain the solar network's memory archives",
        "crime_type": "murder",
        "theme": "A data-monk is found frozen solid on the exterior hull; the airlock logs show it was never opened",
    },
    {
        "setting": "Louisiana Territory, 1805 — a remote plantation house deep in the bayou, visited by a French government surveyor",
        "crime_type": "murder",
        "theme": "The surveyor arrives to find a formal dinner party frozen mid-meal — food still warm, wine poured, eight guests motionless at the table",
    },
    {
        "setting": "The Hyborian Age — the top of a windowless sorcerer's tower in the city of Tarantia, Kingdom of Aquilonia",
        "crime_type": "murder",
        "theme": "A high-ranking Aquilonian envoy and old mercenary brother-in-arms to King Conan is found dead atop the tower; no stairs lead to the roof",
    },
    # --- 4 additional mysteries ---
    {
        "setting": "France, 1917 — a ruined farmhouse command post on the Western Front, the morning after an assault",
        "crime_type": "disappearance",
        "theme": "An entire battalion of French soldiers vanished from their trench line during the night; cowardice or desertion is assumed, but the rifles, boots, and identity tags are all still there",
    },
    {
        "setting": "North Sea, 1943 — aboard a Finnish Navy patrol vessel that has intercepted a drifting trawler in international waters",
        "crime_type": "murder",
        "theme": "The trawler's crew is gone, the radio is smashed, and a meal is half-eaten — but the cargo hold is locked from the inside",
    },
    {
        "setting": "Yucatan, 14th century — inside a Maya temple complex during the feast of Tlacaxipehualiztli, when ritual heart sacrifice is performed",
        "crime_type": "theft",
        "theme": "A sacred jade-and-gold pectoral worn only by the high priest has vanished from the altar room during the height of the ceremony; the guards claim no one entered or left",
    },
    {
        "setting": "Central Asian steppe, 1206 — the forward camp of a Mongol scouting party riding ahead of Genghis Khan's main horde",
        "crime_type": "murder",
        "theme": "The Khan's most trusted advance scout is found with a broken neck; someone in the camp killed him before he could report what he had discovered",
    },
]

# ---------------------------------------------------------------------------


def make_args(mystery: dict, db_dir: str, num_players: int, demo: bool) -> SimpleNamespace:
    """Build a fake argparse Namespace that cmd_generate expects."""
    return SimpleNamespace(
        setting=mystery["setting"],
        crime_type=mystery.get("crime_type", "any"),
        num_players=num_players,
        theme=mystery.get("theme", ""),
        max_per_source=2,
        demo=demo,
        yes=True,          # skip confirmation prompt
        no_theme=False,
        db_dir=db_dir,
    )


def run_batch(db_dir: str, num_players: int, demo: bool):
    results = []
    total = len(MYSTERIES)

    print(f"\n{'='*60}")
    print(f"  BATCH MYSTERY GENERATION  ({total} mysteries)")
    print(f"  db_dir={db_dir}  players={num_players}  demo={demo}")
    print(f"{'='*60}\n")

    for i, m in enumerate(MYSTERIES, 1):
        slug = m["setting"][:60]
        print(f"\n[{i}/{total}] {slug}...")
        print(f"         crime={m.get('crime_type','any')}")
        t0 = time.time()
        status = "OK"
        error = None
        try:
            args = make_args(m, db_dir, num_players, demo)
            cli.cmd_generate(args)
        except SystemExit:
            pass  # cli calls sys.exit on some paths — ignore
        except Exception as exc:
            status = "ERROR"
            error = str(exc)
            traceback.print_exc()
        elapsed = time.time() - t0

        results.append({
            "index": i,
            "setting": m["setting"],
            "crime_type": m.get("crime_type", "any"),
            "status": status,
            "elapsed_s": round(elapsed, 1),
            "error": error,
        })
        print(f"         → {status}  ({elapsed:.1f}s)")

    # Summary table
    print(f"\n{'='*60}")
    print("  BATCH SUMMARY")
    print(f"{'='*60}")
    ok = sum(1 for r in results if r["status"] == "OK")
    err = len(results) - ok
    for r in results:
        flag = "✓" if r["status"] == "OK" else "✗"
        print(f"  {flag} [{r['index']:02d}] {r['setting'][:50]:<50}  {r['elapsed_s']:>6.1f}s")
        if r["error"]:
            print(f"       ERROR: {r['error']}")
    print(f"\n  {ok}/{total} succeeded, {err} failed")

    # Save machine-readable summary
    summary_path = Path(db_dir) / "generated" / f"batch_summary_{int(time.time())}.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Summary saved → {summary_path}\n")


def main():
    parser = argparse.ArgumentParser(description="Batch-generate mysteries non-interactively")
    parser.add_argument("--db-dir", default="./mystery_database", metavar="DIR")
    parser.add_argument("--players", type=int, default=4, metavar="N")
    parser.add_argument("--demo", action="store_true", help="No API calls (demo mode)")
    args = parser.parse_args()
    run_batch(args.db_dir, args.players, args.demo)


if __name__ == "__main__":
    main()
