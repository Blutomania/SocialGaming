#!/usr/bin/env python3
"""Check the decision record for the failure modes that made CLAUDE.md unreadable.

Session 38 split CLAUDE.md into what is true now (CLAUDE.md) and why it is like
that (docs/DECISIONS.md). Three things can silently undo that split, and each
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
RECORD = ROOT / "docs" / "DECISIONS.md"

# Where item numbers are cited. SESSIONS.md is excluded on purpose, for the same
# reason check_doc_claims.py excludes it: it is a historical log, and its claims
# were true when written.
CITING = [ROOT / "CLAUDE.md"] + sorted((ROOT / "docs").glob("*.md"))

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


def check_numbering(items, fails):
    """Complete run of 1..N, no gaps. Duplicates are impossible in a dict, so the
    raw headings are counted separately by the caller."""
    if not items:
        fails.append(f"{RECORD.name}: no items found at all")
        return
    expected = set(range(1, max(items) + 1))
    for missing in sorted(expected - set(items)):
        fails.append(f"{RECORD.name}: item {missing} is referenced by the "
                     f"sequence but has no entry")


def check_duplicates(text, fails):
    seen = {}
    for m in re.finditer(r"^(\d+)\.\s+\*\*", text, re.M):
        num = int(m.group(1))
        line = text[:m.start()].count("\n") + 1
        if num in seen:
            fails.append(f"{RECORD.name}:{line}: item {num} is declared twice "
                         f"(first at line {seen[num]}) -- numbers are the only "
                         f"stable handle citations have")
        else:
            seen[num] = line


def check_open_but_closed(items, fails):
    """An item labelled open that another item says is finished."""
    for num, (label, _) in items.items():
        if not any(lbl in label.upper() for lbl in OPEN_LABELS):
            continue
        for other, (_, body) in items.items():
            if other == num:
                continue
            # "...deletes ... item 21's deadlock" / "supersedes item 20"
            near = re.search(
                rf"{CLOSED}\w*\b[^.]{{0,80}}\bitem {num}\b"
                rf"|\bitem {num}\b[^.]{{0,80}}\b{CLOSED}\w*",
                body, re.I)
            if near:
                fails.append(
                    f"{RECORD.name}: item {num} is labelled [{label}] but item "
                    f"{other} says it is finished -- {near.group(0).strip()[:70]}")
                break


# Mind Your Friends shares this repo and has its own numbered items, running past
# 50. A reference that names MYF is talking about MYF's list, not this one, and is
# correct as written -- docs/WIRING.md legitimately cites "MYF's CLAUDE.md item
# 31/32". Only unqualified references are this record's to resolve.
OTHER_PROJECT = re.compile(r"MYF|mind[- ]your[- ]friends", re.I)


def check_references(items, fails):
    known = set(items)
    # RECORD is scanned too: an entry citing a sibling item that does not exist
    # is as dead an end as one in CLAUDE.md. Entry headings read "21. **", not
    # "item 21", so they cannot match the pattern below.
    for path in dict.fromkeys(CITING + [RECORD]):  # CITING's glob already holds RECORD
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"\bitem (\d+)\b", text):
            num = int(m.group(1))
            if num in known:
                continue
            if OTHER_PROJECT.search(text[max(0, m.start() - 120):m.start()]):
                continue
            line = text[:m.start()].count("\n") + 1
            rel = path.relative_to(ROOT)
            fails.append(f"{rel}:{line}: cites item {num}, which has no "
                         f"entry in {RECORD.name} and is not marked as MYF's")


def main():
    if not RECORD.exists():
        print(f"FAIL: {RECORD} does not exist")
        return 1

    text = RECORD.read_text(encoding="utf-8")
    # The index table at the top repeats every number; only the entry headings
    # (which start a line with "N. **") are parsed, so the table cannot confuse it.
    items = parse_items(text)

    fails = []
    check_numbering(items, fails)
    check_duplicates(text, fails)
    check_open_but_closed(items, fails)
    check_references(items, fails)

    print(f"Checked {len(items)} items in {RECORD.relative_to(ROOT)} "
          f"and references from {len(CITING)} file(s).\n")
    if fails:
        print(f"FAILURES ({len(fails)}):")
        for f in fails:
            print(f"  ✗ {f}")
        return 1
    print("No failures: items run 1..%d with no gaps or duplicates, no item is "
          "labelled open while another says it is finished, and every cited "
          "item number resolves." % max(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
