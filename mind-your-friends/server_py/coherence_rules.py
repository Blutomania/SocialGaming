# MYF's coherence rules — the title's instance of the shared Coherence Engine,
# ported from lib/coherence.js.
#
# WIRED to coherence.engine as of August 20 2026 (MYF CLAUDE.md item 8). The
# shared framework at the monorepo root now genuinely has two consumers:
# CYM's coherence_validator.py (MysteryPartsRuleSet / MysteryRuleSet) and this
# file's QuestionRuleSet. Same Issue shape, same severity vocabulary, same
# CoherenceReport, same RuleSet.run(context) contract.
#
# WHY THIS FILE IS NO LONGER CALLED coherence.py. It could not be. A top-level
# module named `coherence` and a package named `coherence` cannot both sit on
# sys.path: whichever comes first wins, and since server_py/ is always first,
# `from coherence.engine import ...` resolved to THIS file and died with
# "'coherence' is not a package". The rename is what made the wiring possible
# at all, and the new name is the more accurate one anyway — this assembles
# constraints and validates questions; the engine is the shared thing.
# It sits parallel to CYM's coherence_validator.py rather than duplicating it.
#
# Two-pass constraint assembly (unchanged, a straight semantic port of the JS):
#   1. round_constraints(round_rule) — runs once at round start.
#   2. turn_constraints(round_ctx, category, wager, resolved_card) — runs
#      per turn after card resolution, layers on turn-specific modifiers.
#
# Post-generation:
#   3. validate_question(question, constraints) — confirms the generated
#      Q&A satisfies the assembled constraints. Backed by QuestionRuleSet.

import random
import sys
from pathlib import Path

from cards import CARDS, pick_random_language_register
from constants import BASE_TIMER_SECONDS, WAGER_TIERS, wager_tier_index

# The shared engine lives at the monorepo root, two levels up. APPENDED rather
# than inserted: server_py's own modules must keep winning any name collision,
# and this only needs to add what the root uniquely provides.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))

from coherence.engine import (  # noqa: E402
    BLOCKING,
    WARNING,
    INFO,
    CoherenceReport,
    Issue,
    RuleSet,
)

_DIFFICULTY_PROMPT = {
    "trivial": "Generate a very easy question — almost everyone should get this one.",
    "easy": "Generate an easy question that most people would know the answer to.",
    "medium": "Generate a moderately challenging question — not trivial, but fair.",
    "hard": "Generate a difficult question that requires specific knowledge.",
    "brutal": "Generate a genuinely hard question — most of the room should miss it.",
}

_FORMAT_CARD_IDS = {"boxedIn", "languageBarrier"}


# One difficulty per rung of the wager ladder, so the stake the room watched
# somebody choose is the stake the question is actually written to. The old
# mapping normalised a continuous range into three buckets, which meant two
# visibly different wagers routinely produced identically-pitched questions.
_DIFFICULTY_BY_TIER = ["trivial", "easy", "medium", "hard", "brutal"]

# The fact bank only knows three difficulties (they come from the research
# prompt in claude_client.py), so the five-rung ladder maps down for filtering.
# Deliberately not widened to five: that would mean re-generating every cached
# fact bank to add two values the bank has never produced.
_BANK_DIFFICULTY = {
    "trivial": "easy",
    "easy": "easy",
    "medium": "medium",
    "hard": "hard",
    "brutal": "hard",
}


def _wager_to_difficulty(wager: int) -> str:
    return _DIFFICULTY_BY_TIER[wager_tier_index(wager)]


def _bank_difficulty(difficulty: str) -> str:
    return _BANK_DIFFICULTY.get(difficulty, difficulty)


