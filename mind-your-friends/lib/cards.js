/**
 * Card definitions for Mind Your Friends
 * One card is dealt to each player each round.
 */

export const CARDS = {
  WHOA_NELLIE: {
    id: 'WHOA_NELLIE',
    name: 'Whoa Nellie',
    emoji: '🐴',
    description: 'Skip current question and get a new one.',
    target: 'self', // self | other | none
    timing: 'before_answer', // before_answer | after_answer | anytime
  },
  REDIRECT: {
    id: 'REDIRECT',
    name: 'Redirect',
    emoji: '↩️',
    description: 'Pass this question to another player.',
    target: 'other',
    timing: 'before_answer',
  },
  HINT_ME_UP: {
    id: 'HINT_ME_UP',
    name: 'Hint Me Up',
    emoji: '💡',
    description: 'AI reveals a hint for the current question.',
    target: 'self',
    timing: 'before_answer',
  },
  BEAR_MARKET: {
    id: 'BEAR_MARKET',
    name: 'Bear Market',
    emoji: '🐻',
    description: 'Wager goes up 50%.',
    target: 'none',
    timing: 'before_answer',
  },
  BULL_MARKET: {
    id: 'BULL_MARKET',
    name: 'Bull Market',
    emoji: '🐂',
    description: 'Wager goes down 50%.',
    target: 'none',
    timing: 'before_answer',
  },
  PINCH_PENNY: {
    id: 'PINCH_PENNY',
    name: 'Pinch Penny',
    emoji: '💰',
    description: 'Active player loses 25% of their total points if wrong.',
    target: 'other',
    timing: 'before_answer',
  },
  SAFETY_NET: {
    id: 'SAFETY_NET',
    name: 'Safety Net',
    emoji: '🛡️',
    description: 'Active player loses no points if wrong this turn.',
    target: 'self',
    timing: 'before_answer',
  },
  MUTED: {
    id: 'MUTED',
    name: 'Muted',
    emoji: '🔇',
    description: 'Target player skips their next turn.',
    target: 'other',
    timing: 'anytime',
  },
  HALFTIME: {
    id: 'HALFTIME',
    name: 'Halftime',
    emoji: '⏱️',
    description: "Active player's timer is cut in half.",
    target: 'other',
    timing: 'before_answer',
  },
};

export const CARD_LIST = Object.values(CARDS);

/**
 * Deal one random card to each player.
 * Returns { [playerId]: cardId }
 */
export function dealCards(playerIds) {
  const deck = {};
  for (const pid of playerIds) {
    const card = CARD_LIST[Math.floor(Math.random() * CARD_LIST.length)];
    deck[pid] = card.id;
  }
  return deck;
}
