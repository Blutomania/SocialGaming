#!/usr/bin/env python3
"""Do the docs' checkable claims still hold? Zero API cost, no Godot needed.

WHY THIS EXISTS. Session 35 found four places where a document said a thing was
built and the code disagreed: the result screen's node paths, the saved-mystery
dropdown's signals, `_slug`, and a `"Video Scene Will Play Here"` panel that
exists in no client file. Three were found by reading code for other reasons.
The fourth was found by grep -- and a first run of this checker immediately
found a FIFTH: the same video-panel claim, still live in docs/WIRING.md, an
hour after the identical sentence was corrected in CLAUDE.md. A human
re-reading does not catch that. A grep does.

WHAT IT CHECKS. Only claims a machine can settle:

  1. `path/to/file.py`      -- the file exists
  2. `path/to/file.py:123`  -- and has at least that many lines
  3. `"a literal string"`   -- appears somewhere in the repo

WHAT IT DELIBERATELY DOES NOT CHECK.

  * SESSIONS.md. It is a historical record: "the registry had been frozen since
    March 11" was true when written and must not be re-verified against today.
    CLAUDE.md and docs/ are different -- they describe the CURRENT state, which
    is exactly the thing that rots.
  * Prose claims ("the engine validates X"). Not machine-settleable, and a
    checker that guesses at those would cry wolf until nobody ran it.
  * Numbers. Part counts and source counts drift legitimately between a doc's
    measurement and today; scripts/test_registry_staleness.py covers the one
    number that must not drift silently.

THE ALLOWLIST IS THE ESCAPE HATCH, AND IT COSTS A SENTENCE. A doc may honestly
reference something that does not exist yet -- a file the tooling generates on
demand, an artifact of a designed-but-unbuilt feature. Those go in ALLOWED
below WITH A REASON, so "not built yet" stays a stated decision rather than an
untracked drift.
"""
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Docs that describe the CURRENT state. SESSIONS.md is excluded on purpose.
DOC_GLOBS = ["CLAUDE.md", "docs/*.md"]

# Referenced-but-absent, each with the reason it is legitimate.
ALLOWED = {
    "coherence.py":
        "historical: MYF's file, renamed to coherence_rules.py in Session 33. "
        "CLAUDE.md item 16 names the old file to explain the rename.",
    "mystery_database/new_sources/_MISSING_SOURCES.md":
        "generated on demand by upgrade_p1_to_p1p2.py --find-missing.",
    "mystery_database/craft_grounding_index.json":
        "craft_grounding.py's cache; written on first index build.",
    "mystery_database/accessory_catalog.json":
        "Phase 3e avatar system — designed, not built (CLAUDE.md item 4).",
    "SOMETHING_CRAFT_FINDINGS.md":
        "a fill-in-the-blank placeholder in SOURCING_METHODOLOGY.md's process, "
        "not a real filename.",
}

# Paths may resolve anywhere. Literals are claims about the PRODUCT, so they are
# searched in code only -- see _appears_in_code().
CODE_SUFFIXES = {".py", ".gd", ".tscn", ".html", ".js", ".jsx", ".mjs"}
SKIP_DIRS = {"__pycache__", ".git", "node_modules", "deprecated"}

# Quoted strings that are honestly quoted from another DOCUMENT rather than
# asserted to be in the product. Each needs the source named.
ALLOWED_LITERALS = {
    "Minimize actual lies; let circumstance do the misdirecting":
        "a craft finding quoted from SCREEN_CRAFT_FINDINGS.md, not a UI string.",
    "C(4)+F(2)+A(6)+...":
        "illustrative SOURCE(INDEX) notation, not a string in the product.",
}

PATH_RE = re.compile(r'`([A-Za-z0-9_./-]+\.(?:py|gd|tscn|html|json|md|js|jsx|mjs))(?::(\d+))?`')
LITERAL_RE = re.compile(r'`"([^"]{8,80})"`')


def _docs() -> list:
    out = []
    for pattern in DOC_GLOBS:
        out.extend(sorted(glob.glob(str(ROOT / pattern))))
    return out


