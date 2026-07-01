import fs from 'fs';
import Anthropic from '@anthropic-ai/sdk';
import { FACTS_PER_CATEGORY, CATEGORIES_PER_FETCH_BATCH } from './constants.js';

const MODEL = 'claude-sonnet-4-6';

const INGRESS_TOKEN_FILE = '/home/claude/.claude/remote/.session_ingress_token';

function buildClient() {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (apiKey) return new Anthropic({ apiKey });

  if (fs.existsSync(INGRESS_TOKEN_FILE)) {
    const authToken = fs.readFileSync(INGRESS_TOKEN_FILE, 'utf8').trim();
    return new Anthropic({ authToken });
  }

  return null;
}

const client = buildClient();

function requireClient() {
  if (!client) {
    throw new Error('No API key found. Set ANTHROPIC_API_KEY or ensure ingress token exists — see .env.local.example');
  }
  return client;
}

// Claude sometimes wraps JSON replies in a ```json ... ``` fence despite
// being asked for raw JSON — strip it before parsing.
function parseJson(text) {
  const trimmed = text.trim();
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
  return JSON.parse(fenced ? fenced[1] : trimmed);
}

// Fetch structured factoids for a batch of categories. Called at game start
// to build the fact bank — all questions are later constructed from these
// factoids rather than generated from scratch per turn.
export async function fetchFactsBatch(categories) {
  const anthropic = requireClient();
  const results = {};

  const batches = [];
  for (let i = 0; i < categories.length; i += CATEGORIES_PER_FETCH_BATCH) {
    batches.push(categories.slice(i, i + CATEGORIES_PER_FETCH_BATCH));
  }

  for (const batch of batches) {
    const categoryList = batch.map((c) => `"${c}"`).join(', ');

    const prompt = `You are an expert researcher. For each of the following categories: ${categoryList}

Provide ${FACTS_PER_CATEGORY} diverse, strictly factual data points per category. Organize each category's facts into these five buckets (2 facts per bucket):

1. Catalyst & Origins: Key dates, events, and underlying factors that caused or initiated this topic.
2. Execution & Methodology: The primary strategies, tools, techniques, or defining characteristics.
3. Key Figures & Collaborators: Crucial individuals, leaders, or recurring contributors.
4. Major Milestones & Turning Points: The most significant events, releases, or awards.
5. Verified Trivia & Behind-the-Scenes: Esoteric, lesser-known, yet confirmed and documented anecdotes.

Each fact must be objective and free of opinion or speculation.

Respond with ONLY a JSON object mapping each category to its array of facts:
{
  "Category Name": [
    {
      "fact": "A clear, specific factual statement",
      "answer": "The key piece of information (the trivia answer)",
      "bucket": 1,
      "difficulty": "easy",
      "answerWordCount": 2,
      "questionAngles": ["naming", "year", "person-to-achievement"],
      "sourceType": "encyclopedia"
    }
  ]
}

difficulty must be "easy", "medium", or "hard". Buckets 1-3 should lean easy/medium, bucket 4 medium/hard, bucket 5 hard.
questionAngles is an array of 1-3 strings describing how this fact could be asked as a trivia question (e.g. "naming", "year", "person-to-achievement", "number", "location", "cause-effect").
answerWordCount is the word count of the answer field.
sourceType is the kind of reference this fact would be found in. Use one of: "encyclopedia", "biography", "news-archive", "awards-registry", "music-database", "sports-database", "academic-journal", "government-record", "industry-publication", "documentary", "interview", "almanac".`;

    const response = await anthropic.messages.create({
      model: MODEL,
      max_tokens: 4096,
      messages: [{ role: 'user', content: prompt }],
    });

    const text = response.content[0].text;
    const parsed = parseJson(text);
    Object.assign(results, parsed);
  }

  return results;
}

