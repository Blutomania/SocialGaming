/**
 * In-memory game state manager (singleton for the Node.js server process).
 * All game state lives here — no database needed for MVP.
 */

import { dealCards } from './cards.js';
import { pickRoundRule } from './roundRules.js';

// Map of gameCode -> gameState
const games = new Map();

export const PHASES = {
  LOBBY: 'lobby',
  CATEGORY: 'category',
  WAGER: 'wager',
  CARD: 'card',
  QUESTION: 'question',
  ANSWER: 'answer',
  RESULT: 'result',
  GAME_OVER: 'game_over',
};

export const MAX_ROUNDS_DEFAULT = 6;
export const ANSWER_TIME_DEFAULT = 15; // seconds
export const STARTING_POINTS = 1000;

export const CATEGORIES = [
  'Pop Culture',
  'Science',
  'History',
  'Sports',
  'Music',
  'Food & Drink',
  'Tech',
  'Wild Card',
];

export const HOST_PERSONALITIES = [
  'Funny',
  'Sarcastic',
  'Encouraging',
  'Mysterious',
  'Game Show Host',
];

/**
 * Generate a 4-letter game code.
 */
function generateCode() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ'; // no I or O to avoid confusion
  let code;
  do {
    code = Array.from({ length: 4 }, () =>
      chars[Math.floor(Math.random() * chars.length)]
    ).join('');
  } while (games.has(code));
  return code;
}

/**
 * Create a new game and return its code.
 */
export function createGame(hostSocketId, hostName) {
  const code = generateCode();
  const hostPlayer = {
    id: hostSocketId,
    name: hostName,
    isHost: true,
    connected: true,
    muted: false, // skip next turn if MUTED card played
  };

  const state = {
    code,
    phase: PHASES.LOBBY,
    players: [hostPlayer],
    hostId: hostSocketId,
    roundNumber: 0,
    maxRounds: MAX_ROUNDS_DEFAULT,
    currentPlayerIndex: 0,
    roundRule: null,
    previousRuleId: null,
    scores: { [hostSocketId]: STARTING_POINTS },
    deck: {}, // { playerId: cardId }
    cardsPlayedThisRound: [], // [{ playerId, cardId, targetId? }]
    wager: 0,
    currentQuestion: null, // { question, hint, correctAnswer, hostQuip, revealed }
    timerSeconds: ANSWER_TIME_DEFAULT,
    timerInterval: null,
    hostPersonality: 'Game Show Host',
    previousQuestions: [],
    // Per-turn effect flags (reset each turn)
    effects: {
      safetyNet: false,    // active player immune to point loss
      pinchPenny: false,   // active player loses 25% of total on wrong
      bearMarket: false,   // wager * 1.5
      bullMarket: false,   // wager * 0.5
      halftime: false,     // timer halved
      redirectedTo: null,  // playerId if REDIRECT played
      newQuestion: false,  // WHOA_NELLIE — flag to re-generate
    },
  };

  games.set(code, state);
  return code;
}

/**
 * Add a player to an existing game. Returns null if game not found or already started.
 */
export function joinGame(code, socketId, playerName) {
  const game = games.get(code);
  if (!game) return { error: 'Game not found.' };
  if (game.phase !== PHASES.LOBBY) return { error: 'Game already in progress.' };
  if (game.players.find((p) => p.id === socketId)) return { error: 'Already in game.' };

  const player = {
    id: socketId,
    name: playerName,
    isHost: false,
    connected: true,
    muted: false,
  };
  game.players.push(player);
  game.scores[socketId] = STARTING_POINTS;
  return { game };
}

/**
 * Remove a player (on disconnect). Returns updated game or null if game dissolved.
 */
