// The card pool: 8 sabotage + 2 anti-sabotage + 1 universal.
// See GAME_DESIGN.md → Card Mechanic.
// Sabotage/anti-sabotage cards are single-use and resolve via the FCFS card
// slot (gameState.playCard). Half-Off is universal — always available, never consumed.

import { RANDOM_CARDS_PER_ROUND } from './constants.js';

export const LANGUAGE_BARRIER_REGISTERS = [
  'Old English ("Hark! What sayest thou...")',
  'Pirate ("Arrr, what be...")',
  'Corporate legalese ("Pursuant to the aforementioned...")',
  'Gen-Z slang ("no cap, what is the...")',
  'Victorian formal ("Pray tell, dear sir or madam...")',
];

export const HALF_OFF = {
  id: 'halfOff',
  name: 'Half-Off',
  type: 'universal',
  description: "Halves the active player's wager value. Available every round.",
};

export const CARDS = {
  skip: {
    id: 'skip',
    name: 'Skip',
    type: 'sabotage',
    description: "Target player's turn is skipped entirely.",
  },
  redirect: {
    id: 'redirect',
    name: 'Redirect',
    type: 'sabotage',
    description: 'Changes who must answer the question.',
  },
  whoaNellie: {
    id: 'whoaNellie',
    name: 'Whoa Nellie',
    type: 'sabotage',
    description: 'Swaps the category to a random different one from the pool.',
  },
  fiftyOff: {
    id: 'fiftyOff',
    name: '50% Off',
    type: 'sabotage',
    description: "Halves the active player's wager value.",
  },
  spotlight: {
    id: 'spotlight',
    name: 'Spotlight',
    type: 'sabotage',
    description: 'Active player must answer immediately, with no prep time.',
  },
  heckle: {
    id: 'heckle',
    name: 'Heckle',
    type: 'sabotage',
    description:
      'Submit a one-line heckle read aloud by the AI host before the active player answers. No mechanical effect.',
  },
  languageBarrier: {
    id: 'languageBarrier',
    name: 'Language Barrier',
    type: 'sabotage',
    description:
      'AI host phrases the question in a randomly-chosen silly register.',
  },
  boxedIn: {
    id: 'boxedIn',
    name: 'Boxed In',
    type: 'sabotage',
    description:
      "Active player's answer must fit in one or two words.",
  },
  insurance: {
    id: 'insurance',
    name: 'Insurance',
    type: 'anti-sabotage',
    description: 'Question proceeds completely normally, no matter what else was played.',
  },
  fixer: {
    id: 'fixer',
    name: 'The Fixer',
    type: 'anti-sabotage',
    description:
      'Question proceeds normally (like Insurance), and you bank a +50 pt bonus.',
  },
};

export const ALL_CARD_IDS = Object.keys(CARDS);

// All cards are available for the pick-one-at-game-start moment.
export const PICKABLE_CARD_IDS = ALL_CARD_IDS;

// Deal 2 random cards for a round. Excludes the player's picked card (if still
// available) to avoid duplicates with their permanent card.
export function dealRoundCards(excludeCardId) {
  const pool = ALL_CARD_IDS.filter((id) => id !== excludeCardId);
  const shuffled = pool.sort(() => Math.random() - 0.5);
  return shuffled.slice(0, RANDOM_CARDS_PER_ROUND);
}

// Build a player's hand for a given round:
// - Half-Off (always)
// - picked card (if not yet used)
// - 2 random cards for this round
export function buildRoundHand(pickedCardId, pickedCardUsed) {
  const hand = ['halfOff'];
  if (!pickedCardUsed) {
    hand.push(pickedCardId);
  }
  hand.push(...dealRoundCards(pickedCardUsed ? null : pickedCardId));
  return hand;
}

export function pickRandomLanguageRegister() {
  return LANGUAGE_BARRIER_REGISTERS[
    Math.floor(Math.random() * LANGUAGE_BARRIER_REGISTERS.length)
  ];
}
