#!/usr/bin/env python3
"""Is the story connected? Checks the narrative the way check_solvability checks the arithmetic.

The coherence engine has 26 rules and almost all of them ask "is this field
present?" or "are there enough of this kind?". Two do referential integrity, and
both check structured fields -- solution.culprit against characters[], and
key_evidence IDs against evidence[]. NOTHING checks the prose, which is where
the story actually is.

That gap is not theoretical. `daggers_in_the_forum` scores passed=True,
blocking=0, warnings=0 -- a clean sweep -- and its deduction turns on Apolonios,
Demetrios and Senator Manilius, none of whom appear in its own character list.
A player cannot meet, question or accuse any of them. The mystery is provably
structured and narratively broken, and every existing check passes it.

Three things are checked here, in ascending strictness:

  CAST      A person named in the deduction chain who is not in characters[].
            Works on every mystery ever generated. This is the daggers defect.

  LINKS     Session 38 reordered generation to write the solution FIRST and made
            each clue declare what it serves -- `supports` naming chain steps,
            `exonerates` and `implicates` naming suspects. Where those fields
            exist, coherence becomes graph reachability and is checked exactly:
            every link resolves, every step is supported, elimination leaves
            exactly the culprit. Mysteries without the fields predate the change
            and are reported as legacy, not failed.

  ORPHAN    A name that appears ONLY inside the solution -- nowhere in the cast,
            the evidence, the areas or the leads. The player cannot encounter it
            by any route.

  NARROWS   Item 27's glove. An evidence item may carry `narrows` -- the suspects
            still possible given a physical fact ("a bloody man's glove"). It is
            hidden bookkeeping; the prose states the fact and the player draws
            the line. Checked here: a narrowing that excludes the culprit (the
            mystery contradicting its own solution and punishing correct
            reasoning -- M3 Clue Fairness), a narrowing naming one suspect (the
            answer printed on a finding), a narrowing naming somebody who is not
            a suspect, prose that gives the inference away instead of stating
            the fact, and narrowing that has become load-bearing so a withheld
            glove could make the case unprovable.

  REVEALS   APF deals findings rather than letting players gather them, and only
            evidence[] carries elimination data. A witness statement and a lead
            result reach it through a `reveals` pointer naming the evidence they
            surface (see deal.py). Checked here: a pointer resolving to no
            evidence item, a witness or lead carrying no pointer at all, and an
            exoneration reachable ONLY as a crime-scene clue -- which would make
            witness and lead findings decorative, since a clue is always
            available anyway.

ON FALSE POSITIVES, HONESTLY. Extracting people from prose is a heuristic. A
mystery may legitimately name someone who is not a character -- Pompey in a
Roman setting, a courier nobody questions. NOT_PEOPLE below is a curated
stoplist and it will need adding to. Treat CAST findings as a list to triage,
not a verdict, and prefer fixing a real one over growing the stoplist.

Exit is non-zero only for mysteries generated under the CURRENT schema, so the
legacy corpus does not hold the suite red. See SCHEMA_EPOCH.

Zero API cost.
"""

import argparse
import datetime
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATED = ROOT / "mystery_database" / "generated"

# Mysteries older than this predate the current rules and are reported but never
# failed -- the same reasoning check_solvability.py applies to the suspect count,
# which looked like generation drift and was corpus age.
#
# Moved 2026-08-21 -> 2026-09-01 in Session 39. The earlier date marked the
# solution-first reorder; this one marks Clue's two structural rules (an item
# clears at most one suspect; every suspect is clearable two independent ways),
# which the owner's "it has to be a race to proof" decision requires.
#
# An intra-day epoch was tried first, to exempt one mystery generated hours
# before the rules landed. That was the wrong instrument: mystery_database/
# generated/ is SERVED to players, so a mystery the deal refuses cannot sit
# there whatever the checker says about it. Both Session 39 mysteries moved to
# mystery_database/rejected/ instead, and the epoch went back to a plain date.
SCHEMA_EPOCH = datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc).timestamp()

