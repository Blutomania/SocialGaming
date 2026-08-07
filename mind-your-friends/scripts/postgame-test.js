// Focused test for the post-game social layer (CLAUDE.md item 35).
//
// Deliberately does NOT play a real 24-question game: that costs ~30+ Claude
// calls to reach GAME_OVER, and none of them exercise anything this feature
// owns. Instead it builds a finished-looking game object directly and drives
// the post-game functions against it. The two Claude calls it does make
// (superlative generation + result narration) are the ones actually under test.
//
// Run: node scripts/postgame-test.js

import {
  createGame,
  addPlayer,
  nextTurn,
  beginSuperlativeVoting,
  castSuperlativeVote,
  allSuperlativeVotesIn,
  resolveSuperlatives,
  playerView,
} from '../lib/gameState.js';

let failures = 0;
function check(condition, description) {
  console.log(`  ${condition ? 'PASS' : 'FAIL'}  ${description}`);
  if (!condition) failures += 1;
}

// --- Part 1: logQuestion, across every resolution shape --------------------

function turnFixture({ roundRule, lastResult, skipped = false, lineup = null }) {
  const game = createGame('p1', 'Alice');
  addPlayer(game, 'p2', 'Bob');
  addPlayer(game, 'p3', 'Cara');
  game.phase = 'RESULT';
  game.questionIndex = 0;
  game.activePlayerIndex = 0;
  game.answererIndex = 0;
  game.currentCategory = '90s Movies';
  game.currentCategoryAttribution = { submittedBy: 'Cara', submittedById: 'p3' };
  game.currentWager = 200;
  game.roundRule = roundRule;
  game.currentQuestion = { question: 'Q?', answer: 'A', hostQuip: '', lineup };
  game.lastResult = lastResult;
  game.skippedTurn = skipped;
  return game;
}

console.log('=== logQuestion ===');

const correct = turnFixture({
  roundRule: { id: 'eli5', name: 'ELI5' },
  lastResult: { correct: true, wager: 200, playerAnswer: 'A' },
});
nextTurn(correct);
check(correct.questionLog.length === 1, 'a resolved turn is logged');
check(correct.questionLog[0].outcome === 'correct', 'correct answer -> outcome "correct"');
check(correct.questionLog[0].roomMissedIt === false, 'correct answer -> roomMissedIt false');
check(
  correct.questionLog[0].categoryAttribution === 'Cara',
  'category attribution is carried into the log'
);

const missed = turnFixture({
  roundRule: { id: 'eli5', name: 'ELI5' },
  lastResult: { correct: false, wager: 200, playerAnswer: 'nope' },
});
nextTurn(missed);
check(missed.questionLog[0].outcome === 'wrong', 'wrong answer -> outcome "wrong"');
check(missed.questionLog[0].roomMissedIt === true, 'wrong answer -> roomMissedIt true');

// The trap: claimSteal sets `stolen: true` whether the steal succeeded OR
// failed. A failed steal must not be reported as a successful one.
const stoleIt = turnFixture({
  roundRule: { id: 'steal', name: 'Steal' },
  lastResult: { correct: true, stolen: true, stealerName: 'Bob', wager: 200 },
});
nextTurn(stoleIt);
check(stoleIt.questionLog[0].outcome === 'stolen', 'successful steal -> outcome "stolen"');
check(
  stoleIt.questionLog[0].outcomeSummary.includes('Bob stole it'),
  'successful steal names the stealer'
);
check(stoleIt.questionLog[0].roomMissedIt === false, 'successful steal -> roomMissedIt false');

const failedSteal = turnFixture({
  roundRule: { id: 'steal', name: 'Steal' },
  lastResult: { correct: false, stolen: true, stealerName: 'Bob', wager: 200 },
});
nextTurn(failedSteal);
check(
  failedSteal.questionLog[0].outcome === 'wrong',
  'FAILED steal -> outcome "wrong", not "stolen"'
);
check(
  !failedSteal.questionLog[0].outcomeSummary.includes('stole it'),
  'failed steal does not claim someone stole it'
);
check(failedSteal.questionLog[0].roomMissedIt === true, 'failed steal -> roomMissedIt true');

