// In-memory game state machine. See GAME_DESIGN.md for the full design and
// mind-your-friends/CLAUDE.md for the architecture summary.
//
// Phases: LOBBY -> CATEGORY -> WAGER -> CARD -> QUESTION -> ANSWER -> RESULT -> (loop) -> GAME_OVER
//
// server.js is the only caller of these functions; it owns the in-memory
// `games` map (code -> game object) and emits Socket.io events after each
// mutation.

import { dealHand, pickRandomLanguageRegister } from './cards.js';
import { pickRandomRoundRule, transformAnswer } from './roundRules.js';
import { generateQuestion, evaluateAnswer } from './claudeClient.js';
import {
  ROUNDS,
  QUESTIONS_PER_ROUND,
  TOTAL_QUESTIONS,
  MIN_WAGER,
  MAX_WAGER,
  RESULT_SCREEN_MS,
  CATEGORIES_PER_PLAYER,
  CATEGORY_OPTIONS_COUNT,
} from './constants.js';

export {
  ROUNDS,
  QUESTIONS_PER_ROUND,
  TOTAL_QUESTIONS,
  MIN_WAGER,
  MAX_WAGER,
  RESULT_SCREEN_MS,
  CATEGORIES_PER_PLAYER,
  CATEGORY_OPTIONS_COUNT,
};

function generateGameCode() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ'; // no I/O — avoid confusion with 1/0
  let code = '';
  for (let i = 0; i < 4; i++) {
    code += chars[Math.floor(Math.random() * chars.length)];
  }
  return code;
}

export function createGame(hostId, hostName) {
  return {
    code: generateGameCode(),
    phase: 'LOBBY',
    players: [makePlayer(hostId, hostName)],
    questionIndex: 0, // 0-23
    activePlayerIndex: 0,
    currentCategory: null,
    currentWager: null,
    roundRule: null,
    cardSlot: null, // { playerId, cardId, payload }
    currentQuestion: null, // { question, answer, hostQuip }
    answererIndex: null,
    highlightReel: [],
  };
}

function makePlayer(id, name) {
  return {
    id,
    name,
    score: 0,
    categories: [], // 5 free-text tags, set during registration
    hand: [], // 6 card ids, set during registration
    registered: false,
  };
}

export function addPlayer(game, id, name) {
  if (game.phase !== 'LOBBY') {
    throw new Error('Cannot join — game already started');
  }
  game.players.push(makePlayer(id, name));
  return game;
}

// Registration: each player submits 5 categories and picks 4 of the 8
// pickable cards (2 common cards are added automatically). See
// GAME_DESIGN.md -> Hand Dealing, Categories -> Registration.
export function registerPlayer(game, playerId, { categories, pickedCardIds }) {
  const player = getPlayer(game, playerId);
  if (categories.length !== CATEGORIES_PER_PLAYER) {
    throw new Error(`Must submit exactly ${CATEGORIES_PER_PLAYER} categories`);
  }
  player.categories = categories;
  player.hand = dealHand(pickedCardIds);
  player.registered = true;
  return game;
}

export function allPlayersRegistered(game) {
  return game.players.length >= 2 && game.players.every((p) => p.registered);
}

export function startGame(game) {
  if (!allPlayersRegistered(game)) {
    throw new Error('All players must register before the game can start');
  }
  game.phase = 'CATEGORY';
  game.activePlayerIndex = 0;
  game.questionIndex = 0;
  beginTurn(game);
  return game;
}

function beginTurn(game) {
  game.roundRule = pickRandomRoundRule();
  game.currentCategory = null;
  game.currentWager = null;
  game.cardSlot = null;
  game.currentQuestion = null;
  game.answererIndex = game.activePlayerIndex;
  game.categoryOptions = getCategoryOptions(game);
}

// 6 random categories drawn from the shared pool of all players' submissions.
function getCategoryOptions(game) {
  const pool = game.players.flatMap((p) => p.categories);
  const options = [];
  const remaining = [...pool];
  const count = Math.min(CATEGORY_OPTIONS_COUNT, remaining.length);
  for (let i = 0; i < count; i++) {
    const idx = Math.floor(Math.random() * remaining.length);
    options.push(remaining.splice(idx, 1)[0]);
  }
  return options;
}

