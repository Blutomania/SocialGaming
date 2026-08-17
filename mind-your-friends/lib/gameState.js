// In-memory game state machine. See GAME_DESIGN.md for the full design and
// mind-your-friends/CLAUDE.md for the architecture summary.
//
// Phases: LOBBY -> CATEGORY -> WAGER -> CARD -> QUESTION -> ANSWER -> RESULT -> (loop) -> GAME_OVER
//
// server.js is the only caller of these functions; it owns the in-memory
// `games` map (code -> game object) and emits Socket.io events after each
// mutation.

import { buildRoundHand, pickRandomLanguageRegister } from './cards.js';
import { pickRandomRoundRule, transformAnswer, NO_RULE, forcedRuleForRoundOne } from './roundRules.js';
import {
  generateQuestion,
  generateLineupOptions,
  evaluateAnswer,
  evaluateWorstAnswers,
  fetchFactsBatch,
  moderateHeckle,
  generateSuperlatives,
  narrateSuperlativeResults,
} from './claudeClient.js';
import { roundConstraints, turnConstraints, validateQuestion, pickFactoid } from './coherence.js';
import { pickColorLineupEntry, buildColorOptions } from './lineupData.js';
import { pickRebusPuzzle, resolveRebus } from './rebusData.js';
import {
  ROUNDS,
  QUESTIONS_PER_ROUND,
  TOTAL_QUESTIONS,
  MIN_WAGER,
  MAX_WAGER,
  RESULT_SCREEN_MS,
  MIN_PLAYERS,
  MAX_PLAYERS,
  CATEGORIES_PER_PLAYER,
  CATEGORY_OPTIONS_COUNT,
  DISCONNECT_GRACE_MS,
  AUTO_ADVANCE_AWAY_THRESHOLD,
  LINEUP_COLOR_FLAVOR_CHANCE,
  OPEN_ANSWER_POINTS,
  READING_SECONDS,
  ACTIVE_WINDOW_SECONDS,
  ACTIVE_WINDOW_MAX_SHARE,
} from './constants.js';

export {
  ROUNDS,
  QUESTIONS_PER_ROUND,
  TOTAL_QUESTIONS,
  MIN_WAGER,
  MAX_WAGER,
  RESULT_SCREEN_MS,
  MIN_PLAYERS,
  MAX_PLAYERS,
  CATEGORIES_PER_PLAYER,
  CATEGORY_OPTIONS_COUNT,
  DISCONNECT_GRACE_MS,
  OPEN_ANSWER_POINTS,
  READING_SECONDS,
  ACTIVE_WINDOW_SECONDS,
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
    // Structured record of every question actually asked, appended by
    // logQuestion() as each turn resolves. The highlight reel is prose meant
    // to be read back to the room; this is data, and it's what the post-game
    // social layer (superlatives, Shareable Question) is built on.
    // Contains correct answers, so playerView() only exposes it at GAME_OVER.
    questionLog: [],
    postGame: null,
    // Round-level state. roundNumber is 1-based; usedRuleIds keeps a rule
    // from repeating until every rule has had a round.
    roundNumber: 0,
    usedRuleIds: [],
    roundAnnouncement: null,
    // playerId -> attempt, for open answering. Reset every turn.
    answerAttempts: {},
    // Epoch ms when the buzzer opens (reading window over). Null outside ANSWER.
    answerOpensAt: null,
    // Non-null only while startGame() is building the fact bank. The build
    // takes ~50s even with the batches running concurrently, which is long
    // enough that a Lobby showing nothing reads as a hang — this is what the
    // Lobby renders instead. See CLAUDE.md item 36.
    startProgress: null,
  };
}

