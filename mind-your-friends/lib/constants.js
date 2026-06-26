// Shared constants — safe to import from both server (server.js, lib/gameState.js)
// and client components (no Node-only dependencies here).

export const ROUNDS = 4;
export const QUESTIONS_PER_ROUND = 6;
export const TOTAL_QUESTIONS = ROUNDS * QUESTIONS_PER_ROUND; // 24
export const MIN_WAGER = 50;
export const MAX_WAGER = 500;
export const RESULT_SCREEN_MS = 4000;
export const STEAL_WINDOW_MS = 8000;
export const MIN_PLAYERS = 3;
export const MAX_PLAYERS = 6;
export const CATEGORIES_PER_PLAYER = 5;
export const CATEGORY_OPTIONS_COUNT = 6;
export const CARD_PICK_TIMER_MS = 40000;
export const RANDOM_CARDS_PER_ROUND = 2;
export const FACTS_PER_CATEGORY = 10;
export const CATEGORIES_PER_FETCH_BATCH = 3;
export const DISCONNECT_GRACE_MS = 45000;
export const DISCONNECT_VOTE_EXTENSION_MS = 45000;
export const AUTO_ADVANCE_AWAY_THRESHOLD = 2;