export function getPlayer(game, playerId) {
  const player = game.players.find((p) => p.id === playerId);
  if (!player) throw new Error('Player not found');
  return player;
}

export function getActivePlayer(game) {
  return game.players[game.activePlayerIndex];
}

// The wager-decider is always the next player after the active player.
export function getWagerPlayer(game) {
  const idx = (game.activePlayerIndex + 1) % game.players.length;
  return game.players[idx];
}

export function pickCategory(game, playerId, category) {
  assertPhase(game, 'CATEGORY');
  if (playerId !== getActivePlayer(game).id) {
    throw new Error('Only the active player picks the category');
  }
  if (!game.categoryOptions.includes(category)) {
    throw new Error('Category must be one of the offered options');
  }
  game.currentCategory = category;
  game.phase = 'WAGER';
  return game;
}

export function setWager(game, playerId, amount) {
  assertPhase(game, 'WAGER');
  if (playerId !== getWagerPlayer(game).id) {
    throw new Error('Only the wager-decider sets the wager');
  }
  let wager = Math.max(MIN_WAGER, Math.min(MAX_WAGER, Math.round(amount)));
  if (game.roundRule.wagerMultiplier) {
    wager *= game.roundRule.wagerMultiplier; // Double Down
  }
  game.currentWager = wager;
  game.phase = 'CARD';
  return game;
}

// First-come-first-served: the first card played claims the single slot for
// this question. Everyone else's attempt is rejected. Cards are single-use —
// removed from the player's hand the moment they claim the slot.
// `payload` carries card-specific data (e.g. Heckle's message text).
export function playCard(game, playerId, cardId, payload) {
  assertPhase(game, 'CARD');
  if (game.cardSlot) {
    throw new Error('Card slot already claimed — too slow!');
  }
  const player = getPlayer(game, playerId);
  if (!player.hand.includes(cardId)) {
    throw new Error('Card not in hand');
  }
  player.hand = player.hand.filter((id) => id !== cardId);
  game.cardSlot = { playerId, cardId, payload };
  return game;
}

// Closes the card window (no more cards may be played) and resolves whatever
// is in the slot. Returns control to the caller, which should then call
// runQuestionPhase() unless the turn was skipped entirely (Skip card).
export function resolveCardSlot(game) {
  assertPhase(game, 'CARD');
  const slot = game.cardSlot;
  game.cardModifier = null;
  game.timerSecondsOverride = null;
  game.heckleMessage = null;

  if (!slot) {
    game.phase = 'QUESTION';
    return game;
  }

  switch (slot.cardId) {
    case 'skip':
      logHighlight(game, `${getPlayer(game, slot.playerId).name} played Skip — ${getActivePlayer(game).name}'s turn is skipped!`);
      game.phase = 'RESULT';
      game.skippedTurn = true;
      return game;

    case 'redirect': {
      // Simplification for v1: redirects to a random other player.
      const others = game.players
        .map((_, i) => i)
        .filter((i) => i !== game.activePlayerIndex);
      game.answererIndex = others[Math.floor(Math.random() * others.length)];
      logHighlight(game, `${getPlayer(game, slot.playerId).name} played Redirect — ${game.players[game.answererIndex].name} must answer instead!`);
      break;
    }

    case 'whoaNellie':
      // TODO: define what makes the regenerated question different from a
      // normal one. For now this is a flavor-only re-roll.
      game.cardModifier = 'Generate a different question than you might normally pick for this category — surprise the players.';
      logHighlight(game, `${getPlayer(game, slot.playerId).name} played Whoa Nellie — re-rolling the question!`);
      break;

    case 'fiftyOff':
      game.currentWager = Math.round(game.currentWager / 2);
      logHighlight(game, `${getPlayer(game, slot.playerId).name} played 50% Off — the wager is now ${game.currentWager}!`);
      break;

    case 'spotlight':
      // TODO: "no prep time" — UI should skip any pre-answer countdown.
      game.timerSecondsOverride = 5;
      logHighlight(game, `${getPlayer(game, slot.playerId).name} played Spotlight — ${getActivePlayer(game).name} must answer immediately!`);
      break;

    case 'heckle':
      game.heckleMessage = slot.payload?.text || '...';
      logHighlight(game, `${getPlayer(game, slot.playerId).name} heckled: "${game.heckleMessage}"`);
      break;

    case 'languageBarrier': {
      const register = pickRandomLanguageRegister();
      game.cardModifier = `Phrase the question in this register: ${register}.`;
      logHighlight(game, `${getPlayer(game, slot.playerId).name} played Language Barrier — the host now speaks in ${register}!`);
      break;
    }

    case 'boxedIn':
      game.cardModifier = 'The correct answer MUST be ONE OR TWO WORDS — overriding the normal "more than 3 words" convention.';
      logHighlight(game, `${getPlayer(game, slot.playerId).name} played Boxed In — the answer must be one or two words!`);
      break;

    case 'insurance':
      logHighlight(game, `${getPlayer(game, slot.playerId).name} played Insurance — this question proceeds normally.`);
      break;

    case 'fixer':
      getPlayer(game, slot.playerId).score += 50;
      logHighlight(game, `${getPlayer(game, slot.playerId).name} played The Fixer — +50 pts, and this question proceeds normally.`);
      break;

    default:
      throw new Error(`Unknown card: ${slot.cardId}`);
  }

  game.phase = 'QUESTION';
  return game;
}

