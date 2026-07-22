"""
coherence_validator.py — P1 Chain + Witness Interrogability + Scene Investigation Checks

Two entry points:

    check_parts(parts)    — PRE-generation: validates sampled MysteryPart list
                            Catches gaps BEFORE calling Claude, so fixes cost nothing.

    check_mystery(mystery) — POST-generation: validates generated mystery dict
                             Verifies the P1 causal chain and gameplay data integrity.

Design principle: surface repair hints that reference part registry part_types
(free re-sample) rather than requiring a new full generation call.

Check families
--------------
1. P1 CHAIN          crime → victim → closed_world → culprit → resolution
2. WITNESS FOUNDATION each suspect/witness has material to answer traditional
                      interrogation questions (alibi, motive, "why were you there",
                      "why didn't you do X")
3. SCENE INVESTIGATION enough physical evidence and red herrings exist for scene-
                      based discovery; maximised from pre-sampled parts where possible
4. CRAFT INVARIANTS  new checks added from the July 2026 taxonomy-expansion research
                      (TAXONOMY_EXPANSION_CANDIDATES.md) — see individual Rule docstrings
                      for authority citations

Architecture
------------
Every check below is a `coherence.engine.Rule` subclass: a `code`, a `severity`
(BLOCKING/WARNING/INFO — how bad a violation is), an optional `applicability`
(does this rule even apply to this content — orthogonal to severity, see
coherence/engine.py's module docstring), and a `check(context)` method.
`check_parts`/`check_mystery` build a `MysteryContext`/`PartsContext`, run the
domain's `RuleSet`, and return the resulting `CoherenceReport` — same external
shape as before this refactor (`.passed`, `.blocking_count`, `.warning_count`),
so `server/main.py`'s `check_mystery()` call is unaffected.

This mirrors the shape MYF's own `coherence/engine.py` subclasses — see
`mind-your-friends/lib/coherence.js` once that game is wired to it (post-Godot
port; see that project's own CLAUDE.md item 31).
"""

from __future__ import annotations

import re
from typing import Any, List

from coherence.engine import (
    BLOCKING,
    WARNING,
    INFO,
    Applicability,
    CoherenceReport,
    Issue,
    Rule,
    RuleSet,
)

# Re-exported for backward compatibility with any existing importers of these names.
__all__ = [
    "BLOCKING", "WARNING", "INFO", "Issue", "CoherenceReport",
    "check_parts", "check_mystery", "rich_panels",
]


# ─── Helper regexes / keyword sets ──────────────────────────────────────────

# Keywords that suggest an evidence piece is physically present at a scene
_PHYSICAL_KW = re.compile(
    r"\b(found|discovered|object|item|trace|blood|stain|fingerprint|footprint|"
    r"wound|weapon|tool|paper|document|letter|photograph|bottle|fabric|cloth|"
    r"key|lock|mark|scratch|burn|residue|fragment|shard|chemical|record|"
    r"log|ledger|note|map|container|device|body|remains|sample|artifact|"
    r"hidden|concealed|beneath|behind|inside|under|on\s+the\s+floor|"
    r"on\s+the\s+desk|at\s+the\s+scene)\b",
    re.IGNORECASE,
)

# Keywords indicating an evidence type part leans testimonial only
_TESTIMONIAL_ONLY_KW = re.compile(
    r"\b(confession|testimony|statement|hearsay|rumour|gossip|overheard|"
    r"told|said|claimed|alleged|admitted)\b",
    re.IGNORECASE,
)

# Keywords that suggest motive has concrete specificity
_MOTIVE_SPECIFIC_KW = re.compile(
    r"\b(inheritance|debt|secret|blackmail|revenge|promotion|affair|"
    r"competition|patent|profit|silence|exposure|shame|jealousy|"
    r"discovery|evidence|treaty|contract|will|insurance|power|"
    r"betrayal|rivalry|custody|honour|disgrace)\b",
    re.IGNORECASE,
)

_PRESENCE_KW = re.compile(
    r"\b(occupation|role|position|rank|servant|guard|staff|employee|"
    r"resident|guest|invited|member|officer|scholar|merchant|trader|"
    r"physician|scribe|attendant|delegate|diplomat|crew|lodger)\b",
    re.IGNORECASE,
)

_DISCOVERABLE_KW = re.compile(
    r"\b(planted|staged|placed|left|found|object|item|evidence|"
    r"frame|false|forged|fabricated|disguised|misdirect|mislead|"
    r"apparent|look|seem|suggest)\b",
    re.IGNORECASE,
)