# Mid-sentence capitalised words. Sentence-initial ones are skipped because
# how_to_deduce is written as "Step 1 - Establish ...", and Establish, Confirm
# and Eliminate are not suspects.
NAME = re.compile(
    r'(?<=[a-z,] )((?:Dr\.|Mr\.|Mrs\.|Ms\.|Sister|Brother|Captain|Lord|Lady)\s?[A-Z][a-z]{2,}'
    r'|[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)')

# Capitalised mid-sentence and not a person. Curated by hand; add to it only
# when a finding is genuinely not a person.
NOT_PEOPLE = re.compile(
    r'Module|Chamber|Room|Log|Drive|Bay|Consortium|Energy|Street|Berlin|City|Company|Corp|'
    r'Hall|Lane|Station|Base|Club|Cage|Forum|Sector|Area|Mirrors|Stood|Camera|Booth|Tier|'
    r'Strategy|Express|Institute|Polar|Senate|Portico|Prohibition|Harlem|Ottoman|Venetian|'
    r'Janissary|Western|Stasi|Star|Cold Storage|Document|Communications|Tome|Village|'
    r'Fresnel|Lantern|Lamp|Foundation|Pelican|Basin|Array|Totality|Corona')


def words(text):
    return {w.strip(".,'s") for w in re.split(r"\s+", text or "") if len(w.strip(".,'s")) > 2}


def deduction_text(solution):
    chain = solution.get("chain") or []
    steps = " ".join(str(s.get("claim", "")) for s in chain if isinstance(s, dict))
    return f"{solution.get('how_to_deduce', '')} {steps}"