// Calls Claude to generate the question, then advances to ANSWER.
export async function runQuestionPhase(game) {
  assertPhase(game, 'QUESTION');
  const result = await generateQuestion({
    category: game.currentCategory,
    roundRule: game.roundRule,
    cardModifier: game.cardModifier,
    activePlayerName: getActivePlayer(game).name,
    playerNames: game.players.map((p) => p.name),
  });
  game.currentQuestion = result;
  game.phase = 'ANSWER';
  return game;
}

export function getTimerSeconds(game) {
  return game.timerSecondsOverride ?? game.roundRule.timerSeconds;
}

// Evaluates the answerer's submission via Claude and applies scoring.
export async function submitAnswer(game, playerId, rawAnswer, inputMode) {
  assertPhase(game, 'ANSWER');
  const answerer = game.players[game.answererIndex];
  if (playerId !== answerer.id) {
    throw new Error('Only the answerer may submit an answer');
  }

  const transformed = transformAnswer(game.roundRule, rawAnswer, inputMode);
  const result = await evaluateAnswer({
    question: game.currentQuestion.question,
    correctAnswer: game.currentQuestion.answer,
    playerAnswer: transformed,
    roundRule: game.roundRule,
  });

  const wager = game.currentWager;
  if (result.correct) {
    answerer.score += wager;
  } else {
    answerer.score -= wager;
    logHighlight(
      game,
      `${answerer.name} wagered ${wager} and answered "${rawAnswer}" — wrong! Correct answer: ${game.currentQuestion.answer}`
    );
    // TODO: Steal round rule — open a steal window for other players here.
  }

  game.lastResult = { ...result, wager, playerAnswer: rawAnswer };
  game.phase = 'RESULT';
  return game;
}

// Advances to the next question/turn, or GAME_OVER once TOTAL_QUESTIONS is reached.
export function nextTurn(game) {
  assertPhase(game, 'RESULT');
  game.skippedTurn = false;
  game.questionIndex += 1;
  if (game.questionIndex >= TOTAL_QUESTIONS) {
    game.phase = 'GAME_OVER';
    return game;
  }
  game.activePlayerIndex = (game.activePlayerIndex + 1) % game.players.length;
  game.phase = 'CATEGORY';
  beginTurn(game);
  return game;
}

export function getWinners(game) {
  const top = Math.max(...game.players.map((p) => p.score));
  return game.players.filter((p) => p.score === top); // ties are shared wins
}

function logHighlight(game, message) {
  game.highlightReel.push(message);
}

function assertPhase(game, expected) {
  if (game.phase !== expected) {
    throw new Error(`Expected phase ${expected}, got ${game.phase}`);
  }
}