_BOUNDED_KW = re.compile(
    r"\b(isolated|locked|sealed|closed|confined|bounded|remote|"
    r"no\s+escape|cut\s+off|trapped|stranded|island|ship|station|"
    r"manor|estate|monastery|colony|mine|bunker|fortress|compound)\b",
    re.IGNORECASE,
)

# New this pass (Knox Commandment 2 — "no supernatural/preternatural agencies");
# see TAXONOMY_EXPANSION_CANDIDATES.md, "Naturalistic Causality Contract".
_SUPERNATURAL_KW = re.compile(
    r"\b(ghost|curse|cursed|prophecy|prophesied|telepath(?:y|ic)|psychic|"
    r"clairvoyant|divine\s+intervention|supernatural|demonic\s+possession|"
    r"spirit\s+possession|haunting|haunted|premonition|astral|occult|"
    r"sorcery|witchcraft)\b",
    re.IGNORECASE,
)

_DASH_RE = re.compile(r"^[\-—–]+$")


def _is_empty(value) -> bool:
    """True if value is missing, "—", or whitespace-only."""
    if not value:
        return True
    s = str(value).strip()
    return not s or bool(_DASH_RE.match(s))


def _is_short(value, min_len: int = 20) -> bool:
    return len(str(value).strip()) < min_len


def _char_by_role(mystery: dict, role: str):
    return [c for c in mystery.get("characters", []) if c.get("role") == role]


def _evidence_by_type(mystery: dict, etype: str):
    return [e for e in mystery.get("evidence", []) if e.get("type") == etype]


def _evidence_by_relevance(mystery: dict, relevance: str):
    return [e for e in mystery.get("evidence", []) if e.get("relevance") == relevance]


# ============================================================================
# CONTEXTS
# ============================================================================

class PartsContext:
    """Wraps a sampled MysteryPart list for check_parts()'s RuleSet."""

    # Choose Your Mystery is always a live, room-code multiplayer game — this
    # is a fixed fact of the product, not per-mystery data, but it's exposed
    # here (rather than hardcoded true in every Applicability check) so the
    # engine's multiplayer-gated rules stay meaningful if this module is ever
    # reused somewhere single-player (e.g. a solo playtest mode).
    is_multiplayer = True
    subgenre_contract = None  # not yet modeled in the part-sampling stage

    def __init__(self, parts):
        self.parts = parts
        self.by_type = {p.part_type: p for p in parts}


class MysteryContext:
    """Wraps a generated mystery dict for check_mystery()'s RuleSet."""

    is_multiplayer = True
    subgenre_contract = None  # not yet modeled in the generated-mystery schema

    def __init__(self, mystery: dict):
        self.mystery = mystery
        self.characters = mystery.get("characters", [])
        self.evidence = mystery.get("evidence", [])
        self.crime = mystery.get("crime", {})
        self.setting = mystery.get("setting", {})
        self.solution = mystery.get("solution", {})
        self.evidence_ids = {e.get("id") for e in self.evidence if e.get("id")}
        self.victims = _char_by_role(mystery, "victim")
        self.suspects = _char_by_role(mystery, "suspect")
        self.interrogatable = [c for c in self.characters if c.get("role") in ("suspect", "witness")]


# ============================================================================
# PARTS RULES (pre-generation)
# ============================================================================

class PartsCompletenessRule(Rule):
    code = "parts.completeness"
    severity = BLOCKING
    family = "PARTS"

    REQUIRED_TYPES = [
        "crime_type", "setting_element", "motive", "suspect_archetype",
        "red_herring", "reveal_mechanic", "social_dynamic", "evidence_type",
    ]

    def check(self, context: PartsContext) -> List[Issue]:
        issues = []
        for pt in self.REQUIRED_TYPES:
            if pt not in context.by_type:
                issues.append(Issue(
                    code=f"parts.missing.{pt}",
                    severity=BLOCKING,
                    family=self.family,
                    message=f"No part sampled for part_type='{pt}'.",
                    repair_hint=f"Re-sample: registry.get_candidates('{pt}', ...) and add one part.",
                ))
        return issues