export function removePlayer(socketId) {
  for (const [code, game] of games.entries()) {
    const idx = game.players.findIndex((p) => p.id === socketId);
    if (idx === -1) continue;

    game.players[idx].connected = false;

    // If host leaves and game is in lobby, dissolve
    if (game.players[idx].isHost && game.phase === PHASES.LOBBY) {
      games.delete(code);
      return { code, dissolved: true };
    }

    // If all players disconnected, clean up
    if (game.players.every((p) => !p.connected)) {
      clearTimer(game);
      games.delete(code);
      return { code, dissolved: true };
    }

    // Reassign host if needed
    if (game.players[idx].isHost) {
      const newHost = game.players.find((p) => p.connected);
      if (newHost) {
        newHost.isHost = true;
        game.hostId = newHost.id;
      }
    }

    return { code, game };
  }
  return null;
}

export function getGame(code) {
  return games.get(code) || null;
}

export function getGameBySocketId(socketId) {
  for (const game of games.values()) {
    if (game.players.find((p) => p.id === socketId)) return game;
  }
  return null;
}

/**
 * Set host personality during lobby.
 */
export function setHostPersonality(code, personality) {
  const game = games.get(code);
  if (!game) return null;
  game.hostPersonality = personality;
  return game;
}

/**
 * Start the game. Transitions from LOBBY to first round.
 */
export function startGame(code) {
  const game = games.get(code);
  if (!game) return null;
  if (game.players.filter((p) => p.connected).length < 2) {
    return { error: 'Need at least 2 players to start.' };
  }

  game.roundNumber = 1;
  game.currentPlayerIndex = 0;
  beginRound(game);
  return game;
}

/**
 * Internal: set up a new round.
 */
function beginRound(game) {
  const rule = pickRoundRule(game.previousRuleId);
  game.previousRuleId = game.roundRule?.id || null;
  game.roundRule = rule;

  const activePlayers = game.players.filter((p) => p.connected);
  game.deck = dealCards(activePlayers.map((p) => p.id));
  game.cardsPlayedThisRound = [];
  game.wager = 0;
  game.currentQuestion = null;
  game.effects = {
    safetyNet: false,
    pinchPenny: false,
    bearMarket: false,
    bullMarket: false,
    halftime: false,
    redirectedTo: null,
    newQuestion: false,
  };

  // Skip muted player at round start
  advanceToNextNonMutedPlayer(game);

  game.phase = PHASES.CATEGORY;
}

/**
 * Advance currentPlayerIndex, skipping disconnected players.
 * Muted players have their flag consumed and are also skipped.
 */
function advanceToNextNonMutedPlayer(game) {
  const n = game.players.length;
  let attempts = 0;
  while (attempts < n) {
    const p = game.players[game.currentPlayerIndex];
    if (!p.connected) {
      game.currentPlayerIndex = (game.currentPlayerIndex + 1) % n;
      attempts++;
      continue;
    }
    if (p.muted) {
      p.muted = false; // consume the mute
      game.currentPlayerIndex = (game.currentPlayerIndex + 1) % n;
      attempts++;
      continue;
    }
    break;
  }
}

export function getCurrentPlayer(game) {
  return game.players[game.currentPlayerIndex];
}

/**
 * Get the "next" connected player index (for wager phase — next player after active).
 */
export function getNextPlayerIndex(game) {
  const n = game.players.length;
  let idx = (game.currentPlayerIndex + 1) % n;
  for (let i = 0; i < n; i++) {
    if (game.players[idx].connected) return idx;
    idx = (idx + 1) % n;
  }
  return game.currentPlayerIndex;
}

/**
 * Active player selects a category.
 */
export function selectCategory(code, socketId, category) {
  const game = games.get(code);
  if (!game || game.phase !== PHASES.CATEGORY) return { error: 'Wrong phase.' };
  const active = getCurrentPlayer(game);
  if (active.id !== socketId) return { error: 'Not your turn.' };

  game.selectedCategory = category;
  game.phase = PHASES.WAGER;
  return { game };
}

/**
 * Next player sets the wager.
 */
export function setWager(code, socketId, wagerAmount) {
  const game = games.get(code);
  if (!game || game.phase !== PHASES.WAGER) return { error: 'Wrong phase.' };
  const nextIdx = getNextPlayerIndex(game);
  const wagerer = game.players[nextIdx];
  if (wagerer.id !== socketId) return { error: 'Not your turn to wager.' };

  const base = Math.max(50, Math.min(wagerAmount, 500));
  game.wager = base;
  game.phase = PHASES.CARD;
  return { game };
}