// Generate a question for the active player.
//
// `constraints` — assembled by the Coherence Engine (lib/coherence.js).
//   Contains `promptInstructions` (array of strings), `category`, `difficulty`,
//   and any card effects. The CE owns all prompt-shaping logic; this function
//   just formats and sends.
// `activePlayerName` / `playerNames` — for host personalization (hostQuip).
export async function generateQuestion({
  constraints,
  factoid,
  activePlayerName,
  playerNames,
}) {
  const anthropic = requireClient();

  const instructions = constraints.promptInstructions.join('\n');
  const otherPlayers = playerNames.filter((n) => n !== activePlayerName).join(', ');

  let prompt;

  if (factoid) {
    const angle = factoid.questionAngles[Math.floor(Math.random() * factoid.questionAngles.length)];
    prompt = `You are the AI host of "Mind Your Friends," a fast-paced multiplayer
trivia game. Build a trivia question from this factoid for ${activePlayerName}
(other players: ${otherPlayers}).

Factoid: ${factoid.fact}
Answer: ${factoid.answer}
Question angle: ${angle}

${instructions}

Turn this factoid into an engaging trivia question using the given angle.
The answer MUST be exactly: ${factoid.answer}

Respond with ONLY a JSON object, no other text:
{
  "question": "the trivia question text",
  "answer": "${factoid.answer}",
  "hostQuip": "a short, personalized, game-show-host-style line addressed to ${activePlayerName} introducing the question"
}`;
  } else {
    prompt = `You are the AI host of "Mind Your Friends," a fast-paced multiplayer
trivia game. Generate one trivia question for ${activePlayerName} (other
players: ${otherPlayers}).

${instructions}

By default, the correct answer should be a short phrase of MORE than 3 words,
unless a card or round rule overrides this.

Respond with ONLY a JSON object, no other text:
{
  "question": "the trivia question text",
  "answer": "the correct answer",
  "hostQuip": "a short, personalized, game-show-host-style line addressed to ${activePlayerName} introducing the question"
}`;
  }

  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 2048,
    messages: [{ role: 'user', content: prompt }],
  });

  const text = response.content[0].text;
  return parseJson(text);
}

// Evaluate a player's answer.
//
// `roundRule` — used for special evaluation behavior (ELI5 judges
// understanding, Hot Take rewards confidence over correctness).
export async function evaluateAnswer({ question, correctAnswer, playerAnswer, roundRule }) {
  const anthropic = requireClient();

  const evaluationNote =
    roundRule?.id === 'eli5'
      ? 'This is an ELI5 round — judge whether the player demonstrated understanding, not exact wording.'
      : roundRule?.id === 'worstAnswerWins'
      ? 'This is a Worst Answer Wins round — the answer should be factually wrong. Do not evaluate for correctness.'
      : 'Use fuzzy matching — minor wording differences, typos, or synonyms still count as correct.';

  const prompt = `Question: ${question}
Expected answer: ${correctAnswer}
Player's answer: ${playerAnswer}

${evaluationNote}

Respond with ONLY a JSON object, no other text:
{
  "correct": true or false,
  "feedback": "a short, host-style line reacting to the answer"
}`;

  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 512,
    messages: [{ role: 'user', content: prompt }],
  });

  const text = response.content[0].text;
  return parseJson(text);
}

// Moderate a Heckle submission via host-reinterpretation.
export async function moderateHeckle({ heckleText, activePlayerName, hecklerName }) {
  const anthropic = requireClient();

  const prompt = `You are the AI host of "Mind Your Friends," a social trivia game.
A player named ${hecklerName} submitted this heckle aimed at ${activePlayerName}:

"${heckleText}"

Your job: deliver this heckle in your game-show-host voice. Rules:
- Light trash talk, teasing, and playful insults are ENCOURAGED — this is a party game
- Rewrite (don't censor) anything that crosses into slurs, hate speech, or attacks on identity
- Keep it short — one punchy line
- If the original is fine, you can use it nearly verbatim with your own flair

Respond with ONLY a JSON object:
{
  "heckle": "the host-delivered heckle line",
  "moderated": true or false
}

Set moderated to true only if you had to meaningfully change the intent.`;

  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 256,
    messages: [{ role: 'user', content: prompt }],
  });

  return parseJson(response.content[0].text);
}