const spotted = turnFixture({
  roundRule: { id: 'theLineup', name: 'The Lineup', lineupBased: true },
  lastResult: { correct: true, lineupWinner: true, winnerName: 'Cara', wager: 200 },
  lineup: { options: [{ id: 'o1' }], correctOptionId: 'o1' },
});
nextTurn(spotted);
check(spotted.questionLog[0].outcome === 'spotted', 'lineup win -> outcome "spotted"');
check(spotted.questionLog[0].lineup !== null, 'lineup payload is preserved in the log');

const unclaimed = turnFixture({
  roundRule: { id: 'theLineup', name: 'The Lineup', lineupBased: true },
  lastResult: { correct: false, lineupWinner: false, wager: 200 },
  lineup: { options: [{ id: 'o1' }], correctOptionId: 'o1' },
});
nextTurn(unclaimed);
check(unclaimed.questionLog[0].outcome === 'unclaimed', 'lineup expiry -> outcome "unclaimed"');
check(unclaimed.questionLog[0].roomMissedIt === true, 'lineup expiry -> roomMissedIt true');

const skippedTurn = turnFixture({
  roundRule: { id: 'eli5', name: 'ELI5' },
  lastResult: null,
  skipped: true,
});
nextTurn(skippedTurn);
check(skippedTurn.questionLog.length === 0, 'a skipped turn logs nothing');

// --- Part 2: the answer leak guard -----------------------------------------

console.log('=== playerView withholding ===');

const midGame = turnFixture({
  roundRule: { id: 'eli5', name: 'ELI5' },
  lastResult: { correct: true, wager: 200, playerAnswer: 'A' },
});
nextTurn(midGame);
midGame.phase = 'CATEGORY';
const midView = playerView(midGame, 'p1');
check(
  midView.questionLog === undefined,
  'questionLog is NOT sent mid-game (it contains every correct answer)'
);

midGame.phase = 'GAME_OVER';
const endView = playerView(midGame, 'p1');
check(Array.isArray(endView.questionLog), 'questionLog IS sent at GAME_OVER');

// --- Part 3: superlative voting (2 real Claude calls) ----------------------

console.log('=== superlative voting ===');

const game = createGame('p1', 'Alice');
addPlayer(game, 'p2', 'Bob');
addPlayer(game, 'p3', 'Cara');
game.phase = 'GAME_OVER';
game.players[0].score = 900;
game.players[1].score = 400;
game.players[2].score = 900;
game.highlightReel = [
  'Bob played Whoa Nellie — category swapped from "Geography" to Cara\'s "90s Hip Hop"!',
  'Alice wagered 400 and answered "the Nile" — wrong!',
  'Cara stole it for 400 pts!',
  'Bob played Skip — Alice\'s turn is skipped!',
  'Bob heckled: "Alice thinks Australia is a country AND a continent"',
];
game.questionLog = [
  {
    index: 0,
    question: 'What is the longest river in the world?',
    answer: 'The Nile',
    category: 'Geography',
    categoryAttribution: 'Bob',
    outcome: 'wrong',
    outcomeSummary: 'Alice missed this one.',
    roomMissedIt: true,
  },
  {
    index: 1,
    question: 'Which 90s rapper released "Ready to Die"?',
    answer: 'The Notorious B.I.G.',
    category: '90s Hip Hop',
    categoryAttribution: 'Cara',
    outcome: 'stolen',
    outcomeSummary: 'Alice missed it — Cara stole it.',
    roomMissedIt: false,
  },
];

await beginSuperlativeVoting(game);
check(game.postGame !== null, 'beginSuperlativeVoting creates postGame state');
check(game.postGame.stage === 'voting', 'stage starts at "voting"');
check(game.postGame.categories.length >= 3, `Claude returned >=3 categories (got ${game.postGame.categories.length})`);
console.log('  categories:', game.postGame.categories.map((c) => c.title).join(' | '));