def _appears_in_code(literal: str) -> bool:
    """Is this string actually in a code file?

    Searched in code ONLY, and never in this file. Both restrictions were earned
    the hard way -- every earlier version of this check passed clean on a claim
    already known to be false, for a different reason each time:

      1. searching everything, so the doc's own sentence was the evidence;
      2. searching all markdown, so CLAUDE.md and SESSIONS.md writing UP the
         correction became evidence the thing existed;
      3. searching code including this script, whose comment quoted the example.

    A doc discussing a UI string is not proof the UI has it. Any doc that
    legitimately quotes another document goes in ALLOWED_LITERALS by name.

    Done in Python rather than by shelling out to grep: grep's --include/--exclude
    did not filter as expected in this environment, and a search that silently
    matches more than it should is exactly the failure this script exists to
    prevent. The tree is a few megabytes; reading it is cheap and unambiguous.
    """
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in CODE_SUFFIXES:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            if literal in path.read_text(errors="replace"):
                return True
        except OSError:
            continue
    return False


def _mentions_deprecated(text: str, pos: int, window: int = 400) -> bool:
    """Does the surrounding prose already say this is retired?

    CLAUDE.md lists every file in deprecated/ by name, backticked, so that
    nobody opens deprecated/requirements.txt thinking it is the server's. That
    list is a legitimate reference to retired code; a section heading that
    presents app.py as the live UI is not. The difference is whether the prose
    says so, so that is what is checked.
    """
    # Looked for on BOTH sides: a list of retired filenames often names
    # deprecated/ only after the last of them ("...what now lives in
    # deprecated/"), which a backward-only window misses.
    return "deprecated" in text[max(0, pos - window):pos + window].lower()


def main() -> int:
    failures = []
    checked_paths = checked_literals = 0

    print("--- file and line references ---")
    for doc in _docs():
        rel_doc = os.path.relpath(doc, ROOT)
        for m in PATH_RE.finditer(Path(doc).read_text()):
            ref, line = m.group(1), m.group(2)
            if ref in ALLOWED:
                continue
            checked_paths += 1
            target = ROOT / ref
            if not target.exists():
                # A bare filename may legitimately live deeper in the tree.
                found = glob.glob(str(ROOT / "**" / os.path.basename(ref)),
                                  recursive=True)
                live = [f for f in found
                        if not any(part in SKIP_DIRS
                                   for part in Path(f).relative_to(ROOT).parts)]
                if live:
                    continue
                if found and not live:
                    # Resolves ONLY into deprecated/. This is the hole that let
                    # docs/WIRING.md document the retired Streamlit app.py and
                    # cli.py as the live cinematic-brief trigger for several
                    # sessions: the files do exist, so "no such file" never
                    # fired, and existing anywhere was treated as existing.
                    # Naming deprecated/ nearby is the legitimate case --
                    # CLAUDE.md lists those filenames precisely to say do not
                    # touch them.
                    if _mentions_deprecated(Path(doc).read_text(), m.start()):
                        continue
                    failures.append((
                        rel_doc, ref,
                        "resolves ONLY into deprecated/ -- it is retired code. "
                        "Reference it as deprecated/<name>, say 'deprecated' "
                        "nearby, or use italics if you are naming it as history"))
                    continue
                failures.append((rel_doc, ref, "no such file"))
            elif line and len(target.read_text(errors="replace").splitlines()) < int(line):
                failures.append((rel_doc, f"{ref}:{line}", "line number is past end of file"))
    print(f"  {checked_paths} checked")

    print("\n--- quoted literals the docs say are in the product ---")
    for doc in _docs():
        rel_doc = os.path.relpath(doc, ROOT)
        for m in LITERAL_RE.finditer(Path(doc).read_text()):
            literal = m.group(1)
            # An ellipsis INSIDE a literal marks an illustrative pattern
            # ("C(4)+F(2)+A(6)+..."), not a string to go and find. A TRAILING
            # one does not -- spinner and progress labels genuinely end that
            # way, and skipping those hid two real stale claims about UI text
            # that now exists only in deprecated/.
            body = literal.rstrip(". …")
            if "…" in body or "..." in body:
                continue
            if literal in ALLOWED_LITERALS:
                continue
            checked_literals += 1
            if not _appears_in_code(literal):
                failures.append((rel_doc, f'"{literal}"', "appears in no code file"))
    print(f"  {checked_literals} checked")

    print()
    if failures:
        print(f"=== {len(failures)} STALE CLAIM(S) ===\n")
        for doc, claim, why in failures:
            print(f"  {doc}")
            print(f"    {claim}")
            print(f"    -> {why}\n")
        print("Fix the doc, or add the reference to ALLOWED with the reason it is legitimate.")
        return 1

    print("=== ALL CLAIMS HOLD ===")
    print(f"({len(ALLOWED)} path(s) and {len(ALLOWED_LITERALS)} literal(s) allowlisted, with reasons.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