function makePlayer(id, name) {
  return {
    id,
    name,
    score: 0,
    categories: [],
    pickedCardId: null,
    pickedCardUsed: false,
    hand: [],
    registered: false,
    connected: true,
    droppedOut: false,
    away: false,
    autoAdvanceCount: 0,
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
// pool of 10. The picked card persists for the entire game (single use).
// Per-round random cards are dealt at the start of each round via dealRoundHands().
export function registerPlayer(game, playerId, { categories, pickedCardId }) {
  const player = getPlayer(game, playerId);
  if (categories.length !== CATEGORIES_PER_PLAYER) {
    throw new Error(`Must submit exactly ${CATEGORIES_PER_PLAYER} categories`);
  }
  player.categories = categories;
  player.pickedCardId = pickedCardId;
  player.pickedCardUsed = false;
  player.registered = true;
  return game;
}

// Deal fresh hands at the start of each round: Half-Off + picked card (if unused) + 2 random.
function dealRoundHands(game) {
  for (const player of game.players) {
    player.hand = buildRoundHand(player.pickedCardId, player.pickedCardUsed);
  }
}

export function allPlayersRegistered(game) {
  return game.players.length >= MIN_PLAYERS && game.players.every((p) => p.registered);
}

// --- Fact bank -------------------------------------------------------------
//
// Facts are fetched per category, on demand, instead of all of them up front
// (playtest, Aug 12). Building the whole bank at Start Game meant a wait
// before anyone had touched the game — the worst possible place to put one,
// because nothing has happened yet to make it feel earned. Now Start Game is
// instant, the categories nobody picks are never paid for at all, and the
// fetch for a category that IS picked happens behind the wager and card
// windows, where there is already time to fill.
//
// Two entry points, and both are needed:
//   ensureCategoryFacts() — correctness. Awaited before a question is
//     generated, so a category always has facts by the time it matters.
//   prefetchFactBank() — smoothness. Fired at game start; quietly fills in
//     everything else so the awaited call above is almost always a no-op.

// De-duplicates concurrent fetches for the same category: the prefetch and a
// player's pick can easily target the same category at the same moment, and
// paying twice for that would be the exact cost this design is avoiding.
function trackFetch(game, categories, promise) {
  game._factFetches ??= {};
  for (const c of categories) game._factFetches[c] = promise;
  const clear = () => {
    for (const c of categories) {
      if (game._factFetches[c] === promise) delete game._factFetches[c];
    }
  };
  promise.then(clear, clear);
  return promise;
}

export function ensureCategoryFacts(game, category) {
  if (!category) return Promise.resolve();
  game.factBank ??= {};
  if (game.factBank[category]) return Promise.resolve();
  if (game._factFetches?.[category]) return game._factFetches[category];

  const promise = fetchFactsBatch([category])
    .then((facts) => {
      Object.assign(game.factBank, facts);
    })
    .catch((err) => {
      // Deliberately swallowed. generateQuestion() already has a no-factoid
      // fallback path, so a failed fetch costs question quality, not the
      // turn — and a thrown error here would take the whole turn down.
      console.error(`Fact fetch failed for "${category}":`, err.message);
    });

  return trackFetch(game, [category], promise);
}

// Fire-and-forget. `onUpdate(game)` is the server's broadcast, so the room can
// see how much of the bank is warm.
export function prefetchFactBank(game, onUpdate) {
  game.factBank ??= {};
  game._factFetches ??= {};
  const all = [...new Set(game.players.flatMap((p) => p.categories))];
  const missing = all.filter((c) => !game.factBank[c] && !game._factFetches[c]);
  if (missing.length === 0) return Promise.resolve();

  const setProgress = (progress) => {
    game.factPrefetch = progress;
    try {
      onUpdate?.(game);
    } catch (err) {
      console.error('prefetch progress callback failed:', err);
    }
  };

  const promise = fetchFactsBatch(missing, (completed, total) => {
    setProgress({ active: completed < total, completed, total });
  })
    .then((facts) => {
      Object.assign(game.factBank, facts);
    })
    .catch((err) => {
      console.error('Fact-bank prefetch failed:', err.message);
    })
    .finally(() => {
      setProgress(null);
    });

  return trackFetch(game, missing, promise);
}

// Kept for tests and any caller that genuinely wants the whole bank warm
// before continuing.
export async function buildFactBank(game, onProgress) {
  const allCategories = [...new Set(game.players.flatMap((p) => p.categories))];
  game.factBank = await fetchFactsBatch(allCategories, onProgress);
  return game;
}

// Start is now instant — there is no fact-bank build to wait for. The
// `onUpdate` callback is still accepted and still fires once, so the server
// and the Godot client keep their existing contract (and so a future
// blocking step at start has somewhere to report from).
export function startGame(game, onUpdate) {
  if (!allPlayersRegistered(game)) {
    throw new Error('All players must register before the game can start');
  }
  game.factBank ??= {};
  game.startProgress = null;
  game.phase = 'CATEGORY';
  game.activePlayerIndex = 0;
  game.questionIndex = 0;
  dealRoundHands(game);
  beginTurn(game);
  try {
    onUpdate?.(game);
  } catch (err) {
    console.error('startGame callback failed:', err);
  }
  return game;
}

// 1-based round number for the question about to be played.
export function currentRoundNumber(game) {
  return Math.floor(game.questionIndex / QUESTIONS_PER_ROUND) + 1;
}

// Round rules are assigned once per ROUND, not per turn (playtest, Aug 12).
// Round 1 is deliberately plain: a new player should learn the base game
// before a rule bends it, which is the casual-first thesis applied to
// onboarding. Every round after that gets exactly one rule, announced at the
// top of the round and kept on screen for its whole duration.
function beginRoundIfNeeded(game) {
  const round = currentRoundNumber(game);
  if (game.roundNumber === round && game.roundRule) return;

  game.roundNumber = round;
  if (round === 1) {
    // MYF_FORCE_ROUND_RULE wins here so a playtest doesn't have to burn a
    // whole round to reach the rule under test. Unset, this is always NO_RULE.
    game.roundRule = forcedRuleForRoundOne() ?? NO_RULE;
  } else {
    // Rules don't repeat until every one has had a turn, so a 4-round game
    // shows four different twists.
    game.roundRule = pickRandomRoundRule(game.usedRuleIds);
    game.usedRuleIds.push(game.roundRule.id);
  }
  game.roundConstraints = roundConstraints(game.roundRule);

  // Cleared one turn later (see nextTurn) — it exists to be announced, and
  // the rule itself stays on screen for the round via view.roundRule.
  game.roundAnnouncement = {
    round,
    ruleId: game.roundRule.id,
    name: game.roundRule.name,
    emoji: game.roundRule.emoji,
    description: game.roundRule.description,
  };
}

function beginTurn(game) {
  beginRoundIfNeeded(game);
  game.answerAttempts = {};
  game.answerOpensAt = null;
  game.currentCategory = null;
  game.currentCategoryAttribution = null;
  game.currentWager = null;
  game.cardSlot = null;
  game.currentQuestion = null;
  game.answererIndex = game.activePlayerIndex;
  game.categoryOptions = getCategoryOptions(game);
  game.submissions = null;
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
  // Half-Off is universal — never removed from hand
  if (cardId !== 'halfOff') {
    player.hand = player.hand.filter((id) => id !== cardId);
  }
  // Mark picked card as used (gone for the rest of the game)
  if (cardId === player.pickedCardId) {
    player.pickedCardUsed = true;
  }
  game.cardSlot = { playerId, cardId, payload };
  return game;
}

// Closes the card window (no more cards may be played) and resolves whatever
// is in the slot. Returns control to the caller, which should then call
// runQuestionPhase() unless the turn was skipped entirely (Skip card).
// Closes the card window and resolves state-side effects. Prompt modifiers
// (Language Barrier, Boxed In) are handled by the CE in runQuestionPhase —
// this switch only handles game-state mutations and highlight logging.
export async function resolveCardSlot(game) {
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

    case 'halfOff':
      game.currentWager = Math.round(game.currentWager / 2);
      logHighlight(game, `${playerName} played Half-Off — the wager is now ${game.currentWager}!`);
      break;

    case 'fiftyOff':
      game.currentWager = Math.round(game.currentWager / 2);
      logHighlight(game, `${playerName} played 50% Off — the wager is now ${game.currentWager}!`);
      break;

    case 'spotlight':
      logHighlight(game, `${playerName} played Spotlight — ${activeName} must answer immediately!`);
      break;

    case 'heckle': {
      const rawHeckle = slot.payload?.text || '...';
      const result = await moderateHeckle({
        heckleText: rawHeckle,
        activePlayerName: activeName,
        hecklerName: playerName,
      });
      game.heckleMessage = result.heckle;
      logHighlight(game, `${playerName} heckled: "${game.heckleMessage}"`);
      break;
    }

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

  // Correctness backstop for the lazy fact bank: the prefetch has usually
  // covered this already (started at game start, and the wager + card windows
  // have run since the pick), in which case this resolves immediately.
  await ensureCategoryFacts(game, game.currentCategory);

  const constraints = turnConstraints(game.roundConstraints, {
    category: game.currentCategory,
    wager: game.currentWager,
    resolvedCard: getEffectiveCard(game),
  });

  let result;
  if (game.roundRule.rebusBased) {
    result = buildRebusQuestion(game);
  } else if (game.roundRule.lineupBased) {
    result = await buildLineupQuestion(game, constraints);
  } else {
    const factoid = game.factBank
      ? pickFactoid(game.factBank, game.currentCategory, constraints)
      : null;
    result = await generateQuestion({
      constraints,
      factoid,
      activePlayerName: getActivePlayer(game).name,
      playerNames: game.players.map((p) => p.name),
    });
  }

  const validation = validateQuestion(result, constraints);
  if (!validation.passed) {
    console.warn('CE validation failed:', validation.issues);
  }

  game.currentQuestion = result;
  game.turnConstraints = constraints;
  game.phase = 'ANSWER';
  game.answerAttempts = {};
  // The question and the clock used to arrive together, so the timer was
  // partly a reading-speed test (playtest, Aug 12). Now the question lands,
  // the room reads it, and only then does the buzzer open. Rules with their
  // own answer flow (Worst Answer Wins, The Lineup) keep their existing
  // behaviour and open immediately.
  const ownAnswerFlow = game.roundRule.submissionBased || game.roundRule.lineupBased;
  const readingMs = ownAnswerFlow ? 0 : READING_SECONDS * 1000;
  game.answerOpensAt = Date.now() + readingMs;
  // Flow B: the answerer alone may act between answerOpensAt and buzzOpensAt.
  // Rules with their own answer flow have no exclusive window at all —
  // everyone submits (Worst Answer Wins) or everyone taps (The Lineup) — so
  // the two timestamps coincide and every gate below is a no-op for them.
  //
  // An answerer who has already dropped out never gets a window: the room
  // would otherwise sit through it waiting for somebody who isn't there.
  const answerer = game.players[game.answererIndex];
  const exclusiveMs = ownAnswerFlow || answerer?.droppedOut
    ? 0
    : getActiveWindowSeconds(game) * 1000;
  game.buzzOpensAt = game.answerOpensAt + exclusiveMs;
  if (game.roundRule.submissionBased) {
    game.submissions = {};
  }
  return game;
}

// --- Rebus (emoji-wordplay round rule) ---
//
// Zero API calls: puzzles come from the curated bank in lib/rebusData.js.
// That's deliberate and it's the same call made for The Lineup's colour
// flavour — a rebus whose pieces don't reconstruct the answer is unsolvable,
// and a room can't tell "we're stupid" from "the game is broken". Asking
// Claude to build one live invites exactly that failure, because
// decomposing a word into sounds is the thing language models are worst at.
//
// Known limitation, same shape as the colour flavour's: the puzzle ignores
// the picked category. The bank isn't categorized, and forcing a match would
// mean either a much larger bank or falling back to live generation, which is
// the thing this avoids. The category pick still happens — it sets the wager
// difficulty and keeps the turn loop and its attribution beat intact.
function buildRebusQuestion(game) {
  game.usedRebusAnswers ??= [];
  const puzzle = pickRebusPuzzle(game.usedRebusAnswers);
  game.usedRebusAnswers.push(puzzle.answer);

  const pieces = resolveRebus(puzzle);
  return {
    question: `Read the emoji: ${puzzle.hint}`,
    answer: puzzle.answer,
    hostQuip: 'Say what you see.',
    rebus: {
      pieces: pieces.map((p) => p.emoji),
      // Withheld from the client until RESULT — see playerView. Handing over
      // the readings mid-question is handing over the answer.
      reads: pieces.map((p) => p.reads),
      hint: puzzle.hint,
      phonetic: !!puzzle.phonetic,
    },
  };
}

// --- The Lineup (pick-one round rule) ---
//
// Two flavors, chosen randomly per question: "text" (a fact-bank-grounded
// multiple-choice question via Claude — see generateLineupOptions) and
// "color" (a curated real color + procedurally-perturbed near-miss decoys,
// no API call — see lib/lineupData.js). Color flavor is intentionally
// category-agnostic: real colors need verified hex values that can't be
// reliably tied to arbitrary player-submitted category strings, so it draws
// from its own curated pool instead of the turn's picked category. The
// category pick still happens (keeps the round loop and wager-sizing intact)
// but only shapes the question for text flavor.
//
// Known gap: format-constraining cards (Boxed In, Language Barrier) have no
// effect on Lineup questions — their prompt instructions are never wired
// into generateLineupOptions, since a "pick one" answer has no free-text
// format to constrain. Left as a documented limitation rather than special-
// cased, matching this file's existing style for scoped-out edge cases.
async function buildLineupQuestion(game, constraints) {
  if (Math.random() < LINEUP_COLOR_FLAVOR_CHANCE) {
    const entry = pickColorLineupEntry();
    const { options, correctOptionId } = buildColorOptions(entry);
    return {
      question: `Which one is ${entry.entity} ${entry.label}?`,
      answer: `${entry.entity} (${entry.label})`,
      hostQuip: `Spot the real ${entry.label}, ${getActivePlayer(game).name} — don't blink!`,
      lineup: { flavor: 'color', options, correctOptionId },
    };
  }

  const factoid = game.factBank
    ? pickFactoid(game.factBank, game.currentCategory, constraints)
    : null;

  const result = await generateLineupOptions({
    factoid,
    activePlayerName: getActivePlayer(game).name,
    playerNames: game.players.map((p) => p.name),
  });

  const options = result.options.map((label, i) => ({ id: `opt${i}`, label }));
  const correctOptionId = options[result.correctIndex]?.id ?? options[0].id;

  return {
    question: result.question,
    answer: result.options[result.correctIndex] ?? result.options[0],
    hostQuip: result.hostQuip,
    lineup: { flavor: 'text', options, correctOptionId },
  };
}

// FCFS pick: any eligible player may tap any option at any time during
// ANSWER. Wrong taps fail silently — no penalty, no lockout, the round stays
// open — first correct tap (processed in socket-event order, so no race)
// claims the wager and ends the turn.
//
// Unlike other phase-gated actions in this file, this deliberately does NOT
// throw for a stale/late tap (phase already moved past ANSWER because
// someone else won, or a dropped-out player's queued click) — this
// mechanic invites genuinely simultaneous taps by design, and a throw here
// would surface as the client's global 'error' handler, which replaces the
// whole page (see app/game/[code]/page.js), not just this widget. Anything
// short of a clean win is treated the same as a wrong guess.
export function attemptLineupPick(game, playerId, optionId) {
  if (!game.roundRule?.lineupBased) {
    throw new Error('attemptLineupPick called on a non-Lineup round');
  }
  if (game.phase !== 'ANSWER') {
    return { correct: false };
  }
  const player = getPlayer(game, playerId);
  if (player.droppedOut) {
    return { correct: false };
  }
  const lineup = game.currentQuestion.lineup;
  const picked = lineup.options.find((o) => o.id === optionId);
  if (!picked || optionId !== lineup.correctOptionId) {
    return { correct: false };
  }

  const wager = game.currentWager;
  player.score += wager;
  logHighlight(game, `${player.name} spotted it in The Lineup and won ${wager} pts!`);
  game.lastResult = {
    correct: true,
    lineupWinner: true,
    winnerName: player.name,
    wager,
    correctOptionId: lineup.correctOptionId,
  };
  game.phase = 'RESULT';
  return { correct: true };
}

// Called when the answer timer expires with nobody having tapped correctly.
export function expireLineup(game) {
  if (game.phase !== 'ANSWER') return game;
  const wager = game.currentWager;
  logHighlight(game, `Nobody spotted it in The Lineup — ${wager} pts unclaimed!`);
  game.lastResult = {
    correct: false,
    lineupWinner: false,
    wager,
    correctOptionId: game.currentQuestion.lineup.correctOptionId,
  };
  game.phase = 'RESULT';
  return game;
}

// --- Worst Answer Wins (submission-based rounds) ---
//
// Unlike the normal single-answerer flow, every non-dropped-out player
// submits their own answer to the same question. Once everyone eligible has
// submitted (or the timer forces it), all submissions are scored together in
// one Claude call (see evaluateWorstAnswers) and the full per-player,
// per-axis breakdown is stored on lastResult so it can be shown to everyone
// -- not just who won, but why.

function submissionEligiblePlayers(game) {
  return game.players.filter((p) => !p.droppedOut);
}

export function allSubmitted(game) {
  const eligible = submissionEligiblePlayers(game);
  return eligible.every((p) => game.submissions[p.id] !== undefined);
}

// Records one player's raw submission. Returns true once every eligible
// player has submitted (signal to the caller to move on to evaluation).
export function submitGroupAnswer(game, playerId, rawAnswer, inputMode) {
  assertPhase(game, 'ANSWER');
  if (!game.roundRule.submissionBased) {
    throw new Error('submitGroupAnswer called on a non-submission-based round');
  }
  const player = getPlayer(game, playerId);
  if (player.droppedOut) {
    throw new Error('Dropped-out players cannot submit');
  }
  if (game.submissions[playerId] !== undefined) {
    throw new Error('Already submitted');
  }
  game.submissions[playerId] = { rawAnswer, inputMode };
  return allSubmitted(game);
}

// Called by the answer timer when it expires: any eligible player who never
// submitted is filled in with a blank answer so the round can still resolve.
export function autoFillMissingSubmissions(game) {
  for (const player of submissionEligiblePlayers(game)) {
    if (game.submissions[player.id] === undefined) {
      recordAutoAdvance(game, player.id);
      game.submissions[player.id] = { rawAnswer: '', inputMode: 'text' };
    }
  }
  return game;
}

// Synchronous phase flip so a submission arriving at the same instant the
// timer fires can't trigger evaluation twice (see server.js).
export function beginGroupEvaluation(game) {
  assertPhase(game, 'ANSWER');
  game.phase = 'EVALUATING';
  return game;
}

// Calls Claude once for the whole batch, computes totals, determines the
// winner(s) (lowest total; ties share the win, same convention as
// getWinners()), and stores the full breakdown on lastResult.
export async function resolveGroupAnswers(game) {
  assertPhase(game, 'EVALUATING');

  const eligible = submissionEligiblePlayers(game);
  const transformedAnswers = eligible.map((p) => {
    const { rawAnswer, inputMode } = game.submissions[p.id];
    return transformAnswer(game.roundRule, rawAnswer, inputMode);
  });

  const scores = await evaluateWorstAnswers({
    question: game.currentQuestion.question,
    correctAnswer: game.currentQuestion.answer,
    submissions: eligible.map((p, i) => ({ name: p.name, answer: transformedAnswers[i] })),
  });

  const entries = eligible.map((p, i) => {
    const s = scores[i];
    const total = s.factuallyWrong + s.creativelyWrong + s.plausibility;
    return {
      playerId: p.id,
      name: p.name,
      answer: game.submissions[p.id].rawAnswer,
      factuallyWrong: s.factuallyWrong,
      creativelyWrong: s.creativelyWrong,
      plausibility: s.plausibility,
      total,
      feedback: s.feedback,
    };
  });

  const lowestTotal = Math.min(...entries.map((e) => e.total));
  const wager = game.currentWager;
  for (const entry of entries) {
    entry.isWinner = entry.total === lowestTotal;
    if (entry.isWinner) {
      getPlayer(game, entry.playerId).score += wager;
    }
  }

  const winnerNames = entries.filter((e) => e.isWinner).map((e) => e.name);
  logHighlight(
    game,
    `Worst Answer Wins: ${winnerNames.join(' & ')} nailed being wrong (total ${lowestTotal}) and won ${wager} pts!`
  );

  game.lastResult = {
    submissionBased: true,
    wager,
    entries,
  };
  game.phase = 'RESULT';
  return game;
}

export function getTimerSeconds(game) {
  return game.turnConstraints?.timerSeconds ?? game.roundRule.timerSeconds;
}

// Total time the ANSWER phase is open: the reading window plus the answer
// clock. The server arms one timer for the whole thing (see startAnswerTimer)
// — the reading window is enforced by answerOpensAt, not a separate phase,
// deliberately: every phase-timeout and auto-advance helper in this file
// assumes the existing phase loop, and a tenth phase would mean auditing all
// of them for a state that can't affect scoring.
export function getAnswerWindowMs(game) {
  return (READING_SECONDS + getTimerSeconds(game)) * 1000;
}

// Flow B: how long the answerer has the question to themselves. Carved out of
// the answer clock rather than added to it — the question is the same length
// either way — and capped at a share of that clock so a halved timer doesn't
// become a mostly-exclusive round.
export function getActiveWindowSeconds(game) {
  const clock = getTimerSeconds(game);
  return Math.round(Math.min(ACTIVE_WINDOW_SECONDS, clock * ACTIVE_WINDOW_MAX_SHARE));
}

// Time from the start of the ANSWER phase to the buzzer opening: the reading
// window plus the exclusive window. server.js arms one timer for this and
// another for the whole phase (getAnswerWindowMs).
export function getActiveWindowMs(game) {
  return (READING_SECONDS + getActiveWindowSeconds(game)) * 1000;
}

// Everyone who could still buzz in on this question.
function openAnswerEligible(game) {
  return game.players.filter((p) => !p.droppedOut && !game.answerAttempts?.[p.id]);
}

function isAnswerer(game, playerId) {
  return game.players[game.answererIndex]?.id === playerId;
}

// --- Answering: Flow B ------------------------------------------------------
//
// Three windows, one after the other, all inside the ANSWER phase:
//
//   1. Reading (READING_SECONDS) — nobody may answer.
//   2. Exclusive (getActiveWindowSeconds) — only the answerer may act. It is
//      their wager, so they get first refusal on their own question. They can
//      answer, or pass; either one opens the buzzer immediately.
//   3. Open — everyone else races for a flat OPEN_ANSWER_POINTS, one attempt
//      each, first correct answer wins.
//
// Step 2 is Flow B (GAME_DESIGN.md → "The Round Loop", agreed Aug 17). The
// Aug 12 free-for-all had no such window, so a faster player could take every
// question and the active player's wager never bit — worse, it broke "I cut,
// you choose": if anyone can claim the wager, the setter is no longer setting
// a punishment but a bounty they might collect themselves, so they'd always
// set maximum. See PLAYTEST.md PT-4.
//
// Only the answerer has money on it. They win or lose the wager; everyone
// else risks nothing. That asymmetry is the point: buzzing in has to feel
// free, or nobody does it, and the wager has to still sting, or "I cut, you
// choose" stops meaning anything. Buzzing is now vulture rather than race —
// you pounce on a fumble instead of outrunning someone who never got a turn.
export async function submitAnswer(game, playerId, rawAnswer, inputMode) {
  assertPhase(game, 'ANSWER');
  if (game.roundRule.submissionBased || game.roundRule.lineupBased) {
    throw new Error('This round rule has its own answer flow');
  }
  const player = getPlayer(game, playerId);
  if (player.droppedOut) {
    throw new Error('You are out of this game');
  }
  const now = Date.now();
  if (now < (game.answerOpensAt ?? 0)) {
    throw new Error('Still reading — nobody can answer yet');
  }
  const mine = isAnswerer(game, playerId);
  if (!mine && now < (game.buzzOpensAt ?? 0)) {
    const answerer = game.players[game.answererIndex];
    throw new Error(`${answerer.name} gets first shot at their own question`);
  }
  if (game.answerAttempts[playerId]) {
    throw new Error('You already had your shot at this one');
  }

  // Claim the attempt slot synchronously, before any await: two taps from the
  // same player would otherwise both pass the check above and queue twice.
  const attempt = { playerId, name: player.name, answer: rawAnswer, correct: null };
  game.answerAttempts[playerId] = attempt;

  // The answerer has spoken, so the room is in. Opened on SUBMISSION, not on
  // the evaluation coming back: the answer is a real Claude call, and making
  // everyone wait it out would hand seconds of a shared clock to whoever the
  // API happened to be slow for. Ordering is safe regardless — evaluations
  // are serialised below, so this answer is still judged first.
  if (mine) game.buzzOpensAt = now;

  // Evaluations are serialized rather than run in parallel, so "first correct
  // wins" is decided by SUBMISSION order. Evaluating concurrently would hand
  // the win to whoever's Claude call happened to return first, which is a
  // coin flip, and would let two players both be paid for the same question.
  const run = () => resolveOpenAnswer(game, attempt, inputMode);
  game._answerChain = (game._answerChain ?? Promise.resolve()).then(run, run);
  await game._answerChain;
  return game;
}

async function resolveOpenAnswer(game, attempt, inputMode) {
  // Somebody already won (or the window closed) while this was queued.
  if (game.phase !== 'ANSWER') {
    attempt.correct = false;
    attempt.moot = true;
    return;
  }

  const player = getPlayer(game, attempt.playerId);
  const transformed = transformAnswer(game.roundRule, attempt.answer, inputMode);
  const result = await evaluateAnswer({
    question: game.currentQuestion.question,
    correctAnswer: game.currentQuestion.answer,
    playerAnswer: transformed,
    roundRule: game.roundRule,
  });

  // Re-check: the window can close while the evaluation is in flight.
  if (game.phase !== 'ANSWER') {
    attempt.correct = false;
    attempt.moot = true;
    return;
  }

  attempt.correct = !!result.correct;
  attempt.feedback = result.feedback;

  const answerer = game.players[game.answererIndex];
  const isActivePlayer = attempt.playerId === answerer.id;
  const wager = game.currentWager;

  if (result.correct) {
    const points = isActivePlayer ? wager : OPEN_ANSWER_POINTS;
    player.score += points;
    logHighlight(
      game,
      isActivePlayer
        ? `${player.name} took their own question for ${points} pts.`
        : `${player.name} pounced on ${answerer.name}'s question for ${points} pts!`
    );
    finishOpenAnswer(game, { ...result, winner: attempt, points });
    return;
  }

  if (isActivePlayer) {
    player.score -= wager;
    logHighlight(game, `${player.name} wagered ${wager} and answered "${attempt.answer}" — wrong!`);
  }

  // Everyone eligible has now had their shot and nobody got it.
  if (openAnswerEligible(game).length === 0) {
    finishOpenAnswer(game, { ...result, winner: null, points: 0 });
  }
}

// Folding. The answerer declines their own question, the buzzer opens
// immediately, and it costs them nothing.
//
// Passing must be an EXPLICIT action, and it must not be reachable by simply
// doing nothing — see expireActiveWindow. A free opt-out from any hard
// question would put the wager right back where Flow B found it.
//
// It opens the buzzer at once, deliberately: making the room sit out a window
// the answerer has already declined is exactly the dead air this game keeps
// trying to remove.
export function passAnswer(game, playerId) {
  assertPhase(game, 'ANSWER');
  if (game.roundRule.submissionBased || game.roundRule.lineupBased) {
    throw new Error('This round rule has its own answer flow');
  }
  const answerer = game.players[game.answererIndex];
  if (!isAnswerer(game, playerId)) {
    throw new Error('Only the player whose question it is can pass');
  }
  const now = Date.now();
  if (now < (game.answerOpensAt ?? 0)) {
    throw new Error('Still reading — nobody can act yet');
  }
  if (game.answerAttempts[playerId]) {
    throw new Error('You already had your shot at this one');
  }
  if (now >= (game.buzzOpensAt ?? 0)) {
    throw new Error('Too late to pass — the buzzer is already open');
  }

  // Recorded as a spent attempt so the rest of the file needs no new concept:
  // it is what stops them buzzing back in on a question they folded on, and
  // what stops expireAnswerWindow charging them for it later.
  game.answerAttempts[playerId] = {
    playerId,
    name: answerer.name,
    answer: '',
    correct: false,
    passed: true,
  };
  game.buzzOpensAt = now;
  logHighlight(game, `${answerer.name} passed on ${game.currentWager} pts — over to the room.`);
  return game;
}

// The exclusive window closing with the answerer having done nothing at all.
//
// This is the load-bearing half of the pass/timeout split: folding is a
// decision and costs nothing, freezing is a failure and costs the wager,
// exactly as answering wrong would (the "stalling isn't free" rule that
// expireAnswerWindow has always enforced). Collapse the two and "pass"
// becomes a free opt-out of every hard question.
//
// Returns true when it changed anything, so the caller knows to broadcast.
export function expireActiveWindow(game) {
  if (game.phase !== 'ANSWER') return false;
  if (game.roundRule.submissionBased || game.roundRule.lineupBased) return false;

  const answerer = game.players[game.answererIndex];
  // They answered or passed inside the window; the buzzer opened then, not now.
  if (game.answerAttempts[answerer.id]) return false;

  game.buzzOpensAt = Date.now();
  if (answerer.droppedOut) return true;

  answerer.score -= game.currentWager;
  game.answerAttempts[answerer.id] = {
    playerId: answerer.id,
    name: answerer.name,
    answer: '',
    correct: false,
    timedOut: true,
  };
  logHighlight(game, `${answerer.name} froze and dropped ${game.currentWager} pts — buzzers open!`);
  return true;
}

function finishOpenAnswer(game, { winner, points, ...result }) {
  const answerer = game.players[game.answererIndex];
  const answererAttempt = game.answerAttempts[answerer.id];
  // What became of the person whose wager it was. The result screen and the
  // question log both need to tell "passed" (costs nothing) apart from
  // "froze" (costs the wager) — they look identical from the outside
  // otherwise, and reporting a fold as a forfeit is a lie about the score.
  const activeOutcome = !answererAttempt
    ? 'none'
    : answererAttempt.passed
    ? 'passed'
    : answererAttempt.timedOut
    ? 'timedOut'
    : answererAttempt.correct
    ? 'correct'
    : 'wrong';

  game.lastResult = {
    ...result,
    correct: !!winner,
    wager: game.currentWager,
    // The winner's own words, or the active player's failed attempt when
    // nobody got it — ResultPhase shows whichever exists.
    playerAnswer: winner ? winner.answer : answererAttempt?.answer || null,
    winnerId: winner ? winner.playerId : null,
    winnerName: winner ? winner.name : null,
    points: points ?? 0,
    // True when someone other than the active player took it — the thing
    // worth putting a headline on.
    buzzedIn: !!winner && winner.playerId !== answerer.id,
    activeOutcome,
    wagerLost: activeOutcome === 'wrong' || activeOutcome === 'timedOut',
    attempts: Object.values(game.answerAttempts).map((a) => ({
      playerId: a.playerId,
      name: a.name,
      answer: a.answer,
      correct: !!a.correct,
      passed: !!a.passed,
      timedOut: !!a.timedOut,
    })),
  };
  game.phase = 'RESULT';
}

// Called when the answer window expires with nobody having got it right.
//
// Under Flow B the answerer has almost always been dealt with already — by
// expireActiveWindow when they froze, or by their own answer or pass. The
// charge below still stands for the paths that skip the exclusive window
// (a dropped-out answerer's slot, or a rule that opens the buzzer at once),
// and never double-charges: a spent attempt of any kind takes the else branch.
export function expireAnswerWindow(game) {
  if (game.phase !== 'ANSWER') return game;
  if (game.roundRule.submissionBased || game.roundRule.lineupBased) return game;

  const answerer = game.players[game.answererIndex];
  if (!game.answerAttempts[answerer.id] && !answerer.droppedOut) {
    answerer.score -= game.currentWager;
    game.answerAttempts[answerer.id] = {
      playerId: answerer.id,
      name: answerer.name,
      answer: '',
      correct: false,
      timedOut: true,
    };
    logHighlight(game, `${answerer.name} ran out of time and lost ${game.currentWager} pts.`);
  } else {
    logHighlight(game, 'Nobody got it — the points go unclaimed.');
  }

  finishOpenAnswer(game, { winner: null, points: 0 });
  return game;
}

// Advances to the next question/turn, or GAME_OVER once TOTAL_QUESTIONS is reached.
// Appends the turn that just resolved to game.questionLog. Called from
// nextTurn() rather than from each resolution path (submitAnswer,
// expireAnswerWindow, resolveGroupAnswers, the two lineup paths) because nextTurn is
// the single funnel every one of them passes through — logging in six places
// would mean six places to forget.
function logQuestion(game) {
  if (!game.currentQuestion || game.skippedTurn) return;

  const answerer = game.answererIndex != null ? game.players[game.answererIndex] : null;
  const result = game.lastResult ?? {};
  const rule = game.roundRule ?? {};

  let outcome;
  let outcomeSummary;
  if (rule.submissionBased) {
    outcome = 'group';
    outcomeSummary = 'The whole room answered this one.';
  } else if (rule.lineupBased) {
    const winnerName = result.lineupWinner ? result.winnerName : null;
    outcome = winnerName ? 'spotted' : 'unclaimed';
    outcomeSummary = winnerName
      ? `${winnerName} spotted it first.`
      : 'Nobody in the room spotted it.';
  } else if (result.buzzedIn) {
    // Someone other than the active player took it. `buzzedIn` is only ever
    // true alongside a winner, so this can't report a steal that didn't
    // happen — the trap the old `stolen` flag fell into, which was set on
    // failed steals too.
    //
    // How they came to lose it matters: a fold and a freeze read the same
    // from outside, and "hesitated" is only true of one of them.
    outcome = 'buzzed';
    const gaveItUp = {
      passed: 'passed and',
      wrong: 'got it wrong and',
      timedOut: 'froze and',
    }[result.activeOutcome] ?? 'hesitated and';
    outcomeSummary = `${answerer?.name ?? 'The answerer'} ${gaveItUp} ${result.winnerName} took it.`;
  } else if (result.correct) {
    outcome = 'correct';
    outcomeSummary = `${answerer?.name ?? 'The answerer'} got this one.`;
  } else if (result.activeOutcome === 'passed') {
    outcome = 'passed';
    outcomeSummary = `${answerer?.name ?? 'The answerer'} passed and nobody else got it either.`;
  } else {
    outcome = 'wrong';
    // Nobody in the room got it, not just the active player — everyone had a
    // shot at it once the buzzer opened.
    outcomeSummary = `Nobody got this one past ${answerer?.name ?? 'the answerer'}.`;
  }

  game.questionLog.push({
    index: game.questionIndex,
    question: game.currentQuestion.question,
    answer: game.currentQuestion.answer,
    category: game.currentCategory,
    categoryAttribution: game.currentCategoryAttribution?.submittedBy ?? null,
    roundRuleId: rule.id ?? null,
    roundRuleName: rule.name ?? null,
    answererName: answerer?.name ?? null,
    playerAnswer: result.playerAnswer ?? null,
    wager: game.currentWager ?? null,
    outcome,
    outcomeSummary,
    // The room failing a question is the strongest share hook — it turns the
    // card into a challenge ("nobody here got this") rather than a flashcard.
    roomMissedIt: outcome === 'wrong' || outcome === 'unclaimed' || outcome === 'passed',
    lineup: game.currentQuestion.lineup
      ? {
          options: game.currentQuestion.lineup.options,
          correctOptionId: game.currentQuestion.lineup.correctOptionId,
        }
      : null,
  });
}

export function nextTurn(game) {
  assertPhase(game, 'RESULT');
  logQuestion(game);
  game.skippedTurn = false;
  // The announcement gets exactly one turn on screen; the rule itself stays
  // visible for the whole round via view.roundRule.
  game.roundAnnouncement = null;
  game.questionIndex += 1;
  if (game.questionIndex >= TOTAL_QUESTIONS) {
    game.phase = 'GAME_OVER';
    return game;
  }
  // Deal fresh hands at the start of each new round
  if (game.questionIndex % QUESTIONS_PER_ROUND === 0) {
    dealRoundHands(game);
  }
  game.activePlayerIndex = (game.activePlayerIndex + 1) % game.players.length;
  skipUnavailablePlayers(game);
  if (game.phase === 'GAME_OVER') return game;
  game.phase = 'CATEGORY';
  beginTurn(game);
  return game;
}

export function getWinners(game) {
  const top = Math.max(...game.players.map((p) => p.score));
  return game.players.filter((p) => p.score === top); // ties are shared wins
}

const ANTI_SABOTAGE = new Set(['insurance', 'fixer']);
const STATE_ONLY_CARDS = new Set(['skip', 'redirect', 'fiftyOff', 'halfOff', 'heckle', 'whoaNellie']);

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

// --- Inactivity detection ---

export function recordAutoAdvance(game, playerId) {
  const player = getPlayer(game, playerId);
  player.autoAdvanceCount += 1;
  if (player.autoAdvanceCount >= AUTO_ADVANCE_AWAY_THRESHOLD) {
    player.away = true;
    logHighlight(game, `${player.name} seems to be away — skipping their turns until they're back.`);
  }
  return game;
}

export function recordPlayerAction(game, playerId) {
  const player = game.players.find((p) => p.id === playerId);
  if (!player) return;
  if (player.away) {
    player.away = false;
    logHighlight(game, `${player.name} is back in action!`);
  }
  player.autoAdvanceCount = 0;
}

export function isPlayerAway(game, playerIndex) {
  return game.players[playerIndex]?.away === true;
}

// --- Disconnection / Reconnection ---

export function disconnectPlayer(game, playerId) {
  const player = game.players.find((p) => p.id === playerId);
  if (!player) return game;
  player.connected = false;
  if (game.phase === 'LOBBY') return game;
  game.disconnectPending = game.disconnectPending || {};
  game.disconnectPending[playerId] = { since: Date.now() };
  logHighlight(game, `${player.name} disconnected — waiting for reconnect…`);
  return game;
}

// Returns true if the game should pause (disconnected player needs to act).
export function shouldPause(game) {
  if (game.phase === 'LOBBY' || game.phase === 'GAME_OVER') return false;
  const activePlayer = getActivePlayer(game);
  const answerer = game.players[game.answererIndex];
  const wagerPlayer = game.players.length >= 2 ? getWagerPlayer(game) : null;
  const needsAction = [activePlayer, answerer, wagerPlayer].filter(Boolean);
  return needsAction.some((p) => !p.connected && !p.droppedOut);
}

export function reconnectPlayer(game, oldPlayerId, newSocketId) {
  const player = game.players.find((p) => p.id === oldPlayerId);
  if (!player) return null;
  player.id = newSocketId;
  player.connected = true;
  if (game.disconnectPending) delete game.disconnectPending[oldPlayerId];
  if (game.disconnectVote) game.disconnectVote = null;
  logHighlight(game, `${player.name} is back!`);
  return game;
}

export function startDisconnectVote(game, disconnectedPlayerId) {
  const player = game.players.find((p) => p.id === disconnectedPlayerId);
  if (!player) return game;
  game.disconnectVote = {
    targetPlayerId: disconnectedPlayerId,
    targetName: player.name,
    votes: {},
  };
  return game;
}

export function castDisconnectVote(game, playerId, vote) {
  if (!game.disconnectVote) return { game, resolved: false };
  if (playerId === game.disconnectVote.targetPlayerId) return { game, resolved: false };
  game.disconnectVote.votes[playerId] = vote; // 'wait' | 'continue'

  const eligible = game.players.filter(
    (p) => p.id !== game.disconnectVote.targetPlayerId && p.connected
  );
  const voteCount = Object.keys(game.disconnectVote.votes).length;
  if (voteCount < eligible.length) return { game, resolved: false };

  const continueVotes = Object.values(game.disconnectVote.votes).filter((v) => v === 'continue').length;
  const majority = continueVotes > eligible.length / 2;

  if (majority) {
    const target = game.players.find((p) => p.id === game.disconnectVote.targetPlayerId);
    if (target) {
      target.droppedOut = true;
      logHighlight(game, `The group voted to continue without ${target.name}. Score frozen.`);
    }
    game.disconnectVote = null;
    if (game.disconnectPending) delete game.disconnectPending[game.disconnectVote?.targetPlayerId];
    return { game, resolved: true, action: 'continue' };
  }

  logHighlight(game, `The group voted to wait for ${game.disconnectVote.targetName}.`);
  game.disconnectVote = null;
  return { game, resolved: true, action: 'wait' };
}

// Skip a dropped-out player's turn.
export function isPlayerDroppedOut(game, playerIndex) {
  return game.players[playerIndex]?.droppedOut === true;
}

function shouldSkipPlayer(game, playerIndex) {
  return isPlayerDroppedOut(game, playerIndex) || isPlayerAway(game, playerIndex);
}

// Advance past dropped-out or away players' turns.
export function skipUnavailablePlayers(game) {
  const n = game.players.length;
  let checks = 0;
  while (shouldSkipPlayer(game, game.activePlayerIndex) && checks < n) {
    game.questionIndex += 1;
    if (game.questionIndex >= TOTAL_QUESTIONS) {
      game.phase = 'GAME_OVER';
      return game;
    }
    game.activePlayerIndex = (game.activePlayerIndex + 1) % n;
    checks++;
  }
  return game;
}

// Resume play after a dropped-out player's turn is skipped.
export function resumeAfterDrop(game) {
  skipUnavailablePlayers(game);
  if (game.phase !== 'GAME_OVER') {
    beginTurn(game);
    game.phase = 'CATEGORY';
  }
  return game;
}

// Build a state view tailored to a specific player. Hides information that
// the game rules say they shouldn't see: other players' hands, the correct
// answer (until RESULT), and internal CE/constraint data.
export function playerView(game, playerId) {
  const phase = game.phase;

  const allReg = game.players.every((p) => p.registered);
  const players = game.players.map((p) => {
    const isMe = p.id === playerId;
    return {
      id: p.id,
      name: p.name,
      score: p.score,
      registered: p.registered,
      connected: p.connected,
      droppedOut: p.droppedOut,
      away: p.away,
      categories: p.categories,
      cardCount: p.hand.length,
      hand: isMe ? p.hand : undefined,
      pickedCard: allReg ? p.pickedCardId : (isMe ? p.pickedCardId : undefined),
      pickedCardUsed: p.pickedCardUsed,
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
      ? {
          id: game.roundRule.id,
          name: game.roundRule.name,
          emoji: game.roundRule.emoji,
          description: game.roundRule.description,
          submissionBased: !!game.roundRule.submissionBased,
          lineupBased: !!game.roundRule.lineupBased,
          // The client renders the clock from this. It was missing, so every
          // answer screen showed a bare "s" where the seconds should be —
          // invisible until the reading window put a real countdown next to
          // it. Card effects can shorten it (Spotlight), hence the helper
          // rather than the raw rule value.
          timerSeconds: getTimerSeconds(game),
        }
      : null,
    categoryOptions: game.categoryOptions ?? null,
    roundNumber: game.roundNumber ?? 1,
    totalRounds: ROUNDS,
    // Set for exactly one turn at the top of each round; the client shows it
    // as a banner. Null the rest of the time.
    roundAnnouncement: game.roundAnnouncement ?? null,
    heckleMessage: game.heckleMessage,
    highlightReel: game.highlightReel,
    skippedTurn: !!game.skippedTurn,
    // Null except while the fact bank is building. Same shape for every
    // player — this is room-wide progress, not per-player state.
    startProgress: game.startProgress ?? null,
    // Background fact-bank warm-up. Not blocking anything — shown as a quiet
    // footer so a slow first question reads as "still loading" rather than
    // "broken".
    factPrefetch: game.factPrefetch ?? null,
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

    if (game.currentQuestion.rebus) {
      const rebus = game.currentQuestion.rebus;
      // Pieces are the puzzle itself, so they're safe to send. `reads` is the
      // solution spelled out — same withholding rule as the free-text answer
      // below.
      view.rebus = { pieces: rebus.pieces, hint: rebus.hint, phonetic: rebus.phonetic };
      if (phase === 'RESULT' || phase === 'GAME_OVER') {
        view.rebus.reads = rebus.reads;
      }
    }

    if (game.currentQuestion.lineup) {
      // Options are safe pre-reveal (that's the multiple-choice UI itself) —
      // only correctOptionId is withheld until RESULT/GAME_OVER, same
      // withholding pattern as the free-text `answer` field below.
      view.lineup = {
        flavor: game.currentQuestion.lineup.flavor,
        options: game.currentQuestion.lineup.options,
      };
    }

    if (phase === 'RESULT' || phase === 'GAME_OVER') {
      view.answer = game.currentQuestion.answer;

      if (game.currentQuestion.lineup) {
        view.lineup.correctOptionId = game.currentQuestion.lineup.correctOptionId;
      }
    }
  }

  // Flow B. Deliberately does NOT include other players' answer TEXT while
  // the window is open — only who has burned their attempt — so nobody can
  // copy a neighbour's wording.
  //
  // The two timestamps are sent raw and the client compares them against its
  // own clock: a view is only rebuilt when the server broadcasts, so anything
  // computed from Date.now() here would be stale the moment it arrived, and
  // both windows are short enough for that to matter.
  if (phase === 'ANSWER' && !game.roundRule?.submissionBased && !game.roundRule?.lineupBased) {
    const mine = game.answerAttempts?.[playerId];
    const amAnswerer = isAnswerer(game, playerId);
    view.answerOpensAt = game.answerOpensAt ?? null;
    view.buzzOpensAt = game.buzzOpensAt ?? null;
    view.activeWindowSeconds = getActiveWindowSeconds(game);
    view.iAmAnswerer = amAnswerer;
    // Attempt-spent only, so it stays true for the answerer during their own
    // exclusive window; whether the window is open to ME is the client's
    // clock comparison against the two timestamps above.
    view.iCanAnswer = !mine && !game.players[myIndex]?.droppedOut;
    view.iCanPass = amAnswerer && !mine && !game.players[myIndex]?.droppedOut;
    view.myAttempt = mine
      ? { answer: mine.answer, correct: mine.correct, passed: !!mine.passed, timedOut: !!mine.timedOut }
      : null;
    view.spentAttempts = Object.values(game.answerAttempts ?? {}).map((a) => ({
      playerId: a.playerId,
      name: a.name,
      correct: a.correct,
      passed: !!a.passed,
      timedOut: !!a.timedOut,
    }));
    view.openAnswerPoints = OPEN_ANSWER_POINTS;
  }

  if ((phase === 'ANSWER' || phase === 'EVALUATING') && game.roundRule?.submissionBased) {
    const eligible = submissionEligiblePlayers(game);
    view.mySubmitted = game.submissions?.[playerId] !== undefined;
    view.submittedCount = eligible.filter((p) => game.submissions?.[p.id] !== undefined).length;
    view.totalToSubmit = eligible.length;
  }

  if (game.lastResult && (phase === 'RESULT' || phase === 'GAME_OVER')) {
    view.lastResult = game.lastResult;
  }

  if (phase === 'GAME_OVER') {
    view.winners = getWinners(game).map((p) => ({ id: p.id, name: p.name, score: p.score }));

    // questionLog carries every correct answer, so it ships ONLY here — the
    // game is over and there is nothing left to spoil. Never move this out of
    // the GAME_OVER branch.
    view.questionLog = game.questionLog;

    if (game.postGame) {
      view.postGame = {
        stage: game.postGame.stage,
        categories: game.postGame.categories,
        // Individual votes stay hidden during voting so nobody can bandwagon;
        // they're only meaningful in aggregate anyway, and the results stage
        // publishes the tallies.
        myVotes: game.postGame.votes[playerId] ?? {},
        votedCount: Object.keys(game.postGame.votes).length,
        totalToVote: superlativeVoters(game).length,
        results: game.postGame.stage === 'results' ? game.postGame.results : null,
      };
    }
  }

  if (game.disconnectVote) {
    view.disconnectVote = {
      targetName: game.disconnectVote.targetName,
      canVote: playerId !== game.disconnectVote.targetPlayerId &&
        !game.disconnectVote.votes[playerId],
    };
  }

  view.paused = shouldPause(game);

  return view;
}

// ---------------------------------------------------------------------------
// Post-game social layer — superlative voting (CLAUDE.md item 35).
//
// Runs entirely inside the GAME_OVER phase rather than adding new phases to
// the main state machine. The game is over; this is an epilogue, and every
// phase-timeout/auto-advance helper in this file assumes the eight-phase loop.
// Bolting a tenth phase on would mean auditing all of them for a state that
// can't affect scoring.
//
// game.postGame = {
//   stage: 'voting' | 'results',
//   categories: [{ id, title, description }],
//   votes: { [voterId]: { [categoryId]: targetPlayerId } },
//   results: [{ id, title, description, winnerNames, voteCount, quip }] | null
// }
// ---------------------------------------------------------------------------

// Builds the superlative categories and opens voting. Safe to call more than
// once — the server's game:over path and a manual client request can race.
export async function beginSuperlativeVoting(game) {
  if (game.phase !== 'GAME_OVER') {
    throw new Error('Superlative voting only runs after the game is over');
  }
  if (game.postGame) return game; // already started

  // Claim the slot synchronously BEFORE the await, so two concurrent callers
  // can't both pass the guard above and generate two sets of categories.
  game.postGame = { stage: 'voting', categories: [], votes: {}, results: null };

  const categories = await generateSuperlatives({
    highlightReel: game.highlightReel,
    questionLog: game.questionLog,
    playerNames: game.players.map((p) => p.name),
  });

  game.postGame.categories = categories;
  return game;
}

// Sentinel stored in a ballot slot when a player abstains. Not a player id,
// so the tally below skips it naturally.
export const SKIPPED_VOTE = '__skipped__';

export function castSuperlativeVote(game, voterId, categoryId, targetPlayerId) {
  if (game.phase !== 'GAME_OVER' || !game.postGame) {
    throw new Error('Voting is not open');
  }
  if (game.postGame.stage !== 'voting') {
    throw new Error('Voting has already closed');
  }
  if (!game.postGame.categories.some((c) => c.id === categoryId)) {
    throw new Error(`Unknown superlative category: ${categoryId}`);
  }
  // SKIPPED is an abstention: it fills the ballot slot so the room isn't held
  // waiting on this player, but counts for nobody in the tally. Without it,
  // "Skip all" would either stall the room or have to invent a vote.
  if (targetPlayerId !== SKIPPED_VOTE && !getPlayer(game, targetPlayerId)) {
    throw new Error('You can only vote for a player in this game');
  }

  // Voting for yourself is allowed on purpose — "Best Sabotage" is a real
  // thing to be proud of, and policing it invites more argument than it saves.
  game.postGame.votes[voterId] = game.postGame.votes[voterId] ?? {};
  game.postGame.votes[voterId][categoryId] = targetPlayerId;
  return game;
}

// Abstain from every remaining award in one go. The post-game screens are
// optional fun, and a player who wants out has to be able to get out without
// stranding everyone else behind the 90s timer.
export function skipSuperlativeVoting(game, voterId) {
  if (game.phase !== 'GAME_OVER' || !game.postGame) {
    throw new Error('Voting is not open');
  }
  if (game.postGame.stage !== 'voting') {
    throw new Error('Voting has already closed');
  }
  game.postGame.votes[voterId] = game.postGame.votes[voterId] ?? {};
  for (const category of game.postGame.categories) {
    game.postGame.votes[voterId][category.id] ??= SKIPPED_VOTE;
  }
  return game;
}

// Who still owes a ballot. Excludes disconnected players as well as
// dropped-out ones: after the game ends people close the tab, and a player who
// has left must not hold the remaining room on the voting screen until the
// timer expires.
export function superlativeVoters(game) {
  return game.players.filter((p) => !p.droppedOut && p.connected);
}

// True once every still-present player has voted in every category.
export function allSuperlativeVotesIn(game) {
  if (!game.postGame || game.postGame.stage !== 'voting') return false;
  if (game.postGame.categories.length === 0) return false;
  const eligible = superlativeVoters(game);
  if (eligible.length === 0) return false;
  return eligible.every((p) => {
    const ballot = game.postGame.votes[p.id];
    return ballot && game.postGame.categories.every((c) => ballot[c.id]);
  });
}

// Tallies the votes and closes voting. Called when everyone has voted or when
// the post-game timer expires — whichever comes first, so one slow player
// can't strand the room on the voting screen.
export async function resolveSuperlatives(game) {
  if (!game.postGame || game.postGame.stage !== 'voting') return game;

  // Flip the stage synchronously so the all-voted path and the timer path
  // can't both tally — same guard pattern as beginGroupEvaluation().
  game.postGame.stage = 'results';

  const results = game.postGame.categories.map((category) => {
    const tally = {};
    for (const ballot of Object.values(game.postGame.votes)) {
      const target = ballot[category.id];
      // SKIPPED_VOTE fills a ballot slot so the room can move on, but it is
      // an abstention — it must not become a candidate in the tally, or
      // "skipped" wins the award.
      if (target && target !== SKIPPED_VOTE) tally[target] = (tally[target] ?? 0) + 1;
    }

    const top = Math.max(0, ...Object.values(tally));
    const winnerIds = Object.keys(tally).filter((id) => tally[id] === top);
    return {
      id: category.id,
      title: category.title,
      description: category.description,
      // Ties are shared wins — same convention as getWinners().
      winnerNames: winnerIds.map((id) => getPlayer(game, id)?.name).filter(Boolean),
      voteCount: top,
      quip: null,
    };
  });

  const awarded = results.filter((r) => r.winnerNames.length > 0);
  if (awarded.length > 0) {
    try {
      const quips = await narrateSuperlativeResults({ results: awarded });
      quips.forEach((entry, i) => {
        if (!entry?.quip) return;
        // Prefer matching on id, but fall back to position — the prompt asks
        // for the same order, and an id mismatch previously dropped every
        // quip silently rather than degrading to "mostly right".
        const match =
          results.find((r) => r.id === entry.id) ??
          results.find((r) => r.title === entry.id) ??
          awarded[i];
        if (match) match.quip = entry.quip;
      });
    } catch {
      // The quips are flavor. If Claude fails here the awards are still
      // correct and the screen still works — don't lose the results over it.
    }
  }

  game.postGame.results = results;
  return game;
}
