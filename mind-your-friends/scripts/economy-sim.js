// What is a point worth? — a Monte Carlo model of MYF's scoring economy.
//
// This exists because "is 100 a lot or a little?" is not answerable by
// staring at the constant. The wager range, the buzz payout and the game
// length only mean anything relative to each other, and that relationship is
// arithmetic, not taste. This prints it.
//
// Run: node scripts/economy-sim.js
//
// SCOPE, stated plainly. This is NOT a test of the state machine — it does
// not call gameState.js, and passing here proves nothing about the code.
// It models the SCORING RULES: who can win what, how often. The payout
// formula itself is imported from lib/constants.js rather than copied, so
// that one number can't drift; everything else here is a behavioural
// assumption, and every assumption is a named knob below.
//
// Costs zero API calls.

import {
  ROUNDS,
  QUESTIONS_PER_ROUND,
  TOTAL_QUESTIONS,
  MIN_WAGER,
  MAX_WAGER,
  WAGER_TIERS,
  WAGER_VALUES,
  BUZZ_WAGER_SHARE,
  buzzPointsForWager,
} from '../lib/constants.js';

// --- Behavioural assumptions ------------------------------------------------
// Deliberately explicit: the conclusions below are only as good as these, and
// the honest way to argue with a result is to argue with one of these numbers.
const ASSUMPTIONS = {
  players: 4,
  // Chance any given player knows any given question. Trivia aimed at a
  // casual party audience; the room is not a quiz team.
  pKnow: 0.5,
  // When the answerer doesn't know it, how often they fold rather than
  // guessing or freezing.
  pPass: 0.35,
  // How often a non-answerer bothers committing an answer during the
  // exclusive window. They commit whether or not they're sure — a guess is
  // free — so this is about engagement, not knowledge.
  pLock: 0.7,
  games: 20000,
};

// Wager-setting policies over the five-rung ladder. The setter is adversarial
// by design ("I cut, you choose"), so an even draw across the tiers is the
// least realistic of these — it's here as the baseline the others read
// against.
const pick = (xs) => xs[Math.floor(Math.random() * xs.length)];
const POLICIES = {
  uniform: () => pick(WAGER_VALUES),
  // What people actually do: reach for the top of the ladder, because a big
  // number is funnier and the downside is somebody else's.
  adversarial: () => (Math.random() < 0.5 ? MAX_WAGER : pick(WAGER_VALUES)),
};

function roundTo(value, step) {
  return Math.round(value / step) * step;
}

// The live payout, unless a sweep is asking "what if it were X instead?".
// Anything but `undefined` here is a hypothetical, never what the game does.
function payout(wager, shareOverride, flatOverride) {
  if (flatOverride !== undefined) return flatOverride;
  if (shareOverride !== undefined) return roundTo(wager * shareOverride, 5);
  return buzzPointsForWager(wager);
}

function simulate({ wagerFor, players, pKnow, pPass, pLock, games, share, flat }) {
  const totals = {
    wagerWon: 0,
    wagerLost: 0,
    buzzWon: 0,
    questionsAnsweredByAnswerer: 0,
    questionsReachingBuzzer: 0,
    questionsClaimedByBuzz: 0,
    questionsUnclaimed: 0,
    questionsPassed: 0,
    finalSpreads: [],
    perPlayerBuzzShare: [],
  };

  for (let g = 0; g < games; g++) {
    const scores = new Array(players).fill(0);
    const fromBuzz = new Array(players).fill(0);
    const fromWager = new Array(players).fill(0);

    for (let q = 0; q < TOTAL_QUESTIONS; q++) {
      const answerer = q % players;
      const wager = roundTo(wagerFor(), 10);
      const buzzPoints = payout(wager, share, flat);

      if (Math.random() < pKnow) {
        scores[answerer] += wager;
        fromWager[answerer] += wager;
        totals.wagerWon += wager;
        totals.questionsAnsweredByAnswerer += 1;
        continue;
      }

      // The answerer didn't know it: fold (free) or fail (costs the wager).
      if (Math.random() < pPass) {
        totals.questionsPassed += 1;
      } else {
        scores[answerer] -= wager;
        fromWager[answerer] -= wager;
        totals.wagerLost += wager;
      }
      totals.questionsReachingBuzzer += 1;

      // Everyone else plays whatever they committed, in a random order.
      const contenders = [];
      for (let p = 0; p < players; p++) {
        if (p === answerer) continue;
        if (Math.random() < pLock) contenders.push({ p, correct: Math.random() < pKnow });
      }
      contenders.sort(() => Math.random() - 0.5);
      const winner = contenders.find((c) => c.correct);
      if (winner) {
        scores[winner.p] += buzzPoints;
        fromBuzz[winner.p] += buzzPoints;
        totals.buzzWon += buzzPoints;
        totals.questionsClaimedByBuzz += 1;
      } else {
        totals.questionsUnclaimed += 1;
      }
    }

    totals.finalSpreads.push(Math.max(...scores) - Math.min(...scores));
    for (let p = 0; p < players; p++) {
      const gross = Math.abs(fromWager[p]) + fromBuzz[p];
      if (gross > 0) totals.perPlayerBuzzShare.push(fromBuzz[p] / gross);
    }
  }

  return totals;
}

