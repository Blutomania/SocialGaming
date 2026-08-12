// Round rule variations. See GAME_DESIGN.md → Round Rules.
// Audience Poll is out for v1. Hot Take removed (see PLAYTEST.md PT-2).
// Steal removed (see PLAYTEST.md PT-3): open answering made it the default.
//
// Assigned once per ROUND, not per turn (pickRandomRoundRule) — round 1 is
// deliberately plain so a new player learns the base game before a rule bends
// it, and every round after that has exactly one rule, announced at the top of
// the round and kept on screen for its duration.
//
// Rules that constrain the answer format define both `transform.text` and
// `transform.voice` — see GAME_DESIGN.md → Input Modes. Rules with no answer
// constraint are input-agnostic and have no `transform`.

// Doubled from 20s (playtest, Aug 12): 20s was measured against a question
// the player had already read, but in practice the clock and the question
// arrived together. Reading is now its own phase (READING_SECONDS) and this
// is time to actually think.
export const BASE_TIMER_SECONDS = 40;

// Round 1's "rule". Not in ROUND_RULES, never picked at random, and hidden by
// the UI — it exists so nothing downstream has to null-check game.roundRule.
export const NO_RULE = {
  id: 'none',
  name: 'No Rule',
  emoji: '',
  description: 'Straight trivia — no twist this round.',
  promptInstruction: null,
  timerSeconds: BASE_TIMER_SECONDS,
};

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
      'Generate a question whose correct answer can be reduced to a single word.',
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
  takeYourTime: {
    id: 'takeYourTime',
    name: 'Take Your Time',
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
  doubleDown: {
    id: 'doubleDown',
    name: 'Double Down',
    emoji: '💰',
    description: 'Wager auto-doubled, no backing out.',
    promptInstruction: null,
    timerSeconds: BASE_TIMER_SECONDS,
    wagerMultiplier: 2,
  },
  worstAnswerWins: {
    id: 'worstAnswerWins',
    name: 'Worst Answer Wins',
    emoji: '🏆',
    description: 'Everyone submits — worst answer wins. Scored on: factually wrong, creatively wrong, plausibility.',
    promptInstruction:
      'Generate a factual question with a clear correct answer. All players will submit intentionally wrong answers. The question must have a definitive factual answer so "wrongness" is measurable.',
    timerSeconds: BASE_TIMER_SECONDS * 2,
    submissionBased: true,
  },
  rebus: {
    id: 'rebus',
    name: 'Rebus',
    emoji: '🧩',
    description: 'The answer is spelled out in emoji. Read the pictures, not the words.',
    promptInstruction: null,
    timerSeconds: BASE_TIMER_SECONDS,
    rebusBased: true,
  },
  theLineup: {
    id: 'theLineup',
    name: 'The Lineup',
    emoji: '🕵️',
    description: 'Pick the right one from a lineup of look-alikes. First correct tap wins — wrong taps just fail, no penalty.',
    promptInstruction: null,
    timerSeconds: BASE_TIMER_SECONDS,
    lineupBased: true,
  },
};

// Playtesting affordance: pin every round to one rule.
//
//   MYF_FORCE_ROUND_RULE=rebus npm run dev
//
// Previous sessions each hacked this in locally and reverted it before
// committing, which meant re-writing it every time and risking it shipping
// by accident. It's a real, documented switch now. Unset in normal play, and
// it overrides round 1's deliberately-plain rule too — otherwise testing a
// rule costs a whole round to reach.
function forcedRule() {
  const id = process.env.MYF_FORCE_ROUND_RULE;
  if (!id) return null;
  const rule = ROUND_RULES[id];
  if (!rule) {
    console.warn(`MYF_FORCE_ROUND_RULE="${id}" is not a rule. Known: ${Object.keys(ROUND_RULES).join(', ')}`);
    return null;
  }
  return rule;
}

// `exclude` — rule ids already used this game. A rule is only repeated once
// every rule has had a turn, so a 4-round game shows four different twists
// instead of rolling the same one twice.
export function pickRandomRoundRule(exclude = []) {
  const forced = forcedRule();
  if (forced) return forced;
  const ids = Object.keys(ROUND_RULES);
  const fresh = ids.filter((id) => !exclude.includes(id));
  const pool = fresh.length > 0 ? fresh : ids;
  return ROUND_RULES[pool[Math.floor(Math.random() * pool.length)]];
}

// Round 1 is plain by design, but that makes any forced rule cost a whole
// round to reach. This is the one place the force is allowed to override the
// design invariant.
export function forcedRuleForRoundOne() {
  return forcedRule();
}

// Apply a round rule's answer transform, if any, for the given input mode.
export function transformAnswer(roundRule, answer, inputMode) {
  if (!roundRule?.transform) return answer;
  return roundRule.transform[inputMode](answer);
}
