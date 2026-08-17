# Shared constants — ported from lib/constants.js. Keep in sync with that
# file until the Next.js prototype is retired (see docs/WIRING.md).

ROUNDS = 4
QUESTIONS_PER_ROUND = 6
TOTAL_QUESTIONS = ROUNDS * QUESTIONS_PER_ROUND  # 24
MIN_WAGER = 50
MAX_WAGER = 500
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

# Points for anyone other than the active player who answers correctly. Flat and
# modest by design: the active player wagered, so they win big or lose big.
# Everyone else plays for a steady trickle and risks nothing — that is what makes
# answering feel free rather than scary.
OPEN_ANSWER_POINTS = 100
