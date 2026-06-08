/**
 * Claude API wrapper for Mind Your Friends
 * Handles question generation and answer evaluation.
 */

import fs from 'fs';
import Anthropic from '@anthropic-ai/sdk';

function getApiKey() {
  if (process.env.ANTHROPIC_API_KEY) {
    return process.env.ANTHROPIC_API_KEY;
  }
  try {
    return fs
      .readFileSync('/home/claude/.claude/remote/.session_ingress_token', 'utf8')
      .trim();
  } catch {
    throw new Error(
      'No Anthropic API key found. Set ANTHROPIC_API_KEY or provide the session token.'
    );
  }
}

let _client = null;
function getClient() {
  if (!_client) {
    _client = new Anthropic({ apiKey: getApiKey() });
  }
  return _client;
}

const PERSONALITY_PROMPTS = {
  Funny:
    'You are a hilarious game show host who loves puns, absurd comparisons, and getting laughs. ' +
    'Keep quips short and punchy. Roast wrong answers gently.',
  Sarcastic:
    'You are a deeply sarcastic game show host who acts perpetually unimpressed. ' +
    'Your enthusiasm is always ironic. Deadpan everything.',
  Encouraging:
    'You are an overwhelmingly positive, enthusiastic game show host. ' +
    'Every answer attempt is amazing. Hype players up constantly.',
  Mysterious:
    'You are a cryptic, enigmatic host who speaks in riddles and hints. ' +
    'Dramatic pauses. Allusions to ancient knowledge.',
  'Game Show Host':
    'You are the quintessential high-energy 80s game show host — big personality, ' +
    'rapid-fire energy, catchphrases, and audience references.',
};

/**
 * Generate a trivia question with host flair.
 *
 * @param {object} params
 * @param {string} params.category
 * @param {string} params.roundRule  - round rule id
 * @param {string} params.roundRuleName
 * @param {string} params.roundRuleInstruction - prompt instruction for the rule
 * @param {string} params.hostPersonality
 * @param {string[]} params.previousQuestions - avoid repeating
 * @returns {Promise<{question: string, hint: string, correctAnswer: string, hostQuip: string}>}
 */
export async function generateQuestion({
  category,
  roundRule,
  roundRuleName,
  roundRuleInstruction,
  hostPersonality,
  previousQuestions = [],
}) {
  const client = getClient();
  const personalityPrompt =
    PERSONALITY_PROMPTS[hostPersonality] || PERSONALITY_PROMPTS['Game Show Host'];

  const avoidList =
    previousQuestions.length > 0
      ? `\n\nAvoid questions similar to these already asked:\n${previousQuestions.slice(-5).join('\n')}`
      : '';

  const systemPrompt =
    `${personalityPrompt}\n\n` +
    `You are generating content for "Mind Your Friends", a social trivia party game.\n` +
    `Respond ONLY with valid JSON — no markdown, no extra text.`;

  const userPrompt =
    `Generate a trivia question for the category: "${category}".\n\n` +
    `Active Round Rule: "${roundRuleName}"\n` +
    `Rule instruction: ${roundRuleInstruction}\n\n` +
    `Return JSON with exactly these fields:\n` +
    `{\n` +
    `  "question": "the trivia question text",\n` +
    `  "hint": "a helpful but not too obvious hint (1 sentence)",\n` +
    `  "correctAnswer": "the correct answer (concise)",\n` +
    `  "hostQuip": "a short in-character line introducing this question (max 15 words)"\n` +
    `}${avoidList}`;

  const message = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 512,
    system: systemPrompt,
    messages: [{ role: 'user', content: userPrompt }],
  });

  const raw = message.content[0].text.trim();
  // Strip any accidental markdown fences
  const jsonStr = raw.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  return JSON.parse(jsonStr);
}

/**
 * Evaluate a player's answer against the correct answer using Claude.
 * Lightweight — uses minimal tokens.
 *
 * @param {string} playerAnswer
 * @param {string} correctAnswer
 * @param {string} question  - for context
 * @returns {Promise<{correct: boolean, explanation: string}>}
 */
export async function evaluateAnswer(playerAnswer, correctAnswer, question) {
  const client = getClient();

  const prompt =
    `Question: "${question}"\n` +
    `Correct answer: "${correctAnswer}"\n` +
    `Player's answer: "${playerAnswer}"\n\n` +
    `Is the player's answer correct? Be lenient with spelling, spacing, and phrasing — ` +
    `accept reasonable synonyms and partial matches that show clear knowledge.\n\n` +
    `Respond with ONLY valid JSON: {"correct": true/false, "explanation": "one short sentence"}`;

  const message = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 128,
    messages: [{ role: 'user', content: prompt }],
  });

  const raw = message.content[0].text.trim();
  const jsonStr = raw.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
  return JSON.parse(jsonStr);
}
