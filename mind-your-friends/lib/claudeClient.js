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

// Test seam. scripts/start-progress-test.js swaps in a fake client so the
// fact-bank plumbing (batch concurrency + progress callbacks) can be
// exercised deterministically without spending real API calls. Nothing in
// the game ever calls this; pass null to restore the real client.
let clientOverride = null;
export function __setClientForTests(fake) {
  clientOverride = fake;
}

function requireClient() {
  if (clientOverride) return clientOverride;
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
//
// The batches are independent, so they run CONCURRENTLY (Promise.all) rather
// than in sequence. That is the whole difference between a ~250s game start
// and a ~50s one: with 3 players × 5 categories there are 15 unique categories
// = 5 batches at ~50s each, and running them one after another was the single
// reason "Start Game" read as a hang. See CLAUDE.md item 36.
//
// `onProgress(completed, total)` — optional; called once with (0, total)
// before any request goes out, then again as each batch lands. Because the
// batches are concurrent, `completed` is a count of finished batches, not an
// index — they do not finish in order. The server uses this to push a live
// progress state to the Lobby.
export async function fetchFactsBatch(categories, onProgress) {
  const anthropic = requireClient();

  const batches = [];
  for (let i = 0; i < categories.length; i += CATEGORIES_PER_FETCH_BATCH) {
    batches.push(categories.slice(i, i + CATEGORIES_PER_FETCH_BATCH));
  }

  let completed = 0;
  const report = (n) => {
    // A throwing progress callback must never take the game start down with
    // it — the fact bank is the real work, progress is decoration.
    try {
      onProgress?.(n, batches.length);
    } catch (err) {
      console.error('fetchFactsBatch progress callback failed:', err);
    }
  };
  report(0);

  const runBatch = async (batch) => {
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
    report(++completed);
    return parsed;
  };

  // Merged in batch order, not completion order, so an overlapping category
  // name resolves the same way it did when these ran sequentially.
  const parsedBatches = await Promise.all(batches.map(runBatch));
  return Object.assign({}, ...parsedBatches);
}

// Every generated question has to obey this, whatever else the round rule or
// cards are asking for. Questions were running long enough that reading them
// ate the clock (playtest, Aug 12) — and now that the whole room races to
// answer, a long question punishes slow readers rather than people who don't
// know the answer.
const LENGTH_RULE = `LENGTH IS A HARD CONSTRAINT. The question must be 8-20 words,
readable out loud in under 10 seconds, and at most two short sentences. No
preamble, no scene-setting, no "In this question..." — ask the thing directly.
If the factoid is complicated, ask about the single most interesting part of it
rather than trying to fit all of it in.`;

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

${LENGTH_RULE}

Respond with ONLY a JSON object, no other text:
{
  "question": "the trivia question text (8-20 words)",
  "answer": "${factoid.answer}",
  "hostQuip": "one short game-show-host line addressed to ${activePlayerName} introducing the question — under 12 words"
}`;
  } else {
    prompt = `You are the AI host of "Mind Your Friends," a fast-paced multiplayer
trivia game. Generate one trivia question for ${activePlayerName} (other
players: ${otherPlayers}).

${instructions}

By default, the correct answer should be a short phrase of MORE than 3 words,
unless a card or round rule overrides this.

${LENGTH_RULE}

Respond with ONLY a JSON object, no other text:
{
  "question": "the trivia question text (8-20 words)",
  "answer": "the correct answer",
  "hostQuip": "one short game-show-host line addressed to ${activePlayerName} introducing the question — under 12 words"
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

// Generate a "pick the right one" multiple-choice question for The Lineup
// round rule: 5 options, exactly one correct, the rest plausible near-misses.
// Unlike generateQuestion(), the correct answer isn't fuzzy-matched later —
// it's a discrete pick — so we ask Claude for an explicit correctIndex
// instead of inferring it by string-matching the options.
export async function generateLineupOptions({ factoid, activePlayerName, playerNames }) {
  const anthropic = requireClient();

  const otherPlayers = playerNames.filter((n) => n !== activePlayerName).join(', ');

  let prompt;
  if (factoid) {
    prompt = `You are the AI host of "Mind Your Friends," a fast-paced multiplayer
trivia game. Build a "pick the right one" multiple-choice question from this
factoid for ${activePlayerName} (other players: ${otherPlayers}).

Factoid: ${factoid.fact}
Correct answer: ${factoid.answer}

One of the 5 options MUST be exactly "${factoid.answer}". Generate 4 decoy
options that are plausible near-misses — real adjacent entities that are NOT
correct, or believable invented look-alikes. Decoys should genuinely tempt a
guess, not be obviously wrong.

Respond with ONLY a JSON object, no other text:
{
  "question": "the multiple-choice question text",
  "options": ["option A", "option B", "option C", "option D", "option E"],
  "correctIndex": 0,
  "hostQuip": "a short, personalized, game-show-host-style line addressed to ${activePlayerName} introducing the question"
}

"options" must have exactly 5 short, distinct entries in random order.
"correctIndex" is the 0-based index of "${factoid.answer}" within "options".`;
  } else {
    prompt = `You are the AI host of "Mind Your Friends," a fast-paced multiplayer
trivia game. Generate one "pick the right one" multiple-choice question for
${activePlayerName} (other players: ${otherPlayers}).

Pick a real, verifiable fact with one clearly correct answer. Generate 4
decoy options that are plausible near-misses — real adjacent entities that
are NOT correct, or believable invented look-alikes. Decoys should genuinely
tempt a guess, not be obviously wrong.

Respond with ONLY a JSON object, no other text:
{
  "question": "the multiple-choice question text",
  "options": ["option A", "option B", "option C", "option D", "option E"],
  "correctIndex": 0,
  "hostQuip": "a short, personalized, game-show-host-style line addressed to ${activePlayerName} introducing the question"
}

"options" must have exactly 5 short, distinct entries in random order.
"correctIndex" is the 0-based index of the correct one within "options".`;
  }

  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 1024,
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

// Score every player's submission for a Worst Answer Wins round in a single
// call (cheaper than N calls, and lets Claude judge creativity/plausibility
// relative to the other submissions in the same batch). Per GAME_DESIGN.md:
// each axis is 1-10 where 1 is the "best" (most wrong / most creative / most
// convincing) and 10 is the "worst" (correct / boring / unbelievable) --
// lowest total across the three axes wins.
export async function evaluateWorstAnswers({ question, correctAnswer, submissions }) {
  const anthropic = requireClient();

  const list = submissions
    .map((s, i) => `${i + 1}. ${s.name}: "${s.answer || '(no answer submitted)'}"`)
    .join('\n');

  const prompt = `Question: ${question}
Expected correct answer: ${correctAnswer}

This is a "Worst Answer Wins" round — every player was told to submit an
answer that is confidently, entertainingly WRONG. Score each submission on
three axes, each 1-10:
- factuallyWrong: how far from the truth? 1 = maximally wrong, 10 = actually correct
- creativelyWrong: how inventive is the wrongness? 1 = most creative/funny, 10 = laziest/most boring
- plausibility: how convincing does it sound despite being false? 1 = most convincing, 10 = obviously absurd
A blank submission ("(no answer submitted)") should score 10 on all three axes —
they didn't attempt the bit.

Submissions:
${list}

Respond with ONLY a JSON array, no other text, one object per submission in
the SAME ORDER as listed above:
[
  { "factuallyWrong": 1-10, "creativelyWrong": 1-10, "plausibility": 1-10, "feedback": "a short, host-style line reacting to this specific answer" }
]`;

  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 1536,
    messages: [{ role: 'user', content: prompt }],
  });

  const text = response.content[0].text;
  const scores = parseJson(text);
  if (!Array.isArray(scores) || scores.length !== submissions.length) {
    throw new Error('evaluateWorstAnswers: response length did not match submissions');
  }
  return scores;
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

// Generates the post-game superlative categories from what actually happened
// in the game. One call, not one per category — same batching reason as
// evaluateWorstAnswers: cheaper, and it lets Claude pick a *set* of awards
// that don't all reward the same player.
//
// Deliberately grounded in the highlight reel and question log rather than
// invented: a superlative nobody recognizes ("Most Diplomatic") is worse than
// no superlative at all, because the room can't vote on it honestly.
export async function generateSuperlatives({ highlightReel, questionLog, playerNames }) {
  const anthropic = requireClient();

  const moments = highlightReel.slice(-40).join('\n') || '(nothing notable was logged)';
  const questions = questionLog
    .map((q) => `Q${q.index + 1} [${q.category}] ${q.question} -> ${q.outcomeSummary}`)
    .join('\n') || '(no questions recorded)';

  const prompt = `A group of friends just finished a party trivia game. Here are the players:
${playerNames.join(', ')}

Memorable moments logged during the game:
${moments}

The questions asked and how they went:
${questions}

Invent 3-4 superlative award categories for the group to vote on, based on what
ACTUALLY happened above. Rules:
- Every category must be recognizable to someone who was in this game — reference
  real events from the log, not generic party-game awards.
- They should be funny and affectionate, not mean. This is a casual social game.
- Do NOT decide the winners. The players vote; you only write the categories.
- Vary them — don't write four awards that would all obviously go to one person.

Respond with ONLY a JSON array, no other text:
[
  {
    "id": "short_snake_case_id",
    "title": "The award name",
    "description": "one line explaining what it's for, referencing what happened"
  }
]`;

  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 1024,
    messages: [{ role: 'user', content: prompt }],
  });

  const parsed = parseJson(response.content[0].text);
  return Array.isArray(parsed) ? parsed : [];
}

// Writes the host's announcement line for each superlative winner once voting
// closes. Batched into a single call for the same reason as above.
export async function narrateSuperlativeResults({ results }) {
  const anthropic = requireClient();

  // The id must appear in the prompt, or Claude has no way to echo it back and
  // will helpfully return the title instead — which silently matches nothing
  // on the other side.
  const summary = results
    .map((r) => `[${r.id}] ${r.title}: ${r.winnerNames.join(' & ')} (${r.voteCount} vote(s))`)
    .join('\n');

  const prompt = `You are the AI host of a party trivia game announcing the final superlative
awards. Here are the categories and who the group voted for:

${summary}

Write one short, punchy announcement line per award — the kind a game show host
delivers. Address winners by name. Affectionate teasing is good; meanness is not.

Respond with ONLY a JSON array, in the same order as the awards above. Use the
exact id shown in [square brackets], not the award title:
[{ "id": "the_award_id", "quip": "the host's line" }]`;

  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 768,
    messages: [{ role: 'user', content: prompt }],
  });

  const parsed = parseJson(response.content[0].text);
  return Array.isArray(parsed) ? parsed : [];
}