class PartsWitnessFoundationRule(Rule):
    code = "parts.social_dynamic.presence"
    severity = WARNING
    family = "PARTS"

    def check(self, context: PartsContext) -> List[Issue]:
        sd = context.by_type.get("social_dynamic")
        if not sd or _PRESENCE_KW.search(sd.content):
            return []
        return [Issue(
            code="parts.social_dynamic.no_presence_context",
            severity=WARNING,
            family=self.family,
            message=(
                f"social_dynamic part [{sd.label()}] doesn't name occupations or "
                "roles that explain why people are in the closed world. "
                "Witnesses may lack 'why were you there' foundation."
            ),
            repair_hint=(
                "Re-sample part_type='social_dynamic'; prefer parts that describe "
                "specific roles, occupations, or patronage relationships."
            ),
        )]


class PartsSceneEvidenceRule(Rule):
    code = "parts.evidence_type.scene_observable"
    severity = WARNING
    family = "PARTS"

    def check(self, context: PartsContext) -> List[Issue]:
        ev = context.by_type.get("evidence_type")
        if not ev:
            return []
        has_physical = bool(_PHYSICAL_KW.search(ev.content))
        is_testimonial_only = bool(_TESTIMONIAL_ONLY_KW.search(ev.content)) and not has_physical
        if is_testimonial_only:
            return [Issue(
                code="parts.evidence_type.testimonial_only",
                severity=WARNING,
                family=self.family,
                message=(
                    f"evidence_type part [{ev.label()}] describes only testimonial "
                    "evidence (confession/statement). Scene investigation will have "
                    "nothing physical to discover."
                ),
                repair_hint=(
                    "Re-sample part_type='evidence_type'; prefer parts with physical, "
                    "documentary, or forensic evidence (objects, records, traces)."
                ),
            )]
        if not has_physical:
            return [Issue(
                code="parts.evidence_type.no_physical_anchor",
                severity=INFO,
                family=self.family,
                message=(
                    f"evidence_type part [{ev.label()}] has no clear physical anchor. "
                    "Consider adding a physical evidence item at generation time."
                ),
                repair_hint=(
                    "At generation: instruct Claude to include at least 2 physical "
                    "evidence items alongside the part's evidence type."
                ),
            )]
        return []


class PartsRedHerringRule(Rule):
    code = "parts.red_herring.discoverable"
    severity = WARNING
    family = "PARTS"

    def check(self, context: PartsContext) -> List[Issue]:
        rh = context.by_type.get("red_herring")
        if not rh or _DISCOVERABLE_KW.search(rh.content):
            return []
        return [Issue(
            code="parts.red_herring.not_discoverable",
            severity=WARNING,
            family=self.family,
            message=(
                f"red_herring part [{rh.label()}] doesn't describe a "
                "scene-discoverable object or planted piece of evidence. "
                "Players may have nothing to find during investigation."
            ),
            repair_hint=(
                "Re-sample part_type='red_herring'; prefer parts describing "
                "planted objects, staged scenes, or forged documents."
            ),
        )]


class PartsMotiveSpecificityRule(Rule):
    code = "parts.motive.specificity"
    severity = INFO
    family = "PARTS"

    def check(self, context: PartsContext) -> List[Issue]:
        mv = context.by_type.get("motive")
        if not mv or _MOTIVE_SPECIFIC_KW.search(mv.content):
            return []
        return [Issue(
            code="parts.motive.too_vague",
            severity=INFO,
            family=self.family,
            message=(
                f"motive part [{mv.label()}] lacks concrete specificity "
                "(no financial, relational, or secret-exposure angle). "
                "Interrogation 'why did you do X' questions may be thin."
            ),
            repair_hint=(
                "Re-sample part_type='motive'; prefer parts with specific stakes "
                "(inheritance, blackmail, rivalry, discovery, exposure)."
            ),
        )]


PARTS_RULES: List[Rule] = [
    PartsCompletenessRule(),
    PartsWitnessFoundationRule(),
    PartsSceneEvidenceRule(),
    PartsRedHerringRule(),
    PartsMotiveSpecificityRule(),
]


# ============================================================================
# MYSTERY RULES — FAMILY 1: P1 CAUSAL CHAIN
# ============================================================================

