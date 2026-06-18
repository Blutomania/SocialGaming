import Anthropic from '@anthropic-ai/sdk';

const MODEL = 'claude-sonnet-4-6';

const apiKey = process.env.ANTHROPIC_API_KEY;
const client = apiKey ? new Anthropic({ apiKey }) : null;

function requireClient() {
  if (!client) {
    throw new Error('ANTHROPIC_API_KEY not set — see .env.local.example');
  }
  return client;
}

// Generate a question for the active player.
//
// `category` — one of the 6 options the active player chose from (see
// GAME_DESIGN.md → Categories).
// `roundRule` — the active round rule (lib/roundRules.js); its
// `promptInstruction` (if any) is folded into the prompt.
// `cardModifier` — optional prompt instruction from a resolved
// format-constraining card (Language Barrier, Boxed In). See GAME_DESIGN.md →
// "Format-constraining cards are generateQuestion() prompt modifiers".
// `activePlayerName` / `playerNames` — for host personalization (hostQuip).
export async function generateQuestion({
  category,
  roundRule,
  cardModifier,
  activePlayerName,
  playerNames,
}) {
  const anthropic = requireClient();

  const instructions = [
    `Category: ${category}`,
    'By default, the correct answer should be a short phrase of MORE than 3 words (see GAME_DESIGN.md → Question Design Conventions).',
    roundRule?.promptInstruction,
    cardModifier,
  ]
    .filter(Boolean)
    .join('\n');

  const prompt = `You are the AI host of "Mind Your Friends," a fast-paced multiplayer
trivia game. Generate one trivia question for ${activePlayerName} (other
players: ${playerNames.filter((n) => n !== activePlayerName).join(', ')}).

${instructions}

Respond with ONLY a JSON object, no other text:
{
  "question": "the trivia question text",
  "answer": "the correct answer",
  "hostQuip": "a short, personalized, game-show-host-style line addressed to ${activePlayerName} introducing the question"
}`;

  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 1024,
    messages: [{ role: 'user', content: prompt }],
  });

  const text = response.content[0].text;
  return JSON.parse(text);
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
      : roundRule?.id === 'hotTake'
      ? 'This is a Hot Take round — there is no single correct answer. Reward confident, well-argued answers.'
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
  return JSON.parse(text);
}