def audit(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    solution = data.get("solution") or {}
    characters = [c for c in (data.get("characters") or []) if isinstance(c, dict)]
    suspects = [c.get("name", "") for c in characters if c.get("role") == "suspect"]
    culprit = solution.get("culprit") or ""

    cast_words = set()
    for c in characters:
        cast_words |= words(c.get("name", ""))

    # Everything the player can encounter, i.e. the mystery minus its solution.
    outside = json.dumps({k: v for k, v in data.items()
                          if k not in ("solution", "_provenance", "_coherence", "_meta")})

    report = {"file": path.name, "legacy": None, "cast": [], "orphans": [],
              "links": [], "reveals": []}

    try:
        stamp = int(path.stem.rsplit("_", 1)[1])
        report["legacy"] = stamp < SCHEMA_EPOCH
    except (IndexError, ValueError):
        report["legacy"] = True

    # --- CAST ---
    for cand in sorted({m.strip() for m in NAME.findall(deduction_text(solution))}):
        if NOT_PEOPLE.search(cand):
            continue
        if words(cand) & cast_words:
            continue
        report["cast"].append(cand)

    # --- ORPHAN ---
    prose = " ".join(str(solution.get(k, "")) for k in ("method", "motive", "how_to_deduce"))
    for cand in sorted({m.strip() for m in NAME.findall(prose)}):
        if NOT_PEOPLE.search(cand):
            continue
        if any(w in outside for w in words(cand)):
            continue
        report["orphans"].append(cand)

    # Built before LINKS because the two-routes check counts dealable findings,
    # and a witness or lead pointing at an evidence item is one of them.
    witnesses = [c for c in characters if (c.get("role") or "").lower() == "witness"]
    leads = [l for l in (data.get("leads") or []) if isinstance(l, dict)]
    areas = [a for a in (data.get("investigation_areas") or []) if isinstance(a, dict)]
    pointer_sources = (
        [(f"witness {c.get('name', '?')}", c) for c in witnesses]
        + [(f"lead {l.get('id', '?')}", l) for l in leads]
        + [(f"area {a.get('id', '?')}", a) for a in areas]
    )

    # --- LINKS (only where the schema provides them) ---
    chain = solution.get("chain") or []
    evidence = [e for e in (data.get("evidence") or []) if isinstance(e, dict)]
    has_links = bool(chain) or any("supports" in e for e in evidence)
    report["has_links"] = has_links
    if has_links:
        step_ids = {s.get("id") for s in chain if isinstance(s, dict)}
        supported = set()
        exonerated = set()
        implicated = set()
        for e in evidence:
            for sid in e.get("supports") or []:
                if sid not in step_ids:
                    report["links"].append(f"{e.get('id')} supports {sid}, which is not a chain step")
                supported.add(sid)
            if e.get("relevance") == "red_herring" and (e.get("supports") or []):
                report["links"].append(f"{e.get('id')} is a red herring but supports a chain step")
            exo_here = [n for n in (e.get("exonerates") or []) if str(n).strip()]
            if len(exo_here) > 1:
                report["links"].append(
                    f"{e.get('id')} clears {len(exo_here)} suspects at once {exo_here}; "
                    f"a finding must clear at most one, or it solves the case alone")
            exonerated |= set(e.get("exonerates") or [])
            implicated |= set(e.get("implicates") or [])

        for sid in sorted(step_ids - supported):
            report["links"].append(f"chain step {sid} is supported by no evidence")
        if culprit and any(w in exonerated for w in [culprit] + list(words(culprit))):
            report["links"].append(f"the culprit ({culprit}) is exonerated by the evidence")
        if culprit and not implicated:
            report["links"].append("no evidence implicates anyone; the culprit is reached only by elimination")
        # Two independent routes: a suspect clearable one way only becomes
        # unclearable the moment that finding is withheld (Session 39).
        #
        # COUNTED OVER DEALABLE FINDINGS, NOT EVIDENCE ITEMS. An earlier version
        # counted entries in evidence[] and was wrong: a witness whose `reveals`
        # names E1 is a SEPARATE finding, dealt to a different player and
        # hoarded independently, so it is a genuine second route to the same
        # exoneration. One evidence item plus one witness pointing at it
        # satisfies this; two evidence items nobody reveals does not, because
        # the second is only reachable by drawing the clue.
        from collections import Counter
        routes = Counter()
        for e in evidence:
            eid = e.get("id")
            names = [str(n).strip() for n in (e.get("exonerates") or []) if str(n).strip()]
            if not names:
                continue
            for n in names:
                routes[n] += 1                      # the clue itself
                for _, obj in pointer_sources:
                    if eid in (obj.get("reveals") or []):
                        routes[n] += 1              # each witness/lead/area too
        for who in sorted(x for x in suspects if x != culprit):
            if routes.get(who, 0) < 2:
                report["links"].append(
                    f"{who} is cleared by only {routes.get(who, 0)} finding(s); needs two "
                    f"independent routes or hoarding can make the case unprovable")

        # --- NARROWS (item 27) ---
        narrowing = [e for e in evidence
                     if [str(n).strip() for n in (e.get("narrows") or []) if str(n).strip()]]
        for e in narrowing:
            named = [str(n).strip() for n in (e.get("narrows") or []) if str(n).strip()]
            if len(named) < 2:
                report["links"].append(
                    f"{e.get('id')} narrows to a single suspect {named}; that is the whole "
                    f"answer in one finding, and whoever is dealt it wins without sharing")
            elif suspects and len(named) >= len(suspects):
                report["links"].append(
                    f"{e.get('id')} narrows to all {len(named)} suspects, so it rules nobody "
                    f"out; a narrowing must exclude at least one person to be worth reading")
            stranger = [n for n in named if n not in suspects]
            if stranger:
                report["links"].append(f"{e.get('id')} narrows to {stranger}, who are not suspects")
            if culprit and culprit not in named:
                report["links"].append(
                    f"{e.get('id')} narrows to {named}, excluding the culprit ({culprit}) -- "
                    f"the mystery contradicts its own solution and punishes correct reasoning")
            # The prose must state the FACT, never the inference. Naming a
            # suspect in a narrowing clue's own description hands the player the
            # conclusion they were supposed to reach.
            blurb = f"{e.get('name', '')} {e.get('description', '')}"
            spoiled = [n for n in named if n and n in blurb]
            if spoiled:
                report["links"].append(
                    f"{e.get('id')} is a narrowing clue whose own text names {spoiled}; it must "
                    f"state the fact and let the player draw the line")

        # Narrowing must never be load-bearing: elimination alone has to reach
        # the culprit, or withholding one glove makes the case unprovable.
        if narrowing:
            standing_no_glove = [s for s in suspects if s not in exonerated]
            if standing_no_glove != [culprit]:
                report["links"].append(
                    f"narrowing is load-bearing: elimination alone leaves {standing_no_glove}, "
                    f"so withholding a narrowing finding could make the case unprovable")

        remaining = [s for s in suspects if s not in exonerated]
        if len(remaining) != 1:
            report["links"].append(
                f"eliminating the exonerated leaves {len(remaining)} suspect(s), not 1: {remaining}")

    # --- REVEALS (only where the schema provides them) ---
    has_reveals = any("reveals" in obj for _, obj in pointer_sources)
    report["has_reveals"] = has_reveals
    if has_reveals:
        ev_ids = {e.get("id") for e in evidence if e.get("id")}
        reached = set()
        for label, obj in pointer_sources:
            pointers = obj.get("reveals") or []
            if not pointers:
                report["reveals"].append(f"{label} reveals nothing; it cannot be reasoned from")
            for eid in pointers:
                if eid not in ev_ids:
                    report["reveals"].append(f"{label} reveals '{eid}', which is not in evidence[]")
                else:
                    reached.add(eid)

        # An exoneration reachable only as a clue makes the other two kinds
        # decorative -- the inertness this pointer exists to fix.
        for e in evidence:
            if (e.get("exonerates") or []) and e.get("id") not in reached:
                report["reveals"].append(
                    f"{e.get('id')} exonerates {list(e.get('exonerates'))} but no witness, "
                    f"lead or area reveals it")
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--strict", action="store_true",
                    help="fail on legacy mysteries too, not only current-schema ones")
    args = ap.parse_args()

    files = [Path(f) for f in sorted(glob.glob(str(GENERATED / "*.json")))
             if "batch_summary" not in Path(f).name]
    if not files:
        print(f"No generated mysteries in {GENERATED}.")
        return 0

    reports = [audit(f) for f in files]
    fail = 0

    for r in reports:
        problems = r["cast"] or r["orphans"] or r["links"] or r["reveals"]
        if not problems:
            continue
        tag = "legacy" if r["legacy"] else "CURRENT"
        print(f"\n  [{tag}] {r['file']}")
        for name in r["cast"]:
            print(f"     CAST    reasons about '{name}', who is not in characters[]")
        for name in r["orphans"]:
            print(f"     ORPHAN  '{name}' appears only inside the solution")
        for msg in r["links"]:
            print(f"     LINKS   {msg}")
        for msg in r["reveals"]:
            print(f"     REVEALS {msg}")
        if not r["legacy"] or args.strict:
            fail += 1

    legacy = sum(1 for r in reports if r["legacy"])
    linked = sum(1 for r in reports if r.get("has_links"))
    pointed = sum(1 for r in reports if r.get("has_reveals"))
    cast_hits = sum(1 for r in reports if r["cast"])

    print(f"\n{'-' * 78}")
    print(f"  {len(reports)} mysteries: {legacy} predate the current schema, "
          f"{linked} declare chain links, {pointed} declare reveals pointers.")
    print(f"  {cast_hits} reason about a person absent from characters[].")
    if not args.strict and legacy:
        print(f"  Legacy mysteries are reported, not failed. Use --strict to fail on them too.")
    print("  CAST findings are a triage list, not a verdict — see this file's header on "
          "false positives.")

    if fail:
        print(f"\n=== {fail} CURRENT-SCHEMA mystery(s) failed ===")
        return 1
    print("\n=== no current-schema failures ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