class CrimeDefinedRule(Rule):
    code = "P1.C1.crime_defined"
    severity = BLOCKING
    family = "P1_CHAIN"

    def check(self, context: MysteryContext) -> List[Issue]:
        issues = []
        crime = context.crime
        if _is_empty(crime.get("what_happened")):
            issues.append(Issue(
                code="P1.C1.what_happened_missing", severity=BLOCKING, family=self.family,
                message="crime.what_happened is empty. The crime has no description.",
                repair_hint="Regenerate the 'crime' section only, guided by the crime_type part.",
            ))
        if _is_empty(crime.get("initial_discovery")):
            issues.append(Issue(
                code="P1.C1.discovery_missing", severity=WARNING, family=self.family,
                message="crime.initial_discovery is empty. Players have no hook to enter the scene.",
                repair_hint="Add a one-sentence discovery trigger (who found what, where, when).",
            ))
        return issues


class VictimRule(Rule):
    code = "P1.C2.victim"
    severity = BLOCKING
    family = "P1_CHAIN"

    def check(self, context: MysteryContext) -> List[Issue]:
        if not context.victims:
            return [Issue(
                code="P1.C2.no_victim", severity=BLOCKING, family=self.family,
                message="No character has role='victim'. P1 chain cannot proceed.",
                repair_hint="Add a victim character; re-generate characters section with victim role.",
            )]
        victim = context.victims[0]
        if _is_empty(victim.get("occupation")):
            return [Issue(
                code="P1.C2.victim_no_occupation", severity=WARNING, family=self.family,
                message=f"Victim '{victim.get('name', '?')}' has no occupation. "
                        "Hard to establish who had a reason to harm them.",
                repair_hint="Add occupation; derive from setting_element + suspect_archetype parts.",
            )]
        return []


class ClosedWorldRule(Rule):
    code = "P1.C3.closed_world"
    severity = WARNING
    family = "P1_CHAIN"

    def check(self, context: MysteryContext) -> List[Issue]:
        issues = []
        setting_desc = context.setting.get("description", "")
        if setting_desc and not _BOUNDED_KW.search(setting_desc):
            issues.append(Issue(
                code="P1.C3.open_world", severity=WARNING, family=self.family,
                message="Setting description doesn't convey a bounded/closed world. "
                        "Suspects could simply leave, undermining the mystery structure.",
                repair_hint="Add a sentence to setting.description explaining why no one can easily leave "
                            "(storm, distance, locked gates, professional obligation, etc.).",
            ))
        elif not setting_desc:
            issues.append(Issue(
                code="P1.C3.no_setting_description", severity=WARNING, family=self.family,
                message="setting.description is empty. Closed-world logic cannot be established.",
                repair_hint="Regenerate setting section; draw on setting_element part content.",
            ))

        for s in context.suspects:
            if _is_empty(s.get("occupation")) and _is_empty(s.get("secret")):
                issues.append(Issue(
                    code=f"P1.C3.suspect_no_presence.{s.get('name', '?')}",
                    severity=WARNING, family=self.family,
                    message=f"Suspect '{s.get('name', '?')}' has no occupation or secret. "
                            "Their presence in the closed world is ungrounded.",
                    repair_hint="Add occupation drawn from social_dynamic part; "
                                "or add a secret explaining why they were present.",
                    meta={"character_name": s.get("name", "?")},
                ))
        return issues


class CulpritMotiveRule(Rule):
    code = "P1.C4.culprit_motive"
    severity = BLOCKING
    family = "P1_CHAIN"

    def check(self, context: MysteryContext) -> List[Issue]:
        issues = []
        culprit_name = context.solution.get("culprit", "")
        culprit_char = next(
            (c for c in context.characters if c.get("name", "").lower() == culprit_name.lower()),
            None,
        )
        if not culprit_name:
            return [Issue(
                code="P1.C4.no_culprit", severity=BLOCKING, family=self.family,
                message="solution.culprit is empty. Mystery is unsolvable.",
                repair_hint="Regenerate solution section; ensure culprit maps to a suspect character.",
            )]
        if not culprit_char:
            return [Issue(
                code="P1.C4.culprit_not_in_characters", severity=BLOCKING, family=self.family,
                message=f"Culprit '{culprit_name}' does not match any character name. "
                        "Chain is broken; players can never identify them.",
                repair_hint="Fix name mismatch between solution.culprit and characters list.",
            )]
        if _is_empty(culprit_char.get("motive")):
            issues.append(Issue(
                code="P1.C4.culprit_no_motive", severity=BLOCKING, family=self.family,
                message=f"Culprit '{culprit_name}' has no motive in their character entry. "
                        "The core 'why' of the crime is absent.",
                repair_hint="Add motive derived from the motive part content.",
            ))
        if _is_empty(context.solution.get("motive")):
            issues.append(Issue(
                code="P1.C4.solution_no_motive", severity=BLOCKING, family=self.family,
                message="solution.motive is empty. The reveal has no explanation.",
                repair_hint="Populate solution.motive; must match culprit character's motive field.",
            ))
        return issues


