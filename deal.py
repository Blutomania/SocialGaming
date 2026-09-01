"""
deal.py — APF's constrained deal (root CLAUDE.md item 23, build-order step 2).

Findings are DEALT, NOT GATHERED. This module takes a generated mystery and
hands each player a small set of findings, subject to constraints that make the
game winnable without making it a lottery. It is pure computation: no API call,
deterministic from a seed, and a failed deal is simply re-dealt at zero cost
(docs/PLAYTEST_FLOW.md, "The deal is a separate step from generation").

WHY A POINTER AND NOT DUPLICATED FIELDS. Only evidence[] carries elimination
data -- `exonerates` / `implicates`, added in Session 38. A witness statement
and a lead result carry none, so two of APF's three finding kinds were inert:
they could not participate in the set arithmetic all three deal constraints
are defined over. The fix is a `reveals` pointer on witnesses, leads and areas
naming the evidence they surface. Elimination data therefore lives in exactly
ONE place and a witness's exoneration cannot drift out of agreement with the
evidence item's -- a defect no structural check could have caught, which is
why the alternative (copying all three link fields onto every kind) was
rejected. See docs/INVESTIGATION_DESIGN.md §4.

THE ARITHMETIC. A finding set eliminates the suspects exonerated by the evidence
it reveals. The set SOLVES when exactly one suspect is left standing and that
suspect is the culprit. Everything below is that one predicate applied to
different subsets: all hands together, each hand alone, and each hand's
contribution to a single exoneration.

THE WORD IS "FINDING", NOT "CARD". docs/PLAYTEST_FLOW.md:139 draws the
distinction precisely -- "the data is already CARD-SHAPED: a FINDING has a
name, a description, a type, a relevance." A finding is the domain object; a
card is one way a client might draw it. MYF's vocabulary (GameCard.jsx,
CardHand.jsx) is about its UI, and borrowing it here would take the word from
the layer that should own it. server/main.py already agrees: witness_findings,
investigation_findings, lead_findings.

WHAT THIS DOES NOT DO. It does not judge whether a clue's prose actually
supports the link it declares. A model can emit reveals: ["E3"] on a statement
that says nothing about E3, and nothing structural can tell -- the same
limitation Session 38 recorded for `supports`. The pointer changes what drift
looks like, not whether drift is possible.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Set

# APF's hand: one witness statement, one crime-scene clue, one lead result
# (docs/PLAYTEST_FLOW.md step 4). "Ideally" is load-bearing in that sentence --
# a mystery has 3-4 witnesses and 4 leads against 4 players, so the pools run
# dry and the deal substitutes. See _FALLBACK_KIND.
DEFAULT_HAND_SPEC = ("witness", "clue", "lead")

# Which pool a slot falls back to when its own is exhausted. evidence[] is the
# largest pool in every mystery on disk (6-10 items against 3-4 witnesses and
# 4 leads), so it is the only sensible donor.
_FALLBACK_KIND = "clue"

# How many DISTINCT hands each required exoneration must land in.
#
# This is the replacement for PLAYTEST_FLOW's third deal constraint, which
# Session 38 measured as not well-formed: "becomes solvable once the minimum
# share threshold is met" cannot hold, because share_min is a fraction of a
# player's OWN findings and the player chooses which to share -- so meeting the
# threshold does not determine what reaches the pool, and a finding that MUST
# reach it is a finding nobody may keep, which deletes the hoarding decision.
#
# Redundancy is the option that survives that argument, and it does double duty:
# Session 38 also found the difficulty ladder is inert at a three-finding hand
# (EASY/MEDIUM/HARD all resolve to "share 2, keep 1" -- a percentage has no
# resolution over three items), and named redundancy as difficulty's natural
# home. EASY puts each exoneration in two hands so somebody will share it; HARD
# puts it in exactly one so withholding really bites.
#
# OWNER'S CALL, NOT SETTLED HERE. docs/INVESTIGATION_DESIGN.md §4 lists three
# options and this implements two of them: redundancy=1 IS the "accept it"
# option (constraints 1 and 2 only, universal hoarding can end a game with no
# winner). "Pigeonhole it" is a genuinely different constraint and is NOT
# implemented -- see module docs rather than assuming it is in here.
REDUNDANCY_BY_DIFFICULTY = {"EASY": 2, "MEDIUM": 1, "HARD": 1}

# Re-dealing is free, so the ceiling is generous. It exists to bound a mystery
# that cannot be dealt at all, and when it is hit the feasibility report -- not
# the attempt count -- is what says why.
MAX_ATTEMPTS = 400


@dataclass
class Finding:
    """One dealt finding. `reveals` is the join key to evidence[]."""
    id: str
    kind: str          # "witness" | "clue" | "lead"
    title: str
    body: str
    reveals: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DealResult:
    hands: List[List[Finding]]
    ok: bool
    issues: List[str] = field(default_factory=list)
    attempts: int = 0
    seed: int = 0
    redundancy: int = 1

    def to_dict(self) -> dict:
        return {
            "hands": [[c.to_dict() for c in h] for h in self.hands],
            "ok": self.ok,
            "issues": list(self.issues),
            "attempts": self.attempts,
            "seed": self.seed,
            "redundancy": self.redundancy,
        }


# --------------------------------------------------------------------------
# Reading the mystery
# --------------------------------------------------------------------------

def _name(character: dict) -> str:
    return (character.get("name") or "").strip()


def suspects(mystery: dict) -> List[str]:
    return [
        _name(c) for c in mystery.get("characters", []) or []
        if (c.get("role") or "").strip().lower() == "suspect" and _name(c)
    ]


def culprit(mystery: dict) -> str:
    return ((mystery.get("solution") or {}).get("culprit") or "").strip()


def required_exonerations(mystery: dict) -> Set[str]:
    """Every suspect EXCEPT the culprit.

    Eliminating exactly these leaves one person standing, which is the schema's
    own stated contract for evidence[].exonerates.
    """
    return {s for s in suspects(mystery) if s != culprit(mystery)}


def evidence_by_id(mystery: dict) -> Dict[str, dict]:
    return {
        (e.get("id") or "").strip(): e
        for e in mystery.get("evidence", []) or []
        if (e.get("id") or "").strip()
    }


def build_pool(mystery: dict) -> List[Finding]:
    """Every finding that could be dealt, in three kinds.

    A clue finding reveals ITSELF -- an evidence item is its own join key, which
    is why dealing from evidence[] alone would need no pointer at all. The
    pointer exists for the other two kinds.

    INVESTIGATION AREAS ARE DELIBERATELY NOT DEALT. APF has no traversal, so
    "you searched the library" is a sentence about a move nobody makes. They
    still carry `reveals` in the schema because the map is deferred, not
    cancelled (CLAUDE.md item 23), and a second schema change would cost a
    second paid generation round.
    """
    pool: List[Finding] = []

    for c in mystery.get("characters", []) or []:
        if (c.get("role") or "").strip().lower() != "witness":
            continue
        statement = (c.get("statement") or "").strip()
        if not statement:
            continue
        pool.append(Finding(
            id=f"W:{_name(c)}",
            kind="witness",
            title=_name(c),
            body=statement,
            reveals=[str(r).strip() for r in (c.get("reveals") or []) if str(r).strip()],
        ))

    for e in mystery.get("evidence", []) or []:
        eid = (e.get("id") or "").strip()
        if not eid:
            continue
        pool.append(Finding(
            id=f"E:{eid}",
            kind="clue",
            title=(e.get("name") or eid).strip(),
            body=(e.get("description") or "").strip(),
            reveals=[eid],
        ))

    for l in mystery.get("leads", []) or []:
        lid = (l.get("id") or "").strip()
        if not lid:
            continue
        pool.append(Finding(
            id=f"L:{lid}",
            kind="lead",
            title=(l.get("title") or lid).strip(),
            body=(l.get("brief") or "").strip(),
            reveals=[str(r).strip() for r in (l.get("reveals") or []) if str(r).strip()],
        ))

    return pool


# --------------------------------------------------------------------------
# The arithmetic
# --------------------------------------------------------------------------

def exonerated_by(findings: Sequence[Finding], ev_by_id: Dict[str, dict]) -> Set[str]:
    """Which suspects this finding set clears, read through the reveals pointer."""
    cleared: Set[str] = set()
    for finding in findings:
        for eid in finding.reveals:
            item = ev_by_id.get(eid)
            if not item:
                continue  # dangling; reported by feasibility(), not silently fatal here
            cleared.update(str(n).strip() for n in (item.get("exonerates") or []) if str(n).strip())
    return cleared


def solves(findings: Sequence[Finding], mystery: dict,
           ev_by_id: Optional[Dict[str, dict]] = None) -> bool:
    """True when this finding set eliminates every suspect but the culprit.

    Note it is not enough to clear |S|-1 people: the ONE left standing must be
    the culprit. A set that exonerates the culprit and leaves an innocent
    standing has the right cardinality and the wrong answer.
    """
    ev_by_id = evidence_by_id(mystery) if ev_by_id is None else ev_by_id
    standing = set(suspects(mystery)) - exonerated_by(findings, ev_by_id)
    return standing == {culprit(mystery)}


# --------------------------------------------------------------------------
# Feasibility — why a deal cannot be made, before trying 400 times
# --------------------------------------------------------------------------

def feasibility(mystery: dict, player_count: int,
                redundancy: int = 1,
                hand_spec: Sequence[str] = DEFAULT_HAND_SPEC) -> List[str]:
    """Cheap structural reasons this mystery can never be dealt.

    WHY THIS EXISTS. Without it, an undealable mystery looks exactly like an
    unlucky one: 400 failed attempts and no explanation. Every check below
    turns "the deal failed" into a sentence naming the mystery's defect, which
    is the difference between re-dealing and regenerating.
    """
    issues: List[str] = []
    ev_by_id = evidence_by_id(mystery)
    pool = build_pool(mystery)
    sus = suspects(mystery)
    cul = culprit(mystery)
    required = required_exonerations(mystery)

    if not sus:
        issues.append("no suspects: characters[] has nobody with role 'suspect'")
    if not cul:
        issues.append("no culprit: solution.culprit is empty")
    elif cul not in sus:
        issues.append(f"culprit {cul!r} is not among the suspects {sorted(sus)}")

    # Dangling pointers. A reveals id naming no evidence item is silently
    # inert in exonerated_by(), so it must be loud here.
    for finding in pool:
        for eid in finding.reveals:
            if eid not in ev_by_id:
                issues.append(f"finding {finding.id} reveals {eid!r}, which is not in evidence[]")

    # An exonerates name matching no suspect eliminates nobody. Reported rather
    # than normalised away: "Dr. Tanaka" against a suspect named "Tanaka" is a
    # real generation defect, and quietly fuzzy-matching it would hide it.
    known = set(sus)
    for eid, item in ev_by_id.items():
        for n in (item.get("exonerates") or []):
            if str(n).strip() and str(n).strip() not in known:
                issues.append(f"evidence {eid} exonerates {str(n).strip()!r}, who is not a suspect")
    if cul and cul in exonerated_by(pool, ev_by_id):
        issues.append(f"the culprit {cul!r} is exonerated by the evidence; nobody can be accused")

    # Constraint 1 must be reachable at all: if the WHOLE pool cannot solve,
    # no subset of it can.
    if sus and cul and not solves(pool, mystery, ev_by_id):
        standing = sorted(set(sus) - exonerated_by(pool, ev_by_id))
        issues.append(
            "the full finding pool does not solve the mystery -- "
            f"suspects left standing: {standing or ['(none)']}, expected exactly [{cul!r}]"
        )

    # Constraint 3 must be reachable: an exoneration carried by fewer distinct
    # findings than the redundancy level can never reach that many hands.
    if redundancy > 1:
        for r in sorted(required):
            carriers = [c for c in pool if r in exonerated_by([c], ev_by_id)]
            if len(carriers) < redundancy:
                issues.append(
                    f"exoneration of {r!r} is carried by {len(carriers)} finding(s) "
                    f"but redundancy {redundancy} needs {redundancy} distinct hands"
                )

    # Constraint 2 must be reachable: if one finding solves outright, whoever gets
    # it wins alone and the deal is a lottery by construction.
    for finding in pool:
        if sus and cul and solves([finding], mystery, ev_by_id):
            issues.append(f"finding {finding.id} solves the mystery by itself; no deal can be fair")

    hand_size = len(hand_spec)
    if len(pool) < player_count * hand_size:
        issues.append(
            f"pool has {len(pool)} findings, short of {player_count} players x {hand_size} = "
            f"{player_count * hand_size}"
        )

    return issues


# --------------------------------------------------------------------------
# The deal
# --------------------------------------------------------------------------

def _violations(hands: List[List[Finding]], mystery: dict,
                ev_by_id: Dict[str, dict], redundancy: int) -> List[str]:
    """The three constraints, checked against one candidate deal."""
    out: List[str] = []
    all_findings = [f for h in hands for f in h]

    # 1. the union of all dealt findings eliminates all but one suspect
    if not solves(all_findings, mystery, ev_by_id):
        standing = sorted(set(suspects(mystery)) - exonerated_by(all_findings, ev_by_id))
        out.append(f"union does not solve; standing: {standing or ['(none)']}")

    # 2. no single player's hand does that alone
    for i, hand in enumerate(hands):
        if solves(hand, mystery, ev_by_id):
            out.append(f"hand {i} solves alone")

    # 3. each required exoneration reaches at least `redundancy` distinct hands
    if redundancy > 1:
        for r in sorted(required_exonerations(mystery)):
            holders = sum(1 for h in hands if r in exonerated_by(h, ev_by_id))
            if holders < redundancy:
                out.append(f"exoneration of {r!r} reaches {holders} hand(s), needs {redundancy}")

    return out


def deal(mystery: dict, player_count: int, seed: int = 0,
         redundancy: Optional[int] = None,
         hand_spec: Sequence[str] = DEFAULT_HAND_SPEC,
         max_attempts: int = MAX_ATTEMPTS) -> DealResult:
    """Deal `player_count` hands under the three constraints.

    Deterministic in `seed`: the same (mystery, players, seed) always gives the
    same hands, so a reconnecting player gets back the hand they left rather
    than a reshuffled one -- the same property background_field.py needs for
    the same reason.

    Returns a DealResult rather than raising. A deal that cannot be made is
    diagnostic data about the MYSTERY -- the caller decides between re-dealing
    with a new seed and regenerating -- and an exception would throw that away.
    """
    if redundancy is None:
        difficulty = ((mystery.get("gameplay_notes") or {}).get("difficulty") or "MEDIUM").strip().upper()
        redundancy = REDUNDANCY_BY_DIFFICULTY.get(difficulty, 1)

    ev_by_id = evidence_by_id(mystery)
    pool = build_pool(mystery)

    blocking = feasibility(mystery, player_count, redundancy, hand_spec)
    if blocking:
        return DealResult(hands=[], ok=False, issues=blocking, attempts=0,
                          seed=seed, redundancy=redundancy)

    rng = random.Random(seed)
    last: List[str] = []

    for attempt in range(1, max_attempts + 1):
        by_kind: Dict[str, List[Finding]] = {}
        for finding in pool:
            by_kind.setdefault(finding.kind, []).append(finding)
        for bucket in by_kind.values():
            rng.shuffle(bucket)

        hands: List[List[Finding]] = [[] for _ in range(player_count)]
        # Slot-major, not player-major. MEASURED, NOT ASSUMED: with one slot per
        # kind and a single shared fallback pool, the two orders produce the
        # SAME distribution -- an earlier version of this comment claimed
        # player-major would "give player 0 the full spec and player 3 three
        # fallbacks", and a negative test proved that false. It is kept because
        # it stays correct if hand_spec ever takes two slots of one kind, where
        # player-major would let an early hand take both copies of a scarce kind
        # before any later hand takes one.
        short = False
        for slot in hand_spec:
            for hand in hands:
                src = by_kind.get(slot) or []
                if not src:
                    src = by_kind.get(_FALLBACK_KIND) or []
                if not src:
                    short = True
                    break
                hand.append(src.pop())
            if short:
                break
        if short:
            last = ["ran out of findings while dealing"]
            continue

        last = _violations(hands, mystery, ev_by_id, redundancy)
        if not last:
            return DealResult(hands=hands, ok=True, issues=[], attempts=attempt,
                              seed=seed, redundancy=redundancy)

    return DealResult(
        hands=[], ok=False,
        issues=[f"no valid deal in {max_attempts} attempts; last: " + "; ".join(last)],
        attempts=max_attempts, seed=seed, redundancy=redundancy,
    )
