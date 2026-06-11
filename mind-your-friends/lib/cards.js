// The 10-card pool: 8 sabotage + 2 anti-sabotage. See GAME_DESIGN.md → The 10 Base Cards.
// All cards are single-use and resolve via the FCFS card slot (gameState.playCard).

export const LANGUAGE_BARRIER_REGISTERS = [
  'Old English ("Hark! What sayest thou...")',
  'Pirate ("Arrr, what be...")',
  'Corporate legalese ("Pursuant to the aforementioned...")',
  'Gen-Z slang ("no cap, what is the...")',
  'Victorian formal ("Pray tell, dear sir or madam...")',
];

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
    description: 'Forces the server to re-generate the question.',
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
      'Player who plays it submits a one-line heckle, read aloud by the AI host before the active player answers. No mechanical effect.',
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
      "Active player's answer must fit in one or two words (questions normally expect more than 3).",
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
      'Question proceeds normally (like Insurance), and the player who played it banks a +50 pt bonus.',
  },
};

// Common cards — every player starts with these. See GAME_DESIGN.md → Common Cards.
export const COMMON_CARD_IDS = ['insurance', 'skip'];

// The remaining 8 cards, from which each player picks 4 at registration.
export const PICKABLE_CARD_IDS = Object.keys(CARDS).filter(
  (id) => !COMMON_CARD_IDS.includes(id)
);

// Build a player's fixed 6-card hand: 2 common + 4 player-picked.
export function dealHand(pickedCardIds) {
  if (pickedCardIds.length !== 4) {
    throw new Error('Players must pick exactly 4 cards from the pickable pool');
  }
  for (const id of pickedCardIds) {
    if (!PICKABLE_CARD_IDS.includes(id)) {
      throw new Error(`Invalid card id: ${id}`);
    }
  }
  return [...COMMON_CARD_IDS, ...pickedCardIds];
}

export function pickRandomLanguageRegister() {
  return LANGUAGE_BARRIER_REGISTERS[
    Math.floor(Math.random() * LANGUAGE_BARRIER_REGISTERS.length)
  ];
}