/**
 * Apply a card effect. Any player may play their card during CARD phase.
 * Returns { game } or { error }.
 */
export function playCard(code, socketId, targetPlayerId) {
  const game = games.get(code);
  if (!game || game.phase !== PHASES.CARD) return { error: 'Wrong phase.' };

  const cardId = game.deck[socketId];
  if (!cardId) return { error: 'No card to play.' };
  if (game.cardsPlayedThisRound.find((c) => c.playerId === socketId)) {
    return { error: 'Already played a card this round.' };
  }

  // Apply effect
  applyCardEffect(game, socketId, cardId, targetPlayerId);

  game.cardsPlayedThisRound.push({ playerId: socketId, cardId, targetPlayerId });
  delete game.deck[socketId]; // card consumed
  return { game, cardId };
}

function applyCardEffect(game, playerId, cardId, targetPlayerId) {
  switch (cardId) {
    case 'BEAR_MARKET':
      game.effects.bearMarket = true;
      game.wager = Math.round(game.wager * 1.5);
      break;
    case 'BULL_MARKET':
      game.effects.bullMarket = true;
      game.wager = Math.round(game.wager * 0.5);
      break;
    case 'SAFETY_NET':
      game.effects.safetyNet = true;
      break;
    case 'PINCH_PENNY':
      game.effects.pinchPenny = true;
      break;
    case 'HALFTIME':
      game.effects.halftime = true;
      break;
    case 'MUTED':
      if (targetPlayerId) {
        const target = game.players.find((p) => p.id === targetPlayerId);
        if (target) target.muted = true;
      }
      break;
    case 'REDIRECT':
      if (targetPlayerId) {
        game.effects.redirectedTo = targetPlayerId;
      }
      break;
    case 'WHOA_NELLIE':
      game.effects.newQuestion = true;
      break;
    // HINT_ME_UP is handled client-side after question is revealed
    default:
      break;
  }
}

/**
 * Skip playing a card — move to question phase.
 */
export function skipCard(code, socketId) {
  const game = games.get(code);
  if (!game || game.phase !== PHASES.CARD) return { error: 'Wrong phase.' };
  // Only the active player (or redirected target) can finalize move to question
  const active = game.effects.redirectedTo
    ? game.players.find((p) => p.id === game.effects.redirectedTo)
    : getCurrentPlayer(game);
  if (!active || active.id !== socketId) return { error: 'Not your turn.' };
  game.phase = PHASES.QUESTION;
  return { game };
}

/**
 * Transition to QUESTION phase (called after card phase is finalized by host/server logic).
 */
export function beginQuestionPhase(code) {
  const game = games.get(code);
  if (!game) return null;
  game.phase = PHASES.QUESTION;
  return game;
}

/**
 * Store the generated question on the game state.
 */
export function setCurrentQuestion(code, questionData) {
  const game = games.get(code);
  if (!game) return null;
  game.currentQuestion = { ...questionData, revealed: false };
  game.previousQuestions.push(questionData.question);
  if (game.previousQuestions.length > 20) game.previousQuestions.shift();
  game.phase = PHASES.ANSWER;
  return game;
}

/**
 * Submit an answer. Returns { game, correct, explanation, pointDelta }.
 */
export function submitAnswer(code, socketId, isCorrect, explanation) {
  const game = games.get(code);
  if (!game || game.phase !== PHASES.ANSWER) return { error: 'Wrong phase.' };

  clearTimer(game);

  // Determine the answering player
  const answeringPlayerId = game.effects.redirectedTo || getCurrentPlayer(game).id;
  if (socketId !== answeringPlayerId) return { error: 'Not your turn to answer.' };

  let pointDelta = 0;
  const currentScore = game.scores[answeringPlayerId] || STARTING_POINTS;

  if (isCorrect) {
    pointDelta = game.wager;
    game.scores[answeringPlayerId] = currentScore + pointDelta;
  } else if (!game.effects.safetyNet) {
    if (game.effects.pinchPenny) {
      pointDelta = -Math.round(currentScore * 0.25);
    } else {
      pointDelta = -game.wager;
    }
    game.scores[answeringPlayerId] = Math.max(0, currentScore + pointDelta);
  }

  game.phase = PHASES.RESULT;
  game.lastResult = { answeringPlayerId, isCorrect, explanation, pointDelta };
  return { game, isCorrect, explanation, pointDelta };
}