def round_constraints(round_rule: dict) -> dict:
    return {
        "roundRuleId": round_rule["id"],
        "roundRuleName": round_rule["name"],
        "timerSeconds": round_rule.get("timerSeconds", BASE_TIMER_SECONDS),
        "wagerMultiplier": round_rule.get("wagerMultiplier", 1),
        "stealOnWrong": round_rule.get("stealOnWrong", False),
        "lineupBased": round_rule.get("lineupBased", False),
        "promptInstructions": (
            [round_rule["promptInstruction"]] if round_rule.get("promptInstruction") else []
        ),
        "answerFormat": (
            "single-word" if round_rule["id"] == "oneWordOnly"
            else "lineup" if round_rule.get("lineupBased")
            else "phrase"
        ),
    }


def turn_constraints(round_ctx: dict, *, category: str, wager: int, resolved_card: str | None) -> dict:
    difficulty = _wager_to_difficulty(wager)
    effective_wager = round(wager * round_ctx["wagerMultiplier"])

    prompt_instructions = [
        f"Category: {category}",
        _DIFFICULTY_PROMPT[difficulty],
        *round_ctx["promptInstructions"],
    ]

    answer_format = round_ctx["answerFormat"]
    timer_seconds = round_ctx["timerSeconds"]
    card_effects: dict = {}

    if resolved_card:
        card = CARDS.get(resolved_card)
        if not card:
            raise ValueError(f"Unknown card: {resolved_card}")

        if card["id"] == "boxedIn":
            answer_format = "one-or-two-words"
            prompt_instructions.append(
                "The correct answer MUST be exactly one or two words. Design the "
                "question so that a short answer is natural."
            )

        if card["id"] == "languageBarrier":
            register = pick_random_language_register()
            prompt_instructions.append(
                f"Phrase the entire question in this register: {register}. The "
                "answer itself should still be straightforward."
            )
            card_effects["languageRegister"] = register

        if card["id"] == "spotlight":
            timer_seconds = 5
            card_effects["spotlight"] = True

        if card["id"] == "fiftyOff":
            card_effects["wagerHalved"] = True

        if card["id"] == "heckle":
            card_effects["heckle"] = True

        card_effects["cardId"] = card["id"]
        card_effects["cardName"] = card["name"]

    return {
        "category": category,
        "difficulty": difficulty,
        "difficultyTier": wager_tier_index(wager),
        "wager": wager,
        "effectiveWager": effective_wager,
        "answerFormat": answer_format,
        "timerSeconds": timer_seconds,
        "stealOnWrong": round_ctx["stealOnWrong"],
        "lineupBased": round_ctx["lineupBased"],
        "roundRuleId": round_ctx["roundRuleId"],
        "roundRuleName": round_ctx["roundRuleName"],
        "promptInstructions": prompt_instructions,
        "cardEffects": card_effects,
    }


def pick_factoid(fact_bank: dict, category: str, constraints: dict):
    """Pick a factoid from the bank that matches the current turn constraints.
    Removes the picked factoid so it's never reused within a game."""
    facts = fact_bank.get(category)
    if not facts:
        return None

    answer_format = constraints["answerFormat"]
    format_max = 1 if answer_format == "single-word" else 2 if answer_format == "one-or-two-words" else float("inf")

    def matches(f):
        if f["answerWordCount"] > format_max:
            return False
        if answer_format == "phrase" and f["answerWordCount"] < 2:
            return False
        return f["difficulty"] == _bank_difficulty(constraints["difficulty"])

    matching = [f for f in facts if matches(f)]
    pool = matching if matching else [f for f in facts if f["answerWordCount"] <= format_max]
    if not pool:
        picked = facts.pop(0)
        return picked

    picked = random.choice(pool)
    facts.remove(picked)
    return picked


