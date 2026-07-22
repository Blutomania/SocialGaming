"""
coherence.engine — domain-agnostic coherence framework, shared between
Choose Your Mystery (CYM) and Mind Your Friends (MYF).

A "coherence check" is a deterministic, zero-API-call verification that
generated content actually satisfies a declared structural contract —
distinct from RAG/retrieval, which only grounds what the LLM is *given*,
not what it *produces*. See TAXONOMY_EXPANSION_CANDIDATES.md for the
research this shape is built to support.

Building blocks:
    Issue            — one finding (a rule fired and has something to report)
    CoherenceReport   — the aggregated result of running a RuleSet
    Applicability     — governs whether a Rule fires at all for a given context
    Rule              — one named, composable check
    RuleSet           — a domain's ordered collection of Rules

A domain (CYM's coherence_validator.py; MYF's lib/coherence.js, once wired)
defines its own context object, its own Rule subclasses, and calls
RuleSet(rules).run(context) to get a CoherenceReport back.

Applicability is deliberately a separate axis from severity:
    - severity   answers "how bad is it if this rule is violated"
    - applicability answers "does this rule even apply to this content"
A rule can be narrowly applicable (only fires for one subgenre) and still
be BLOCKING within that scope — applicability doesn't imply "lesser."
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional


# ─── Severity levels ─────────────────────────────────────────────────────────
# How bad is it if a rule's check fails.

BLOCKING = "blocking"   # must be fixed; output should not be used as-is
WARNING  = "warning"    # degrades quality but doesn't break correctness
INFO     = "info"       # cosmetic / enhancement suggestion


# ─── Issue & report ──────────────────────────────────────────────────────────

@dataclass
class Issue:
    code: str
    severity: str
    message: str
    repair_hint: str = ""
    family: str = ""                                     # display grouping label, e.g. "P1_CHAIN"
    meta: Dict[str, Any] = field(default_factory=dict)    # structured extras (character_name, role, ...)

    @property
    def is_blocking(self) -> bool:
        return self.severity == BLOCKING


@dataclass
class CoherenceReport:
    passed: bool
    issues: List[Issue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def blocking_count(self) -> int:
        return sum(1 for i in self.issues if i.is_blocking)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == WARNING)

    def by_family(self, family: str) -> List[Issue]:
        return [i for i in self.issues if i.family == family]

    def all_repair_hints(self) -> List[str]:
        seen, out = set(), []
        for i in self.issues:
            if i.repair_hint and i.repair_hint not in seen:
                out.append(i.repair_hint)
                seen.add(i.repair_hint)
        return out

    def format_text(self, title: str = "COHERENCE REPORT") -> str:
        """Plain-text report for terminals without Rich."""
        lines = ["=" * 68, title, "=" * 68]
        lines.append(
            f"Status: {'PASS' if self.passed else 'FAIL'}   "
            f"Blocking: {self.blocking_count}   Warnings: {self.warning_count}"
        )
        lines.append("")

        families: List[str] = []
        for i in self.issues:
            if i.family not in families:
                families.append(i.family)

        for fam in families:
            items = self.by_family(fam)
            heading = fam or "GENERAL"
            lines.append(f"── {heading} " + "─" * max(0, 50 - len(heading)))
            for i in items:
                prefix = "X" if i.is_blocking else "!" if i.severity == WARNING else "i"
                lines.append(f"  [{prefix}] {i.code}: {i.message}")
                if i.repair_hint:
                    lines.append(f"      -> {i.repair_hint}")
            lines.append("")

        if self.all_repair_hints():
            lines.append("── REPAIR SUMMARY (no new API call needed) " + "─" * 10)
            for h in self.all_repair_hints():
                lines.append(f"  * {h}")
            lines.append("")

        lines.append("=" * 68)
        return "\n".join(lines)


# ─── Applicability ───────────────────────────────────────────────────────────
# Does this Rule even fire for this context? Orthogonal to severity — see
# module docstring. A context is expected to expose (as attributes, or via
# getattr with a default):
#   subgenre_contract: str | None   — e.g. "puzzle", "hardboiled", "procedural",
#                                     "inverted_suspense", or None if undeclared
#   is_multiplayer: bool            — True for live, session-based, multi-agent
#                                     experiences (CYM's room-code play, MYF)

@dataclass(frozen=True)
class Applicability:
    universal: bool = True
    subgenres: Optional[FrozenSet[str]] = None
    requires_multiplayer: bool = False

    def matches(self, context: Any) -> bool:
        if self.requires_multiplayer and not getattr(context, "is_multiplayer", False):
            return False
        if self.subgenres is not None:
            if getattr(context, "subgenre_contract", None) not in self.subgenres:
                return False
        return True

    @staticmethod
    def for_subgenres(*subgenres: str) -> "Applicability":
        return Applicability(universal=False, subgenres=frozenset(subgenres))

    @staticmethod
    def multiplayer_only() -> "Applicability":
        return Applicability(universal=False, requires_multiplayer=True)


# ─── Rule & RuleSet ──────────────────────────────────────────────────────────

class Rule(ABC):
    """One named, composable coherence check."""

    code: str = ""
    severity: str = WARNING
    family: str = ""
    applicability: Applicability = Applicability()  # default: universal

    @abstractmethod
    def check(self, context: Any) -> List[Issue]:
        """Return zero or more Issues. Only called if applicability.matches(context)."""
        ...


class RuleSet:
    """An ordered collection of Rules for one domain (CYM, MYF, ...)."""

    def __init__(self, rules: List[Rule]):
        self.rules = rules

    def run(self, context: Any) -> CoherenceReport:
        issues: List[Issue] = []
        for rule in self.rules:
            if rule.applicability.matches(context):
                issues.extend(rule.check(context))
        return CoherenceReport(passed=not any(i.is_blocking for i in issues), issues=issues)
