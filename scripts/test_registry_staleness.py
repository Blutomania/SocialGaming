#!/usr/bin/env python3
"""Regression test for the part-registry staleness check. Zero API cost.

WHY THIS EXISTS. `mystery_database/part_registry.json` is a derived index —
generation samples it, never the extraction files themselves. `load_registry()`
used to rebuild it only when the file was MISSING, never when the corpus had
moved on, so every extraction run after the last manual delete was silently
invisible to generation. That happened twice for real:

  March 11 -> Session 23   ~75 sources lost
  Session 23 -> Session 33  13 sources / 145 parts lost

Both times the corpus was correct on disk and the index simply did not know.
Nothing errored, which is exactly why it went unnoticed for months at a time.

The cheap way to pass "it detects staleness" is to rebuild unconditionally, so
this asserts both halves: a moved-on corpus rebuilds, AND an unchanged one does
not. The second is checked by corrupting the cached file and confirming the
corruption SURVIVES — a rebuild would repair it, so survival proves the cache
was genuinely reused.

Run: python3 scripts/test_registry_staleness.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import part_registry as pr  # noqa: E402

DB = Path(__file__).resolve().parent.parent / "mystery_database"
REGISTRY = DB / "part_registry.json"
PROBE = DB / "extractions" / "zz_staleness_probe.json"

failures = []


def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        failures.append(msg)


def main():
    if not REGISTRY.exists():
        pr.load_registry(str(DB))

    real = json.load(open(REGISTRY))
    stub = json.dumps(real[:10])

    print("--- an unchanged corpus reuses the cache ---")
    pr.load_registry(str(DB), force=True)          # establish a known-fresh sidecar
    REGISTRY.write_text(stub)
    reg = pr.load_registry(str(DB))
    check(len(reg.parts) == 10, "the corrupted cache survives, so nothing was rebuilt")

    print("\n--- force=True rebuilds regardless ---")
    reg = pr.load_registry(str(DB), force=True)
    check(len(reg.parts) == len(real), f"rebuilt to {len(reg.parts)} parts")

    print("\n--- a new extraction file makes it stale ---")
    PROBE.write_text(json.dumps({
        "crime": {"value": "a probe crime", "confidence": "high"},
        "_meta": {"title": "Staleness Probe"},
    }))
    try:
        REGISTRY.write_text(stub)
        reg = pr.load_registry(str(DB))
        check(len(reg.parts) > 10, f"rebuilt on its own ({len(reg.parts)} parts)")
        check(
            any(p.source_title == "Staleness Probe" for p in reg.parts),
            "and the new source is actually sampled, not merely counted",
        )
    finally:
        PROBE.unlink(missing_ok=True)

    print("\n--- a source REWRITTEN IN PLACE makes it stale ---")
    # The case the filename-only fingerprint could not see, and it is not
    # hypothetical: the P1->P1P2P3 upgrade replaces an extraction under its own
    # name, turning ~6 parts into ~20. Session 35's first 7 upgraded stories
    # landed with load_registry() reporting itself fresh and 98 parts unsampled.
    victim = sorted((DB / "extractions").glob("*.json"))[0]
    original = victim.read_bytes()
    before = len(pr.load_registry(str(DB), force=True).parts)
    try:
        enriched = json.loads(original)
        enriched["_meta"] = {**enriched.get("_meta", {}), "title": "Rewritten In Place"}
        # Add the exact field a real P1P2 -> P1P2P3 upgrade adds, so the rewrite
        # changes the part count the way the real thing does rather than only
        # changing bytes on disk. (P3.F4, mapped to axis 2 in Session 34.)
        enriched["setting_as_constraint"] = {
            "value": "a room reachable only through a spring-hinged passage",
            "confidence": "high",
        }
        victim.write_text(json.dumps(enriched))
        REGISTRY.write_text(stub)
        reg = pr.load_registry(str(DB))
        check(len(reg.parts) > 10, f"rebuilt on its own ({len(reg.parts)} parts)")
        check(len(reg.parts) > before,
              f"and picked up the added part ({before} -> {len(reg.parts)})")
    finally:
        victim.write_bytes(original)

    print("\n--- a schema-version bump makes it stale ---")
    # The other way this has gone stale: the extraction files are untouched but
    # the code that turns them into parts changed (Session 23's KEY_TO_IDX fix).
    # Nothing on disk moves, so only an explicit version can catch it.
    REGISTRY.write_text(stub)
    pr.REGISTRY_SCHEMA_VERSION += 1
    try:
        reg = pr.load_registry(str(DB))
        check(len(reg.parts) > 10, f"rebuilt on a version bump ({len(reg.parts)} parts)")
    finally:
        pr.REGISTRY_SCHEMA_VERSION -= 1

    # Leave the real registry correct whatever happened above.
    reg = pr.load_registry(str(DB), force=True)
    print(f"\nrestored: {len(reg.parts)} parts / "
          f"{len({p.source_id for p in reg.parts})} sources")

    print("\n=== ALL PASSED ===" if not failures else f"\n=== {len(failures)} FAILED ===")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