class QuestionRuleSet(RuleSet):
    """MYF's post-generation check: does the question Claude returned actually
    satisfy the constraints that were sent to it?

    This is the title's instance of the shared engine — the same role CYM's
    MysteryRuleSet plays for a generated mystery. The two games validate
    completely different objects and share the vocabulary for saying so:
    Issue, the severity levels, and CoherenceReport.

    run(context) takes {"question": dict, "constraints": dict}. A BLOCKING
    issue means the question is unusable as generated; WARNING means the round
    rule or an active card was not honoured, which is worth logging but not
    worth spending another API call over mid-turn; INFO is a note.
    """

    def run(self, context) -> CoherenceReport:
        return self._check(context["question"], context["constraints"])

    @staticmethod
    def _check(question: dict, constraints: dict) -> CoherenceReport:
        issues: list[Issue] = []

        answer = (question.get("answer") or "").strip()
        word_count = len(answer.split()) if answer else 0
        answer_format = constraints["answerFormat"]

        metadata = {"answer_format": answer_format, "word_count": word_count}

        # No answer is terminal: every check below reasons about the answer, so
        # continuing would pile up noise about a question that cannot be used
        # regardless. Same early-out the JS version has.
        if not answer:
            issues.append(Issue(
                code="question.no_answer",
                severity=BLOCKING,
                message="Generated question has no answer.",
                repair_hint="Regenerate; the answer field came back empty.",
            ))
            return CoherenceReport(passed=False, issues=issues, metadata=metadata)

        if not (question.get("question") or "").strip():
            issues.append(Issue(
                code="question.no_question_text",
                severity=BLOCKING,
                message="Generated question has no question text.",
                repair_hint="Regenerate; the question field came back empty.",
            ))

        if answer_format == "single-word" and word_count > 1:
            issues.append(Issue(
                code="question.answer_too_long.one_word",
                severity=WARNING,
                message=f'One Word Only round: answer "{answer}" has {word_count} words.',
                repair_hint="The round rule's answer-format instruction was not honoured.",
            ))

        if answer_format == "one-or-two-words" and word_count > 2:
            issues.append(Issue(
                code="question.answer_too_long.boxed_in",
                severity=WARNING,
                message=f'Boxed In card active: answer "{answer}" has {word_count} words (max 2).',
                repair_hint="The Boxed In prompt modifier was not honoured.",
            ))

        if answer_format == "phrase" and word_count < 2:
            issues.append(Issue(
                code="question.answer_too_short",
                severity=INFO,
                message=(
                    f'Baseline expects >3 word answers for card interplay; got '
                    f'"{answer}" ({word_count} word).'
                ),
                repair_hint="Short answers give Boxed In and One Word Only nothing to bite on.",
            ))

        if constraints.get("lineupBased"):
            lineup = question.get("lineup")
            options = (lineup or {}).get("options")
            if not lineup or not isinstance(options, list) or len(options) < 2:
                issues.append(Issue(
                    code="lineup.invalid_options",
                    severity=BLOCKING,
                    message="The Lineup requires at least 2 options.",
                    repair_hint="A pick-list with fewer than two options is not a choice.",
                ))
            else:
                ids = [o["id"] for o in options]
                if len(set(ids)) != len(ids):
                    issues.append(Issue(
                        code="lineup.duplicate_option_ids",
                        severity=BLOCKING,
                        message="The Lineup options must have unique ids.",
                        repair_hint="Duplicate ids make the winning tap ambiguous.",
                    ))
                correct_option_id = lineup.get("correctOptionId")
                if not correct_option_id or correct_option_id not in ids:
                    issues.append(Issue(
                        code="lineup.missing_correct_option",
                        severity=BLOCKING,
                        message="The Lineup correctOptionId must reference one of the options.",
                        repair_hint="With no reachable correct option the question is unwinnable.",
                    ))

        return CoherenceReport(
            passed=not any(i.is_blocking for i in issues),
            issues=issues,
            metadata=metadata,
        )


def validate_question(question: dict, constraints: dict) -> CoherenceReport:
    """Thin wrapper kept so the call site did not have to move — see
    QuestionRuleSet. Mirrors how CYM keeps check_parts()/check_mystery().

    NOTE: the return type changed from a plain dict to CoherenceReport, so
    `.passed` / `.issues` replace `["passed"]` / `["issues"]`. There is exactly
    one caller (game_state.py) and it was updated with this change.
    """
    return QuestionRuleSet().run({"question": question, "constraints": constraints})
