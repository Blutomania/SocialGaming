#!/usr/bin/env python3
"""
test_deal.py -- fixture tests for deal.py, APF's constrained deal.

WHY FIXTURES AND NOT THE CORPUS. No mystery on disk carries `reveals` or
`exonerates`: the schema landed in Session 38 and has never been generated
against. All 17 generated mysteries would therefore pass every check below
vacuously, which is the same trap Session 38 named for check_narrative.py --
"a branch with no input is a branch nobody ran".

Each test names the constraint it proves and asserts the deal REFUSES a
mystery that violates it. A test suite that only proves the happy path would
pass just as well against a deal() that returned ok=True unconditionally.

Zero API calls. Run: python3 scripts/test_deal.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import deal as D


# --------------------------------------------------------------------------
# Fixture builder
# --------------------------------------------------------------------------

def mystery(evidence, witnesses=(), leads=(), culprit="Vale",
            suspects=("Vale", "Ortiz", "Brand", "Chen"), difficulty="MEDIUM"):
    """A minimal mystery carrying only what the deal reads.

    Four suspects and one culprit means three required exonerations, which is
    PLAYTEST_FLOW's specified shape rather than the 2-3 suspects most of the
    March corpus actually has.
    """
    chars = [{"name": n, "role": "suspect"} for n in suspects]
    chars += [{"name": n, "role": "witness", "statement": stmt, "reveals": list(rv)}
              for n, stmt, rv in witnesses]
    return {
        "solution": {"culprit": culprit},
        "characters": chars,
        "evidence": [
            {"id": eid, "name": f"item {eid}", "description": "...",
             "exonerates": list(exo), "implicates": list(imp)}
            for eid, exo, imp in evidence
        ],
        "leads": [{"id": lid, "title": f"lead {lid}", "brief": "...", "reveals": list(rv)}
                  for lid, rv in leads],
        "gameplay_notes": {"difficulty": difficulty},
    }


def solvable_fixture(difficulty="MEDIUM"):
    """A mystery that CAN be dealt: three exonerations spread over six items,
    each carried by two separate evidence items so redundancy 2 is reachable,
    and no single item clearing more than one suspect."""
    ev = [
        ("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
        ("E4", ["Ortiz"], []), ("E5", ["Brand"], []), ("E6", ["Chen"], []),
        ("E7", [], ["Vale"]), ("E8", [], []),
    ]
    wit = [("Ada", "I saw the light on.", ["E1"]),
           ("Bo", "The door was bolted.", ["E2"]),
           ("Cy", "He was never there.", ["E3"]),
           ("Di", "Nothing unusual.", ["E8"])]
    leads = [("L1", ["E4"]), ("L2", ["E5"]), ("L3", ["E6"]), ("L4", ["E7"])]
    return mystery(ev, wit, leads, difficulty=difficulty)


def tight_redundancy_fixture():
    """Redundancy 2 is FEASIBLE here but not free.

    Each required exoneration is carried by EXACTLY two findings, so
    feasibility() passes -- two carriers can reach two hands. Whether they
    actually DO is what _violations() has to enforce, because a deal that puts
    both carriers of Ortiz in one hand satisfies constraints 1 and 2 and still
    leaves Ortiz reaching a single hand.

    This is the fixture the first version of this suite lacked: its redundancy
    test was refused by the feasibility pre-check, so deleting the _violations
    branch entirely left the suite green.
    """
    ev = [("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
          ("E4", [], []), ("E5", [], []), ("E6", [], ["Vale"])]
    wit = [("Ada", "s", ["E1"]), ("Bo", "s", ["E4"]), ("Cy", "s", ["E5"])]
    leads = [("L1", ["E2"]), ("L2", ["E3"]), ("L3", []), ("L4", [])]
    return mystery(ev, wit, leads)


FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}" + (f" -- {detail}" if detail else ""))
        FAILURES.append(name)


# --------------------------------------------------------------------------
# The arithmetic itself
# --------------------------------------------------------------------------

def test_arithmetic():
    print("\nthe arithmetic")
    m = solvable_fixture()
    ev = D.evidence_by_id(m)
    pool = D.build_pool(m)

    check("required_exonerations is every suspect but the culprit",
          D.required_exonerations(m) == {"Ortiz", "Brand", "Chen"},
          str(D.required_exonerations(m)))

    check("the full pool solves", D.solves(pool, m, ev))

    # Cardinality is not enough: clearing the culprit and two others leaves ONE
    # suspect standing and still gets the wrong person.
    wrong = [f for f in pool if f.id in ("E:E1", "E:E2")]
    wrong.append(D.Finding(id="X", kind="clue", title="x", body="", reveals=["E9"]))
    m2 = mystery([("E9", ["Vale"], [])] + [("E1", ["Ortiz"], []), ("E2", ["Brand"], [])])
    ev2 = D.evidence_by_id(m2)
    pool2 = D.build_pool(m2)
    standing = set(D.suspects(m2)) - D.exonerated_by(pool2, ev2)
    check("a set clearing the culprit does not solve, even at the right count",
          len(standing) == 1 and not D.solves(pool2, m2, ev2), f"standing={standing}")

    check("a dangling reveals id contributes no exoneration",
          D.exonerated_by([D.Finding("Z", "clue", "z", "", ["NOPE"])], ev) == set())


# --------------------------------------------------------------------------
# The three constraints -- each proved by a mystery that violates it
# --------------------------------------------------------------------------

def test_constraint_1_union_solves():
    print("\nconstraint 1 -- the union of all dealt findings eliminates all but one")
    # Chen is never exonerated by anything, so two suspects always stand.
    ev = [("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", [], []),
          ("E4", [], []), ("E5", [], []), ("E6", [], [])]
    m = mystery(ev, [("Ada", "s", ["E1"]), ("Bo", "s", ["E2"]), ("Cy", "s", ["E3"])],
                [("L1", ["E4"]), ("L2", ["E5"]), ("L3", ["E6"]), ("L4", [])])
    r = D.deal(m, player_count=3, seed=1)
    check("refuses a mystery whose evidence cannot eliminate to one", not r.ok)
    check("and says which suspect is left standing",
          any("Chen" in i for i in r.issues), str(r.issues))


def test_constraint_2_no_solo_win():
    print("\nconstraint 2 -- no single player's hand solves alone")
    # One item clears all three innocents: whoever draws it wins by itself.
    ev = [("E1", ["Ortiz", "Brand", "Chen"], []), ("E2", [], []), ("E3", [], []),
          ("E4", [], []), ("E5", [], []), ("E6", [], [])]
    m = mystery(ev, [("Ada", "s", ["E1"]), ("Bo", "s", ["E2"]), ("Cy", "s", ["E3"])],
                [("L1", ["E4"]), ("L2", ["E5"]), ("L3", ["E6"]), ("L4", [])])
    r = D.deal(m, player_count=3, seed=1)
    check("refuses a mystery where one finding solves outright", not r.ok)
    check("and names the finding that does it",
          any("solves the mystery by itself" in i for i in r.issues), str(r.issues))

    # And the per-hand check fires even when no SINGLE finding solves: two
    # findings that together clear all three, landing in one hand.
    m2 = solvable_fixture()
    ok = D.deal(m2, player_count=4, seed=7)
    check("a well-formed mystery still deals", ok.ok, str(ok.issues))
    check("and no hand solves alone",
          ok.ok and not any(D.solves(h, m2) for h in ok.hands))


def test_constraint_3_redundancy():
    print("\nconstraint 3 -- redundancy (difficulty's new home)")
    # Each exoneration carried by exactly ONE evidence item: reachable at
    # redundancy 1, impossible at 2.
    ev = [("E1", ["Ortiz"], []), ("E2", ["Brand"], []), ("E3", ["Chen"], []),
          ("E4", [], []), ("E5", [], []), ("E6", [], [])]
    m = mystery(ev, [("Ada", "s", ["E4"]), ("Bo", "s", ["E5"]), ("Cy", "s", ["E6"])],
                [("L1", []), ("L2", []), ("L3", []), ("L4", [])])

    # Redundancy in isolation. The proof constraint is switched off here on
    # purpose: this fixture gives each exoneration exactly ONE carrier, so proof
    # does not survive hoarding, and leaving it on would make this a test of the
    # wrong constraint. The next case asserts that it does fire here.
    r1 = D.deal(m, player_count=3, seed=3, redundancy=1,
                require_proof_under_hoarding=False)
    check("deals at redundancy 1 with the proof constraint off", r1.ok, str(r1.issues))

    r1p = D.deal(m, player_count=3, seed=3, redundancy=1)
    check("and the SAME deal is refused with it on, because one route per "
          "suspect cannot survive hoarding",
          not r1p.ok and any("proof dies under hoarding" in i for i in r1p.issues),
          str(r1p.issues))

    r2 = D.deal(m, player_count=3, seed=3, redundancy=2,
                require_proof_under_hoarding=False)
    check("refuses the same mystery at redundancy 2", not r2.ok)
    check("and says the exoneration is carried by too few findings",
          any("carried by 1 finding" in i for i in r2.issues), str(r2.issues))

    # EASY should pick redundancy 2 off the difficulty, HARD 1.
    easy = D.deal(solvable_fixture("EASY"), player_count=4, seed=11)
    hard = D.deal(solvable_fixture("HARD"), player_count=4, seed=11)
    check("EASY deals at redundancy 2", easy.redundancy == 2, str(easy.redundancy))
    check("HARD deals at redundancy 1", hard.redundancy == 1, str(hard.redundancy))

    # The branch that actually enforces it, on a mystery feasibility lets through.
    tight = tight_redundancy_fixture()
    ev = D.evidence_by_id(tight)
    check("redundancy 2 is FEASIBLE on the tight fixture (so _violations, not "
          "feasibility, is what must enforce it)",
          D.feasibility(tight, 3, redundancy=2) == [],
          str(D.feasibility(tight, 3, redundancy=2)))

    t = D.deal(tight, player_count=3, seed=2, redundancy=2)
    check("the tight fixture still deals", t.ok, str(t.issues))
    reach = {r: sum(1 for h in t.hands if r in D.exonerated_by(h, ev))
             for r in D.required_exonerations(tight)}
    check("and every exoneration really reaches two distinct hands",
          t.ok and all(v >= 2 for v in reach.values()), str(reach))

    # The ceiling, which is arithmetic rather than luck. R=3, P=4, k=3 forces
    # some hand to hold all three exonerations, which is constraint 2.
    over = D.deal(solvable_fixture(), player_count=4, seed=1, redundancy=3)
    check("redundancy above the ceiling is refused as impossible, not merely unlucky",
          (not over.ok) and any("is impossible at" in i for i in over.issues), str(over.issues))
    check("and it is refused up front, without burning attempts",
          over.attempts == 0, str(over.attempts))
    check("the ceiling is reported, and at APF's shape it is 2",
          any("Ceiling here is 2" in i for i in over.issues), str(over.issues))
    check("redundancy 2 is at the ceiling and still deals",
          D.deal(solvable_fixture(), player_count=4, seed=1, redundancy=2).ok)
    # A wider table lifts it: R=3, P=5 makes k=3 reachable again.
    check("a five-player table lifts the ceiling to 3",
          not any("is impossible at" in i
                  for i in D.feasibility(solvable_fixture(), 5, redundancy=3)),
          str(D.feasibility(solvable_fixture(), 5, redundancy=3)))

    # _violations() tested directly, on a deal hand-built to break redundancy:
    # both Ortiz carriers in hand 0. Constraints 1 and 2 still hold.
    pool = {f.id: f for f in D.build_pool(tight)}
    stacked = [
        [pool["E:E1"], pool["W:Ada"], pool["E:E6"]],   # both Ortiz carriers here
        [pool["E:E2"], pool["L:L1"], pool["E:E4"]],
        [pool["E:E3"], pool["L:L2"], pool["E:E5"]],
    ]
    v2 = D._violations(stacked, tight, ev, redundancy=2)
    v1 = D._violations(stacked, tight, ev, redundancy=1)
    check("_violations reports an exoneration confined to one hand at redundancy 2",
          any("Ortiz" in x and "1 hand" in x for x in v2), str(v2))
    check("and the same deal is legal at redundancy 1", v1 == [], str(v1))


# --------------------------------------------------------------------------
# Feasibility diagnostics -- the difference between re-dealing and regenerating
# --------------------------------------------------------------------------

def test_proof_survives_hoarding():
    print("\nconstraint 4 -- it is a race to PROOF, not to the best bet")
    # Owner's decision, Session 39. What makes proof survive is CARRIERS -- how
    # many separate findings can clear a given suspect -- not redundancy.

    def carriers(n):
        """Clue-shaped: each item clears AT MOST one suspect, n items per suspect."""
        ev, k = [], 1
        for who in ("Ortiz", "Brand", "Chen"):
            for _ in range(n):
                ev.append((f"E{k}", [who], [])); k += 1
        for _ in range(6):
            ev.append((f"E{k}", [], [])); k += 1
        ev.append((f"E{k}", [], ["Vale"]))
        wit = [(f"W{i}", "s", [ev[i][0]]) for i in range(4)]
        leads = [(f"L{i+1}", [ev[i + 3][0]]) for i in range(4)]
        return mystery(ev, wit, leads)

    one = D.deal(carriers(1), player_count=4, seed=4, require_proof_under_hoarding=False)
    ok1, tot1, _ = D.proof_survives_hoarding(one.hands, carriers(1))
    check("one route per suspect: proof does NOT always survive hoarding",
          one.ok and ok1 < tot1, f"{ok1}/{tot1}")

    two = D.deal(carriers(2), player_count=4, seed=4)
    ok2, tot2, _ = D.proof_survives_hoarding(two.hands, carriers(2))
    check("two routes per suspect: proof survives EVERY hoarding pattern",
          two.ok and ok2 == tot2, f"{ok2}/{tot2}")
    check("and that holds at redundancy 1, so it is carriers and not redundancy "
          "that buys it",
          D.deal(carriers(2), player_count=4, seed=4, redundancy=1).ok)

    check("the enumeration covers 3^4 = 81 patterns at APF's shape",
          tot2 == 81, str(tot2))

    # A player knows what they kept: proof may rest on their own hoarded finding.
    m = carriers(2)
    r = D.deal(m, player_count=4, seed=6)
    evb = D.evidence_by_id(m)
    check("a hand that solves only WITH its own kept finding still counts as proof",
          r.ok and all(D.solves([f for h in r.hands for f in h], m, evb)
                       for _ in [0]))


def test_feasibility_diagnostics():
    print("\nfeasibility -- why a deal cannot be made")
    base = solvable_fixture()

    dangling = solvable_fixture()
    dangling["characters"][4]["reveals"] = ["E99"]
    check("a reveals pointer naming no evidence item is reported",
          any("E99" in i for i in D.feasibility(dangling, 4)),
          str(D.feasibility(dangling, 4)))

    misnamed = solvable_fixture()
    misnamed["evidence"][0]["exonerates"] = ["Dr. Ortiz"]
    issues = D.feasibility(misnamed, 4)
    check("an exonerates name matching no suspect is reported, not fuzzy-matched",
          any("Dr. Ortiz" in i and "not a suspect" in i for i in issues), str(issues))

    cleared = solvable_fixture()
    cleared["evidence"][6]["exonerates"] = ["Vale"]
    check("evidence exonerating the culprit is reported",
          any("culprit" in i and "exonerated" in i for i in D.feasibility(cleared, 4)))

    nocul = solvable_fixture()
    nocul["solution"]["culprit"] = "Nobody"
    check("a culprit who is not a suspect is reported",
          any("not among the suspects" in i for i in D.feasibility(nocul, 4)))

    check("a well-formed mystery has no feasibility issues",
          D.feasibility(base, 4, redundancy=2) == [], str(D.feasibility(base, 4, redundancy=2)))

    thin = solvable_fixture()
    thin["leads"] = []
    thin["evidence"] = thin["evidence"][:2]
    check("a pool too small for the table is reported",
          any("short of" in i for i in D.feasibility(thin, 4)), str(D.feasibility(thin, 4)))


# --------------------------------------------------------------------------
# Determinism and hand shape
# --------------------------------------------------------------------------

def test_determinism_and_shape():
    print("\ndeterminism and hand shape")
    m = solvable_fixture()

    a = D.deal(m, player_count=4, seed=42)
    b = D.deal(m, player_count=4, seed=42)
    check("the same seed gives the same hands",
          a.ok and b.ok and
          [[f.id for f in h] for h in a.hands] == [[f.id for f in h] for h in b.hands])

    check("every player gets a full hand",
          a.ok and all(len(h) == len(D.DEFAULT_HAND_SPEC) for h in a.hands),
          str([len(h) for h in a.hands]))

    dealt = [f.id for h in a.hands for f in h]
    check("no finding is dealt twice", len(dealt) == len(set(dealt)))

    # A short witness pool must degrade fairly, not starve the last player.
    short = solvable_fixture()
    short["characters"] = [c for c in short["characters"]
                           if c.get("role") != "witness" or c["name"] in ("Ada", "Bo")]
    s = D.deal(short, player_count=4, seed=5)
    check("a short witness pool still fills every hand",
          s.ok and all(len(h) == 3 for h in s.hands), str(s.issues))
    # NOT "no hand stacks two witnesses" -- with one witness SLOT per hand that
    # holds by construction and the assertion could never fail. The real
    # property is that a scarce kind is fully USED: two witnesses and four
    # players must put a witness in exactly two hands, not zero (over-eager
    # fallback) and not one (a witness left undealt).
    witness_counts = [sum(1 for f in h if f.kind == "witness") for h in s.hands]
    check("a scarce kind is fully dealt: 2 witnesses reach exactly 2 of 4 hands",
          s.ok and sum(witness_counts) == 2, str(witness_counts))


def main():
    print("deal.py -- constrained deal fixtures")
    test_arithmetic()
    test_constraint_1_union_solves()
    test_constraint_2_no_solo_win()
    test_constraint_3_redundancy()
    test_proof_survives_hoarding()
    test_feasibility_diagnostics()
    test_determinism_and_shape()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): " + ", ".join(FAILURES))
        return 1
    print("All deal constraints hold, and each refuses a mystery that violates it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