class ResolutionRule(Rule):
    code = "P1.C5.resolution"
    severity = BLOCKING
    family = "P1_CHAIN"

    def check(self, context: MysteryContext) -> List[Issue]:
        issues = []
        key_evidence = context.solution.get("key_evidence", [])
        if not key_evidence:
            issues.append(Issue(
                code="P1.C5.no_key_evidence", severity=BLOCKING, family=self.family,
                message="solution.key_evidence is empty. Players have no logical path to the culprit.",
                repair_hint="List at least 2 evidence IDs that, together, prove the culprit's guilt.",
            ))
        else:
            dangling = [e for e in key_evidence if e not in context.evidence_ids]
            if dangling:
                issues.append(Issue(
                    code="P1.C5.dangling_key_evidence", severity=BLOCKING, family=self.family,
                    message=f"Key evidence {dangling} referenced in solution but not in evidence list. "
                            "Resolution refers to evidence players can never find.",
                    repair_hint="Ensure evidence IDs in solution.key_evidence exist in the evidence array.",
                ))
        if _is_empty(context.solution.get("how_to_deduce")):
            issues.append(Issue(
                code="P1.C5.no_deduction_path", severity=BLOCKING, family=self.family,
                message="solution.how_to_deduce is empty. No logical path to the solution exists.",
                repair_hint="Write a step-by-step deduction: 'First, E1 shows X; then E2 contradicts Y ...'",
            ))
        return issues


# ============================================================================
# MYSTERY RULES — FAMILY 2: WITNESS INTERROGATION FOUNDATION
# ============================================================================
# For each suspect or witness, verify they can answer three interrogation
# question types:
#   Q-ALIBI   "Where were you when X happened?"
#   Q-WHY     "Why were you here / why didn't you do X?"  (anchored in secret)
#   Q-MOTIVE  "Did you have a reason to harm the victim?" (suspects only)

class WitnessFoundationRule(Rule):
    code = "witness.foundation"
    severity = WARNING
    family = "WITNESS_FOUNDATION"

    def check(self, context: MysteryContext) -> List[Issue]:
        issues = []
        for char in context.interrogatable:
            name = char.get("name", "?")
            role = char.get("role", "?")
            missing: List[str] = []
            hints: List[str] = []

            alibi = char.get("alibi", "")
            if _is_empty(alibi):
                missing.append("alibi")
                hints.append("add specific alibi drawn from social_dynamic part (where were they, with whom)")
            elif _is_short(alibi, min_len=20):
                missing.append("alibi (too vague)")
                hints.append(f"expand alibi for '{name}' beyond '{alibi.strip()}'; needs location + witness or activity")

            secret = char.get("secret", "")
            if _is_empty(secret):
                missing.append("secret")
                hints.append(
                    "add a secret that anchors 'why were you there' / 'why didn't you act' questions; "
                    "derive from social_dynamic or red_herring part"
                )
            elif _is_short(secret, min_len=30):
                missing.append("secret (too thin)")
                hints.append(
                    f"expand secret for '{name}'; needs a concrete fact, "
                    "not just a label (e.g. not 'has a secret' but 'was meeting the victim privately to demand repayment')"
                )

            if role == "suspect":
                motive = char.get("motive", "")
                if _is_empty(motive):
                    missing.append("motive")
                    hints.append("add motive; re-sample part_type='motive' if current part is too vague")
                elif _is_short(motive, min_len=20):
                    missing.append("motive (too vague)")
                    hints.append(f"expand motive for '{name}': '{motive.strip()}' is too short to justify suspicion")

            if missing:
                issues.append(Issue(
                    code=f"witness.gap.{name}", severity=WARNING, family=self.family,
                    message=f"[{role}] {name}: missing {', '.join(missing)}",
                    repair_hint="; ".join(hints),
                    meta={"character_name": name, "role": role, "missing": missing},
                ))

        if context.victims:
            victim_name = context.victims[0].get("name", "")
            victim_secret = context.victims[0].get("secret", "")
            if _is_empty(victim_secret):
                issues.append(Issue(
                    code=f"witness.gap.{victim_name}", severity=WARNING, family=self.family,
                    message=f"[victim] {victim_name}: missing secret "
                            "(victim needs documented relationships or enemies)",
                    repair_hint=(
                        "Add victim secret explaining who resented them and why; "
                        "this provides the 'why were suspects near victim' foundation."
                    ),
                    meta={"character_name": victim_name, "role": "victim", "missing": ["secret"]},
                ))
        return issues


