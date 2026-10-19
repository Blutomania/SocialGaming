#!/usr/bin/env python3
"""Check the decision record for the failure modes that made CLAUDE.md unreadable.

Session 38 split CLAUDE.md into what is true now (CLAUDE.md) and why it is like
that (docs/DECISIONS.md). Session 50 extended the check to Mind Your Friends'
own list (mind-your-friends/docs/DECISIONS.md) — its item 52 had been cited for
two months without an entry, the dangling-reference shape below. Three things can silently undo that split, and each
has already happened at least once:

  1. An item marked [OPEN] that another item says was closed. Item 21 sat
     labelled "[OPEN] ... a stage-1 playtest-killer" while item 23, on the same
     page, said APF "deletes ... item 21's deadlock outright". A reader arriving
     at 21 first would go and fix a bug with no mechanic left. This is exactly
     the shape that made INVESTIGATION_DESIGN section 6 unreadable too, so it is
     worth catching mechanically rather than by review.

  2. A dangling item reference. Item numbers are cited from CLAUDE.md, six files
     under docs/, and three source files -- "item 17" alone appears fifteen
     times. A reference to an item that does not exist is a dead end for whoever
     follows it.

  3. A renumbered or duplicated item. Numbers are the only stable handle those
     citations have, so a duplicate makes a citation ambiguous.

Exit: 0 = clean, 1 = failures found. Zero API cost.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MYF = ROOT / "mind-your-friends"

# Each game keeps its own numbered list, and both have (for example) an item 27,
# so each record is checked against its OWN citing files only, and a reference
# that names the other game is that game's business, not this record's.
#
# SESSIONS.md is excluded on purpose, for the same reason check_doc_claims.py
# excludes it: it is a historical log, and its claims were true when written.
# So is MYF's docs/archive/: the old record, kept word for word.
#
# CYM's instructions moved from the root CLAUDE.md to .claude/rules/cym.md in
# Session 50, so a path-scoped rule loads them only for CYM work. The rules
# directory is read too, or the move would silently drop CYM's file from this
# check — which is exactly what checking only "CLAUDE.md" would do.
#
# Source comments are read too, since Session 51, as MYF's always were. The
# first run found background_field.py citing "item 40" — MYF's item 40, with
# nothing saying so — which every earlier check had passed.
CYM_CITING = ([ROOT / "CLAUDE.md"] + sorted((ROOT / ".claude" / "rules").glob("*.md"))
              + sorted((ROOT / "docs").glob("*.md"))
              + sorted(p for pattern in ("*.py", "server/**/*.py", "server/**/*.html",
                                         "scripts/*.py", "godot/**/*.gd", "godot/**/*.tscn")
                       for p in ROOT.glob(pattern)
                       # This script names example item numbers in its own comments.
                       if p.resolve() != Path(__file__).resolve()))

# MYF's source comments cite items constantly ("see MYF CLAUDE.md item 47"),
# so code is read too — a dead reference in a comment is still a dead end.
MYF_CITING = sorted(
    [MYF / "CLAUDE.md"]
    + list(MYF.glob("*.md")) + list((MYF / "docs").glob("*.md"))
    + [MYF / "server.js"]
    + [p for pattern in ("lib/*.js", "components/*.jsx", "app/**/*.js", "scripts/*.js",
                         "scripts/*.mjs", "server_py/*.py", "godot/**/*.gd")
       for p in MYF.glob(pattern)]
)

# Mind Your Friends shares this repo and has its own numbered items, running past
# 50. A reference that names MYF is talking about MYF's list, not CYM's, and is
# correct as written -- docs/WIRING.md legitimately cites "MYF's CLAUDE.md item
# 31/32". The same holds the other way round.
GAMES = [
    {"name": "CYM", "record": ROOT / "docs" / "DECISIONS.md", "citing": CYM_CITING,
     "other": re.compile(r"MYF|mind[- ]your[- ]friends", re.I)},
    {"name": "MYF", "record": MYF / "docs" / "DECISIONS.md", "citing": MYF_CITING,
     "other": re.compile(r"\bCYM\b|choose your mystery|root `?CLAUDE|cym\.md", re.I)},
]

# Words that mean an item is finished, in the sentence that names it.
CLOSED = r"(?:delet|clos|supersed|replac|remov|kill)"

OPEN_LABELS = ("OPEN", "IN PROGRESS", "READY TO RUN", "ONGOING", "PARTLY BUILT",
               "PARTIALLY FIXED")


def parse_items(text):
    """Return {number: (label, body)} for every entry in the record."""
    items = {}
    starts = [(m.start(), int(m.group(1))) for m in
              re.finditer(r"^(\d+)\.\s+\*\*", text, re.M)]
    for i, (pos, num) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        body = text[pos:end]
        label = ""
        m = re.match(r"^\d+\.\s+\*\*\[([^\]]*)\]", body, re.S)
        if m:
            label = m.group(1).replace("\n", " ")
        items[num] = (label, body)
    return items


def check_numbering(items, fails, record):
    """Complete run of 1..N, no gaps. Duplicates are impossible in a dict, so the
    raw headings are counted separately by the caller."""
    if not items:
        fails.append(f"{record.name}: no items found at all")
        return
    expected = set(range(1, max(items) + 1))
    for missing in sorted(expected - set(items)):
        fails.append(f"{record.name}: item {missing} is referenced by the "
                     f"sequence but has no entry")


def check_duplicates(text, fails, record):
    seen = {}
    for m in re.finditer(r"^(\d+)\.\s+\*\*", text, re.M):
        num = int(m.group(1))
        line = text[:m.start()].count("\n") + 1
        if num in seen:
            fails.append(f"{record.name}:{line}: item {num} is declared twice "
                         f"(first at line {seen[num]}) -- numbers are the only "
                         f"stable handle citations have")
        else:
            seen[num] = line


def check_open_but_closed(items, fails, record):
    """An item labelled open that another item says is finished."""
    for num, (label, _) in items.items():
        if not any(lbl in label.upper() for lbl in OPEN_LABELS):
            continue
        for other, (_, body) in items.items():
            if other == num:
                continue
            # "...deletes ... item 21's deadlock" / "supersedes item 20"
            # "(?<!by )" is load-bearing and was added in Session 39 after a real
            # false positive. "item 21 ... superseded BY item 23" closes item 21
            # and says nothing about item 23 -- but the closing verb and the
            # number 23 are both present, so without this the successor gets
            # reported as finished the moment it is labelled anything open.
            # Direction is what the phrase "by item N" carries: N is the agent
            # there, not the patient.
            near = re.search(
                rf"{CLOSED}\w*\b[^.]{{0,80}}(?<!by )\bitem {num}\b"
                rf"|\bitem {num}\b[^.]{{0,80}}\b{CLOSED}\w*",
                body, re.I)
            if near:
                fails.append(
                    f"{record.name}: item {num} is labelled [{label}] but item "
                    f"{other} says it is finished -- {near.group(0).strip()[:70]}")
                break


def check_references(items, fails, game):
    record, other = game["record"], game["other"]
    known = set(items)
    # The record is scanned too: an entry citing a sibling item that does not
    # exist is as dead an end as one in CLAUDE.md. Entry headings read "21. **",
    # not "item 21", so they cannot match the pattern below.
    for path in dict.fromkeys(game["citing"] + [record]):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"\bitem (\d+)\b", text):
            num = int(m.group(1))
            if num in known:
                continue
            if other.search(text[max(0, m.start() - 120):m.start()]):
                continue
            line = text[:m.start()].count("\n") + 1
            rel = path.relative_to(ROOT)
            fails.append(f"{rel}:{line}: cites item {num}, which has no entry in "
                         f"{record.relative_to(ROOT)} and is not marked as the other game's")


def check_game(game):
    record = game["record"]
    print(f"--- {game['name']}: {record.relative_to(ROOT)} ---")
    if not record.exists():
        print(f"FAIL: {record} does not exist\n")
        return 1

    text = record.read_text(encoding="utf-8")
    # The index table at the top repeats every number; only the entry headings
    # (which start a line with "N. **") are parsed, so the table cannot confuse it.
    items = parse_items(text)

    fails = []
    check_numbering(items, fails, record)
    check_duplicates(text, fails, record)
    check_open_but_closed(items, fails, record)
    check_references(items, fails, game)

    print(f"Checked {len(items)} items and references from {len(game['citing'])} file(s).")
    if fails:
        print(f"FAILURES ({len(fails)}):")
        for f in fails:
            print(f"  ✗ {f}")
        print()
        return 1
    print("No failures: items run 1..%d with no gaps or duplicates, no item is "
          "labelled open while another says it is finished, and every cited "
          "item number resolves.\n" % max(items))
    return 0


def main():
    return 1 if sum(check_game(g) for g in GAMES) else 0


if __name__ == "__main__":
    sys.exit(main())
