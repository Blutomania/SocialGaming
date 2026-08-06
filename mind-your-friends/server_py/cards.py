# The card pool: 8 sabotage + 2 anti-sabotage + 1 universal.
# Ported from lib/cards.js — see GAME_DESIGN.md -> Card Mechanic.

import random

from constants import RANDOM_CARDS_PER_ROUND

LANGUAGE_BARRIER_REGISTERS = [
    'Old English ("Hark! What sayest thou...")',
    'Pirate ("Arrr, what be...")',
    'Corporate legalese ("Pursuant to the aforementioned...")',
    'Gen-Z slang ("no cap, what is the...")',
    'Victorian formal ("Pray tell, dear sir or madam...")',
]

HALF_OFF = {
    "id": "halfOff",
    "name": "Half-Off",
    "type": "universal",
    "description": "Halves the active player's wager value. Available every round.",
}

CARDS = {
    "skip": {
        "id": "skip",
        "name": "Skip",
        "type": "sabotage",
        "description": "Target player's turn is skipped entirely.",
    },
    "redirect": {
        "id": "redirect",
        "name": "Redirect",
        "type": "sabotage",
        "description": "Changes who must answer the question.",
    },
    "whoaNellie": {
        "id": "whoaNellie",
        "name": "Whoa Nellie",
        "type": "sabotage",
        "description": "Swaps the category to a random different one from the pool.",
    },
    "fiftyOff": {
        "id": "fiftyOff",
        "name": "50% Off",
        "type": "sabotage",
        "description": "Halves the active player's wager value.",
    },
    "spotlight": {
        "id": "spotlight",
        "name": "Spotlight",
        "type": "sabotage",
        "description": "Active player must answer immediately, with no prep time.",
    },
    "heckle": {
        "id": "heckle",
        "name": "Heckle",
        "type": "sabotage",
        "description": (
            "Submit a one-line heckle read aloud by the AI host before the "
            "active player answers. No mechanical effect."
        ),
    },
    "languageBarrier": {
        "id": "languageBarrier",
        "name": "Language Barrier",
        "type": "sabotage",
        "description": "AI host phrases the question in a randomly-chosen silly register.",
    },
    "boxedIn": {
        "id": "boxedIn",
        "name": "Boxed In",
        "type": "sabotage",
        "description": "Active player's answer must fit in one or two words.",
    },
    "insurance": {
        "id": "insurance",
        "name": "Insurance",
        "type": "anti-sabotage",
        "description": "Question proceeds completely normally, no matter what else was played.",
    },
    "fixer": {
        "id": "fixer",
        "name": "The Fixer",
        "type": "anti-sabotage",
        "description": "Question proceeds normally (like Insurance), and you bank a +50 pt bonus.",
    },
}

ALL_CARD_IDS = list(CARDS.keys())

# Lookup covering every possible hand entry, including the universal
# Half-Off card that build_round_hand() always injects but which isn't part
# of the pickable CARDS pool.
CARD_INFO = {**CARDS, HALF_OFF["id"]: HALF_OFF}

# All cards are available for the pick-one-at-game-start moment.
PICKABLE_CARD_IDS = ALL_CARD_IDS


def deal_round_cards(exclude_card_id=None):
    """Deal 2 random cards for a round. Excludes the player's picked card (if
    still available) to avoid duplicates with their permanent card."""
    pool = [cid for cid in ALL_CARD_IDS if cid != exclude_card_id]
    random.shuffle(pool)
    return pool[:RANDOM_CARDS_PER_ROUND]


def build_round_hand(picked_card_id, picked_card_used):
    """Build a player's hand for a given round:
    - Half-Off (always)
    - picked card (if not yet used)
    - 2 random cards for this round
    """
    hand = ["halfOff"]
    if not picked_card_used:
        hand.append(picked_card_id)
    hand.extend(deal_round_cards(None if picked_card_used else picked_card_id))
    return hand


def pick_random_language_register():
    return random.choice(LANGUAGE_BARRIER_REGISTERS)
