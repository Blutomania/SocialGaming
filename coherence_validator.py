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
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ─── Severity levels ─────────────────────────────────────────────────────────

BLOCKING = "blocking"   # must be fixed; mystery should not be output
WARNING  = "warning"    # degrades gameplay but doesn't make mystery unsolvable
INFO     = "info"       # cosmetic / enhancement suggestion


# ─── Result dataclasses ──────────────────────────────────────────────────────

@dataclass
class Issue:
    code: str            # e.g. "P1.culprit.no_motive"
    severity: str        # BLOCKING | WARNING | INFO
    message: str         # human-readable explanation
    repair_hint: str     # how to fix WITHOUT a new full-mystery API call


@dataclass
class WitnessGap:
    character_name: str
    role: str
    missing: List[str]   # e.g. ["alibi", "suspect_specific_motive"]
    repair_hint: str     # targeted fix hint


@dataclass
class CoherenceReport:
    """Full coherence report for one mystery or one part-set."""
    passed: bool

    # Check family results
    p1_issues:      List[Issue]       = field(default_factory=list)
    witness_gaps:   List[WitnessGap]  = field(default_factory=list)
    scene_issues:   List[Issue]       = field(default_factory=list)

    # Pre-generation part-level findings (only populated by check_parts)
    part_issues:    List[Issue]       = field(default_factory=list)

    @property
    def blocking_count(self) -> int:
        all_issues = self.p1_issues + self.scene_issues + self.part_issues
        return sum(1 for i in all_issues if i.severity == BLOCKING)

    @property
    def warning_count(self) -> int:
        all_issues = self.p1_issues + self.scene_issues + self.part_issues
        return sum(1 for i in all_issues if i.severity == WARNING)

    def all_repair_hints(self) -> List[str]:
        hints = []
        for i in self.p1_issues + self.scene_issues + self.part_issues:
            if i.repair_hint:
                hints.append(i.repair_hint)
        for g in self.witness_gaps:
            if g.repair_hint:
                hints.append(g.repair_hint)
        return hints

    def format_text(self, title: str = "COHERENCE REPORT") -> str:
        """Plain-text report for terminals without Rich."""
        lines = ["=" * 68, title, "=" * 68]

        status = "PASS" if self.passed else "FAIL"
        lines.append(f"Status: {status}   Blocking: {self.blocking_count}   Warnings: {self.warning_count}")
        lines.append("")

        def _section(heading, items):
            if not items:
                return
            lines.append(f"── {heading} " + "─" * max(0, 50 - len(heading)))
            for item in items:
                prefix = "X" if getattr(item, "severity", "") == BLOCKING else "!"
                lines.append(f"  [{prefix}] {item.message}")
                if item.repair_hint:
                    lines.append(f"      -> {item.repair_hint}")
            lines.append("")

        _section("PARTS (pre-generation)", self.part_issues)
        _section("P1 CHAIN", self.p1_issues)

        if self.witness_gaps:
            lines.append("── WITNESS INTERROGATION FOUNDATION " + "─" * 14)
            for g in self.witness_gaps:
                lines.append(f"  [{g.role}] {g.character_name}: missing {', '.join(g.missing)}")
                lines.append(f"      -> {g.repair_hint}")
            lines.append("")

        _section("SCENE INVESTIGATION", self.scene_issues)

        if self.all_repair_hints():
            lines.append("── REPAIR SUMMARY (registry re-samples; no new API call needed) ─")
            seen = set()
            for h in self.all_repair_hints():
                if h not in seen:
                    lines.append(f"  * {h}")
                    seen.add(h)
            lines.append("")

        lines.append("=" * 68)
        return "\n".join(lines)


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
    issues: List[Issue] = []

    by_type = {p.part_type: p for p in parts}

    # ── 1. Completeness — all 8 slots must be filled ─────────────────────
    REQUIRED_TYPES = [
        "crime_type", "setting_element", "motive", "suspect_archetype",
        "red_herring", "reveal_mechanic", "social_dynamic", "evidence_type",
    ]
    for pt in REQUIRED_TYPES:
        if pt not in by_type:
            issues.append(Issue(
                code=f"parts.missing.{pt}",
                severity=BLOCKING,
                message=f"No part sampled for part_type='{pt}'.",
                repair_hint=f"Re-sample: registry.get_candidates('{pt}', ...) and add one part.",
            ))

    # ── 2. Witness foundation — social_dynamic must hint at occupations / ─
    #       presence reasons, not just abstract power structures
    if "social_dynamic" in by_type:
        sd = by_type["social_dynamic"]
        presence_kw = re.compile(
            r"\b(occupation|role|position|rank|servant|guard|staff|employee|"
            r"resident|guest|invited|member|officer|scholar|merchant|trader|"
            r"physician|scribe|attendant|delegate|diplomat|crew|lodger)\b",
            re.IGNORECASE,
        )
        if not presence_kw.search(sd.content):
            issues.append(Issue(
                code="parts.social_dynamic.no_presence_context",
                severity=WARNING,
                message=(
                    f"social_dynamic part [{sd.label()}] doesn't name occupations or "
                    "roles that explain why people are in the closed world. "
                    "Witnesses may lack 'why were you there' foundation."
                ),
                repair_hint=(
                    "Re-sample part_type='social_dynamic'; prefer parts that describe "
                    "specific roles, occupations, or patronage relationships."
                ),
            ))

    # ── 3. Scene investigation — evidence_type must be scene-observable ──
    if "evidence_type" in by_type:
        ev = by_type["evidence_type"]
        has_physical = bool(_PHYSICAL_KW.search(ev.content))
        is_testimonial_only = bool(_TESTIMONIAL_ONLY_KW.search(ev.content)) and not has_physical
        if is_testimonial_only:
            issues.append(Issue(
                code="parts.evidence_type.testimonial_only",
                severity=WARNING,
                message=(
                    f"evidence_type part [{ev.label()}] describes only testimonial "
                    "evidence (confession/statement). Scene investigation will have "
                    "nothing physical to discover."
                ),
                repair_hint=(
                    "Re-sample part_type='evidence_type'; prefer parts with physical, "
                    "documentary, or forensic evidence (objects, records, traces)."
                ),
            ))
        elif not has_physical:
            issues.append(Issue(
                code="parts.evidence_type.no_physical_anchor",
                severity=INFO,
                message=(
                    f"evidence_type part [{ev.label()}] has no clear physical anchor. "
                    "Consider adding a physical evidence item at generation time."
                ),
                repair_hint=(
                    "At generation: instruct Claude to include at least 2 physical "
                    "evidence items alongside the part's evidence type."
                ),
            ))

    # ── 4. Red herring — must be something discoverable, not just ────────
    #       a behavioral suspicion
    if "red_herring" in by_type:
        rh = by_type["red_herring"]
        discoverable_kw = re.compile(
            r"\b(planted|staged|placed|left|found|object|item|evidence|"
            r"frame|false|forged|fabricated|disguised|misdirect|mislead|"
            r"apparent|look|seem|suggest)\b",
            re.IGNORECASE,
        )
        if not discoverable_kw.search(rh.content):
            issues.append(Issue(
                code="parts.red_herring.not_discoverable",
                severity=WARNING,
                message=(
                    f"red_herring part [{rh.label()}] doesn't describe a "
                    "scene-discoverable object or planted piece of evidence. "
                    "Players may have nothing to find during investigation."
                ),
                repair_hint=(
                    "Re-sample part_type='red_herring'; prefer parts describing "
                    "planted objects, staged scenes, or forged documents."
                ),
            ))

    # ── 5. Motive specificity — vague motives produce thin interrogations ─
    if "motive" in by_type:
        mv = by_type["motive"]
        if not _MOTIVE_SPECIFIC_KW.search(mv.content):
            issues.append(Issue(
                code="parts.motive.too_vague",
                severity=INFO,
                message=(
                    f"motive part [{mv.label()}] lacks concrete specificity "
                    "(no financial, relational, or secret-exposure angle). "
                    "Interrogation 'why did you do X' questions may be thin."
                ),
                repair_hint=(
                    "Re-sample part_type='motive'; prefer parts with specific stakes "
                    "(inheritance, blackmail, rivalry, discovery, exposure)."
                ),
            ))

    blocking = any(i.severity == BLOCKING for i in issues)
    return CoherenceReport(
        passed=not blocking,
        part_issues=issues,
    )


