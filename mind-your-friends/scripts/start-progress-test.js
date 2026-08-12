// Focused test for the game-start progress state and the concurrent
// fact-bank build (CLAUDE.md item 36).
//
// Costs ZERO API calls: it swaps a fake Anthropic client into claudeClient
// (__setClientForTests) with controllable latency, which is the only way to
// assert the two things that actually matter here — that the batches run
// concurrently rather than in sequence, and that a progress state reaches
// playerView() BEFORE the first Claude call rather than after the last one.
// A real fact-bank build would prove neither and would cost 5 calls a run.
//
// Run: node scripts/start-progress-test.js

import { __setClientForTests } from '../lib/claudeClient.js';
import {
  createGame,
  addPlayer,
  registerPlayer,
  startGame,
  playerView,
} from '../lib/gameState.js';
import { CATEGORIES_PER_FETCH_BATCH } from '../lib/constants.js';

let failures = 0;
function check(condition, description) {
  console.log(`  ${condition ? 'PASS' : 'FAIL'}  ${description}`);
  if (!condition) failures += 1;
}

const BATCH_LATENCY_MS = 200;

// Stands in for the Anthropic SDK client: same `messages.create` shape, a
// fixed delay per call, and a reply built from whichever categories the
// prompt mentions so the merge behaviour is real rather than stubbed.
function fakeClient({ latencyMs = BATCH_LATENCY_MS, failOnCall = 0 } = {}) {
  const state = { calls: 0, concurrentPeak: 0, inFlight: 0 };
  return {
    state,
    messages: {
      create: async ({ messages }) => {
        state.calls += 1;
        const thisCall = state.calls;
        state.inFlight += 1;
        state.concurrentPeak = Math.max(state.concurrentPeak, state.inFlight);
        await new Promise((resolve) => setTimeout(resolve, latencyMs));
        state.inFlight -= 1;
        if (failOnCall === thisCall) throw new Error('simulated batch failure');

        // Recover the batch's categories from the prompt, the same way a real
        // reply would be keyed by them.
        const prompt = messages[0].content;
        const header = prompt.split('\n')[0];
        const names = [...header.matchAll(/"([^"]+)"/g)].map((m) => m[1]);
        const out = {};
        for (const name of names) {
          out[name] = [{
            fact: `A fact about ${name}`,
            answer: name,
            bucket: 1,
            difficulty: 'easy',
            answerWordCount: 1,
            questionAngles: ['naming'],
            sourceType: 'encyclopedia',
          }];
        }
        return { content: [{ text: JSON.stringify(out) }] };
      },
    },
  };
}

// 3 players x 5 categories = 15 unique categories = 5 batches, the exact
// shape CLAUDE.md item 36 measured at 250s.
function registeredGame() {
  const game = createGame('p1', 'Alice');
  addPlayer(game, 'p2', 'Bob');
  addPlayer(game, 'p3', 'Cara');
  const cats = (prefix) => [1, 2, 3, 4, 5].map((n) => `${prefix} Category ${n}`);
  registerPlayer(game, 'p1', { categories: cats('Alice'), pickedCardId: 'insurance' });
  registerPlayer(game, 'p2', { categories: cats('Bob'), pickedCardId: 'insurance' });
  registerPlayer(game, 'p3', { categories: cats('Cara'), pickedCardId: 'skip' });
  return game;
}

const EXPECTED_BATCHES = Math.ceil(15 / CATEGORIES_PER_FETCH_BATCH);

