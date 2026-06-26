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
import { roundConstraints, turnConstraints, validateQuestion } from './coherence.js';
import {
  ROUNDS,
  QUESTIONS_PER_ROUND,
  TOTAL_QUESTIONS,
  MIN_WAGER,
  MAX_WAGER,
  RESULT_SCREEN_MS,
  STEAL_WINDOW_MS,
  MIN_PLAYERS,
  MAX_PLAYERS,
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
  STEAL_WINDOW_MS,
  MIN_PLAYERS,
  MAX_PLAYERS,
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
  if (game.players.length >= MAX_PLAYERS) {
    throw new Error(`Room is full (max ${MAX_PLAYERS} players). Start a second game!`);
  }
  game.players.push(makePlayer(id, name));
  return game;
}

// Registration: each player submits 5 categories and picks 1 card from the
// pool of 10. The remaining 5 are randomly dealt. See GAME_DESIGN.md → Hand Dealing.
export function registerPlayer(game, playerId, { categories, pickedCardId }) {
  const player = getPlayer(game, playerId);
  if (categories.length !== CATEGORIES_PER_PLAYER) {
    throw new Error(`Must submit exactly ${CATEGORIES_PER_PLAYER} categories`);
  }
  player.categories = categories;
  player.hand = dealHand(pickedCardId);
  player.registered = true;
  return game;
}

export function allPlayersRegistered(game) {
  return game.players.length >= MIN_PLAYERS && game.players.every((p) => p.registered);
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
  game.roundConstraints = roundConstraints(game.roundRule);
  game.currentCategory = null;
  game.currentCategoryAttribution = null;
  game.currentWager = null;
  game.cardSlot = null;
  game.currentQuestion = null;
  game.answererIndex = game.activePlayerIndex;
  game.categoryOptions = getCategoryOptions(game);
}

