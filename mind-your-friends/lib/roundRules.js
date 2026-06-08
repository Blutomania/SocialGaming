/**
 * Round Rule definitions for Mind Your Friends
 * Each rule modifies how questions are presented or answered.
 */

export const ROUND_RULES = {
  RHYME_TIME: {
    id: 'RHYME_TIME',
    name: 'Rhyme Time',
    emoji: '🎵',
    description: 'The answer must rhyme with a word given in the question.',
    promptInstruction:
      'The question must end with a word that rhymes with the correct answer. ' +
      'Phrase the question so the last word rhymes with the answer. ' +
      'Example: if answer is "cat", end question with "...that rhymes with hat?"',
    uiEffect: null,
    answerTransform: null,
  },
  FOUR_DOWN: {
    id: 'FOUR_DOWN',
    name: 'Four Down',
    emoji: '4️⃣',
    description: 'Your answer must be 4 words or fewer.',
    promptInstruction:
      'The correct answer must be expressible in 4 words or fewer. ' +
      'Prefer answers that are 1-3 words naturally.',
    uiEffect: null,
    answerTransform: null,
  },
  INFAMOUS_LAST_WORDS: {
    id: 'INFAMOUS_LAST_WORDS',
    name: 'Infamous Last Words',
    emoji: '✂️',
    description: 'The last word of the question is hidden — you must infer it.',
    promptInstruction:
      'Write a complete question normally. The last word will be hidden from the player.',
    uiEffect: 'hideLastWord', // handled in QuestionCard
    answerTransform: null,
  },
  FICKLE_FLICKER: {
    id: 'FICKLE_FLICKER',
    name: 'Fickle Flicker',
    emoji: '⚡',
    description: 'The question text flickers rapidly — read fast!',
    promptInstruction: 'Write a standard trivia question.',
    uiEffect: 'flicker',
    answerTransform: null,
  },
  BLURRY_FLURRY: {
    id: 'BLURRY_FLURRY',
    name: 'Blurry Flurry',
    emoji: '🌫️',
    description: 'Question is blurred — click/tap to reveal it briefly.',
    promptInstruction: 'Write a standard trivia question.',
    uiEffect: 'blur',
    answerTransform: null,
  },
  BACK_IT_UP: {
    id: 'BACK_IT_UP',
    name: 'Back It Up',
    emoji: '🔄',
    description: 'Type your answer backwards.',
    promptInstruction:
      'Write a standard trivia question with a short, single-word or short-phrase answer.',
    uiEffect: null,
    answerTransform: 'reverse', // server reverses submitted answer before checking
  },
};

export const ROUND_RULE_LIST = Object.values(ROUND_RULES);

/**
 * Pick a random round rule for a new round.
 * Avoids repeating the previous rule.
 */
export function pickRoundRule(previousRuleId = null) {
  const available = ROUND_RULE_LIST.filter((r) => r.id !== previousRuleId);
  return available[Math.floor(Math.random() * available.length)];
}

/**
 * Apply any server-side answer transformations before evaluation.
 */
export function transformAnswer(answer, ruleId) {
  const rule = ROUND_RULES[ruleId];
  if (!rule) return answer;
  if (rule.answerTransform === 'reverse') {
    return answer.split('').reverse().join('');
  }
  return answer;
}