const beforeCount = game.postGame.categories.length;
await beginSuperlativeVoting(game);
check(
  game.postGame.categories.length === beforeCount,
  'calling beginSuperlativeVoting twice does not regenerate'
);

let rejected = false;
try {
  castSuperlativeVote(game, 'p1', 'not_a_real_category', 'p2');
} catch {
  rejected = true;
}
check(rejected, 'a vote for an unknown category is rejected');

check(!allSuperlativeVotesIn(game), 'not all votes are in before anyone votes');

for (const voter of ['p1', 'p2', 'p3']) {
  for (const category of game.postGame.categories) {
    castSuperlativeVote(game, voter, category.id, 'p2'); // everyone votes Bob
  }
}
check(allSuperlativeVotesIn(game), 'allSuperlativeVotesIn() true once every ballot is complete');

const partialView = playerView(game, 'p1');
check(
  partialView.postGame.results === null,
  'results are withheld while voting is still open'
);

await resolveSuperlatives(game);
check(game.postGame.stage === 'results', 'stage advances to "results"');
check(
  game.postGame.results.every((r) => r.winnerNames.includes('Bob')),
  'unanimous votes make Bob win every award'
);
check(
  game.postGame.results.every((r) => r.voteCount === 3),
  'vote counts are tallied correctly'
);
const withQuips = game.postGame.results.filter((r) => r.quip).length;
check(withQuips > 0, `host quips were generated (${withQuips}/${game.postGame.results.length})`);
console.log('  sample award:', game.postGame.results[0].title, '->', game.postGame.results[0].quip);

// Ties are shared wins, same convention as getWinners().
const tie = createGame('p1', 'Alice');
addPlayer(tie, 'p2', 'Bob');
tie.phase = 'GAME_OVER';
tie.postGame = {
  stage: 'voting',
  categories: [{ id: 'c1', title: 'Best Sabotage', description: 'x' }],
  votes: { p1: { c1: 'p2' }, p2: { c1: 'p1' } },
  results: null,
};
await resolveSuperlatives(tie);
check(tie.postGame.results[0].winnerNames.length === 2, 'a tied award is a shared win');

// --- Part 4: players leaving during post-game -------------------------------
// After a game ends people close the tab. A departed player must not hold the
// rest of the room on the voting screen until the 90s timer expires.

console.log('=== departures during voting ===');

const leaver = createGame('p1', 'Alice');
addPlayer(leaver, 'p2', 'Bob');
addPlayer(leaver, 'p3', 'Cara');
leaver.phase = 'GAME_OVER';
leaver.postGame = {
  stage: 'voting',
  categories: [{ id: 'c1', title: 'Best Sabotage', description: 'x' }],
  votes: { p1: { c1: 'p2' }, p2: { c1: 'p1' } },
  results: null,
};

check(!allSuperlativeVotesIn(leaver), 'voting is not complete while Cara is still connected');

leaver.players[2].connected = false;
check(
  allSuperlativeVotesIn(leaver),
  'a disconnected player no longer blocks the tally'
);
check(
  playerView(leaver, 'p1').postGame.totalToVote === 2,
  'totalToVote drops to the players actually still present'
);

// Claude returning an empty set must not read as "everyone has voted".
const noCategories = createGame('p1', 'Alice');
addPlayer(noCategories, 'p2', 'Bob');
noCategories.phase = 'GAME_OVER';
noCategories.postGame = { stage: 'voting', categories: [], votes: {}, results: null };
check(
  !allSuperlativeVotesIn(noCategories),
  'zero categories does not vacuously report all votes in'
);

console.log(failures === 0 ? '=== ALL PASSED ===' : `=== ${failures} FAILURE(S) ===`);
process.exit(failures > 0 ? 1 : 0);
