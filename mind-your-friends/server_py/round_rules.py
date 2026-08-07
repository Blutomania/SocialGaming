# 9 round rule variations. Ported from lib/roundRules.js.
#
# Dispatch note (see docs/WIRING.md): rather than inventing a new round_type
# taxonomy, this keeps the same boolean-flag dispatch already proven correct
# in the JS version (submissionBased / lineupBased / stealOnWrong) — simpler
# than a separate config table, and there's no evidence yet that the flags
# don't generalize.
#
# Rules that constrain the answer format define both transform_text and
# transform_voice. Rules with no answer constraint have transform=None.

import random

from constants import BASE_TIMER_SECONDS

ROUND_RULES = {
    "backItUp": {
        "id": "backItUp",
        "name": "Back It Up",
        "emoji": "🔄",
        "description": "The answer must be reversed.",
        "promptInstruction": (
            "The player must answer in reverse — they will say the correct answer backwards."
        ),
        "timerSeconds": BASE_TIMER_SECONDS,
        "transform_text": lambda answer: answer[::-1],
        "transform_voice": lambda answer: " ".join(reversed(answer.split(" "))),
    },
    "oneWordOnly": {
        "id": "oneWordOnly",
        "name": "One Word Only",
        "emoji": "1️⃣",
        "description": "The answer must be a single word.",
        "promptInstruction": "Generate a question whose correct answer can be reduced to a single word.",
        "timerSeconds": BASE_TIMER_SECONDS,
        "transform_text": lambda answer: answer.strip().split()[0] if answer.strip() else answer,
        "transform_voice": lambda answer: answer.strip().split()[0] if answer.strip() else answer,
    },
    "lightningRound": {
        "id": "lightningRound",
        "name": "Lightning Round",
        "emoji": "⚡",
        "description": "Timer halved.",
        "promptInstruction": None,
        "timerSeconds": BASE_TIMER_SECONDS // 2,
    },
    "takeYourTime": {
        "id": "takeYourTime",
        "name": "Take Your Time",
        "emoji": "🐢",
        "description": "Timer doubled; host quip escalates.",
        "promptInstruction": (
            "The host's quip should build suspense slowly, escalating as if stalling for time."
        ),
        "timerSeconds": BASE_TIMER_SECONDS * 2,
    },
    "eli5": {
        "id": "eli5",
        "name": "ELI5",
        "emoji": "🧒",
        "description": "Question phrased by a curious 5-year-old; Claude judges understanding.",
        "promptInstruction": (
            "Phrase the question as if asked by a curious 5-year-old. When evaluating the "
            "answer, judge whether the player demonstrated understanding, not just exact wording."
        ),
        "timerSeconds": BASE_TIMER_SECONDS,
    },
    "doubleDown": {
        "id": "doubleDown",
        "name": "Double Down",
        "emoji": "💰",
        "description": "Wager auto-doubled, no backing out.",
        "promptInstruction": None,
        "timerSeconds": BASE_TIMER_SECONDS,
        "wagerMultiplier": 2,
    },
    "steal": {
        "id": "steal",
        "name": "Steal",
        "emoji": "🦹",
        "description": "Wrong answer opens a steal window for other players.",
        "promptInstruction": None,
        "timerSeconds": BASE_TIMER_SECONDS,
        "stealOnWrong": True,
    },
    "worstAnswerWins": {
        "id": "worstAnswerWins",
        "name": "Worst Answer Wins",
        "emoji": "🏆",
        "description": (
            "Everyone submits — worst answer wins. Scored on: factually wrong, "
            "creatively wrong, plausibility."
        ),
        "promptInstruction": (
            "Generate a factual question with a clear correct answer. All players will submit "
            "intentionally wrong answers. The question must have a definitive factual answer so "
            '"wrongness" is measurable.'
        ),
        "timerSeconds": BASE_TIMER_SECONDS * 2,
        "submissionBased": True,
    },
    "theLineup": {
        "id": "theLineup",
        "name": "The Lineup",
        "emoji": "🕵️",
        "description": (
            "Pick the right one from a lineup of look-alikes. First correct tap wins — "
            "wrong taps just fail, no penalty."
        ),
        "promptInstruction": None,
        "timerSeconds": BASE_TIMER_SECONDS,
        "lineupBased": True,
    },
}


def pick_random_round_rule():
    return ROUND_RULES[random.choice(list(ROUND_RULES.keys()))]


def transform_answer(round_rule, answer, input_mode):
    """Apply a round rule's answer transform, if any, for the given input mode."""
    key = f"transform_{input_mode}"
    fn = round_rule.get(key) if round_rule else None
    if not fn:
        return answer
    return fn(answer)