// 6 random categories drawn from the shared pool. Each entry is attributed
// to the player who submitted it: { category, submittedBy, submittedById }.
function getCategoryOptions(game) {
  const pool = game.players.flatMap((p) =>
    p.categories.map((cat) => ({ category: cat, submittedBy: p.name, submittedById: p.id }))
  );
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
  const match = game.categoryOptions.find((opt) => opt.category === category);
  if (!match) {
    throw new Error('Category must be one of the offered options');
  }
  game.currentCategory = match.category;
  game.currentCategoryAttribution = { submittedBy: match.submittedBy, submittedById: match.submittedById };
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
// Closes the card window and resolves state-side effects. Prompt modifiers
// (Language Barrier, Boxed In) are handled by the CE in runQuestionPhase —
// this switch only handles game-state mutations and highlight logging.
export function resolveCardSlot(game) {
  assertPhase(game, 'CARD');
  const slot = game.cardSlot;
  game.heckleMessage = null;

  if (!slot) {
    game.phase = 'QUESTION';
    return game;
  }

  const playerName = getPlayer(game, slot.playerId).name;
  const activeName = getActivePlayer(game).name;

  switch (slot.cardId) {
    case 'skip':
      logHighlight(game, `${playerName} played Skip — ${activeName}'s turn is skipped!`);
      game.phase = 'RESULT';
      game.skippedTurn = true;
      return game;

    case 'redirect': {
      const others = game.players
        .map((_, i) => i)
        .filter((i) => i !== game.activePlayerIndex);
      game.answererIndex = others[Math.floor(Math.random() * others.length)];
      logHighlight(game, `${playerName} played Redirect — ${game.players[game.answererIndex].name} must answer instead!`);
      break;
    }

    case 'whoaNellie': {
      const pool = game.players.flatMap((p) =>
        p.categories.map((cat) => ({ category: cat, submittedBy: p.name, submittedById: p.id }))
      );
      const alternatives = pool.filter((opt) => opt.category !== game.currentCategory);
      if (alternatives.length > 0) {
        const pick = alternatives[Math.floor(Math.random() * alternatives.length)];
        const oldCategory = game.currentCategory;
        game.currentCategory = pick.category;
        game.currentCategoryAttribution = { submittedBy: pick.submittedBy, submittedById: pick.submittedById };
        logHighlight(game, `${playerName} played Whoa Nellie! Category swapped from "${oldCategory}" to ${pick.submittedBy}'s "${pick.category}"!`);
      } else {
        logHighlight(game, `${playerName} played Whoa Nellie but there's nowhere to go — same category!`);
      }
      break;
    }

    case 'fiftyOff':
      game.currentWager = Math.round(game.currentWager / 2);
      logHighlight(game, `${playerName} played 50% Off — the wager is now ${game.currentWager}!`);
      break;

    case 'spotlight':
      logHighlight(game, `${playerName} played Spotlight — ${activeName} must answer immediately!`);
      break;

    case 'heckle':
      game.heckleMessage = slot.payload?.text || '...';
      logHighlight(game, `${playerName} heckled: "${game.heckleMessage}"`);
      break;

    case 'languageBarrier':
      logHighlight(game, `${playerName} played Language Barrier!`);
      break;

    case 'boxedIn':
      logHighlight(game, `${playerName} played Boxed In — the answer must be one or two words!`);
      break;

    case 'insurance':
      logHighlight(game, `${playerName} played Insurance — this question proceeds normally.`);
      break;

    case 'fixer':
      getPlayer(game, slot.playerId).score += 50;
      logHighlight(game, `${playerName} played The Fixer — +50 pts, and this question proceeds normally.`);
      break;

    default:
      throw new Error(`Unknown card: ${slot.cardId}`);
  }

  game.phase = 'QUESTION';
  return game;
}

// Assembles constraints via the CE, calls Claude, validates the result.
export async function runQuestionPhase(game) {
  assertPhase(game, 'QUESTION');

  const constraints = turnConstraints(game.roundConstraints, {
    category: game.currentCategory,
    wager: game.currentWager,
    resolvedCard: getEffectiveCard(game),
  });

  const result = await generateQuestion({
    constraints,
    activePlayerName: getActivePlayer(game).name,
    playerNames: game.players.map((p) => p.name),
  });

  const validation = validateQuestion(result, constraints);
  if (!validation.passed) {
    console.warn('CE validation failed:', validation.issues);
  }

  game.currentQuestion = result;
  game.turnConstraints = constraints;
  game.phase = 'ANSWER';
  return game;
}

export function getTimerSeconds(game) {
  return game.turnConstraints?.timerSeconds ?? game.roundRule.timerSeconds;
}

// Evaluates the answerer's submission via Claude and applies scoring.
// If the Steal round rule is active and the answer is wrong, transitions
// to the STEAL phase instead of RESULT (see claimSteal / expireSteal).
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
  game.lastResult = { ...result, wager, playerAnswer: rawAnswer };

  if (result.correct) {
    answerer.score += wager;
    game.phase = 'RESULT';
  } else {
    answerer.score -= wager;
    logHighlight(
      game,
      `${answerer.name} wagered ${wager} and answered "${rawAnswer}" — wrong!`
    );

    if (game.roundRule?.stealOnWrong) {
      game.phase = 'STEAL';
      game.stealSlot = null;
      game.stealEligible = game.players
        .filter((p) => p.id !== answerer.id)
        .map((p) => p.id);
    } else {
      game.phase = 'RESULT';
    }
  }

  return game;
}

// FCFS steal: first eligible player to buzz in claims the steal attempt.
export async function claimSteal(game, playerId, rawAnswer, inputMode) {
  assertPhase(game, 'STEAL');
  if (game.stealSlot) {
    throw new Error('Steal already claimed — too slow!');
  }
  if (!game.stealEligible.includes(playerId)) {
    throw new Error('Not eligible to steal');
  }

  game.stealSlot = playerId;
  const stealer = getPlayer(game, playerId);

  const transformed = transformAnswer(game.roundRule, rawAnswer, inputMode);
  const result = await evaluateAnswer({
    question: game.currentQuestion.question,
    correctAnswer: game.currentQuestion.answer,
    playerAnswer: transformed,
    roundRule: game.roundRule,
  });

  const wager = game.currentWager;
  if (result.correct) {
    stealer.score += wager;
    logHighlight(game, `${stealer.name} stole it for ${wager} pts!`);
  } else {
    stealer.score -= Math.round(wager / 2);
    logHighlight(game, `${stealer.name} tried to steal but got it wrong — loses ${Math.round(wager / 2)} pts!`);
  }

  game.lastResult = { ...result, wager, playerAnswer: rawAnswer, stolen: true, stealerName: stealer.name };
  game.phase = 'RESULT';
  return game;
}

