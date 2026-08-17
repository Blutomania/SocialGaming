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
import { wagerTierIndex, WAGER_TIERS } from './constants.js';

// --- Severity levels (shared vocabulary with Choose Your Mystery CE) ---

export const BLOCKING = 'blocking';
export const WARNING = 'warning';
export const INFO = 'info';

// --- Difficulty mapping ---

// One difficulty per rung of the wager ladder, so the stake the room watched
// somebody choose is the stake the question is actually written to. The old
// mapping normalised a continuous 50-500 range into three buckets, which meant
// two visibly different wagers routinely produced identically-pitched
// questions.
const DIFFICULTY_BY_TIER = ['trivial', 'easy', 'medium', 'hard', 'brutal'];

const DIFFICULTY_PROMPT = {
  trivial: 'Generate a very easy question — almost everyone should get this one.',
  easy: 'Generate an easy question that most people would know the answer to.',
  medium: 'Generate a moderately challenging question — not trivial, but fair.',
  hard: 'Generate a difficult question that requires specific knowledge.',
  brutal: 'Generate a genuinely hard question — most of the room should miss it.',
};

// The fact bank only knows three difficulties (they come from the research
// prompt in claudeClient.js), so the five-rung ladder maps down for filtering.
// Deliberately not widened to five: that would mean re-generating every cached
// fact bank to add two values the bank has never produced.
const BANK_DIFFICULTY = {
  trivial: 'easy',
  easy: 'easy',
  medium: 'medium',
  hard: 'hard',
  brutal: 'hard',
};

function wagerToDifficulty(wager) {
  return DIFFICULTY_BY_TIER[wagerTierIndex(wager)];
}

function bankDifficulty(difficulty) {
  return BANK_DIFFICULTY[difficulty] ?? difficulty;
}

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
    lineupBased: rule.lineupBased ?? false,
    rebusBased: rule.rebusBased ?? false,
    promptInstructions: rule.promptInstruction ? [rule.promptInstruction] : [],
    answerFormat: rule.id === 'oneWordOnly' ? 'single-word' : rule.lineupBased ? 'lineup' : 'phrase',
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
    difficultyTier: wagerTierIndex(wager),
    wager,
    effectiveWager,
    answerFormat,
    timerSeconds,
    stealOnWrong: roundCtx.stealOnWrong,
    lineupBased: roundCtx.lineupBased,
    rebusBased: roundCtx.rebusBased,
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
    if (f.difficulty === bankDifficulty(constraints.difficulty)) return true;
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

  if (constraints.lineupBased) {
    const lineup = question.lineup;
    if (!lineup || !Array.isArray(lineup.options) || lineup.options.length < 2) {
      issues.push({
        code: 'lineup.invalid_options',
        severity: BLOCKING,
        message: 'The Lineup requires at least 2 options.',
      });
    } else {
      const ids = lineup.options.map((o) => o.id);
      if (new Set(ids).size !== ids.length) {
        issues.push({
          code: 'lineup.duplicate_option_ids',
          severity: BLOCKING,
          message: 'The Lineup options must have unique ids.',
        });
      }
      if (!lineup.correctOptionId || !ids.includes(lineup.correctOptionId)) {
        issues.push({
          code: 'lineup.missing_correct_option',
          severity: BLOCKING,
          message: 'The Lineup correctOptionId must reference one of the options.',
        });
      }
    }
  }

  const blocking = issues.some((i) => i.severity === BLOCKING);
  return { passed: !blocking, issues };
}