# ============================================================================
# MYSTERY RULES — FAMILY 3: SCENE INVESTIGATION DATA
# ============================================================================

class PhysicalEvidenceCountRule(Rule):
    code = "scene.physical_evidence.count"
    severity = WARNING
    family = "SCENE_INVESTIGATION"

    def check(self, context: MysteryContext) -> List[Issue]:
        physical_ev = _evidence_by_type(context.mystery, "physical")
        if len(physical_ev) >= 2:
            return []
        return [Issue(
            code="scene.physical_evidence.too_few",
            severity=BLOCKING if len(physical_ev) == 0 else WARNING,
            family=self.family,
            message=(
                f"Only {len(physical_ev)} physical evidence item(s). "
                "Players need at least 2 physical clues to investigate a scene "
                "without relying solely on character testimony."
            ),
            repair_hint=(
                "Re-sample part_type='evidence_type' (prefer physical/forensic) and "
                "regenerate the evidence section, OR add 1-2 physical items without "
                "full regeneration by patching the evidence array."
            ),
        )]


class RedHerringEvidenceRule(Rule):
    code = "scene.red_herring.evidence"
    severity = WARNING
    family = "SCENE_INVESTIGATION"

    def check(self, context: MysteryContext) -> List[Issue]:
        rh_evidence = _evidence_by_relevance(context.mystery, "red_herring")
        if not rh_evidence:
            return [Issue(
                code="scene.red_herring.missing", severity=WARNING, family=self.family,
                message="No red-herring evidence item. Scene investigation leads only to the truth; "
                        "no misdirection is possible, making the mystery too easy.",
                repair_hint=(
                    "Re-sample part_type='red_herring' and add 1 red-herring evidence item "
                    "with relevance='red_herring'. Prefer physical or documentary type "
                    "(something players can find, not just hear about)."
                ),
            )]
        rh_discoverable = [e for e in rh_evidence if e.get("type") in ("physical", "documentary", "circumstantial")]
        if not rh_discoverable:
            return [Issue(
                code="scene.red_herring.testimonial_only", severity=WARNING, family=self.family,
                message=(
                    "All red-herring evidence is testimonial. Scene investigation "
                    "will find nothing misleading; misdirection only comes from NPC dialogue."
                ),
                repair_hint=(
                    "Convert at least 1 red herring to type='physical' or 'documentary' "
                    "so players discover it during scene investigation, not only interrogation."
                ),
            )]
        return []


class EvidenceVarietyRule(Rule):
    code = "scene.evidence.variety"
    severity = WARNING
    family = "SCENE_INVESTIGATION"

    def check(self, context: MysteryContext) -> List[Issue]:
        if not context.evidence:
            return []
        types_present = {e.get("type") for e in context.evidence}
        if len(types_present) >= 2:
            return []
        return [Issue(
            code="scene.evidence.no_variety", severity=WARNING, family=self.family,
            message=(
                f"All evidence is of type '{next(iter(types_present), '?')}'. "
                "Scene investigation and interrogation will feel repetitive."
            ),
            repair_hint=(
                "Mix evidence types: add at least one documentary or testimonial item "
                "alongside physical evidence (and vice versa)."
            ),
        )]


class EvidenceDepthRule(Rule):
    code = "scene.evidence.depth"
    severity = INFO
    family = "SCENE_INVESTIGATION"

    def check(self, context: MysteryContext) -> List[Issue]:
        thin_evidence = [
            e for e in context.evidence
            if not _is_empty(e.get("description")) and _is_short(e.get("description", ""), min_len=40)
        ]
        if not thin_evidence:
            return []
        names = [e.get("name", e.get("id", "?")) for e in thin_evidence]
        return [Issue(
            code="scene.evidence.thin_descriptions", severity=INFO, family=self.family,
            message=(
                f"Evidence items with thin descriptions (< 40 chars): {names}. "
                "Players investigating the scene need enough detail to reason with."
            ),
            repair_hint=(
                "Expand descriptions to include: what the item is, where it was found, "
                "and what it initially suggests. No API call needed — patch in place."
            ),
        )]


