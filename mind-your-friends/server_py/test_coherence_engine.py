"""Proves MYF's coherence rules are genuinely wired to the shared engine.
Zero API cost. Run: python3 test_coherence_engine.py

WHY THIS EXISTS. "The Coherence Engine is a shared pillar across every title"
has been claimed in this repo before it was true — MYF CLAUDE.md carries a
correction saying exactly that about an earlier version of the claim. So the
claim gets a test rather than a sentence.

Two halves, and the second is the one that matters:

  1. The plumbing: QuestionRuleSet really subclasses coherence.engine.RuleSet
     and really returns coherence.engine.CoherenceReport — the SAME classes
     CYM's rule sets use, not lookalikes with the same field names.

  2. The behaviour: rewiring changed no rule. A refactor that quietly altered
     what passes and what blocks would be invisible in the plumbing checks and
     would only surface as bad questions at a real table.
"""

import sys

import coherence_rules
from coherence_rules import QuestionRuleSet, validate_question
from coherence.engine import BLOCKING, WARNING, INFO, CoherenceReport, Issue, RuleSet

failures = []


def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        failures.append(msg)


PHRASE = {"answerFormat": "phrase"}


def report(question, constraints=PHRASE):
    return validate_question(question, constraints)


print("--- the plumbing: one engine, not two lookalikes ---")
check(issubclass(QuestionRuleSet, RuleSet), "QuestionRuleSet subclasses coherence.engine.RuleSet")
check(RuleSet.__module__ == "coherence.engine", "and that RuleSet is the shared one, not a local copy")

r = report({"question": "Which planet spins backwards?", "answer": "Venus indeed"})
check(type(r) is CoherenceReport, "validate_question returns coherence.engine.CoherenceReport")
check(type(r).__module__ == "coherence.engine", "and that CoherenceReport is the shared one")
check(
    coherence_rules.BLOCKING is BLOCKING
    and coherence_rules.WARNING is WARNING
    and coherence_rules.INFO is INFO,
    "the severity vocabulary is re-exported from the engine, not redeclared",
)

print("\n--- the same engine CYM uses ---")
# CYM's rule sets live at the monorepo root, which coherence_rules put on
# sys.path. If the two titles were on separate copies of the framework, these
# identity checks are what would catch it.
import coherence_validator  # noqa: E402

check(
    issubclass(coherence_validator.MysteryRuleSet, RuleSet),
    "CYM's MysteryRuleSet subclasses the same RuleSet class",
)
check(
    issubclass(coherence_validator.CoherenceReport, CoherenceReport),
    "CYM's report extends the same CoherenceReport base",
)
check(
    coherence_validator.Issue is Issue,
    "both titles raise the identical Issue class",
)

print("\n--- the wrapper and the rule set agree ---")
q = {"question": "Q?", "answer": "a two"}
direct = QuestionRuleSet().run({"question": q, "constraints": PHRASE})
wrapped = validate_question(q, PHRASE)
check(direct.passed == wrapped.passed, "same passed")
check(
    [(i.code, i.severity) for i in direct.issues] == [(i.code, i.severity) for i in wrapped.issues],
    "same issues, in the same order",
)

print("\n--- the rules themselves are unchanged by the rewire ---")
codes = lambda rep: [i.code for i in rep.issues]

r = report({"question": "Which planet spins backwards?", "answer": "Venus the planet"})
check(r.passed and not codes(r), "a well-formed phrase answer passes clean")

r = report({"question": "Q?", "answer": ""})
check(not r.passed and codes(r) == ["question.no_answer"], "an empty answer blocks, and stops there")

r = report({"question": "", "answer": "Venus and friends"})
check(not r.passed and "question.no_question_text" in codes(r), "empty question text blocks")

r = report({"question": "Q?", "answer": "two words"}, {"answerFormat": "single-word"})
check(
    r.passed and "question.answer_too_long.one_word" in codes(r),
    "One Word Only: a 2-word answer warns but does not block",
)

r = report({"question": "Q?", "answer": "one two three"}, {"answerFormat": "one-or-two-words"})
check(
    r.passed and "question.answer_too_long.boxed_in" in codes(r),
    "Boxed In: a 3-word answer warns but does not block",
)

r = report({"question": "Q?", "answer": "Venus"})
check(
    r.passed and "question.answer_too_short" in codes(r),
    "a 1-word answer to a phrase question is INFO only",
)

LINEUP = {"answerFormat": "phrase", "lineupBased": True}
good = {"options": [{"id": "a"}, {"id": "b"}], "correctOptionId": "a"}
check(report({"question": "Q?", "answer": "A", "lineup": good}, LINEUP).passed, "a valid lineup passes")

for bad, code, why in [
    ({"options": [{"id": "a"}], "correctOptionId": "a"}, "lineup.invalid_options", "one option is not a choice"),
    ({"options": [{"id": "a"}, {"id": "a"}], "correctOptionId": "a"}, "lineup.duplicate_option_ids", "duplicate ids"),
    ({"options": [{"id": "a"}, {"id": "b"}], "correctOptionId": "z"}, "lineup.missing_correct_option", "unreachable answer"),
]:
    r = report({"question": "Q?", "answer": "A", "lineup": bad}, LINEUP)
    check(not r.passed and code in codes(r), f"lineup blocks on {why}")

print("\n--- the report carries what the engine promises ---")
r = report({"question": "Q?", "answer": "two words"}, {"answerFormat": "single-word"})
check(r.warning_count == 1 and r.blocking_count == 0, "blocking_count / warning_count are populated")
check(r.metadata.get("word_count") == 2, "metadata carries the word count")
check("MYF" in r.format_text("MYF") and "one_word" in r.format_text("MYF"), "format_text renders the issues")

print("\n=== ALL PASSED ===" if not failures else f"\n=== {len(failures)} FAILED ===")
sys.exit(1 if failures else 0)
