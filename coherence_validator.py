"""
Choose Your Mystery - Coherence Validator
==========================================

Pre-generation and post-generation checks that ensure every mystery
can actually be played and solved.

Three check families (all inside check_mystery):
  1. P1 chain       — causal spine is intact (BLOCKING)
  2. Interrogation  — suspects/witnesses have usable alibi/secret/motive
  3. Scene          — physical evidence and red-herring discovery paths exist

Pre-generation gate (check_parts):
  Catches weak registry parts before any Claude call is made.
  Auto-retry hint: each Issue.repair_hint names the part_type to re-sample.

Pure logic — zero extra API calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


# ============================================================================
# ISSUE MODEL
# ============================================================================

@dataclass
class Issue:
    """A validation finding with an actionable repair hint."""
    severity: str      # "BLOCKING" | "WARNING"
    family: str        # "p1_chain" | "interrogation" | "scene" | "parts"
    message: str
    repair_hint: str   # which part_type to re-sample from the registry


# ============================================================================
# HELPERS
# ============================================================================

_VAGUE_PLACEHOLDERS = {"—", "-", "n/a", "unknown", "tbd", "none", ""}

_VAGUE_SECRET_PATTERNS = [
    "has a dark past", "hides something", "has secrets",
    "mysterious past", "hidden past", "dark history", "is hiding",
    "something to hide", "not what they seem",
]


def _is_vague(text: str) -> bool:
    """True if text is a placeholder or clearly too thin to be meaningful."""
    return not text or text.strip().lower() in _VAGUE_PLACEHOLDERS


def _evidence_type(e: Dict) -> str:
    """Return the evidence type regardless of which key is used.

    mystery_generator.py uses 'type'; mystery_data_acquisition.py uses
    'evidence_type'. Accept either.
    """
    return (e.get("type") or e.get("evidence_type") or "").lower()


# ============================================================================
# CHECK 1 — P1 CAUSAL CHAIN  (BLOCKING)
# ============================================================================

def _check_p1_chain(mystery: Dict) -> List[Issue]:
    """
    Walk the causal spine:
      crime defined → victim present → closed-world bounded →
      culprit in character list with matching motive →
      resolution has reachable key evidence + deduction path.

    Any broken link is BLOCKING.
    """
    issues: List[Issue] = []
    characters = mystery.get("characters") or []

    # 1a. Crime definition
    crime = mystery.get("crime") or {}
    what_happened = crime.get("what_happened", "") or ""
    if len(what_happened.strip()) < 30:
        issues.append(Issue(
            severity="BLOCKING",
            family="p1_chain",
            message="crime.what_happened is missing or too vague (<30 chars).",
            repair_hint="Re-sample crime block from registry (part_type='crime').",
        ))

    # 1b. Victim present
    victims = [c for c in characters if c.get("role") == "victim"]
    if not victims:
        issues.append(Issue(
            severity="BLOCKING",
            family="p1_chain",
            message="No character with role='victim' found.",
            repair_hint="Re-sample cast from registry (part_type='victim').",
        ))

    # 1c. Closed world: at least one suspect
    suspects = [c for c in characters if c.get("role") == "suspect"]
    if not suspects:
        issues.append(Issue(
            severity="BLOCKING",
            family="p1_chain",
            message="No character with role='suspect' found.",
            repair_hint="Re-sample cast from registry (part_type='suspect').",
        ))

    # 1d. Solution exists and culprit is in the character list
    solution = mystery.get("solution") or {}
    culprit_name = (solution.get("culprit") or "").strip()
    character_names = {c.get("name", "") for c in characters}

    if not culprit_name:
        issues.append(Issue(
            severity="BLOCKING",
            family="p1_chain",
            message="solution.culprit is missing.",
            repair_hint="Re-sample solution block from registry (part_type='solution').",
        ))
    elif culprit_name not in character_names:
        issues.append(Issue(
            severity="BLOCKING",
            family="p1_chain",
            message=(
                f"Culprit '{culprit_name}' is not in the character list "
                f"({sorted(character_names)})."
            ),
            repair_hint="Re-sample solution block from registry (part_type='solution').",
        ))
    else:
        # Culprit must carry a motive that matches the solution
        culprit = next((c for c in characters if c.get("name") == culprit_name), {})
        char_motive = (culprit.get("motive") or "").strip()
        sol_motive  = (solution.get("motive") or "").strip()
        if _is_vague(char_motive) or _is_vague(sol_motive):
            issues.append(Issue(
                severity="BLOCKING",
                family="p1_chain",
                message=(
                    f"Culprit '{culprit_name}' has no specific motive "
                    "(either in character record or in solution)."
                ),
                repair_hint=(
                    f"Re-sample suspect '{culprit_name}' from registry "
                    "(part_type='suspect') with a concrete motive."
                ),
            ))

    # 1e. Key evidence IDs in solution exist in the evidence list
    evidence_ids = {e.get("id", "") for e in (mystery.get("evidence") or [])}
    key_evidence = solution.get("key_evidence") or []

    if not key_evidence:
        issues.append(Issue(
            severity="BLOCKING",
            family="p1_chain",
            message="solution.key_evidence is empty — no deduction path defined.",
            repair_hint="Re-sample solution block from registry (part_type='solution').",
        ))
    else:
        missing = [eid for eid in key_evidence if eid not in evidence_ids]
        if missing:
            issues.append(Issue(
                severity="BLOCKING",
                family="p1_chain",
                message=(
                    f"solution.key_evidence references IDs not in evidence list: "
                    f"{missing}."
                ),
                repair_hint="Re-sample solution block from registry (part_type='solution').",
            ))

    # 1f. Deduction path narrative
    how_to_deduce = (solution.get("how_to_deduce") or "").strip()
    if len(how_to_deduce) < 40:
        issues.append(Issue(
            severity="BLOCKING",
            family="p1_chain",
            message="solution.how_to_deduce is missing or too brief (<40 chars).",
            repair_hint="Re-sample solution block from registry (part_type='solution').",
        ))

    return issues


# ============================================================================
# CHECK 2 — WITNESS INTERROGATION FOUNDATION  (WARNING)
# ============================================================================

def _check_interrogation(mystery: Dict) -> List[Issue]:
    """
    For every suspect and witness, verify three interrogation anchors:

      alibi   — >20 chars, not "—"
                Answers: "where were you?"
      secret  — >30 chars, not a label like "has a dark past"
                Answers: "why were you near the victim / why didn't you do X?"
      motive  — suspects only, >15 chars, specific stake, never "—"

    Also verify the victim has a documented secret or rich-enough personality
    so suspects have a credible reason to be present.
    """
    issues: List[Issue] = []
    characters = mystery.get("characters") or []

    for char in characters:
        role = char.get("role", "")
        name = char.get("name", "unknown")

        if role not in ("suspect", "witness"):
            continue

        # — alibi —
        alibi = (char.get("alibi") or "").strip()
        if _is_vague(alibi) or len(alibi) < 20:
            issues.append(Issue(
                severity="WARNING",
                family="interrogation",
                message=(
                    f"{role.title()} '{name}' has a vague/missing alibi "
                    f"('{alibi[:40]}') — cannot answer 'where were you?'."
                ),
                repair_hint=(
                    f"Re-sample '{name}' from registry (part_type='{role}') "
                    "with alibi >20 chars that names a place and time."
                ),
            ))

        # — secret —
        secret = (char.get("secrets") or "").strip()
        secret_is_label = any(p in secret.lower() for p in _VAGUE_SECRET_PATTERNS)
        if _is_vague(secret) or len(secret) < 30 or secret_is_label:
            issues.append(Issue(
                severity="WARNING",
                family="interrogation",
                message=(
                    f"{role.title()} '{name}' secret is a vague label or too short: "
                    f"'{secret[:50]}' — cannot support interrogation about motivation/presence."
                ),
                repair_hint=(
                    f"Re-sample '{name}' from registry (part_type='{role}') "
                    "with a concrete two-sentence secret (>30 chars)."
                ),
            ))

        # — motive (suspects only) —
        if role == "suspect":
            motive = (char.get("motive") or "").strip()
            if _is_vague(motive) or len(motive) < 15:
                issues.append(Issue(
                    severity="WARNING",
                    family="interrogation",
                    message=(
                        f"Suspect '{name}' has a vague/missing motive: '{motive[:40]}'."
                    ),
                    repair_hint=(
                        f"Re-sample '{name}' from registry (part_type='suspect') "
                        "with a specific stake/motive (>15 chars)."
                    ),
                ))

    # Victim must have a documented secret or rich-enough personality
    victims = [c for c in characters if c.get("role") == "victim"]
    for victim in victims:
        v_name = victim.get("name", "victim")
        v_secret = (victim.get("secrets") or "").strip()
        v_personality = (victim.get("personality") or "").strip()
        if _is_vague(v_secret) and len(v_personality) < 40:
            issues.append(Issue(
                severity="WARNING",
                family="interrogation",
                message=(
                    f"Victim '{v_name}' has no documented secret or rich personality — "
                    "suspects lack a credible reason to have been present."
                ),
                repair_hint=(
                    "Re-sample victim from registry (part_type='victim') "
                    "with a concrete secret or relationship web."
                ),
            ))

    return issues


# ============================================================================
# CHECK 3 — SCENE INVESTIGATION  (WARNING)
# ============================================================================

def _check_scene(mystery: Dict) -> List[Issue]:
    """
    Checks that scene investigation is productive for players:

      ≥5  total evidence items     — 75% sharing mechanic needs real depth
      ≥2  physical items           — something to *find*, not only *hear*
      ≥1  red_herring that is physical or documentary
                                   — players discover misdirection by exploring,
                                     not only through NPC dialogue
      ≥2  distinct evidence types  — variety keeps investigation interesting
      ≥40 chars per description    — enough detail for players to reason about
      ≥2  critical items           — backup deduction path if one is missed

    All geared from initial generation data — no extra API calls needed.
    """
    issues: List[Issue] = []
    evidence = mystery.get("evidence") or []

    # Total count
    if len(evidence) < 5:
        issues.append(Issue(
            severity="WARNING",
            family="scene",
            message=(
                f"Only {len(evidence)} evidence item(s). "
                "Need ≥5 for the 75% sharing mechanic to create real strategic decisions."
            ),
            repair_hint="Re-sample evidence set from registry (part_type='evidence').",
        ))

    # Physical evidence
    physical = [e for e in evidence if _evidence_type(e) == "physical"]
    if len(physical) < 2:
        issues.append(Issue(
            severity="WARNING",
            family="scene",
            message=(
                f"Only {len(physical)} physical evidence item(s). "
                "Need ≥2 so players have something to *find* during scene investigation."
            ),
            repair_hint=(
                "Re-sample evidence from registry (part_type='evidence') "
                "specifying evidence_type='physical'."
            ),
        ))

    # Red herrings must be discoverable during scene investigation
    red_herrings = [e for e in evidence if e.get("relevance") == "red_herring"]
    discoverable_rh = [
        e for e in red_herrings
        if _evidence_type(e) in ("physical", "documentary")
    ]
    if not red_herrings:
        issues.append(Issue(
            severity="WARNING",
            family="scene",
            message="No red herrings — mystery may be trivially easy to solve.",
            repair_hint=(
                "Re-sample evidence from registry (part_type='evidence') "
                "with relevance='red_herring'."
            ),
        ))
    elif not discoverable_rh:
        issues.append(Issue(
            severity="WARNING",
            family="scene",
            message=(
                "All red herrings are testimonial — players only encounter misdirection "
                "through NPC dialogue, not through scene investigation."
            ),
            repair_hint=(
                "Re-sample at least one red_herring from registry "
                "(part_type='evidence') with evidence_type='physical' or 'documentary'."
            ),
        ))

    # Evidence variety
    types_used = {_evidence_type(e) for e in evidence}
    if len(types_used) <= 1:
        issues.append(Issue(
            severity="WARNING",
            family="scene",
            message=(
                f"All evidence is the same type ({types_used or '?'}). "
                "Mix physical, testimonial, and documentary to keep investigation varied."
            ),
            repair_hint="Re-sample evidence set from registry (part_type='evidence').",
        ))

    # Description length
    for e in evidence:
        desc = (e.get("description") or "").strip()
        label = e.get("name") or e.get("id") or "?"
        if len(desc) < 40:
            issues.append(Issue(
                severity="WARNING",
                family="scene",
                message=(
                    f"Evidence '{label}' description is too short "
                    f"({len(desc)} chars, need ≥40) — not enough detail for players to reason about."
                ),
                repair_hint=(
                    "Re-sample this evidence item from registry "
                    "(part_type='evidence') with a richer description."
                ),
            ))

    # Critical items
    critical = [e for e in evidence if e.get("relevance") == "critical"]
    if len(critical) < 2:
        issues.append(Issue(
            severity="WARNING",
            family="scene",
            message=(
                f"Only {len(critical)} critical evidence item(s). "
                "Need ≥2 to provide a backup deduction path."
            ),
            repair_hint=(
                "Re-sample evidence from registry (part_type='evidence') "
                "with relevance='critical'."
            ),
        ))

    return issues


# ============================================================================
# PUBLIC: check_mystery
# ============================================================================

def check_mystery(mystery: Dict) -> List[Issue]:
    """
    Run all three check families on a fully generated mystery dict.

    Returns a (possibly empty) list of Issues.
    BLOCKING issues must be resolved before the mystery reaches a player.
    WARNINGs degrade quality but do not make the mystery unplayable.
    """
    issues: List[Issue] = []
    issues.extend(_check_p1_chain(mystery))
    issues.extend(_check_interrogation(mystery))
    issues.extend(_check_scene(mystery))
    return issues


# ============================================================================
# PUBLIC: check_parts  (pre-generation gate)
# ============================================================================

def check_parts(parts: List[Dict]) -> List[Issue]:
    """
    Validate individual registry parts *before* any Claude API call is made.

    Each part dict must carry:
      part_type  — "suspect" | "witness" | "victim" | "evidence" | "crime" | "solution"
      + type-specific fields

    A non-empty result means at least one part should be re-sampled from the
    registry before generation proceeds — saving the cost of a bad Claude call.
    """
    issues: List[Issue] = []

    for i, part in enumerate(parts):
        part_type = part.get("part_type", "")
        name = part.get("name", f"part[{i}]")

        if part_type in ("suspect", "witness"):

            alibi = (part.get("alibi") or "").strip()
            if _is_vague(alibi) or len(alibi) < 20:
                issues.append(Issue(
                    severity="BLOCKING",
                    family="parts",
                    message=f"{part_type} '{name}' alibi is vague or missing.",
                    repair_hint=(
                        f"Re-sample '{name}' from registry "
                        f"(part_type='{part_type}') before calling Claude."
                    ),
                ))

            secret = (part.get("secrets") or part.get("secret") or "").strip()
            secret_is_label = any(p in secret.lower() for p in _VAGUE_SECRET_PATTERNS)
            if _is_vague(secret) or len(secret) < 30 or secret_is_label:
                issues.append(Issue(
                    severity="BLOCKING",
                    family="parts",
                    message=f"{part_type} '{name}' secret is vague or too short.",
                    repair_hint=(
                        f"Re-sample '{name}' from registry "
                        f"(part_type='{part_type}') before calling Claude."
                    ),
                ))

            if part_type == "suspect":
                motive = (part.get("motive") or "").strip()
                if _is_vague(motive) or len(motive) < 15:
                    issues.append(Issue(
                        severity="BLOCKING",
                        family="parts",
                        message=f"Suspect '{name}' has vague/missing motive.",
                        repair_hint=(
                            f"Re-sample '{name}' from registry "
                            "(part_type='suspect') before calling Claude."
                        ),
                    ))

        elif part_type == "evidence":
            relevance = (part.get("relevance") or "").strip()
            ev_type   = _evidence_type(part)

            # Testimonial-only red herrings are undiscoverable in scene investigation
            if relevance == "red_herring" and ev_type == "testimonial":
                issues.append(Issue(
                    severity="BLOCKING",
                    family="parts",
                    message=(
                        f"Evidence '{name}' is a testimonial red_herring — "
                        "players cannot discover it during scene investigation."
                    ),
                    repair_hint=(
                        "Re-sample this evidence from registry (part_type='evidence') "
                        "with evidence_type='physical' or 'documentary'."
                    ),
                ))

            desc = (part.get("description") or "").strip()
            if len(desc) < 40:
                issues.append(Issue(
                    severity="BLOCKING",
                    family="parts",
                    message=f"Evidence '{name}' description too short ({len(desc)} chars, need ≥40).",
                    repair_hint=(
                        "Re-sample this evidence from registry (part_type='evidence') "
                        "with a richer description."
                    ),
                ))

        elif part_type == "crime":
            what = (part.get("what_happened") or "").strip()
            if len(what) < 30:
                issues.append(Issue(
                    severity="BLOCKING",
                    family="parts",
                    message="Crime part is too vague (what_happened <30 chars).",
                    repair_hint="Re-sample crime from registry (part_type='crime').",
                ))

    return issues


# ============================================================================
# REPORT HELPER
# ============================================================================

def format_report(issues: List[Issue], title: str = "Coherence Validation") -> str:
    """Render a human-readable validation report."""
    lines = []
    lines.append("=" * 70)
    lines.append(title.upper())
    lines.append("=" * 70)

    if not issues:
        lines.append("PASS — no issues found.")
        lines.append("=" * 70)
        return "\n".join(lines)

    blocking = [i for i in issues if i.severity == "BLOCKING"]
    warnings  = [i for i in issues if i.severity == "WARNING"]

    overall = "FAIL" if blocking else "PASS (with warnings)"
    lines.append(f"Result  : {overall}")
    lines.append(f"Blocking: {len(blocking)}   Warnings: {len(warnings)}")
    lines.append("")

    family_labels = {
        "p1_chain":     "P1 CHAIN (causal spine)",
        "interrogation": "INTERROGATION ANCHORS",
        "scene":        "SCENE INVESTIGATION",
        "parts":        "PARTS GATE (pre-generation)",
    }

    for family in ("p1_chain", "interrogation", "scene", "parts"):
        family_issues = [i for i in issues if i.family == family]
        if not family_issues:
            continue
        lines.append(family_labels.get(family, family.upper()))
        lines.append("-" * 70)
        for issue in family_issues:
            tag = "[BLOCKING]" if issue.severity == "BLOCKING" else "[WARNING] "
            lines.append(f"  {tag} {issue.message}")
            lines.append(f"           Hint: {issue.repair_hint}")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


# ============================================================================
# STANDALONE SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("\n=== Coherence Validator — self-test ===\n")

    # --- Good mystery ---
    good = {
        "title": "The Clockwork Poisoning",
        "crime": {
            "type": "murder",
            "what_happened": (
                "Lord Ashford was found dead in his study, a vial of arsenic "
                "dissolved in his nightly brandy. The door was locked from inside."
            ),
            "when": "Between 10 pm and midnight",
            "initial_discovery": "The butler discovered him at breakfast.",
        },
        "characters": [
            {
                "name": "Lord Ashford",
                "role": "victim",
                "personality": (
                    "A secretive industrialist who had recently cut three business "
                    "partners out of a lucrative patent deal."
                ),
                "secrets": (
                    "Lord Ashford had been blackmailing his solicitor over "
                    "a forged will for the past decade."
                ),
            },
            {
                "name": "Mrs. Crane",
                "role": "suspect",
                "motive": "Stood to inherit £40,000 if Lord Ashford died before signing a new will.",
                "alibi": "Claims she was playing whist with the vicar until eleven o'clock.",
                "secrets": (
                    "Mrs. Crane secretly purchased arsenic from a London chemist "
                    "three days before the murder under a false name."
                ),
            },
            {
                "name": "Thomas Webb",
                "role": "witness",
                "alibi": "Was polishing silver in the pantry all evening and heard raised voices at ten-fifteen.",
                "secrets": (
                    "Thomas Webb saw Mrs. Crane enter the study at ten-fifteen "
                    "but feared losing his position if he spoke up."
                ),
            },
        ],
        "evidence": [
            {
                "id": "ev_001",
                "name": "Arsenic vial",
                "description": "A small crystal vial found behind the fireplace grate, still carrying traces of white powder consistent with arsenic.",
                "type": "physical",
                "relevance": "critical",
            },
            {
                "id": "ev_002",
                "name": "Chemist receipt",
                "description": "A receipt from Holt & Sons chemists for one ounce of arsenic, signed 'M. Crawford' in Mrs. Crane's handwriting.",
                "type": "documentary",
                "relevance": "critical",
            },
            {
                "id": "ev_003",
                "name": "Webb's testimony",
                "description": "Thomas Webb states he heard a woman's voice arguing with Lord Ashford at ten-fifteen on the night of the murder.",
                "type": "testimonial",
                "relevance": "supporting",
            },
            {
                "id": "ev_004",
                "name": "Muddy boot print",
                "description": "A partial boot print in the flower bed outside the study window, size 5, consistent with a small woman's boot.",
                "type": "physical",
                "relevance": "supporting",
            },
            {
                "id": "ev_005",
                "name": "Colonel's pipe",
                "description": "A briar pipe belonging to Colonel Fitch found near the garden gate, suggesting he was present that evening.",
                "type": "physical",
                "relevance": "red_herring",
            },
        ],
        "solution": {
            "culprit": "Mrs. Crane",
            "method": "Dissolved arsenic in Lord Ashford's brandy decanter during her visit at ten-fifteen.",
            "motive": "Stood to inherit £40,000 if Lord Ashford died before signing a new will.",
            "key_evidence": ["ev_001", "ev_002"],
            "how_to_deduce": (
                "The chemist receipt proves Mrs. Crane purchased arsenic under a false name. "
                "The arsenic vial found behind the grate matches the compound. "
                "Webb's testimony places her in the room at the time of poisoning."
            ),
        },
    }

    issues = check_mystery(good)
    print(format_report(issues, "Good mystery — expect PASS"))

    # --- Broken mystery ---
    bad = {
        "title": "The Broken Case",
        "crime": {"what_happened": "Someone died."},
        "characters": [
            {"name": "Alice", "role": "victim", "personality": "nice", "secrets": "—"},
            {
                "name": "Bob",
                "role": "suspect",
                "motive": "—",
                "alibi": "Was around",
                "secrets": "has a dark past",
            },
        ],
        "evidence": [
            {
                "id": "ev_001",
                "name": "Rumour",
                "description": "People say Bob did it.",
                "type": "testimonial",
                "relevance": "red_herring",
            },
        ],
        "solution": {
            "culprit": "Carol",          # not in character list
            "method": "poison",
            "motive": "—",
            "key_evidence": ["ev_999"],  # non-existent ID
            "how_to_deduce": "Trust me.",
        },
    }

    issues = check_mystery(bad)
    print(format_report(issues, "Broken mystery — expect FAIL with many issues"))

    # --- Parts gate test ---
    weak_parts = [
        {
            "part_type": "suspect",
            "name": "Dr. Morris",
            "motive": "—",
            "alibi": "Home",
            "secrets": "hides something",
        },
        {
            "part_type": "evidence",
            "name": "Vague clue",
            "relevance": "red_herring",
            "type": "testimonial",
            "description": "A clue.",
        },
    ]

    parts_issues = check_parts(weak_parts)
    print(format_report(parts_issues, "Parts gate — weak parts, expect BLOCKING"))
