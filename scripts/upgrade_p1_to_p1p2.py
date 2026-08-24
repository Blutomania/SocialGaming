#!/usr/bin/env python3
"""
Plan and run the P1 -> P1P2 upgrade for every source that is still P1-only.

WHY A PLANNER AND NOT JUST A COMMAND
------------------------------------
Three things make this job awkward enough to be worth a script:

1. The sources are not one directory. The P1-only extractions trace back to a
   handful of PDFs -- one of which is an anthology holding 63 of them -- and
   the anthology needs `--anthology` while the novels must not have it.
2. Some source PDFs are no longer on disk. An extraction records where it came
   from, but the file may have been moved or removed after extraction, and a
   source you cannot read cannot be upgraded. That should be reported up front,
   not discovered 40 minutes into a paid run.
3. It costs real money, so the default here is to print the plan and stop.
   Nothing is spent until you pass --go.

The upgrade itself is `extract_from_pdfs.py --upgrade`, which re-extracts only
sources whose existing file lacks the requested protocols. That makes the whole
job resumable: if it dies partway, run the same command again and it picks up
where it stopped instead of paying twice.

USAGE
    python3 scripts/upgrade_p1_to_p1p2.py               # plan only, costs nothing
    python3 scripts/upgrade_p1_to_p1p2.py --go          # actually run it
    python3 scripts/upgrade_p1_to_p1p2.py --go --model claude-sonnet-4-6

The replaced extractions are moved to mystery_database/extractions/_superseded/,
not deleted -- generation never reads that subdirectory.

AFTER IT FINISHES
    python3 scripts/test_registry_staleness.py     # the registry rebuild is automatic,
                                                   # this proves it noticed
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTIONS = ROOT / "mystery_database" / "extractions"
NEW_SOURCES = ROOT / "mystery_database" / "new_sources"

# Extra directories to search for source PDFs, added by --source-dir. Sources
# often live outside the repo entirely (a "raw_texts" folder, a Downloads
# directory), and PDFs are not committed, so new_sources/ is a convention
# rather than a guarantee.
EXTRA_ROOTS: list = []

P2_FIELDS = ["suspect_architecture", "red_herring", "clue_fairness",
             "alibi", "reveal_mechanic", "social_world"]

# $ per million tokens, input/output. Per-source figures come from the measured
# bake-off in docs/AI_COST_PLAYBOOK.md; a median source samples ~22.5K chars.
# Measured per source on a real Hitchcock story at P1P2P3, not estimated.
# P3 adds 8 fields for ~$0.03 on Opus; running it as its own later pass would
# cost a further ~$8 and an hour, because it re-reads the same books.
COST_PER_SOURCE = {
    "claude-opus-5": 0.147,
    "claude-sonnet-4-6": 0.065,
    "claude-haiku-4-5": 0.019,
    "claude-haiku-4-5-20251001": 0.019,
}

# P1+P2+P3. P3 (Craft) is where "setting as constraint" lives -- how the
# environment limits what is possible and how the culprit exploited it -- which
# is the transferable part of a crime scene: a relation, not a floor plan, so it
# survives the jump from a country house to a Mars dome.
PROTOCOL = "P1P2P3"

# Mirrors extract_from_pdfs.EXIT_FATAL — "the account or the credentials are the
# problem", as distinct from exit 1, "this one source failed". Duplicated rather
# than imported because importing that module pulls in anthropic/pypdf/dotenv,
# which would make merely *planning* an upgrade require the extraction deps.
# scripts/test_extraction_fatal_errors.py asserts the two stay equal.
EXIT_FATAL = 2


# Filenames carry the download site that produced them. Strip that for display
# so the list reads as book titles someone can go and find.
_NOISE = ("_OceanofPDF.com_", "OceanofPDF.com_", "pdfcoffee.com_", "-pdf-free", "_pdf_free")


_STOPWORDS = {"the", "a", "an", "of", "in", "on", "by", "and", "at", "for",
              "pdf", "free", "com", "mystery", "brit", "london", "book"}


def pretty_title(filename: str) -> str:
    stem = Path(filename).stem
    for n in _NOISE:
        stem = stem.replace(n, "")
    stem = stem.replace("__", " - ").replace("_", " ").replace("-", " ")
    stem = " ".join(stem.split()).strip(" -")
    # Download sites lowercase everything; restore title case only when they did.
    if stem == stem.lower():
        stem = " ".join(w if w in _STOPWORDS else w.capitalize() for w in stem.split())
    return stem


def search_key(filename: str) -> str:
    """The most distinctive word in a title, for a filename search.

    Taking the first word is what a naive version does, and on this list it
    produces `-iname "*The*"` three times over -- a pattern that matches every
    PDF on the disk. Longest non-stopword is short, specific, and survives the
    renaming that download sites do.
    """
    words = [w.strip("'\u2019.,") for w in pretty_title(filename).split()]
    words = [w for w in words if w.lower() not in _STOPWORDS and len(w) > 3]
    return max(words, key=len) if words else Path(filename).stem[:12]


def _norm(text: str) -> str:
    """Lowercase alphanumerics only — so spaces, underscores, hyphens and the
    download-site prefixes all collapse to the same key."""
    stem = Path(text).stem
    for n in _NOISE:
        stem = stem.replace(n, "")
    return "".join(ch for ch in stem.lower() if ch.isalnum())


def find_source(recorded: str) -> Path | None:
    """Locate a source PDF, tolerating renames and a moved or re-cloned repo.

    The path in _meta was correct on the machine that ran the extraction, and a
    file re-acquired later rarely comes back under exactly the same name --
    "The Winter Queen - Boris Akunin.pdf" becomes "The_Winter_Queen.pdf" or just
    "Turkish Gambit.pdf". An exact-filename match misses all of those, so the
    tiers below get progressively looser.

    The loose tiers only accept a UNIQUE hit. Extracting the wrong book against
    an existing extraction's slug would silently corrupt that corpus entry, and
    an ambiguous match is exactly when that happens -- so ambiguity reports
    nothing found rather than guessing.
    """
    if not recorded:
        return None

    # 1. exactly where it says it is
    for candidate in (Path(recorded), ROOT / recorded):
        if candidate.is_file():
            return candidate

    pdfs = []
    for root in [NEW_SOURCES, *EXTRA_ROOTS]:
        if root.exists():
            pdfs += [p for p in root.rglob("*.pdf") if p.is_file()]
    if not pdfs:
        return None

    # 2. same filename, anywhere under new_sources/ (including its top level)
    name = Path(recorded).name
    for hit in pdfs:
        if hit.name == name:
            return hit

    # 3. same title once punctuation and site prefixes are normalised away
    target = _norm(recorded)
    if target:
        exact = [p for p in pdfs if _norm(p.name) == target]
        if len(exact) == 1:
            return exact[0]

        # 4. one name contains the other ("Turkish Gambit" vs "Turkish Gambit - Boris Akunin")
        contained = [p for p in pdfs
                     if _norm(p.name) and (_norm(p.name) in target or target in _norm(p.name))]
        if len(contained) == 1:
            return contained[0]

    # A single-shared-word tier was tried here and removed. It is unique often
    # enough to look like it works and wrong often enough to be dangerous: with
    # only "Turkish" in common it matched "Turkish Delight Mystery.pdf" to
    # "Turkish Gambit - Boris Akunin.pdf". A unique match is not a correct one,
    # and extracting the wrong book into an existing extraction's slug would
    # silently replace that corpus entry with a different novel. Tier 4 already
    # covers the realistic renames; anything looser is the user's call, made by
    # renaming the file to the recorded name.
    return None


def scan() -> tuple[dict, list]:
    """Group P1-only extractions by source. Returns (plan, orphans)."""
    plan: dict[str, dict] = {}
    orphans = []
    for f in sorted(EXTRACTIONS.glob("*.json")):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        if not isinstance(d, dict) or "_meta" not in d:
            continue
        # Scope is deliberately "has no P2 content" -- the 75 P1-only sources --
        # even though the protocol run on them is P1P2P3. Selecting on "lacks P3"
        # instead pulls in all 564 extractions, including the 206 already at P1P2
        # and every ebook_* source: ~$83, and mostly blocked on PDFs that are no
        # longer on disk. Deepening those is a separate, larger decision.
        if any(d.get(k) for k in P2_FIELDS):
            continue
        meta = d["_meta"]
        recorded = meta.get("source") or meta.get("filename") or ""
        if not recorded:
            orphans.append(f.name)        # no recorded source: nothing to re-read
            continue
        found = find_source(recorded)
        key = recorded
        entry = plan.setdefault(key, {
            "recorded": recorded,
            "path": found,
            "count": 0,
            "anthology": bool(meta.get("story_index")),
        })
        entry["count"] += 1
        if not found:
            orphans.append(f.name)
    return plan, orphans


def check_sources(runnable: dict) -> int:
    """Verify each found PDF still yields the text it yielded the first time.

    "Is this copy usable?" is measurable, not a guess. Every one of these files
    was extracted successfully once, and the extraction recorded how many
    characters it sampled. Re-sampling the copy on disk and comparing to that
    number catches the failure that actually happens with a re-acquired book:
    a scan with no OCR layer, which opens fine, shows pages, and yields almost
    no text. The extractor would read it, find too little text, and skip -- but
    only after the run had already started.
    """
    # pypdf logs a warning per malformed cross-reference entry. Old scanned
    # books emit hundreds, which buries the actual result.
    import logging
    logging.getLogger("pypdf").setLevel(logging.ERROR)

    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        import extract_from_pdfs as efp
    except ImportError as exc:
        print(f"\ncannot check: {exc}  (pip install pypdf)")
        return 1

    # Recorded sample length, per source filename.
    recorded_len = {}
    for f in EXTRACTIONS.glob("*.json"):
        try:
            m = json.loads(f.read_text()).get("_meta", {})
        except Exception:
            continue
        if m.get("filename") and m.get("text_len"):
            recorded_len.setdefault(m["filename"], m["text_len"])

    print("\n" + "=" * 78)
    print("SOURCE HEALTH — no API calls")
    print("=" * 78)
    bad = 0
    for v in sorted(runnable.values(), key=lambda x: -x["count"]):
        path = v["path"]
        # An anthology's extractions record PER-STORY lengths, so comparing them
        # to whole-book novel-mode sampling is meaningless -- it flagged a
        # perfectly good 1.6M-character anthology as unusable on the first run.
        want = None if v["anthology"] else recorded_len.get(Path(v["recorded"]).name)
        try:
            sampled, full = efp.extract_text_from_pdf(path)
        except Exception as exc:
            print(f"\n  UNREADABLE  {path.name[:60]}\n              {type(exc).__name__}: {str(exc)[:70]}")
            bad += 1
            continue

        got = len(sampled)
        note = ""
        if got < efp.MIN_TEXT_CHARS:
            note = f"  <- TOO LITTLE TEXT (min {efp.MIN_TEXT_CHARS:,}); likely a scan with no OCR layer"
            bad += 1
        elif want and got < want * 0.5:
            note = f"  <- only {got/want:.0%} of the {want:,} chars the first extraction sampled"
            bad += 1
        ref = f", first extraction sampled {want:,}" if want else ""
        print(f"\n  {path.name[:66]}")
        if v["anthology"]:
            print(f"    {len(full):,} chars in the PDF; anthology mode feeds each story "
                  f"whole (up to {efp.ANTHOLOGY_FULLTEXT_THRESHOLD:,} chars){note}")
        else:
            print(f"    {len(full):,} chars in the PDF, {got:,} sampled for extraction{ref}{note}")

    print("\n" + "-" * 78)
    if bad:
        print(f"{bad} source(s) look unusable. Replace them before running --go;")
        print("the extractor would read each one and skip it, after the run had started.")
    else:
        print("All sources readable and consistent with the original extractions.")
    return 1 if bad else 0


def report_missing(blocked: dict) -> int:
    """Name the absent sources and show how to look for them locally."""
    if not blocked:
        print("\nNothing missing — every source PDF was found.")
        return 0

    names = [Path(v["recorded"]).name for v in blocked.values()]
    print("\n" + "=" * 78)
    print("MISSING SOURCE FILES")
    print("=" * 78)
    for n in sorted(names):
        print(f"\n  {pretty_title(n)}")
        print(f"    original filename: {n}")

    print("\n" + "-" * 78)
    print("TO SEARCH THIS COMPUTER")
    print("-" * 78)
    print("\nmacOS (Spotlight index — fastest, whole disk):")
    for n in sorted(names):
        print(f'  mdfind -name "{search_key(n)}"')
    keys = sorted({search_key(n) for n in names})
    print("\nmacOS or Linux (no index; searches your home folder — slower but thorough):")
    print('  find ~ -iname "*.pdf" \\( ' +
          " -o ".join(f'-iname "*{k}*"' for k in keys) + " \\) 2>/dev/null")
    print("\nOr search for the exact original filenames:")
    print("  for f in \\")
    for n in sorted(names):
        print(f'    "{n}" \\')
    print("  ; do find ~ -iname \"$f\" 2>/dev/null; done")

    print("\n" + "-" * 78)
    print("IF YOU FIND THEM")
    print("-" * 78)
    print("  Copy them anywhere under mystery_database/new_sources/ — this script")
    print("  searches that tree recursively and matches on filename, so the original")
    print("  names above are the safest thing to keep. Then re-run:")
    print("      python3 scripts/upgrade_p1_to_p1p2.py")
    print("  and they will move from BLOCKED to UPGRADEABLE.")

    out = NEW_SOURCES / "_MISSING_SOURCES.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "# Source PDFs needed for the P1->P2 upgrade\n\n"
        "These extractions are still P1-only and cannot be upgraded until the source\n"
        "PDF is available again. Drop the file anywhere under this directory and re-run\n"
        "`python3 scripts/upgrade_p1_to_p1p2.py`.\n\n"
        + "".join(f"- **{pretty_title(n)}**  \n  `{n}`\n" for n in sorted(names))
    )
    print(f"\nmanifest written -> {out.relative_to(ROOT)}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-opus-5",
                    help="model for the upgrade (default: claude-opus-5)")
    ap.add_argument("--go", action="store_true",
                    help="actually run it. Without this, the plan is printed and nothing is spent.")
    ap.add_argument("--source-dir", action="append", default=[], metavar="DIR",
                    help="another directory to search for source PDFs, recursively. "
                         "Repeatable. Use it when the PDFs live outside the repo — e.g. "
                         "--source-dir ~/raw_texts")
    ap.add_argument("--novel-chars", type=int, default=24000, metavar="N",
                    help="how much of each novel to sample (default 24,000; the "
                         "extractor's own default is 6,000, which is thin for P2)")
    ap.add_argument("--check-sources", action="store_true",
                    help="open every found PDF and verify it still yields usable text, "
                         "comparing against the length the original extraction recorded. "
                         "Costs nothing and catches a scanned or truncated replacement "
                         "before it wastes an API call.")
    ap.add_argument("--find-missing", action="store_true",
                    help="print search commands for source PDFs that are not on this machine, "
                         "and write a manifest to mystery_database/new_sources/_MISSING_SOURCES.md")
    args = ap.parse_args()
    EXTRA_ROOTS.extend(Path(d).expanduser().resolve() for d in args.source_dir)
    for d in EXTRA_ROOTS:
        print(f"also searching: {d}" + ("" if d.exists() else "   <- DOES NOT EXIST"))
    if EXTRA_ROOTS:
        print()

    plan, orphans = scan()
    runnable = {k: v for k, v in plan.items() if v["path"]}
    blocked = {k: v for k, v in plan.items() if not v["path"]}

    total = sum(v["count"] for v in plan.values())
    can = sum(v["count"] for v in runnable.values())
    per = COST_PER_SOURCE.get(args.model, 0.12)

    print(f"P1-only extractions: {total}   from {len(plan)} source file(s)")
    print(f"target protocol: {PROTOCOL}")
    print()

    if runnable:
        print("UPGRADEABLE — source PDF found:")
        for v in sorted(runnable.values(), key=lambda x: -x["count"]):
            kind = "anthology" if v["anthology"] else "novel"
            print(f"  {v['count']:>3} extraction(s)  [{kind:9}]  {v['path'].name[:64]}")
            # A file matched under a different name is worth seeing before paying
            # to extract it — it is the one case where the planner could be
            # pointing at the wrong book.
            if v["path"].name != Path(v["recorded"]).name:
                print(f"       ^ matched by title; extraction recorded "
                      f"\"{Path(v['recorded']).name[:56]}\"")
    if blocked:
        print("\nBLOCKED — source PDF not on this machine:")
        for v in sorted(blocked.values(), key=lambda x: -x["count"]):
            print(f"  {v['count']:>3} extraction(s)  {Path(v['recorded']).name[:64]}")
        print("  These stay as they are until the file is put back under "
              "mystery_database/new_sources/ (any subdirectory).")

    if args.check_sources:
        return check_sources(runnable)

    if args.find_missing:
        return report_missing(blocked)

    print(f"\nmodel: {args.model}")
    print(f"will upgrade {can} of {total} extractions   estimated ${can * per:.2f} "
          f"(~${per:.3f}/source)")
    if not args.go:
        print("\nPlan only — nothing spent. Re-run with --go to execute.")
        return 0
    if not runnable:
        print("\nNothing to do: no source PDFs found.")
        return 1

    print("\nRunning. Safe to interrupt — --upgrade resumes without re-paying.\n")
    failures = 0
    aborted = False
    queue = sorted(runnable.values(), key=lambda x: -x["count"])
    for done, v in enumerate(queue):
        cmd = [sys.executable, str(ROOT / "scripts" / "extract_from_pdfs.py"),
               str(v["path"]), "--protocol", PROTOCOL, "--model", args.model, "--upgrade"]
        if v["anthology"]:
            cmd.append("--anthology")
        else:
            # A novel's default 6,000-char sample is ~1.7% of the book. P2 asks
            # about structure that only shows across the whole thing, so give it
            # more to read; input tokens are the cheap half of the call.
            cmd += ["--max-text-chars", str(args.novel_chars)]
        print("=" * 78)
        print(" ".join(cmd[1:]))
        print("=" * 78, flush=True)
        rc = subprocess.call(cmd, cwd=str(ROOT))
        if rc == EXIT_FATAL:
            # Not this source's fault — the account or the credentials are the
            # problem, so every remaining source fails identically. Carrying on
            # would re-open and re-parse each remaining PDF just to reprint the
            # same error, which is what this run did before the check existed.
            aborted = True
            skipped = len(queue) - done - 1
            print("\n  !! STOPPING — that failure is not specific to this source.")
            if skipped:
                print(f"  {skipped} source(s) left untouched.")
            break
        if rc != 0:
            failures += 1
            print(f"  !! exited {rc} — continuing with the next source")

    if aborted:
        print("\nStopped early. Nothing was written for the source that failed, so "
              "re-run this\nexact command once the cause is fixed — --upgrade resumes "
              "and re-pays for nothing.")
        return EXIT_FATAL

    print("\nDone." + (f" {failures} source(s) exited non-zero." if failures else ""))
    print("Next: python3 scripts/test_registry_staleness.py   "
          "(the registry rebuilds itself; this proves it noticed)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