// Called when the steal window expires with no takers.
export function expireSteal(game) {
  if (game.phase !== 'STEAL') return;
  logHighlight(game, 'Nobody stole — moving on!');
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

const ANTI_SABOTAGE = new Set(['insurance', 'fixer']);
const STATE_ONLY_CARDS = new Set(['skip', 'redirect', 'fiftyOff', 'heckle', 'whoaNellie']);

function getEffectiveCard(game) {
  const cardId = game.cardSlot?.cardId;
  if (!cardId || ANTI_SABOTAGE.has(cardId) || STATE_ONLY_CARDS.has(cardId)) return null;
  return cardId;
}

function logHighlight(game, message) {
  game.highlightReel.push(message);
}

function assertPhase(game, expected) {
  if (game.phase !== expected) {
    throw new Error(`Expected phase ${expected}, got ${game.phase}`);
  }
}

// Build a state view tailored to a specific player. Hides information that
// the game rules say they shouldn't see: other players' hands, the correct
// answer (until RESULT), and internal CE/constraint data.
export function playerView(game, playerId) {
  const phase = game.phase;

  const players = game.players.map((p) => {
    const isMe = p.id === playerId;
    return {
      id: p.id,
      name: p.name,
      score: p.score,
      registered: p.registered,
      categories: p.categories,
      cardCount: p.hand.length,
      hand: isMe ? p.hand : undefined,
    };
  });

  const myIndex = game.players.findIndex((p) => p.id === playerId);
  const isActivePlayer = game.activePlayerIndex === myIndex;
  const isWagerPlayer = game.players.length >= 2 && game.players.indexOf(getWagerPlayer(game)) === myIndex;

  const view = {
    code: game.code,
    phase,
    myPlayerId: playerId,
    players,
    questionIndex: game.questionIndex,
    activePlayerIndex: game.activePlayerIndex,
    answererIndex: game.answererIndex,
    isActivePlayer,
    isWagerPlayer,
    currentCategory: game.currentCategory,
    currentCategoryAttribution: game.currentCategoryAttribution ?? null,
    currentWager: game.currentWager,
    roundRule: game.roundRule
      ? { id: game.roundRule.id, name: game.roundRule.name, emoji: game.roundRule.emoji, description: game.roundRule.description }
      : null,
    categoryOptions: game.categoryOptions ?? null,
    heckleMessage: game.heckleMessage,
    highlightReel: game.highlightReel,
  };

  if (game.cardSlot) {
    view.cardSlot = {
      playerId: game.cardSlot.playerId,
      cardId: game.cardSlot.cardId,
    };
  }

  if (game.currentQuestion) {
    view.question = game.currentQuestion.question;
    view.hostQuip = game.currentQuestion.hostQuip;

    if (phase === 'RESULT' || phase === 'GAME_OVER') {
      view.answer = game.currentQuestion.answer;
    }
  }

  if (phase === 'STEAL') {
    view.stealEligible = game.stealEligible?.includes(playerId) && !game.stealSlot;
    view.stealClaimed = !!game.stealSlot;
  }

  if (game.lastResult && (phase === 'RESULT' || phase === 'GAME_OVER' || phase === 'STEAL')) {
    view.lastResult = game.lastResult;
  }

  if (phase === 'GAME_OVER') {
    view.winners = getWinners(game).map((p) => ({ id: p.id, name: p.name, score: p.score }));
  }

  return view;
}
