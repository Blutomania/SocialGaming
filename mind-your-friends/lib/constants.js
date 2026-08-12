// Shared constants — safe to import from both server (server.js, lib/gameState.js)
// and client components (no Node-only dependencies here).

// Game length is overridable for playtesting ONLY. A full game is 24 questions
// (~25 min), and anything that happens at GAME_OVER — superlative voting, the
// Shareable Question card — is gated behind finishing all of them. Testing the
// post-game screens three times would otherwise mean 75 minutes of play to
// exercise the last two.
//
// NEXT_PUBLIC_ prefix is deliberate: GameBoard.jsx renders "Question 3/24" from
// these same constants, so a server-only override would leave the client
// counting to a total the server no longer uses.
//
//   NEXT_PUBLIC_MYF_ROUNDS=1 NEXT_PUBLIC_MYF_QUESTIONS_PER_ROUND=2 npm run dev
//
// Unset for a real playtest of pacing or game length — a 2-question game tells
// you nothing about whether 24 is the right number.
function positiveInt(raw, fallback) {
  const parsed = parseInt(raw ?? '', 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export const ROUNDS = positiveInt(process.env.NEXT_PUBLIC_MYF_ROUNDS, 4);
export const QUESTIONS_PER_ROUND = positiveInt(process.env.NEXT_PUBLIC_MYF_QUESTIONS_PER_ROUND, 6);
export const TOTAL_QUESTIONS = ROUNDS * QUESTIONS_PER_ROUND; // 24 by default
export const MIN_WAGER = 50;
export const MAX_WAGER = 500;
export const RESULT_SCREEN_MS = 4000;
export const MIN_PLAYERS = 3;
export const MAX_PLAYERS = 6;

// 3, not 5. Typing five categories was the single most laborious moment in
// the lobby (playtest, Aug 12) — and with the tappable category grid most
// players never type at all now. See CATEGORY_SUGGESTIONS in lib/categories.js.
export const CATEGORIES_PER_PLAYER = 3;

// Points for anyone other than the active player who buzzes in with the
// right answer. Flat and modest by design: the active player is the one who
// wagered, so they're the one who can win big or lose big. Everybody else is
// playing for a steady trickle and risks nothing — that's what makes buzzing
// in feel free rather than scary. See "open answering" in gameState.js.
export const OPEN_ANSWER_POINTS = 100;

// How long the question sits on screen before the answer clock starts, so
// nobody is racing a timer they haven't finished reading. Questions are
// generated at 8–20 words (see claudeClient.generateQuestion), which reads in
// well under this.
export const READING_SECONDS = 5;
export const CATEGORY_OPTIONS_COUNT = 6;
export const CARD_PICK_TIMER_MS = 40000;
export const RANDOM_CARDS_PER_ROUND = 2;
export const FACTS_PER_CATEGORY = 10;
export const CATEGORIES_PER_FETCH_BATCH = 3;
export const DISCONNECT_GRACE_MS = 45000;
export const DISCONNECT_VOTE_EXTENSION_MS = 45000;
export const AUTO_ADVANCE_AWAY_THRESHOLD = 2;
export const LINEUP_COLOR_FLAVOR_CHANCE = 0.4; // vs. text flavor — see lib/lineupData.js
