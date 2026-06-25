// Question pool — batch pre-generates questions per category at game start.
//
// Flow:
//   1. Game starts → expandCategories() generates sub-topics for each category
//   2. generatePool() batch-generates questions across sub-topics and difficulties
//   3. During play, drawQuestion() pulls from the pool (no per-question API call)
//   4. If the pool runs dry for a category, a refill batch is triggered
//
// Sub-topics create depth within a category by classification. "WWII" becomes
// "Pacific Theater," "Key dates," "Weapons and technology," etc. The LLM
// generates these on the fly so any user-submitted category gets depth.

import { POINT_TIERS } from './constants.js';

const DIFFICULTIES = ['easy', 'easy-alt', 'medium', 'hard', 'expert'];

const TIER_TO_DIFFICULTY = {
  20: 'easy',
  40: 'easy-alt',
  80: 'medium',
  160: 'hard',
  400: 'expert',
};

function stripMarkdownFences(text) {
  return text.replace(/^```(?:json)?\s*\n?/i, '').replace(/\n?```\s*$/i, '').trim();
}

export async function expandCategories(anthropic, model, categories) {
  const prompt = `For each trivia category below, generate 8-10 sub-topics that create depth
and variety within that category. Sub-topics should be distinct enough that
questions drawn from different sub-topics won't overlap.

Categories:
${categories.map((c, i) => `${i + 1}. ${c}`).join('\n')}

Respond with ONLY a JSON object, no other text:
{
  "Category Name": ["sub-topic 1", "sub-topic 2", ...],
  ...
}`;

  const response = await anthropic.messages.create({
    model,
    max_tokens: 2048,
    messages: [{ role: 'user', content: prompt }],
  });

  return JSON.parse(stripMarkdownFences(response.content[0].text));
}

export async function generatePool(anthropic, model, category, subTopics, playerNames) {
  const questionsPerDifficulty = 3;

  const prompt = `You are the AI host of "Mind Your Friends," a fast-paced multiplayer trivia game.
Players: ${playerNames.join(', ')}.

Generate a pool of trivia questions for the category "${category}."
Use the sub-topics below to ensure variety — draw from different sub-topics,
don't cluster questions around one.

Sub-topics: ${subTopics.join(', ')}

Generate exactly ${DIFFICULTIES.length * questionsPerDifficulty} questions (${questionsPerDifficulty} per difficulty level):

Difficulty levels:
- "easy": Most people would know this. The most accessible, obvious question.
- "easy-alt": Still easy, but NOT the most obvious question — a different angle or less-famous fact.
- "medium": Moderately challenging — not trivial, but fair for someone who likes this topic.
- "hard": Requires specific knowledge of this subject.
- "expert": Only someone with deep knowledge would get this right.

Rules:
- Each answer should be a short phrase of MORE than 3 words by default.
- No two questions should have the same answer or test the same fact.
- Draw from different sub-topics across the set — maximize variety.
- Include a short, personalized host quip for each (use a generic "you" — it will be personalized later).

Respond with ONLY a JSON array, no other text:
[
  {
    "question": "...",
    "answer": "...",
    "hostQuip": "...",
    "difficulty": "easy|easy-alt|medium|hard|expert",
    "subTopic": "which sub-topic this draws from"
  }
]`;

  const response = await anthropic.messages.create({
    model,
    max_tokens: 4096,
    messages: [{ role: 'user', content: prompt }],
  });

  return JSON.parse(stripMarkdownFences(response.content[0].text));
}

export function createQuestionPool() {
  return {
    subTopics: {},
    questions: {},
    usedSubTopics: {},
  };
}

export function addToPool(pool, category, subTopics, questions) {
  pool.subTopics[category] = subTopics;
  pool.questions[category] = questions;
  pool.usedSubTopics[category] = new Set();
}

export function drawQuestion(pool, category, wager) {
  const difficulty = TIER_TO_DIFFICULTY[wager] || 'medium';
  const available = pool.questions[category];
  if (!available || available.length === 0) return null;

  const match = available.findIndex((q) => q.difficulty === difficulty);
  if (match === -1) {
    const fallback = available.findIndex((q) => !q._used);
    if (fallback === -1) return null;
    const q = available.splice(fallback, 1)[0];
    pool.usedSubTopics[category]?.add(q.subTopic);
    return q;
  }

  const q = available.splice(match, 1)[0];
  pool.usedSubTopics[category]?.add(q.subTopic);
  return q;
}

export function poolDepth(pool, category) {
  return pool.questions[category]?.length || 0;
}

export function needsRefill(pool, category, threshold = 3) {
  return poolDepth(pool, category) < threshold;
}
