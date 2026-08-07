"""
Coherence Engine — shared framework for SocialGaming projects.

Two projects use this framework with different validation strategies:

  Choose Your Mystery (post-generation validation):
    Generate a mystery artifact → validate it against structural rules
    (P1 causal chain, witness depth, scene investigation).

  Mind Your Friends (pre-generation constraint assembly):
    Collect turn context (round rule, wager, card) → assemble constraints →
    feed to question generator → validate output matches constraints.

Both share the same vocabulary: severity levels, Issue dataclass, and
CoherenceReport. Each project defines its own RuleSet.
"""

from coherence.engine import (
    BLOCKING,
    WARNING,
    INFO,
    Issue,
    CoherenceReport,
    RuleSet,
)
