// Shared constants — safe to import from both server (server.js, lib/gameState.js)
// and client components (no Node-only dependencies here).

export const ROUNDS = 4;
export const QUESTIONS_PER_ROUND = 6;
export const TOTAL_QUESTIONS = ROUNDS * QUESTIONS_PER_ROUND; // 24
export const POINT_TIERS = [20, 40, 80, 160, 400];
export const MIN_WAGER = POINT_TIERS[0];
export const MAX_WAGER = POINT_TIERS[POINT_TIERS.length - 1];
export const RESULT_SCREEN_MS = 4000;
export const STEAL_WINDOW_MS = 8000;
export const MIN_PLAYERS = 3;
export const MAX_PLAYERS = 6;
export const CATEGORIES_PER_PLAYER = 5;
export const CATEGORY_OPTIONS_COUNT = 6;