class EvidenceVolumeRule(Rule):
    """
    Enough total evidence to make the 75% clue-sharing mechanic produce real
    strategic decisions rather than trivial ones. Explicitly multiplayer-only
    — a single-player mode would have no sharing mechanic to serve.
    """
    code = "scene.evidence.volume"
    severity = WARNING
    family = "SCENE_INVESTIGATION"
    applicability = Applicability.multiplayer_only()

    def check(self, context: MysteryContext) -> List[Issue]:
        total_ev = len(context.evidence)
        if total_ev >= 5:
            return []
        return [Issue(
            code="scene.evidence.too_few_total", severity=WARNING, family=self.family,
            message=(
                f"Only {total_ev} evidence items total. "
                "The 75% sharing mechanic needs at least 5 items to create "
                "meaningful strategic decisions about what to withhold."
            ),
            repair_hint=(
                "Add evidence items; use evidence_type and red_herring part content "
                "as seeds. No full regeneration needed — append to evidence array."
            ),
        )]


class CriticalEvidenceRedundancyRule(Rule):
    """
    Every pivotal (P1.C4-tier) conclusion needs enough independent supporting
    evidence to survive any single item being missed or, for CYM specifically,
    randomly excluded from a given player by the 75% clue-sharing roll.

    Threshold raised from the original 2-item minimum to 3, citing Robin D.
    Laws' GUMSHOE system ("never leave clues to chance" — core/pivotal facts
    should never depend on a single delivery path) and Justin Alexander's
    (Inverted) Three Clue Rule (any 3 clues a player ends up with should be
    sufficient to reach the correct conclusion). See
    TAXONOMY_EXPANSION_CANDIDATES.md, Priority 1, for the full citations —
    this is the single most directly actionable finding of that research pass.
    Explicitly multiplayer-only: a single reader missing one clue in a novel
    just re-reads; a player excluded from a clue by the 75% mechanic can't.
    """
    code = "scene.critical_evidence.redundancy"
    severity = BLOCKING
    family = "SCENE_INVESTIGATION"
    applicability = Applicability.multiplayer_only()

    MIN_CRITICAL = 3

    def check(self, context: MysteryContext) -> List[Issue]:
        critical_ev = _evidence_by_relevance(context.mystery, "critical")
        if not critical_ev:
            return [Issue(
                code="scene.critical_evidence.missing", severity=BLOCKING, family=self.family,
                message="No critical evidence items. Mystery has no solvable path.",
                repair_hint=(
                    "Add at least 3 critical evidence items that point to the culprit. "
                    "Derive from reveal_mechanic part: what is the mechanism that exposes guilt?"
                ),
            )]
        if len(critical_ev) < self.MIN_CRITICAL:
            return [Issue(
                code="scene.critical_evidence.insufficient_redundancy",
                severity=WARNING, family=self.family,
                message=(
                    f"Only {len(critical_ev)} critical evidence item(s) (minimum {self.MIN_CRITICAL}). "
                    "Under the 75% clue-sharing mechanic, any single player can miss any single "
                    "clue — fewer than 3 independent paths to the culprit risks a player being "
                    "structurally unable to solve the case through no fault of their own."
                ),
                repair_hint=(
                    f"Add critical evidence items until there are at least {self.MIN_CRITICAL} "
                    "independent paths to the culprit's identity."
                ),
            )]
        return []


# ============================================================================
# MYSTERY RULES — FAMILY 4: CRAFT INVARIANTS (new, July 2026 research pass)
# ============================================================================