async function main() {
  // --- Part 1: the batches run concurrently -------------------------------
  console.log('\n--- Concurrent fact-bank build ---');
  {
    const fake = fakeClient();
    __setClientForTests(fake);
    const game = registeredGame();

    const started = Date.now();
    await startGame(game);
    const elapsed = Date.now() - started;

    check(fake.state.calls === EXPECTED_BATCHES,
      `15 categories became ${EXPECTED_BATCHES} batches (got ${fake.state.calls})`);
    check(fake.state.concurrentPeak === EXPECTED_BATCHES,
      `all ${EXPECTED_BATCHES} batches were in flight at once (peak ${fake.state.concurrentPeak})`);
    // Sequential would be 5 x 200ms = 1000ms+; concurrent is one batch's
    // latency plus overhead. The gap is wide enough that a slow machine
    // can't produce a false pass.
    check(elapsed < BATCH_LATENCY_MS * 2.5,
      `finished in one batch's latency, not five (${elapsed}ms, sequential would be ~${BATCH_LATENCY_MS * EXPECTED_BATCHES}ms)`);
    check(Object.keys(game.factBank).length === 15,
      `fact bank merged all 15 categories (got ${Object.keys(game.factBank).length})`);
    check(game.phase === 'CATEGORY', `phase advanced to CATEGORY (got ${game.phase})`);
  }

  // --- Part 2: progress reaches clients before the first Claude call ------
  console.log('\n--- Progress state ---');
  {
    const fake = fakeClient();
    __setClientForTests(fake);
    const game = registeredGame();

    const pushes = [];
    const promise = startGame(game, (g) => {
      // Record what a client would actually receive, not the raw game object.
      pushes.push(playerView(g, 'p1').startProgress);
    });

    // Everything below this line is asserted BEFORE awaiting the promise, so
    // it describes what a client sees at the instant the build starts rather
    // than ~50s later. That immediacy is the whole fix for "Start Game does
    // nothing": two progress pushes (the opener, then the (0, total) report)
    // are already out the door, and every batch request is already in flight
    // with none of them returned yet.
    check(pushes.length === 2, `progress pushed before any batch returned (got ${pushes.length} pushes)`);
    check(pushes.every((p) => p?.active === true), 'both opening pushes have active: true');
    check(typeof pushes[0]?.label === 'string' && pushes[0].label.length > 0,
      `the first push carries a label (got "${pushes[0]?.label}")`);
    check(pushes[1]?.total === EXPECTED_BATCHES,
      `the client learns the batch count up front (total=${pushes[1]?.total})`);
    check(fake.state.inFlight === EXPECTED_BATCHES && fake.state.calls === EXPECTED_BATCHES,
      `all ${EXPECTED_BATCHES} batches were dispatched and none had returned (in flight: ${fake.state.inFlight})`);

    await promise;

    // 1 initial + 1 for the (0, total) report + one per completed batch.
    check(pushes.length === EXPECTED_BATCHES + 2,
      `one push per batch plus the two openers (got ${pushes.length})`);
    const totals = pushes.map((p) => p?.total).filter((t) => t > 0);
    check(totals.every((t) => t === EXPECTED_BATCHES),
      `every push after the opener reports total=${EXPECTED_BATCHES}`);
    const completions = pushes.map((p) => p?.completed ?? 0);
    check(Math.max(...completions) === EXPECTED_BATCHES,
      `progress reached ${EXPECTED_BATCHES}/${EXPECTED_BATCHES} (got ${Math.max(...completions)})`);
    check(completions.every((c, i) => i === 0 || c >= completions[i - 1]),
      'completed count never goes backwards');
    check(pushes.every((p) => p !== null && p.active === true),
      'every push during the build is active — the clearing push comes from the server, not startGame');

    check(game.startProgress === null, 'startProgress is cleared once the game starts');
    check(playerView(game, 'p1').startProgress === null,
      'playerView reports startProgress: null after the build');
  }

  // --- Part 3: a failed build clears the progress state -------------------
  console.log('\n--- Failure path ---');
  {
    const fake = fakeClient({ failOnCall: 2 });
    __setClientForTests(fake);
    const game = registeredGame();

    let threw = null;
    try {
      await startGame(game, () => {});
    } catch (err) {
      threw = err;
    }

    check(threw !== null, 'a failing batch still rejects startGame');
    check(game.startProgress === null,
      'startProgress is cleared on failure — the lobby must not freeze on a bar that never advances');
    check(game.phase === 'LOBBY', `phase stayed LOBBY on failure (got ${game.phase})`);
  }

  // --- Part 4: progress is never left set by a rejected precondition ------
  console.log('\n--- Precondition guard ---');
  {
    __setClientForTests(fakeClient());
    const game = createGame('p1', 'Alice');
    addPlayer(game, 'p2', 'Bob');

    let threw = null;
    try {
      await startGame(game, () => {});
    } catch (err) {
      threw = err;
    }
    check(threw !== null, 'starting with unregistered players still throws');
    check(game.startProgress === null,
      'the registration check runs before any progress state is set');
  }

  __setClientForTests(null);

  console.log(failures === 0 ? '\n=== ALL PASSED ===' : `\n=== ${failures} FAILED ===`);
  process.exit(failures === 0 ? 0 : 1);
}

main();