function mean(xs) {
  return xs.reduce((a, b) => a + b, 0) / xs.length;
}

function report(label, policy) {
  const t = simulate({ ...ASSUMPTIONS, wagerFor: policy });
  const { games, players } = ASSUMPTIONS;
  const perGame = (n) => (n / games).toFixed(1);
  const pct = (n) => `${(n * 100).toFixed(0)}%`;

  console.log(`\n=== ${label} wagers ===`);
  console.log(`  Questions per game: ${TOTAL_QUESTIONS} (${ROUNDS} x ${QUESTIONS_PER_ROUND}), ${players} players`);
  console.log(`  Answerer takes it:      ${perGame(t.questionsAnsweredByAnswerer)} / game`);
  console.log(`  Reaches the buzzer:     ${perGame(t.questionsReachingBuzzer)} / game  (${perGame(t.questionsPassed)} of those a fold)`);
  console.log(`  Claimed by a buzz:      ${perGame(t.questionsClaimedByBuzz)} / game`);
  console.log(`  Dies unclaimed:         ${perGame(t.questionsUnclaimed)} / game`);
  console.log('');
  console.log(`  Points won on wagers:   ${perGame(t.wagerWon)} / game`);
  console.log(`  Points lost on wagers:  ${perGame(t.wagerLost)} / game`);
  console.log(`  Points won on buzzes:   ${perGame(t.buzzWon)} / game`);
  console.log('');
  console.log(`  BUZZING IS ${pct(mean(t.perPlayerBuzzShare))} OF A TYPICAL PLAYER'S SCORE MOVEMENT`);
  console.log(`  Average winner-to-loser spread: ${Math.round(mean(t.finalSpreads))} pts`);
}

console.log(`Buzz payout: ${BUZZ_WAGER_SHARE}x the wager (${MIN_WAGER}-${MAX_WAGER} range)`);
console.log(`  a ${MIN_WAGER} wager pays a buzzer ${buzzPointsForWager(MIN_WAGER)}`);
console.log(`  a ${MAX_WAGER} wager pays a buzzer ${buzzPointsForWager(MAX_WAGER)}`);
console.log('\nAssumptions: ' + JSON.stringify(ASSUMPTIONS));

report('Uniform', POLICIES.uniform);
report('Adversarial', POLICIES.adversarial);

// --- What the range itself is doing -----------------------------------------
//
// The complaint that started this: a 50-500 slider feels arbitrary. It is
// worth seeing how much of that range is ever really used, and what a single
// question is worth against a whole game.
console.log('\n=== What one question is worth ===');
const t = simulate({ ...ASSUMPTIONS, wagerFor: POLICIES.adversarial });
const avgSpread = mean(t.finalSpreads);
for (const w of WAGER_VALUES) {
  const swing = w * 2; // winning it vs losing it
  console.log(
    `  A ${String(w).padStart(3)} wager swings ${String(swing).padStart(4)} pts ` +
      `= ${((swing / avgSpread) * 100).toFixed(0)}% of the average winning margin`
  );
}
console.log(
  `\n  If one question can swing a large fraction of the whole game, the top of\n` +
    `  the range is too big for ${TOTAL_QUESTIONS} questions — and if the smallest wager\n` +
    `  swings almost nothing, the bottom of the range is decoration.`
);

// --- How much of the game is the buzz game? ---------------------------------
//
// The one number the payout choice actually controls. Too low and buzzing is
// decorative and nobody bothers; too high and the wager — the decision the
// whole "I cut, you choose" design rests on — stops being the main event.
console.log('\n=== Buzz payout sweep ===');
console.log('  payout            buzz share of score movement   winning margin');
const sweep = [
  { label: 'flat 100', flat: 100 },
  { label: 'flat 150', flat: 150 },
  { label: '0.25x wager', share: 0.25 },
  { label: '0.50x wager', share: 0.5 },
  { label: '0.75x wager (live)', share: undefined },
  { label: '1.50x wager', share: 1.5 },
];
for (const s of sweep) {
  const r = simulate({ ...ASSUMPTIONS, wagerFor: POLICIES.adversarial, ...s });
  console.log(
    `  ${s.label.padEnd(20)}${`${(mean(r.perPlayerBuzzShare) * 100).toFixed(0)}%`.padStart(10)}` +
      `${String(Math.round(mean(r.finalSpreads))).padStart(28)}`
  );
}
console.log(
  `\n  The wager is meant to be the main event and the buzz the vulture prize.\n` +
    `  That reads as a buzz share somewhere under half — at half, the two games\n` +
    `  are co-equal and being the active player stops being the thing that\n` +
    `  decides the night.`
);