/**
 * Advance to the next turn or end the game.
 * Called after result is shown.
 */
export function advanceTurn(code) {
  const game = games.get(code);
  if (!game) return null;

  const activePlayers = game.players.filter((p) => p.connected);
  const n = game.players.length;

  // Move to next player
  game.currentPlayerIndex = (game.currentPlayerIndex + 1) % n;

  // Count turns to determine if round is over
  // A round ends when every connected player has had a turn.
  // We track this via a turn counter.
  if (!game._turnsThisRound) game._turnsThisRound = 0;
  game._turnsThisRound++;

  if (game._turnsThisRound >= activePlayers.length) {
    // Round over
    game._turnsThisRound = 0;
    if (game.roundNumber >= game.maxRounds) {
      game.phase = PHASES.GAME_OVER;
      return game;
    }
    game.roundNumber++;
    beginRound(game);
  } else {
    // Next turn in same round
    game.wager = 0;
    game.currentQuestion = null;
    game.effects = {
      safetyNet: false,
      pinchPenny: false,
      bearMarket: false,
      bullMarket: false,
      halftime: false,
      redirectedTo: null,
      newQuestion: false,
    };
    advanceToNextNonMutedPlayer(game);
    game.phase = PHASES.CATEGORY;
  }

  return game;
}

/**
 * Start a countdown timer on the server. Calls onTick(secondsLeft) each second,
 * calls onExpire() when time runs out.
 */
export function startTimer(game, onTick, onExpire) {
  clearTimer(game);
  let seconds = game.effects.halftime
    ? Math.ceil(ANSWER_TIME_DEFAULT / 2)
    : ANSWER_TIME_DEFAULT;
  game.timerSeconds = seconds;

  game.timerInterval = setInterval(() => {
    seconds--;
    game.timerSeconds = seconds;
    onTick(seconds);
    if (seconds <= 0) {
      clearTimer(game);
      onExpire();
    }
  }, 1000);
}

export function clearTimer(game) {
  if (game && game.timerInterval) {
    clearInterval(game.timerInterval);
    game.timerInterval = null;
  }
}

/**
 * Return a sanitized game state safe to send to all clients.
 * Hides other players' cards and the correct answer (until result phase).
 */
export function sanitizeForClient(game, forSocketId) {
  if (!game) return null;
  const showAnswer = game.phase === PHASES.RESULT || game.phase === PHASES.GAME_OVER;
  return {
    code: game.code,
    phase: game.phase,
    players: game.players.map((p) => ({
      id: p.id,
      name: p.name,
      isHost: p.isHost,
      connected: p.connected,
      muted: p.muted,
    })),
    hostId: game.hostId,
    roundNumber: game.roundNumber,
    maxRounds: game.maxRounds,
    currentPlayerIndex: game.currentPlayerIndex,
    roundRule: game.roundRule,
    scores: game.scores,
    myCard: game.deck[forSocketId] || null,
    cardsPlayedThisRound: game.cardsPlayedThisRound,
    wager: game.wager,
    selectedCategory: game.selectedCategory || null,
    effects: game.effects,
    currentQuestion: game.currentQuestion
      ? {
          question: game.currentQuestion.question,
          hint: game.currentQuestion.hint,
          hostQuip: game.currentQuestion.hostQuip,
          correctAnswer: showAnswer ? game.currentQuestion.correctAnswer : null,
        }
      : null,
    timerSeconds: game.timerSeconds,
    hostPersonality: game.hostPersonality,
    lastResult: game.lastResult || null,
  };
}
