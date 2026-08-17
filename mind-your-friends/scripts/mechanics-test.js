// Regression suite for the August 12 playtest changes (CLAUDE.md item 37):
// open answering, the reading window, round-per-rule assignment, and the
// lazy fact bank.
//
// Costs ZERO API calls. A fake Anthropic client (__setClientForTests) answers
// both kinds of call this exercises — fact fetches and answer evaluations —
// keyed off the prompt, with controllable latency. That's what lets the
// concurrency and ordering claims actually be asserted instead of assumed:
// "first correct wins" is a race, and a race can't be tested against a real
// API whose response times are the thing under test.
//
// Replaces scripts/start-progress-test.js, whose subject (a blocking
// fact-bank build at game start) no longer exists.
//
// Run: node scripts/mechanics-test.js

import { __setClientForTests } from '../lib/claudeClient.js';
import {
  createGame,
  addPlayer,
  registerPlayer,
  startGame,
  prefetchFactBank,
  ensureCategoryFacts,
  pickCategory,
  setWager,
  resolveCardSlot,
  runQuestionPhase,
  submitAnswer,
  lockAnswer,
  buzzIn,
  passAnswer,
  expireActiveWindow,
  expireAnswerWindow,
  getAnswerWindowMs,
  getActiveWindowSeconds,
  getBuzzPoints,
  nextTurn,
  playerView,
  currentRoundNumber,
} from '../lib/gameState.js';
import {
  CATEGORIES_PER_PLAYER,
  BUZZ_WAGER_SHARE,
  ACTIVE_WINDOW_SECONDS,
  ACTIVE_WINDOW_MAX_SHARE,
  READING_SECONDS,
  QUESTIONS_PER_ROUND,
  CATEGORIES_PER_FETCH_BATCH,
} from '../lib/constants.js';
import { BASE_TIMER_SECONDS, ROUND_RULES } from '../lib/roundRules.js';
import { REBUS_PIECES, REBUS_PUZZLES, resolveRebus, pickRebusPuzzle } from '../lib/rebusData.js';
import { roundConstraints } from '../lib/coherence.js';

let failures = 0;
function check(condition, description) {
  console.log(`  ${condition ? 'PASS' : 'FAIL'}  ${description}`);
  if (!condition) failures += 1;
}

const CORRECT_ANSWER = 'Correct Answer';

