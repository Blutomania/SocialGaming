"""
coherence.engine — domain-agnostic coherence framework.

Provides the shared vocabulary (Issue, CoherenceReport, severity levels) and
the RuleSet base class that each project extends with domain-specific checks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# --- Severity levels ---

BLOCKING = "blocking"
WARNING = "warning"
INFO = "info"


# --- Core dataclasses ---

@dataclass
class Issue:
    code: str
    severity: str
    message: str
    repair_hint: str = ""

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

    def format_text(self, title: str = "COHERENCE REPORT") -> str:
        lines = ["=" * 68, title, "=" * 68]
        status = "PASS" if self.passed else "FAIL"
        lines.append(f"Status: {status}   Blocking: {self.blocking_count}   Warnings: {self.warning_count}")
        lines.append("")

        for issue in self.issues:
            prefix = "X" if issue.is_blocking else "!" if issue.severity == WARNING else "i"
            lines.append(f"  [{prefix}] {issue.code}: {issue.message}")
            if issue.repair_hint:
                lines.append(f"      -> {issue.repair_hint}")

        lines.append("=" * 68)
        return "\n".join(lines)


# --- RuleSet base class ---

class RuleSet(ABC):
    """
    A domain-specific set of coherence checks.

    Subclass this for each project. The engine calls run() with whatever
    context the domain needs, and gets back a CoherenceReport.
    """

    @abstractmethod
    def run(self, context: Any) -> CoherenceReport:
        ...
