# Coherence Engine for Mind Your Friends — ported from lib/coherence.js.
#
# NOT yet wired to the shared coherence.engine.RuleSet base (see root
# docs/WIRING.md and this project's docs/WIRING.md) — that's the next step
# once this port is otherwise proven, tracked as MYF CLAUDE.md item 31/33.
# This is a straight semantic port of the JS two-pass constraint assembly,
# not a redesign.
#
# Two-pass constraint assembly:
#   1. round_constraints(round_rule) — runs once at round start.
#   2. turn_constraints(round_ctx, category, wager, resolved_card) — runs
#      per turn after card resolution, layers on turn-specific modifiers.
#
# Post-generation:
#   3. validate_question(question, constraints) — confirms the generated
#      Q&A satisfies the assembled constraints.

import random

from cards import CARDS, pick_random_language_register
from constants import BASE_TIMER_SECONDS, MAX_WAGER, MIN_WAGER

BLOCKING = "blocking"
WARNING = "warning"
INFO = "info"

_DIFFICULTY_PROMPT = {
    "easy": "Generate an easy question that most people would know the answer to.",
    "medium": "Generate a moderately challenging question — not trivial, but fair.",
    "hard": "Generate a difficult question that requires specific knowledge.",
}

_FORMAT_CARD_IDS = {"boxedIn", "languageBarrier"}


def _wager_to_difficulty(wager: int) -> str:
    normalized = (wager - MIN_WAGER) / (MAX_WAGER - MIN_WAGER)
    if normalized <= 0.33:
        return "easy"
    if normalized <= 0.66:
        return "medium"
    return "hard"


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
        return f["difficulty"] == constraints["difficulty"]

    matching = [f for f in facts if matches(f)]
    pool = matching if matching else [f for f in facts if f["answerWordCount"] <= format_max]
    if not pool:
        picked = facts.pop(0)
        return picked

    picked = random.choice(pool)
    facts.remove(picked)
    return picked


def validate_question(question: dict, constraints: dict) -> dict:
    issues = []

    answer = (question.get("answer") or "").strip()
    word_count = len(answer.split()) if answer else 0

    if not answer:
        issues.append({
            "code": "question.no_answer",
            "severity": BLOCKING,
            "message": "Generated question has no answer.",
        })
        return {"passed": False, "issues": issues}

    if not (question.get("question") or "").strip():
        issues.append({
            "code": "question.no_question_text",
            "severity": BLOCKING,
            "message": "Generated question has no question text.",
        })

    answer_format = constraints["answerFormat"]

    if answer_format == "single-word" and word_count > 1:
        issues.append({
            "code": "question.answer_too_long.one_word",
            "severity": WARNING,
            "message": f'One Word Only round: answer "{answer}" has {word_count} words.',
        })

    if answer_format == "one-or-two-words" and word_count > 2:
        issues.append({
            "code": "question.answer_too_long.boxed_in",
            "severity": WARNING,
            "message": f'Boxed In card active: answer "{answer}" has {word_count} words (max 2).',
        })

    if answer_format == "phrase" and word_count < 2:
        issues.append({
            "code": "question.answer_too_short",
            "severity": INFO,
            "message": (
                f'Baseline expects >3 word answers for card interplay; got '
                f'"{answer}" ({word_count} word).'
            ),
        })

    if constraints.get("lineupBased"):
        lineup = question.get("lineup")
        options = (lineup or {}).get("options")
        if not lineup or not isinstance(options, list) or len(options) < 2:
            issues.append({
                "code": "lineup.invalid_options",
                "severity": BLOCKING,
                "message": "The Lineup requires at least 2 options.",
            })
        else:
            ids = [o["id"] for o in options]
            if len(set(ids)) != len(ids):
                issues.append({
                    "code": "lineup.duplicate_option_ids",
                    "severity": BLOCKING,
                    "message": "The Lineup options must have unique ids.",
                })
            correct_option_id = lineup.get("correctOptionId")
            if not correct_option_id or correct_option_id not in ids:
                issues.append({
                    "code": "lineup.missing_correct_option",
                    "severity": BLOCKING,
                    "message": "The Lineup correctOptionId must reference one of the options.",
                })

    blocking = any(i["severity"] == BLOCKING for i in issues)
    return {"passed": not blocking, "issues": issues}