// One fake client serves both call types. Fact prompts start with "You are an
// expert researcher"; evaluation prompts start with "Question:". Anything
// else would be a call this suite doesn't know about, so it throws rather
// than silently returning nonsense.
function fakeClient({ latencyMs = 0 } = {}) {
  const state = { factCalls: 0, evalCalls: 0, inFlight: 0, concurrentPeak: 0, evalOrder: [] };
  return {
    state,
    messages: {
      create: async ({ messages }) => {
        const prompt = messages[0].content;
        state.inFlight += 1;
        state.concurrentPeak = Math.max(state.concurrentPeak, state.inFlight);
        if (latencyMs) await new Promise((r) => setTimeout(r, latencyMs));
        state.inFlight -= 1;

        if (prompt.startsWith('You are an expert researcher')) {
          state.factCalls += 1;
          const names = [...prompt.split('\n')[0].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
          const out = {};
          for (const name of names) {
            out[name] = Array.from({ length: 10 }, (_, i) => ({
              fact: `Fact ${i} about ${name}`,
              answer: CORRECT_ANSWER,
              bucket: (i % 5) + 1,
              difficulty: 'easy',
              answerWordCount: 2,
              questionAngles: ['naming'],
              sourceType: 'encyclopedia',
            }));
          }
          return { content: [{ text: JSON.stringify(out) }] };
        }

        if (prompt.startsWith('Question:')) {
          state.evalCalls += 1;
          const given = prompt.match(/Player's answer: (.*)/)[1];
          // Compare against the expected answer carried in the prompt rather
          // than a fixed string: rebus rounds supply their own answers, and
          // hardcoding one would make every rebus attempt read as wrong.
          const expected = prompt.match(/Expected answer: (.*)/)[1];
          state.evalOrder.push(given);
          return {
            content: [{
              text: JSON.stringify({
                correct: given.trim().toLowerCase() === expected.trim().toLowerCase(),
                feedback: `You said ${given}`,
              }),
            }],
          };
        }

        // Question generation.
        state.inFlight += 0;
        return {
          content: [{
            text: JSON.stringify({
              question: 'Who did the thing in the place at the time?',
              answer: CORRECT_ANSWER,
              hostQuip: 'Here we go.',
            }),
          }],
        };
      },
    },
  };
}

function registeredGame() {
  const game = createGame('p1', 'Alice');
  addPlayer(game, 'p2', 'Bob');
  addPlayer(game, 'p3', 'Cara');
  const cats = (prefix) =>
    Array.from({ length: CATEGORIES_PER_PLAYER }, (_, n) => `${prefix} Cat ${n + 1}`);
  registerPlayer(game, 'p1', { categories: cats('Alice'), pickedCardId: 'insurance' });
  registerPlayer(game, 'p2', { categories: cats('Bob'), pickedCardId: 'insurance' });
  registerPlayer(game, 'p3', { categories: cats('Cara'), pickedCardId: 'skip' });
  return game;
}

// Drives a game from CATEGORY to an ANSWER phase with the reading window
// already elapsed. The answerer's exclusive window is still live, so this is
// the state Flow B's own assertions need.
async function toActiveWindow(game, { category, wager = 200 } = {}) {
  const pick = category ?? game.categoryOptions[0].category;
  pickCategory(game, game.players[game.activePlayerIndex].id, pick);
  const wagerPlayer = game.players[(game.activePlayerIndex + 1) % game.players.length];
  setWager(game, wagerPlayer.id, wager);
  await resolveCardSlot(game);
  await runQuestionPhase(game);
  game.answerOpensAt = 0; // reading window over
  return game;
}

// …and on to the buzzer being open to the whole room, for the assertions
// about what happens once anyone can answer.
async function toOpenAnswer(game, opts = {}) {
  await toActiveWindow(game, opts);
  game.buzzOpensAt = 0; // exclusive window over
  return game;
}

async function main() {
  // --- Start is instant, and costs nothing --------------------------------
  console.log('\n--- Instant start + lazy fact bank ---');
  {
    const fake = fakeClient();
    __setClientForTests(fake);
    const game = registeredGame();

    const started = Date.now();
    startGame(game);
    const elapsed = Date.now() - started;

    check(game.phase === 'CATEGORY', `start lands straight on CATEGORY (got ${game.phase})`);
    check(elapsed < 50, `start is instant (${elapsed}ms)`);
    check(fake.state.factCalls === 0, `no facts fetched at start (got ${fake.state.factCalls} calls)`);
    check(Object.keys(game.factBank).length === 0, 'fact bank starts empty');
    check(game.categoryOptions.length > 0, 'category options are ready immediately');

    // The prefetch fills it in behind the game.
    await prefetchFactBank(game);
    const unique = new Set(game.players.flatMap((p) => p.categories)).size;
    check(Object.keys(game.factBank).length === unique,
      `prefetch warmed all ${unique} categories (got ${Object.keys(game.factBank).length})`);
    check(fake.state.factCalls === Math.ceil(unique / CATEGORIES_PER_FETCH_BATCH),
      `prefetch batched the fetches (${fake.state.factCalls} calls for ${unique} categories)`);
  }

  // --- A picked category is never paid for twice --------------------------
  console.log('\n--- Fetch de-duplication ---');
  {
    const fake = fakeClient({ latencyMs: 40 });
    __setClientForTests(fake);
    const game = registeredGame();
    startGame(game);

    const category = game.players[0].categories[0];
    // The pick and the prefetch target the same category at the same instant
    // — the exact collision the game creates every single turn.
    const a = ensureCategoryFacts(game, category);
    const b = prefetchFactBank(game);
    const c = ensureCategoryFacts(game, category);
    await Promise.all([a, b, c]);

    const unique = new Set(game.players.flatMap((p) => p.categories)).size;
    check(fake.state.factCalls <= Math.ceil(unique / CATEGORIES_PER_FETCH_BATCH) + 1,
      `overlapping fetches didn't double-pay (${fake.state.factCalls} calls)`);
    check(!!game.factBank[category], 'the contended category ended up in the bank');

    // Already warm — this must not spend anything at all.
    const before = fake.state.factCalls;
    await ensureCategoryFacts(game, category);
    check(fake.state.factCalls === before, 'a warm category costs nothing');
  }

  // --- The reading window ------------------------------------------------
  console.log('\n--- Reading window ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);

    pickCategory(game, game.players[0].id, game.categoryOptions[0].category);
    setWager(game, game.players[1].id, 200);
    await resolveCardSlot(game);
    await runQuestionPhase(game);

    check(game.phase === 'ANSWER', `question lands in ANSWER (got ${game.phase})`);
    const readingMs = game.answerOpensAt - Date.now();
    check(readingMs > (READING_SECONDS - 1) * 1000,
      `buzzers open ~${READING_SECONDS}s after the question (${Math.round(readingMs / 1000)}s)`);

    let threw = null;
    try {
      await submitAnswer(game, 'p1', CORRECT_ANSWER, 'text');
    } catch (err) {
      threw = err;
    }
    check(threw !== null, 'answering during the reading window is rejected');
    check(Object.keys(game.answerAttempts).length === 0,
      'a rejected early answer does not burn the attempt');
    check(game.players[0].score === 0, 'and scores nothing');

    // The window covers reading AND answering, so the server arms one timer.
    const expected = (READING_SECONDS + BASE_TIMER_SECONDS) * 1000;
    check(getAnswerWindowMs(game) === expected,
      `answer window is reading + answer time (${getAnswerWindowMs(game)}ms of ${expected}ms)`);
    check(BASE_TIMER_SECONDS === 40, `answer clock doubled to 40s (got ${BASE_TIMER_SECONDS}s)`);
  }

  // --- Flow B: the answerer's exclusive window -----------------------------
  console.log('\n--- Flow B: first refusal ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);
    await toActiveWindow(game, { wager: 300 });

    const answerer = game.players[game.answererIndex];
    const other = game.players.find((p) => p.id !== answerer.id);

    // The window is carved OUT of the answer clock, not added to it.
    check(getAnswerWindowMs(game) === (READING_SECONDS + BASE_TIMER_SECONDS) * 1000,
      'the exclusive window does not lengthen the question');
    check(getActiveWindowSeconds(game) === ACTIVE_WINDOW_SECONDS,
      `a 40s clock gives the full ${ACTIVE_WINDOW_SECONDS}s window (got ${getActiveWindowSeconds(game)}s)`);

    // Nobody else can play a locked answer while it is still the answerer's.
    lockAnswer(game, other.id, CORRECT_ANSWER, 'text');
    let threw = null;
    try {
      await buzzIn(game, other.id);
    } catch (err) {
      threw = err;
    }
    check(threw !== null, 'buzzing during the exclusive window is rejected');
    check(game.phase === 'ANSWER', 'and does not take the question');
    check(other.score === 0, 'and pays nothing');

    // The answerer takes their own question for the full wager.
    await submitAnswer(game, answerer.id, CORRECT_ANSWER, 'text');
    check(game.phase === 'RESULT', 'the answerer answering correctly ends it');
    check(answerer.score === 300, `and wins the whole wager (${answerer.score})`);
    check(game.lastResult.buzzedIn === false, 'nobody buzzed in');
    check(game.lastResult.unplayedAnswers.length === 1,
      'the answer that never got played is revealed');
    check(game.lastResult.unplayedAnswers[0].answer === CORRECT_ANSWER,
      'including what it actually was — "you HAD it" is the point');
  }

  // --- The 25% cap ---------------------------------------------------------
  console.log('\n--- Exclusive window is capped ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);
    game.roundRule = ROUND_RULES.lightningRound;
    game.roundConstraints = roundConstraints(game.roundRule);
    await toActiveWindow(game, { wager: 200 });

    const clock = ROUND_RULES.lightningRound.timerSeconds;
    const window = getActiveWindowSeconds(game);
    check(window === Math.round(clock * ACTIVE_WINDOW_MAX_SHARE),
      `a halved clock gets a capped window, not ${ACTIVE_WINDOW_SECONDS}s (${window}s of ${clock}s)`);
    check(window < ACTIVE_WINDOW_SECONDS,
      'so a short round never becomes mostly-exclusive');
  }

  // --- Passing is free, freezing is not ------------------------------------
  console.log('\n--- Pass vs freeze ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);
    await toActiveWindow(game, { wager: 400 });

    const answerer = game.players[game.answererIndex];
    const other = game.players.find((p) => p.id !== answerer.id);
    lockAnswer(game, other.id, CORRECT_ANSWER, 'text');

    passAnswer(game, answerer.id);
    check(answerer.score === 0, `folding costs nothing (${answerer.score})`);
    check(game.buzzOpensAt <= Date.now(),
      'and opens the buzzer at once — no waiting out a declined window');
    check(game.lockClosesAt > Date.now(),
      'but does NOT slam the lock window shut on everyone still typing');

    await buzzIn(game, other.id);
    check(game.phase === 'RESULT', 'the room can then take it');
    check(other.score === getBuzzPoints(game), `for the buzz share (${other.score})`);
    check(game.lastResult.activeOutcome === 'passed', 'the result records a fold, not a forfeit');
    check(game.lastResult.wagerLost === false, 'and does not report points the answerer kept');
  }

  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);
    await toActiveWindow(game, { wager: 400 });

    const answerer = game.players[game.answererIndex];
    const other = game.players.find((p) => p.id !== answerer.id);
    lockAnswer(game, other.id, 'nope', 'text');

    game.lockClosesAt = 0; // the exclusive window runs out
    expireActiveWindow(game);
    check(answerer.score === -400,
      `freezing costs the wager, exactly like a wrong answer (${answerer.score})`);
    check(game.phase === 'ANSWER', 'and the room still gets its shot');

    // The charge happens once, not again when the whole window closes.
    expireAnswerWindow(game);
    check(answerer.score === -400, `and is never charged twice (${answerer.score})`);
    check(game.lastResult.activeOutcome === 'timedOut', 'the result tells a freeze from a fold');
    check(game.lastResult.wagerLost === true, 'and reports the wager as lost');
  }

  // --- Pre-committed answers ----------------------------------------------
  console.log('\n--- Locked answers ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);
    await toActiveWindow(game, { wager: 200 });

    const answerer = game.players[game.answererIndex];
    const [first, second] = game.players.filter((p) => p.id !== answerer.id);

    lockAnswer(game, first.id, CORRECT_ANSWER, 'text');
    let threw = null;
    try {
      lockAnswer(game, first.id, 'changed my mind', 'text');
    } catch (err) {
      threw = err;
    }
    check(threw !== null, 'a locked answer cannot be revised');
    check(game.lockedAnswers[first.id].answer === CORRECT_ANSWER, 'the original stands');

    // Nobody sees anybody else's commitment while the question is live.
    const view = playerView(game, second.id);
    check(view.lockedCount === 1, 'the room sees how many are ready');
    check(view.myLockedAnswer === null, 'but not what they said');
    check(view.iCanLock === true, 'a player who has not committed still can');
    check(playerView(game, first.id).iCanBuzz === true, 'a committed player can buzz');
    check(playerView(game, second.id).iCanBuzz === false, 'an uncommitted one cannot');

    // Locking closes with the exclusive window, and never reopens.
    game.lockClosesAt = 0;
    game.buzzOpensAt = 0;
    threw = null;
    try {
      lockAnswer(game, second.id, CORRECT_ANSWER, 'text');
    } catch (err) {
      threw = err;
    }
    check(threw !== null,
      'no locking in after the buzzer opens — that is the lookup window this closes');
    threw = null;
    try {
      await buzzIn(game, second.id);
    } catch (err) {
      threw = err;
    }
    check(threw !== null, 'and no answer means no buzz at all');

    await buzzIn(game, first.id);
    check(game.phase === 'RESULT', 'the committed player takes it');
    check(first.score === getBuzzPoints(game), `for the buzz share (${first.score})`);
  }

  // --- The buzz share ------------------------------------------------------
  console.log('\n--- Buzz payout scales with the wager ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);
    await toOpenAnswer(game, { wager: 400 });

    check(getBuzzPoints(game) === 300, `0.75 x 400 = ${getBuzzPoints(game)}`);
    check(getBuzzPoints(game) < game.currentWager,
      'a buzz never out-earns the wager it was played for — otherwise being the active player is strictly worse');
    check(BUZZ_WAGER_SHARE < 1, 'the share is below 1 by design');

    game.currentWager = 250;
    check(getBuzzPoints(game) % 5 === 0,
      `and rounds to something a scoreboard can show (${getBuzzPoints(game)})`);
  }

  // --- One shot each, and a wrong shot is free for non-active players -----
  console.log('\n--- One attempt each ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);
    await toActiveWindow(game, { wager: 200 });

    const answerer = game.players[game.answererIndex];
    const [first, second] = game.players.filter((p) => p.id !== answerer.id);
    lockAnswer(game, first.id, 'wrong', 'text');
    lockAnswer(game, second.id, CORRECT_ANSWER, 'text');
    game.lockClosesAt = 0;
    game.buzzOpensAt = 0;

    await buzzIn(game, first.id);
    check(first.score === 0, `a non-active player risks nothing (${first.score})`);
    check(game.phase === 'ANSWER', 'a wrong buzz does not end the question');

    let threw = null;
    try {
      await buzzIn(game, first.id);
    } catch (err) {
      threw = err;
    }
    check(threw !== null, 'a second attempt from the same player is rejected');

    const view = playerView(game, first.id);
    check(view.iCanBuzz === false, 'the view tells that player they are locked out');
    check(view.spentAttempts.length === 1, 'the room sees who has already swung');
    check(view.spentAttempts[0].answer === undefined,
      "but not what they played — nobody can copy a neighbour's wording");

    await buzzIn(game, second.id);
    check(game.phase === 'RESULT', 'the first correct buzz ends it');
    check(second.score === getBuzzPoints(game), `and is paid the share (${second.score})`);
    check(game.lastResult.buzzedIn === true, 'the result records that someone buzzed in');
  }

  // --- Everyone misses ----------------------------------------------------
  console.log('\n--- Nobody gets it ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);
    await toActiveWindow(game, { wager: 150 });

    const answerer = game.players[game.answererIndex];
    for (const p of game.players) {
      if (p.id !== answerer.id) lockAnswer(game, p.id, 'wrong', 'text');
    }
    await submitAnswer(game, answerer.id, 'nope', 'text');
    check(answerer.score === -150, `the active player pays for being wrong (${answerer.score})`);
    check(game.phase === 'ANSWER', 'and the buzzer opens rather than ending the turn');

    for (const p of game.players) {
      if (game.phase === 'ANSWER' && p.id !== answerer.id) await buzzIn(game, p.id);
    }
    check(game.phase === 'RESULT', 'the question ends once everyone has had a shot');
    check(game.lastResult.correct === false, 'and is recorded as unclaimed');
    check(game.players.filter((p) => p.score === 0).length === 2, 'the other two are untouched');
  }

  // --- Nobody committed ----------------------------------------------------
  console.log('\n--- No locked answers, no dead air ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);
    await toActiveWindow(game, { wager: 250 });

    const answerer = game.players[game.answererIndex];
    await submitAnswer(game, answerer.id, 'nope', 'text');
    check(game.phase === 'ANSWER', 'still open while locking is live');

    game.lockClosesAt = 0;
    expireActiveWindow(game);
    check(game.phase === 'RESULT',
      'with nobody holding an answer the question ends instead of running the clock down');
    check(answerer.score === -250, `and the wrong answer still cost the wager (${answerer.score})`);
  }

  // --- Timing out costs the same as answering wrong -----------------------
  console.log('\n--- Timeout ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);
    await toOpenAnswer(game, { wager: 250 });

    const answerer = game.players[game.answererIndex];
    expireAnswerWindow(game);
    check(game.phase === 'RESULT', 'the window closing ends the question');
    check(answerer.score === -250,
      `saying nothing costs the same as being wrong (${answerer.score}) — otherwise stalling is free`);
  }

  // --- First CORRECT wins, decided by buzz order --------------------------
  console.log('\n--- Race resolution ---');
  {
    // Evaluations take real time here, so two correct answers are genuinely
    // in flight at once. Buzz order must decide it, not whichever Claude
    // call happens to come back first.
    const fake = fakeClient({ latencyMs: 60 });
    __setClientForTests(fake);
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);
    await toActiveWindow(game, { wager: 200 });

    const answerer = game.players[game.answererIndex];
    const [first, second] = game.players.filter((p) => p.id !== answerer.id);
    lockAnswer(game, first.id, CORRECT_ANSWER, 'text');
    lockAnswer(game, second.id, CORRECT_ANSWER, 'text');
    game.lockClosesAt = 0;
    game.buzzOpensAt = 0;

    const a = buzzIn(game, first.id);
    const b = buzzIn(game, second.id).catch(() => {});
    await Promise.all([a, b]);

    check(game.lastResult.winnerId === first.id,
      `the earlier buzz won (${game.lastResult.winnerName})`);
    check(second.score === 0, `the later one was not also paid (${second.score})`);
    check(first.score === getBuzzPoints(game), `exactly one player was paid (${first.score})`);
  }

  // --- Round rules --------------------------------------------------------
  console.log('\n--- Round rules ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);

    check(currentRoundNumber(game) === 1, 'the game opens on round 1');
    check(game.roundRule.id === 'none', `round 1 has no rule (got ${game.roundRule.id})`);
    check(game.roundAnnouncement?.round === 1, 'round 1 is still announced');
    check(playerView(game, 'p1').roundAnnouncement !== null, 'and the announcement reaches clients');

    // The announcement gets one turn, then clears; the rule itself persists.
    game.phase = 'RESULT';
    game.lastResult = { correct: true, wager: 0 };
    nextTurn(game);
    check(game.roundAnnouncement === null, 'the announcement clears after one turn');
    check(game.roundRule.id === 'none', 'but the round rule stays put mid-round');

    // Walk to the end of round 1.
    while (currentRoundNumber(game) === 1) {
      game.phase = 'RESULT';
      game.lastResult = { correct: true, wager: 0 };
      nextTurn(game);
    }
    check(currentRoundNumber(game) === 2, 'round 2 begins after QUESTIONS_PER_ROUND questions');
    check(game.roundRule.id !== 'none', `round 2 has a real rule (${game.roundRule.id})`);
    check(game.roundAnnouncement?.ruleId === game.roundRule.id, 'and it is announced');
    check(!!ROUND_RULES[game.roundRule.id], 'the announced rule is a real rule');

    const round2Rule = game.roundRule.id;
    let sawChange = false;
    while (game.phase !== 'GAME_OVER' && currentRoundNumber(game) === 2) {
      game.phase = 'RESULT';
      game.lastResult = { correct: true, wager: 0 };
      nextTurn(game);
    }
    if (game.phase !== 'GAME_OVER') {
      sawChange = game.roundRule.id !== round2Rule;
      check(sawChange, `round 3 drew a different rule (${round2Rule} -> ${game.roundRule.id})`);
    } else {
      console.log('  SKIP  round 3 — game length is configured to end first');
    }
  }

  // --- Rebus round ---------------------------------------------------------
  console.log('\n--- Rebus data integrity ---');
  {
    // These assertions are the reason the curated bank is safe to trust. A
    // rebus whose pieces don't reconstruct its answer is unsolvable, and
    // nobody would notice until a real room sat staring at it.
    let unknownPieces = 0;
    let literalMismatches = 0;
    for (const puzzle of REBUS_PUZZLES) {
      let parts;
      try {
        parts = resolveRebus(puzzle);
      } catch {
        unknownPieces += 1;
        continue;
      }
      if (puzzle.phonetic) continue;
      const built = parts.map((p) => p.reads).join('').toUpperCase();
      const want = puzzle.answer.toUpperCase().replace(/[^A-Z]/g, '');
      if (built !== want) {
        console.log(`    "${puzzle.answer}" builds "${built}"`);
        literalMismatches += 1;
      }
    }
    check(unknownPieces === 0, `every puzzle resolves its pieces (${unknownPieces} broken)`);
    check(literalMismatches === 0,
      `every non-phonetic puzzle spells its answer exactly (${literalMismatches} mismatched)`);
    check(REBUS_PUZZLES.length >= QUESTIONS_PER_ROUND,
      `bank has enough puzzles for a full round (${REBUS_PUZZLES.length} vs ${QUESTIONS_PER_ROUND})`);
    check(REBUS_PUZZLES.every((p) => p.hint && p.hint.length > 0),
      'every puzzle has a hint — without one a rebus has no way in');

    const usedKeys = new Set(REBUS_PUZZLES.flatMap((p) => p.pieces));
    const orphans = Object.keys(REBUS_PIECES).filter((k) => !usedKeys.has(k));
    check(orphans.length === 0, `no orphaned pieces in the library (${orphans.join(', ') || 'none'})`);
  }

  console.log('\n--- Rebus round play ---');
  {
    __setClientForTests(fakeClient());
    const game = registeredGame();
    startGame(game);
    await prefetchFactBank(game);

    // Force the round rule, same convention as previous round-rule work.
    // Constraints have to be recomputed with it — they're derived at round
    // start, so swapping the rule alone leaves them describing the old one.
    game.roundRule = ROUND_RULES.rebus;
    game.roundConstraints = roundConstraints(game.roundRule);
    await toOpenAnswer(game, { wager: 200 });

    check(game.phase === 'ANSWER', `a rebus turn reaches ANSWER (got ${game.phase})`);
    check(!!game.currentQuestion.rebus, 'the question carries a rebus');
    check(game.currentQuestion.rebus.pieces.length >= 2, 'with at least two pieces');

    // The solution must not ride along with the puzzle.
    const midView = playerView(game, 'p1');
    check(!!midView.rebus, 'the client is sent the puzzle');
    check(midView.rebus.reads === undefined,
      'but NOT the readings — those spell the answer out');
    check(midView.answer === undefined, 'and not the answer itself');

    const answer = game.currentQuestion.answer;
    await submitAnswer(game, 'p1', answer, 'text');
    check(game.phase === 'RESULT', 'solving it ends the question');

    const revealView = playerView(game, 'p1');
    check(Array.isArray(revealView.rebus.reads),
      'the reveal includes the decomposition — otherwise a player who missed it never learns why');
    check(revealView.rebus.reads.length === revealView.rebus.pieces.length,
      'one reading per piece');
  }

  console.log('\n--- Rebus repeats ---');
  {
    const used = [];
    for (let i = 0; i < QUESTIONS_PER_ROUND; i++) {
      const puzzle = pickRebusPuzzle(used);
      used.push(puzzle.answer);
    }
    check(new Set(used).size === used.length,
      `a full round draws ${used.length} different puzzles`);
  }

  __setClientForTests(null);
  console.log(failures === 0 ? '\n=== ALL PASSED ===' : `\n=== ${failures} FAILED ===`);
  process.exit(failures === 0 ? 0 : 1);
}

main();
