# Shared constants — ported from lib/constants.js. Keep in sync with that
# file until the Next.js prototype is retired (see docs/WIRING.md).

ROUNDS = 4
QUESTIONS_PER_ROUND = 6
TOTAL_QUESTIONS = ROUNDS * QUESTIONS_PER_ROUND  # 24

# The wager ladder — five tiers, each a fraction of a pie, 100 = the whole pie
# and 200 = more pie than there is. Replaced a 50-500 slider: 46 values across a
# range whose ends were both wrong (a 50 swung ~4% of a typical winning margin,
# a 500 swung 43%), at a resolution finer than any decision a person can make.
# See lib/constants.js for the full reasoning and scripts/economy-sim.js for the
# numbers behind it.
WAGER_TIERS = [
    {"value": 12, "label": "Sliver", "fraction": 1 / 8},
    {"value": 25, "label": "Slice", "fraction": 1 / 4},
    {"value": 50, "label": "Half", "fraction": 1 / 2},
    {"value": 100, "label": "Whole pie", "fraction": 1},
    {"value": 200, "label": "DOUBLE", "fraction": 1, "super": True},
]
WAGER_VALUES = [t["value"] for t in WAGER_TIERS]
MIN_WAGER = WAGER_VALUES[0]
MAX_WAGER = WAGER_VALUES[-1]
RESULT_SCREEN_SECONDS = 4
MIN_PLAYERS = 3
MAX_PLAYERS = 6
# 3, not 5. Typing five categories was the single most laborious moment in the
# lobby (playtest, Aug 12), and with the tappable category grid most players
# never type at all now.
CATEGORIES_PER_PLAYER = 3
CATEGORY_OPTIONS_COUNT = 6
CARD_PICK_TIMER_SECONDS = 40
RANDOM_CARDS_PER_ROUND = 2
FACTS_PER_CATEGORY = 10
CATEGORIES_PER_FETCH_BATCH = 3
DISCONNECT_GRACE_SECONDS = 45
DISCONNECT_VOTE_EXTENSION_SECONDS = 45
AUTO_ADVANCE_AWAY_THRESHOLD = 2
LINEUP_COLOR_FLAVOR_CHANCE = 0.4
# Doubled from 20s (playtest, Aug 12): 20s was measured against a question the
# player had already read, but in practice the clock and the question arrived
# together. Reading is its own window now (READING_SECONDS) and this is time to
# actually think.
BASE_TIMER_SECONDS = 40

# How long the question sits on screen before the answer clock starts, so nobody
# races a timer they haven't finished reading.
READING_SECONDS = 5

# What a buzz-in win pays: a share of the wager the question was played for,
# not a flat number. Self-anchoring ("three-quarters of what they were playing
# for" needs no explanation, a flat 100 floats free of every other number on
# screen) and scaled to the question's danger.
#
# MUST stay below 1. At 1.5x a buzzer would earn 300 on a question the answerer
# could only win 200 on while risking nothing, which inverts the risk hierarchy
# of the whole game and makes being the active player something to avoid.
BUZZ_WAGER_SHARE = 0.75
BUZZ_POINTS_ROUNDING = 5

# Flow B: after the reading window the answerer gets this long alone with their
# own question before the buzzer opens. It is their wager, so they get first
# refusal on it. Carved OUT of the round rule's answer clock, never added to it,
# and capped at a share of that clock so a halved timer does not become a
# mostly-exclusive round.
ACTIVE_WINDOW_SECONDS = 8
ACTIVE_WINDOW_MAX_SHARE = 0.25


def wager_tier_index(wager) -> int:
    """Which rung of the ladder a wager sits on. Tolerant of values between
    rungs — Double Down multiplies past the top, Half-Off lands in between — by
    taking the nearest, so callers never special-case a card effect."""
    return min(
        range(len(WAGER_VALUES)),
        key=lambda i: abs(WAGER_VALUES[i] - (wager or 0)),
    )


def buzz_points_for_wager(wager) -> int:
    """The buzz payout as a pure function of the wager. Rounded so the
    scoreboard stays legible — 0.75 x 25 is 18.75, which nobody wants to read."""
    raw = (wager or 0) * BUZZ_WAGER_SHARE
    return round(raw / BUZZ_POINTS_ROUNDING) * BUZZ_POINTS_ROUNDING
