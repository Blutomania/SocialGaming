// 8 round rule variations. See GAME_DESIGN.md → Round Rules. Audience Poll is out for v1.
// Assigned randomly each turn (pickRandomRoundRule).
//
// Rules that constrain the answer format define both `transform.text` and
// `transform.voice` — see GAME_DESIGN.md → Input Modes. Rules with no answer
// constraint are input-agnostic and have no `transform`.

export const BASE_TIMER_SECONDS = 20;

export const ROUND_RULES = {
  backItUp: {
    id: 'backItUp',
    name: 'Back It Up',
    emoji: '🔄',
    description: 'The answer must be reversed.',
    promptInstruction:
      'The player must answer in reverse — they will say the correct answer backwards.',
    timerSeconds: BASE_TIMER_SECONDS,
    transform: {
      text: (answer) => answer.split('').reverse().join(''),
      voice: (answer) => answer.split(' ').reverse().join(' '),
    },
  },
  oneWordOnly: {
    id: 'oneWordOnly',
    name: 'One Word Only',
    emoji: '1️⃣',
    description: 'The answer must be a single word.',
    promptInstruction:
      'Generate a question whose correct answer is exactly ONE word — a single common word, number, or name (not a multi-word proper noun). Design the question so a one-word answer is natural.',
    timerSeconds: BASE_TIMER_SECONDS,
    transform: {
      text: (answer) => answer.trim().split(/\s+/)[0],
      voice: (answer) => answer.trim().split(/\s+/)[0],
    },
  },
  lightningRound: {
    id: 'lightningRound',
    name: 'Lightning Round',
    emoji: '⚡',
    description: 'Timer halved.',
    promptInstruction: null,
    timerSeconds: BASE_TIMER_SECONDS / 2,
  },
  slowBurn: {
    id: 'slowBurn',
    name: 'Slow Burn',
    emoji: '🐢',
    description: 'Timer doubled; host quip escalates.',
    promptInstruction:
      "The host's quip should build suspense slowly, escalating as if stalling for time.",
    timerSeconds: BASE_TIMER_SECONDS * 2,
  },
  eli5: {
    id: 'eli5',
    name: 'ELI5',
    emoji: '🧒',
    description: 'Question phrased by a curious 5-year-old; Claude judges understanding.',
    promptInstruction:
      'Phrase the question as if asked by a curious 5-year-old. When evaluating the answer, judge whether the player demonstrated understanding, not just exact wording.',
    timerSeconds: BASE_TIMER_SECONDS,
  },
  hotTake: {
    id: 'hotTake',
    name: 'Hot Take',
    emoji: '🔥',
    description: 'Opinion question; confidence beats correctness.',
    promptInstruction:
      'Generate an opinion-based question with no single correct answer. When evaluating, reward confident, well-argued answers over "correctness".',
    timerSeconds: BASE_TIMER_SECONDS,
  },
  doubleDown: {
    id: 'doubleDown',
    name: 'Double Down',
    emoji: '💰',
    description: 'Wager auto-doubled, no backing out.',
    promptInstruction: null,
    timerSeconds: BASE_TIMER_SECONDS,
    wagerMultiplier: 2,
  },
  steal: {
    id: 'steal',
    name: 'Steal',
    emoji: '🦹',
    description: 'Wrong answer opens a steal window for other players.',
    promptInstruction: null,
    timerSeconds: BASE_TIMER_SECONDS,
    stealOnWrong: true,
  },
};

export function pickRandomRoundRule() {
  const ids = Object.keys(ROUND_RULES);
  const id = ids[Math.floor(Math.random() * ids.length)];
  return ROUND_RULES[id];
}

// Apply a round rule's answer transform, if any, for the given input mode.
export function transformAnswer(roundRule, answer, inputMode) {
  if (!roundRule?.transform) return answer;
  return roundRule.transform[inputMode](answer);
}
