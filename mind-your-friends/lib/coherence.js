// Coherence Engine for Mind Your Friends.
//
// Two-pass constraint assembly:
//   1. roundConstraints(roundRule) — runs once at round start, produces base
//      constraints that hold for every question in the round.
//   2. turnConstraints(roundConstraints, { category, wager, resolvedCard }) —
//      runs per turn after card resolution, layers on turn-specific modifiers
//      and returns the final prompt instructions for generateQuestion().
//
// Post-generation:
//   3. validateQuestion(question, constraints) — confirms the generated Q&A
//      satisfies the assembled constraints.

import { CARDS, pickRandomLanguageRegister } from './cards.js';
import { ROUND_RULES, BASE_TIMER_SECONDS } from './roundRules.js';
import { MIN_WAGER, MAX_WAGER } from './constants.js';

// --- Severity levels (shared vocabulary with Choose Your Mystery CE) ---

export const BLOCKING = 'blocking';
export const WARNING = 'warning';
export const INFO = 'info';

// --- Difficulty mapping ---

function wagerToDifficulty(wager) {
  const range = MAX_WAGER - MIN_WAGER;
  const normalized = (wager - MIN_WAGER) / range;
  if (normalized <= 0.33) return 'easy';
  if (normalized <= 0.66) return 'medium';
  return 'hard';
}

const DIFFICULTY_PROMPT = {
  easy: 'Generate an easy question that most people would know the answer to.',
  medium: 'Generate a moderately challenging question — not trivial, but fair.',
  hard: 'Generate a difficult question that requires specific knowledge.',
};

// --- Format-constraining cards (affect question generation) ---

const FORMAT_CARD_IDS = new Set(['boxedIn', 'languageBarrier']);

// --- Pass 1: Round-level constraints ---

export function roundConstraints(roundRule) {
  const rule = typeof roundRule === 'string' ? ROUND_RULES[roundRule] : roundRule;
  if (!rule) throw new Error(`Unknown round rule: ${roundRule}`);

  return {
    roundRuleId: rule.id,
    roundRuleName: rule.name,
    timerSeconds: rule.timerSeconds ?? BASE_TIMER_SECONDS,
    wagerMultiplier: rule.wagerMultiplier ?? 1,
    stealOnWrong: rule.stealOnWrong ?? false,
    promptInstructions: rule.promptInstruction ? [rule.promptInstruction] : [],
    answerFormat: rule.id === 'oneWordOnly' ? 'single-word' : 'phrase',
  };
}

// --- Pass 2: Turn-level constraints ---

export function turnConstraints(roundCtx, { category, wager, resolvedCard }) {
  const difficulty = wagerToDifficulty(wager);
  const effectiveWager = Math.round(wager * roundCtx.wagerMultiplier);

  const promptInstructions = [
    `Category: ${category}`,
    DIFFICULTY_PROMPT[difficulty],
    ...roundCtx.promptInstructions,
  ];

  let answerFormat = roundCtx.answerFormat;
  let timerSeconds = roundCtx.timerSeconds;
  let cardEffects = {};

  if (resolvedCard) {
    const card = typeof resolvedCard === 'string' ? CARDS[resolvedCard] : resolvedCard;
    if (!card) throw new Error(`Unknown card: ${resolvedCard}`);

    if (card.id === 'boxedIn') {
      answerFormat = 'one-or-two-words';
      promptInstructions.push(
        'The correct answer MUST be exactly one or two words. Design the question so that a short answer is natural.'
      );
    }

    if (card.id === 'languageBarrier') {
      const register = pickRandomLanguageRegister();
      promptInstructions.push(
        `Phrase the entire question in this register: ${register}. The answer itself should still be straightforward.`
      );
      cardEffects.languageRegister = register;
    }

    if (card.id === 'spotlight') {
      timerSeconds = 5;
      cardEffects.spotlight = true;
    }

    if (card.id === 'fiftyOff') {
      cardEffects.wagerHalved = true;
    }

    if (card.id === 'heckle') {
      cardEffects.heckle = true;
    }

    cardEffects.cardId = card.id;
    cardEffects.cardName = card.name;
  }

  return {
    category,
    difficulty,
    wager,
    effectiveWager,
    answerFormat,
    timerSeconds,
    stealOnWrong: roundCtx.stealOnWrong,
    roundRuleId: roundCtx.roundRuleId,
    roundRuleName: roundCtx.roundRuleName,
    promptInstructions,
    cardEffects,
  };
}

// Pick a factoid from the bank that matches the current turn constraints.
// Removes the picked factoid so it's never reused within a game.
export function pickFactoid(factBank, category, constraints) {
  const facts = factBank[category];
  if (!facts || facts.length === 0) return null;

  const formatMax =
    constraints.answerFormat === 'single-word' ? 1
    : constraints.answerFormat === 'one-or-two-words' ? 2
    : Infinity;

  const matching = facts.filter((f) => {
    if (f.answerWordCount > formatMax) return false;
    if (constraints.answerFormat === 'phrase' && f.answerWordCount < 2) return false;
    if (f.difficulty === constraints.difficulty) return true;
    return false;
  });

  // Fallback: relax difficulty if no exact match
  const pool = matching.length > 0 ? matching : facts.filter((f) => f.answerWordCount <= formatMax);
  if (pool.length === 0) return facts.splice(0, 1)[0];

  const idx = Math.floor(Math.random() * pool.length);
  const picked = pool[idx];
  facts.splice(facts.indexOf(picked), 1);
  return picked;
}

// --- Pass 3: Post-generation validation ---

export function validateQuestion(question, constraints) {
  const issues = [];

  const answer = (question.answer || '').trim();
  const wordCount = answer.split(/\s+/).filter(Boolean).length;

  if (!answer) {
    issues.push({
      code: 'question.no_answer',
      severity: BLOCKING,
      message: 'Generated question has no answer.',
    });
    return { passed: false, issues };
  }

  if (!question.question || !question.question.trim()) {
    issues.push({
      code: 'question.no_question_text',
      severity: BLOCKING,
      message: 'Generated question has no question text.',
    });
  }

  if (constraints.answerFormat === 'single-word' && wordCount > 1) {
    issues.push({
      code: 'question.answer_too_long.one_word',
      severity: WARNING,
      message: `One Word Only round: answer "${answer}" has ${wordCount} words.`,
    });
  }

  if (constraints.answerFormat === 'one-or-two-words' && wordCount > 2) {
    issues.push({
      code: 'question.answer_too_long.boxed_in',
      severity: WARNING,
      message: `Boxed In card active: answer "${answer}" has ${wordCount} words (max 2).`,
    });
  }

  if (constraints.answerFormat === 'phrase' && wordCount < 2) {
    issues.push({
      code: 'question.answer_too_short',
      severity: INFO,
      message: `Baseline expects >3 word answers for card interplay; got "${answer}" (${wordCount} word).`,
    });
  }

  const blocking = issues.some((i) => i.severity === BLOCKING);
  return { passed: !blocking, issues };
}
