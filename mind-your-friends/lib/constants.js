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

// What a buzz-in win pays: a share of the wager the question was being played
// for. Anyone but the answerer, and they still risk nothing — that asymmetry
// is what makes buzzing feel free rather than scary.
//
// A share rather than a flat number, decided August 17 2026, for two reasons.
// It is self-anchoring: "three-quarters of what they were playing for" needs
// no explanation, where a flat 100 floats free of every other number on
// screen and can't be judged. And it scales with the question's danger — a
// big wager usually means a category the answerer is in trouble on, and
// taking a hard question should pay more than taking an easy one.
//
// It MUST stay below 1. At 1.5x a buzzer would earn 750 on a question the
// answerer could only win 500 on, while risking nothing — which inverts the
// risk hierarchy of the whole game and makes being the active player
// something to avoid. Below 1 that hierarchy stays the right way up, and the
// wager-setter's decision survives: it only shifts their break-even from
// "will they get this?" at 50% to about 55%.
export const BUZZ_WAGER_SHARE = 0.75;

// Buzz winnings are rounded to this, so the scoreboard stays legible —
// 0.75 x a 250 wager is 187.5, which nobody wants to read.
export const BUZZ_POINTS_ROUNDING = 5;

// How long the question sits on screen before the answer clock starts, so
// nobody is racing a timer they haven't finished reading. Questions are
// generated at 8–20 words (see claudeClient.generateQuestion), which reads in
// well under this.
export const READING_SECONDS = 5;

// Flow B (GAME_DESIGN.md → "The Round Loop"). After the reading window the
// active player gets this long alone with their own question before the
// buzzer opens to the room. It is their wager, so they get first refusal on
// it — without that, a faster player takes every question and the wager never
// bites, which is what PT-4 was about.
//
// Carved OUT of the round rule's answer clock, never added to it, so the
// total length of a question is unchanged.
export const ACTIVE_WINDOW_SECONDS = 8;

// …and capped at this share of the clock, so a halved clock doesn't become a
// mostly-exclusive round: Lightning Round's 20s gets 5s, not 8 of its 20.
export const ACTIVE_WINDOW_MAX_SHARE = 0.25;
export const CATEGORY_OPTIONS_COUNT = 6;
export const CARD_PICK_TIMER_MS = 40000;
export const RANDOM_CARDS_PER_ROUND = 2;
export const FACTS_PER_CATEGORY = 10;
export const CATEGORIES_PER_FETCH_BATCH = 3;
export const DISCONNECT_GRACE_MS = 45000;
export const DISCONNECT_VOTE_EXTENSION_MS = 45000;
export const AUTO_ADVANCE_AWAY_THRESHOLD = 2;
export const LINEUP_COLOR_FLAVOR_CHANCE = 0.4; // vs. text flavor — see lib/lineupData.js