# ============================================================================
# ENTRY POINT 2: Post-generation — check mystery JSON dict
# ============================================================================

def check_mystery(mystery: dict) -> CoherenceReport:
    """
    Validate a fully generated mystery dict against three check families:

        1. P1 causal chain  (crime → victim → closed_world → culprit → resolution)
        2. Witness interrogation foundation  (alibi / motive / secret depth)
        3. Scene investigation data  (physical evidence, red herrings, variety)

    Returns a CoherenceReport. BLOCKING issues mean the mystery should not
    be presented to players without a repair pass.
    """
    p1_issues:    List[Issue]      = []
    witness_gaps: List[WitnessGap] = []
    scene_issues: List[Issue]      = []

    characters = mystery.get("characters", [])
    evidence   = mystery.get("evidence", [])
    crime      = mystery.get("crime", {})
    setting    = mystery.get("setting", {})
    solution   = mystery.get("solution", {})

    evidence_ids = {e.get("id") for e in evidence if e.get("id")}

    # =========================================================================
    # FAMILY 1 — P1 CAUSAL CHAIN
    # =========================================================================

    # C1 — Crime is defined
    if _is_empty(crime.get("what_happened")):
        p1_issues.append(Issue(
            code="P1.C1.what_happened_missing",
            severity=BLOCKING,
            message="crime.what_happened is empty. The crime has no description.",
            repair_hint="Regenerate the 'crime' section only, guided by the crime_type part.",
        ))
    if _is_empty(crime.get("initial_discovery")):
        p1_issues.append(Issue(
            code="P1.C1.discovery_missing",
            severity=WARNING,
            message="crime.initial_discovery is empty. Players have no hook to enter the scene.",
            repair_hint="Add a one-sentence discovery trigger (who found what, where, when).",
        ))

    # C2 — Victim exists and is connected
    victims = _char_by_role(mystery, "victim")
    if not victims:
        p1_issues.append(Issue(
            code="P1.C2.no_victim",
            severity=BLOCKING,
            message="No character has role='victim'. P1 chain cannot proceed.",
            repair_hint="Add a victim character; re-generate characters section with victim role.",
        ))
    else:
        victim = victims[0]
        if _is_empty(victim.get("occupation")):
            p1_issues.append(Issue(
                code="P1.C2.victim_no_occupation",
                severity=WARNING,
                message=f"Victim '{victim.get('name', '?')}' has no occupation. "
                        "Hard to establish who had a reason to harm them.",
                repair_hint="Add occupation; derive from setting_element + suspect_archetype parts.",
            ))

    # C3 — Closed world (setting describes bounded space)
    setting_desc = setting.get("description", "")
    bounded_kw = re.compile(
        r"\b(isolated|locked|sealed|closed|confined|bounded|remote|"
        r"no\s+escape|cut\s+off|trapped|stranded|island|ship|station|"
        r"manor|estate|monastery|colony|mine|bunker|fortress|compound)\b",
        re.IGNORECASE,
    )
    if setting_desc and not bounded_kw.search(setting_desc):
        p1_issues.append(Issue(
            code="P1.C3.open_world",
            severity=WARNING,
            message="Setting description doesn't convey a bounded/closed world. "
                    "Suspects could simply leave, undermining the mystery structure.",
            repair_hint="Add a sentence to setting.description explaining why no one can easily leave "
                        "(storm, distance, locked gates, professional obligation, etc.).",
        ))
    elif not setting_desc:
        p1_issues.append(Issue(
            code="P1.C3.no_setting_description",
            severity=WARNING,
            message="setting.description is empty. Closed-world logic cannot be established.",
            repair_hint="Regenerate setting section; draw on setting_element part content.",
        ))

    # Ensure every suspect has a plausible reason to be in the closed world
    suspects = _char_by_role(mystery, "suspect")
    for s in suspects:
        if _is_empty(s.get("occupation")) and _is_empty(s.get("secret")):
            p1_issues.append(Issue(
                code=f"P1.C3.suspect_no_presence.{s.get('name','?')}",
                severity=WARNING,
                message=f"Suspect '{s.get('name','?')}' has no occupation or secret. "
                        "Their presence in the closed world is ungrounded.",
                repair_hint="Add occupation drawn from social_dynamic part; "
                            "or add a secret explaining why they were present.",
            ))

    # C4 — Culprit and motive
    culprit_name = solution.get("culprit", "")
    culprit_char = next(
        (c for c in characters if c.get("name", "").lower() == culprit_name.lower()),
        None,
    )
    if not culprit_name:
        p1_issues.append(Issue(
            code="P1.C4.no_culprit",
            severity=BLOCKING,
            message="solution.culprit is empty. Mystery is unsolvable.",
            repair_hint="Regenerate solution section; ensure culprit maps to a suspect character.",
        ))
    elif not culprit_char:
        p1_issues.append(Issue(
            code="P1.C4.culprit_not_in_characters",
            severity=BLOCKING,
            message=f"Culprit '{culprit_name}' does not match any character name. "
                    "Chain is broken; players can never identify them.",
            repair_hint="Fix name mismatch between solution.culprit and characters list.",
        ))
    else:
        if _is_empty(culprit_char.get("motive")):
            p1_issues.append(Issue(
                code="P1.C4.culprit_no_motive",
                severity=BLOCKING,
                message=f"Culprit '{culprit_name}' has no motive in their character entry. "
                        "The core 'why' of the crime is absent.",
                repair_hint="Add motive derived from the motive part content.",
            ))
        if _is_empty(solution.get("motive")):
            p1_issues.append(Issue(
                code="P1.C4.solution_no_motive",
                severity=BLOCKING,
                message="solution.motive is empty. The reveal has no explanation.",
                repair_hint="Populate solution.motive; must match culprit character's motive field.",
            ))

    # C5 — Resolution (key evidence exists and is reachable)
    key_evidence = solution.get("key_evidence", [])
    if not key_evidence:
        p1_issues.append(Issue(
            code="P1.C5.no_key_evidence",
            severity=BLOCKING,
            message="solution.key_evidence is empty. Players have no logical path to the culprit.",
            repair_hint="List at least 2 evidence IDs that, together, prove the culprit's guilt.",
        ))
    else:
        dangling = [e for e in key_evidence if e not in evidence_ids]
        if dangling:
            p1_issues.append(Issue(
                code="P1.C5.dangling_key_evidence",
                severity=BLOCKING,
                message=f"Key evidence {dangling} referenced in solution but not in evidence list. "
                        "Resolution refers to evidence players can never find.",
                repair_hint="Ensure evidence IDs in solution.key_evidence exist in the evidence array.",
            ))

    if _is_empty(solution.get("how_to_deduce")):
        p1_issues.append(Issue(
            code="P1.C5.no_deduction_path",
            severity=BLOCKING,
            message="solution.how_to_deduce is empty. No logical path to the solution exists.",
            repair_hint="Write a step-by-step deduction: 'First, E1 shows X; then E2 contradicts Y ...'",
        ))

    # =========================================================================
    # FAMILY 2 — WITNESS INTERROGATION FOUNDATION
    # =========================================================================
    # For each suspect or witness, verify they can answer three interrogation
    # question types:
    #   Q-ALIBI   "Where were you when X happened?"
    #   Q-WHY     "Why were you here / why didn't you do X?"  (anchored in secret)
    #   Q-MOTIVE  "Did you have a reason to harm the victim?" (suspects only)

    interrogatable = [c for c in characters if c.get("role") in ("suspect", "witness")]

    for char in interrogatable:
        name = char.get("name", "?")
        role = char.get("role", "?")
        missing = []
        hints = []

        # Q-ALIBI
        alibi = char.get("alibi", "")
        if _is_empty(alibi):
            missing.append("alibi")
            hints.append("add specific alibi drawn from social_dynamic part (where were they, with whom)")
        elif _is_short(alibi, min_len=20):
            missing.append("alibi (too vague)")
            hints.append(f"expand alibi for '{name}' beyond '{alibi.strip()}'; needs location + witness or activity")

        # Q-WHY (secret provides the material for "why were you there / why didn't you do X")
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

        # Q-MOTIVE (suspects only)
        if role == "suspect":
            motive = char.get("motive", "")
            if _is_empty(motive):
                missing.append("motive")
                hints.append(
                    "add motive; re-sample part_type='motive' if current part is too vague"
                )
            elif _is_short(motive, min_len=20):
                missing.append("motive (too vague)")
                hints.append(
                    f"expand motive for '{name}': '{motive.strip()}' is too short to justify suspicion"
                )

        if missing:
            witness_gaps.append(WitnessGap(
                character_name=name,
                role=role,
                missing=missing,
                repair_hint="; ".join(hints),
            ))

    # Victim's enemies / connections — needed so suspects have credible "why were you there"
    if victims:
        victim_name = victims[0].get("name", "")
        victim_secret = victims[0].get("secret", "")
        if _is_empty(victim_secret):
            witness_gaps.append(WitnessGap(
                character_name=victim_name,
                role="victim",
                missing=["secret (victim needs documented relationships or enemies)"],
                repair_hint=(
                    "Add victim secret explaining who resented them and why; "
                    "this provides the 'why were suspects near victim' foundation."
                ),
            ))

    # =========================================================================
    # FAMILY 3 — SCENE INVESTIGATION DATA
    # =========================================================================

    # 3a. Physical evidence count — minimum 2 for meaningful scene investigation
    physical_ev = _evidence_by_type(mystery, "physical")
    if len(physical_ev) < 2:
        scene_issues.append(Issue(
            code="scene.physical_evidence.too_few",
            severity=BLOCKING if len(physical_ev) == 0 else WARNING,
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
        ))

    # 3b. Red-herring evidence — minimum 1 scene-discoverable mislead
    rh_evidence = _evidence_by_relevance(mystery, "red_herring")
    if not rh_evidence:
        scene_issues.append(Issue(
            code="scene.red_herring.missing",
            severity=WARNING,
            message="No red-herring evidence item. Scene investigation leads only to the truth; "
                    "no misdirection is possible, making the mystery too easy.",
            repair_hint=(
                "Re-sample part_type='red_herring' and add 1 red-herring evidence item "
                "with relevance='red_herring'. Prefer physical or documentary type "
                "(something players can find, not just hear about)."
            ),
        ))
    else:
        # Check that at least 1 red herring is physical/documentary (discoverable, not just hearsay)
        rh_discoverable = [
            e for e in rh_evidence
            if e.get("type") in ("physical", "documentary", "circumstantial")
        ]
        if not rh_discoverable:
            scene_issues.append(Issue(
                code="scene.red_herring.testimonial_only",
                severity=WARNING,
                message=(
                    "All red-herring evidence is testimonial. Scene investigation "
                    "will find nothing misleading; misdirection only comes from NPC dialogue."
                ),
                repair_hint=(
                    "Convert at least 1 red herring to type='physical' or 'documentary' "
                    "so players discover it during scene investigation, not only interrogation."
                ),
            ))

    # 3c. Evidence variety — not all the same type
    if evidence:
        types_present = {e.get("type") for e in evidence}
        if len(types_present) < 2:
            scene_issues.append(Issue(
                code="scene.evidence.no_variety",
                severity=WARNING,
                message=(
                    f"All evidence is of type '{next(iter(types_present), '?')}'. "
                    "Scene investigation and interrogation will feel repetitive."
                ),
                repair_hint=(
                    "Mix evidence types: add at least one documentary or testimonial item "
                    "alongside physical evidence (and vice versa)."
                ),
            ))

    # 3d. Evidence description depth — each item must be specific enough to be a real clue
    thin_evidence = [
        e for e in evidence
        if not _is_empty(e.get("description")) and _is_short(e.get("description", ""), min_len=40)
    ]
    if thin_evidence:
        names = [e.get("name", e.get("id", "?")) for e in thin_evidence]
        scene_issues.append(Issue(
            code="scene.evidence.thin_descriptions",
            severity=INFO,
            message=(
                f"Evidence items with thin descriptions (< 40 chars): {names}. "
                "Players investigating the scene need enough detail to reason with."
            ),
            repair_hint=(
                "Expand descriptions to include: what the item is, where it was found, "
                "and what it initially suggests. No API call needed — patch in place."
            ),
        ))

    # 3e. Total evidence volume — enough for 75% sharing mechanic
    total_ev = len(evidence)
    if total_ev < 5:
        scene_issues.append(Issue(
            code="scene.evidence.too_few_total",
            severity=WARNING,
            message=(
                f"Only {total_ev} evidence items total. "
                "The 75% sharing mechanic needs at least 5 items to create "
                "meaningful strategic decisions about what to withhold."
            ),
            repair_hint=(
                "Add evidence items; use evidence_type and red_herring part content "
                "as seeds. No full regeneration needed — append to evidence array."
            ),
        ))

    # 3f. At least one critical evidence item links to culprit
    critical_ev = _evidence_by_relevance(mystery, "critical")
    if not critical_ev:
        scene_issues.append(Issue(
            code="scene.critical_evidence.missing",
            severity=BLOCKING,
            message="No critical evidence items. Mystery has no solvable path.",
            repair_hint=(
                "Add at least 2 critical evidence items that point to the culprit. "
                "Derive from reveal_mechanic part: what is the mechanism that exposes guilt?"
            ),
        ))
    elif len(critical_ev) < 2:
        scene_issues.append(Issue(
            code="scene.critical_evidence.only_one",
            severity=WARNING,
            message="Only 1 critical evidence item. One clue is fragile — if missed, mystery is unsolvable.",
            repair_hint="Add a second critical evidence item as a backup deduction path.",
        ))

    # ── Compute overall pass/fail ─────────────────────────────────────────
    all_issues = p1_issues + scene_issues
    blocking = any(i.severity == BLOCKING for i in all_issues)
    # Witness gaps don't block by themselves (they degrade gameplay, not solvability)

    return CoherenceReport(
        passed=not blocking,
        p1_issues=p1_issues,
        witness_gaps=witness_gaps,
        scene_issues=scene_issues,
    )


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
            icon = "[red]X[/red]" if i.severity == BLOCKING else "[yellow]![/yellow]"
            lines.append(f"{icon} [bold]{i.code}[/bold]: {i.message}")
            if i.repair_hint:
                lines.append(f"   [dim]-> {i.repair_hint}[/dim]")
        return "\n".join(lines)

    if report.part_issues:
        yield _fmt_issues(report.part_issues), "[cyan]Parts (pre-generation)[/cyan]", "cyan"

    if report.p1_issues:
        yield _fmt_issues(report.p1_issues), "[yellow]P1 Chain[/yellow]", "yellow"

    if report.witness_gaps:
        lines = []
        for g in report.witness_gaps:
            lines.append(
                f"[bold]{g.character_name}[/bold] [{g.role}]: "
                f"missing {', '.join(g.missing)}"
            )
            lines.append(f"   [dim]-> {g.repair_hint}[/dim]")
        yield "\n".join(lines), "[magenta]Witness Interrogation Foundation[/magenta]", "magenta"

    if report.scene_issues:
        yield _fmt_issues(report.scene_issues), "[blue]Scene Investigation[/blue]", "blue"
