"""
Coherence Engine — shared framework for SocialGaming projects.

Two projects use this framework with different validation strategies:

  Choose Your Mystery (pre- and post-generation validation):
    check_parts() validates sampled MysteryPart objects before the Claude
    call (free, catches gaps early); check_mystery() validates the
    generated mystery dict against the P1 causal chain, witness
    interrogation foundation, and scene investigation data. Both are
    RuleSet subclasses — see coherence_validator.MysteryPartsRuleSet and
    coherence_validator.MysteryRuleSet.

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