class NaturalisticCausalityRule(Rule):
    """
    No supernatural/preternatural mechanism anywhere in the causal chain —
    not just at the reveal (P1.C5 already checks the reveal isn't "by luck");
    this scans the crime description and deduction path too. Authority:
    Ronald Knox, Commandment 2 (1929) — "The detective story must not rely on
    supernatural or preternatural agencies." Introduced at WARNING, not
    BLOCKING: new this pass, not yet validated against the live corpus for
    false positives (e.g. a red herring that's merely superstition-themed
    shouldn't trip this if the actual solution stays mundane — this check
    can't yet tell the difference and may need refinement).
    """
    code = "craft.naturalistic_causality"
    severity = WARNING
    family = "CRAFT_INVARIANTS"

    def check(self, context: MysteryContext) -> List[Issue]:
        haystacks = [
            context.crime.get("what_happened", ""),
            context.solution.get("how_to_deduce", ""),
            context.solution.get("motive", ""),
        ]
        hits = set()
        for text in haystacks:
            hits.update(m.group(0).lower() for m in _SUPERNATURAL_KW.finditer(text or ""))
        if not hits:
            return []
        return [Issue(
            code="craft.naturalistic_causality.supernatural_language",
            severity=WARNING, family=self.family,
            message=(
                f"Crime/solution text uses supernatural-leaning language ({', '.join(sorted(hits))}). "
                "Knox's Commandment 2: the causal chain must stay non-supernatural throughout, "
                "not just at the reveal. May be a false positive if this is themed red-herring "
                "language and the actual mechanism stays mundane — review before treating as blocking."
            ),
            repair_hint=(
                "Confirm the actual crime mechanism and deduction path are naturalistic; "
                "if the flagged language is only atmospheric/red-herring framing, no fix needed."
            ),
        )]


MYSTERY_RULES: List[Rule] = [
    CrimeDefinedRule(),
    VictimRule(),
    ClosedWorldRule(),
    CulpritMotiveRule(),
    ResolutionRule(),
    WitnessFoundationRule(),
    PhysicalEvidenceCountRule(),
    RedHerringEvidenceRule(),
    EvidenceVarietyRule(),
    EvidenceDepthRule(),
    EvidenceVolumeRule(),
    CriticalEvidenceRedundancyRule(),
    NaturalisticCausalityRule(),
]


# ============================================================================
# ENTRY POINT 1: Pre-generation — check sampled MysteryPart objects
# ============================================================================

def check_parts(parts) -> CoherenceReport:
    """
    Validate a list of sampled MysteryPart objects BEFORE calling Claude.

    Gaps detected here can be fixed by re-sampling from the part registry
    (zero API cost) rather than by regenerating the full mystery.

    Returns a CoherenceReport. If passed=False, at least one BLOCKING issue
    was found; the caller should re-sample the flagged part_types before
    proceeding.
    """
    context = PartsContext(parts)
    return RuleSet(PARTS_RULES).run(context)


# ============================================================================
# ENTRY POINT 2: Post-generation — check mystery JSON dict
# ============================================================================

def check_mystery(mystery: dict) -> CoherenceReport:
    """
    Validate a fully generated mystery dict against the P1 causal chain,
    witness interrogation foundation, scene investigation data, and craft
    invariants rule families.

    Returns a CoherenceReport. BLOCKING issues mean the mystery should not
    be presented to players without a repair pass.
    """
    context = MysteryContext(mystery)
    return RuleSet(MYSTERY_RULES).run(context)


# ============================================================================
# Convenience: format a report for Rich terminal output
# ============================================================================

def rich_panels(report: CoherenceReport):
    """
    Yield (content_str, title_str, border_color) tuples for Rich Panel rendering.
    Import and call only when Rich is available.
    """
    status_color = "green" if report.passed else "red"
    status_label = "PASS" if report.passed else "FAIL"

    yield (
        f"[{status_color}]{status_label}[/{status_color}]  "
        f"blocking={report.blocking_count}  warnings={report.warning_count}",
        "[bold]Coherence Check[/bold]",
        status_color,
    )

    def _fmt_issues(issues):
        lines = []
        for i in issues:
            icon = "[red]X[/red]" if i.is_blocking else "[yellow]![/yellow]" if i.severity == WARNING else "[dim]i[/dim]"
            lines.append(f"{icon} [bold]{i.code}[/bold]: {i.message}")
            if i.repair_hint:
                lines.append(f"   [dim]-> {i.repair_hint}[/dim]")
        return "\n".join(lines)

    family_titles = {
        "PARTS": ("[cyan]Parts (pre-generation)[/cyan]", "cyan"),
        "P1_CHAIN": ("[yellow]P1 Chain[/yellow]", "yellow"),
        "WITNESS_FOUNDATION": ("[magenta]Witness Interrogation Foundation[/magenta]", "magenta"),
        "SCENE_INVESTIGATION": ("[blue]Scene Investigation[/blue]", "blue"),
        "CRAFT_INVARIANTS": ("[green]Craft Invariants[/green]", "green"),
    }

    for family, (title, color) in family_titles.items():
        items = report.by_family(family)
        if items:
            yield _fmt_issues(items), title, color
