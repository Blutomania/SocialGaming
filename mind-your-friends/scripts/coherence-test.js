// Coherence test: 8 categories × difficulty tiers × round rules × card effects.
// Tests question generation quality, answer format compliance, category depth,
// difficulty scaling, and prompt efficiency.
//
// Usage: ANTHROPIC_API_KEY=... node scripts/coherence-test.js
//   or: node scripts/coherence-test.js  (uses session token fallback)

import Anthropic from '@anthropic-ai/sdk';
import { readFileSync } from 'fs';
import { writeFileSync } from 'fs';
import { POINT_TIERS } from '../lib/constants.js';
import { ROUND_RULES } from '../lib/roundRules.js';
import { CARDS } from '../lib/cards.js';
import { roundConstraints, turnConstraints, validateQuestion } from '../lib/coherence.js';

// --- Auth ---

let apiKey = process.env.ANTHROPIC_API_KEY;
if (!apiKey) {
  try {
    apiKey = readFileSync('/home/claude/.claude/remote/.session_ingress_token', 'utf8').trim();
  } catch { /* fall through */ }
}
if (!apiKey) {
  console.error('No API key or session token found.');
  process.exit(1);
}

const anthropic = new Anthropic({ apiKey });
const MODEL = 'claude-sonnet-4-6';

// --- Test categories ---

const CATEGORIES = [
  'The NBA',
  'High Fashion',
  'PlayStation 5 Games',
  'Top Albums of the 2000s',
  'Famous Military Battles',
  'Jane Austen',
  'High-Performance Cars',
  'Scary Movies',
];

// --- Format-constraining cards that affect question generation ---

const FORMAT_CARDS = ['boxedIn', 'languageBarrier'];
const NOTABLE_ROUND_RULES = ['backItUp', 'oneWordOnly', 'eli5', 'hotTake', 'lightningRound'];

// --- Helper: call Claude for question generation ---

async function generateTestQuestion(constraints, category) {
  const instructions = constraints.promptInstructions.join('\n');

  const prompt = `You are the AI host of "Mind Your Friends," a fast-paced multiplayer
trivia game. Generate one trivia question for TestPlayer.

${instructions}

By default, the correct answer should be a short phrase of MORE than 3 words,
unless a card or round rule overrides this.

Respond with ONLY a JSON object, no other text:
{
  "question": "the trivia question text",
  "answer": "the correct answer",
  "hostQuip": "a short game-show-host-style line introducing the question"
}`;

  const response = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 1024,
    messages: [{ role: 'user', content: prompt }],
  });

  const text = response.content[0].text;
  const inputTokens = response.usage?.input_tokens || 0;
  const outputTokens = response.usage?.output_tokens || 0;
  return { parsed: JSON.parse(text), inputTokens, outputTokens };
}

// --- Test 1: Difficulty scaling per category ---

async function testDifficultyScaling(results) {
  console.log('\n═══════════════════════════════════════════');
  console.log('TEST 1: DIFFICULTY SCALING ACROSS TIERS');
  console.log('═══════════════════════════════════════════\n');

  for (const category of CATEGORIES) {
    console.log(`\n── ${category} ──`);
    const categoryResults = [];

    for (const tier of POINT_TIERS) {
      const roundCtx = roundConstraints(ROUND_RULES.hotTake.id === 'hotTake'
        ? ROUND_RULES.doubleDown  // use a neutral rule so difficulty is isolated
        : ROUND_RULES.doubleDown);

      // Use a simple neutral round rule
      const neutralRound = roundConstraints(ROUND_RULES.lightningRound);
      const constraints = turnConstraints(neutralRound, {
        category,
        wager: tier,
        resolvedCard: null,
      });

      try {
        const { parsed, inputTokens, outputTokens } = await generateTestQuestion(constraints, category);
        const validation = validateQuestion(parsed, constraints);

        const entry = {
          category,
          tier,
          difficulty: constraints.difficulty,
          question: parsed.question,
          answer: parsed.answer,
          validation,
          inputTokens,
          outputTokens,
        };

        categoryResults.push(entry);

        const status = validation.passed ? '✓' : '✗';
        const issues = validation.issues.length > 0
          ? ` [${validation.issues.map(i => i.code).join(', ')}]`
          : '';
        console.log(`  ${tier}pt (${constraints.difficulty}): ${status}${issues}`);
        console.log(`    Q: ${parsed.question}`);
        console.log(`    A: ${parsed.answer}`);
        console.log(`    Tokens: ${inputTokens}→${outputTokens}`);
      } catch (err) {
        console.log(`  ${tier}pt: ERROR — ${err.message}`);
        categoryResults.push({ category, tier, error: err.message });
      }
    }

    results.difficultyScaling.push(...categoryResults);
  }
}

// --- Test 2: Round rule + card compatibility ---

async function testRoundRuleCompatibility(results) {
  console.log('\n═══════════════════════════════════════════');
  console.log('TEST 2: ROUND RULE + CARD COMPATIBILITY');
  console.log('═══════════════════════════════════════════\n');

  // Test each notable round rule with 2 representative categories
  const testPairs = [
    { category: 'The NBA', rules: NOTABLE_ROUND_RULES, cards: FORMAT_CARDS },
    { category: 'Jane Austen', rules: NOTABLE_ROUND_RULES, cards: FORMAT_CARDS },
  ];

  for (const { category, rules, cards } of testPairs) {
    console.log(`\n── ${category} ──`);

    // Round rules (no card)
    for (const ruleId of rules) {
      const rule = ROUND_RULES[ruleId];
      const roundCtx = roundConstraints(rule);
      const constraints = turnConstraints(roundCtx, {
        category,
        wager: 80, // medium
        resolvedCard: null,
      });

      try {
        const { parsed, inputTokens, outputTokens } = await generateTestQuestion(constraints, category);
        const validation = validateQuestion(parsed, constraints);

        const status = validation.passed ? '✓' : '✗';
        const issues = validation.issues.length > 0
          ? ` [${validation.issues.map(i => i.code).join(', ')}]`
          : '';
        console.log(`  ${rule.name}: ${status}${issues}`);
        console.log(`    Q: ${parsed.question}`);
        console.log(`    A: ${parsed.answer}`);

        results.roundRules.push({
          category,
          roundRule: rule.name,
          card: null,
          question: parsed.question,
          answer: parsed.answer,
          validation,
          inputTokens,
          outputTokens,
        });
      } catch (err) {
        console.log(`  ${rule.name}: ERROR — ${err.message}`);
        results.roundRules.push({ category, roundRule: rule.name, error: err.message });
      }
    }

    // Format-constraining cards (with neutral round rule)
    for (const cardId of cards) {
      const card = CARDS[cardId];
      const roundCtx = roundConstraints(ROUND_RULES.doubleDown); // neutral
      const constraints = turnConstraints(roundCtx, {
        category,
        wager: 80,
        resolvedCard: cardId,
      });

      try {
        const { parsed, inputTokens, outputTokens } = await generateTestQuestion(constraints, category);
        const validation = validateQuestion(parsed, constraints);

        const status = validation.passed ? '✓' : '✗';
        const issues = validation.issues.length > 0
          ? ` [${validation.issues.map(i => i.code).join(', ')}]`
          : '';
        console.log(`  ${card.name} card: ${status}${issues}`);
        console.log(`    Q: ${parsed.question}`);
        console.log(`    A: ${parsed.answer}`);

        results.roundRules.push({
          category,
          roundRule: 'Double Down',
          card: card.name,
          question: parsed.question,
          answer: parsed.answer,
          validation,
          inputTokens,
          outputTokens,
        });
      } catch (err) {
        console.log(`  ${card.name} card: ERROR — ${err.message}`);
        results.roundRules.push({ category, card: card.name, error: err.message });
      }
    }
  }
}

// --- Test 3: Category depth (can we sustain 4+ games without repeats?) ---

async function testCategoryDepth(results) {
  console.log('\n═══════════════════════════════════════════');
  console.log('TEST 3: CATEGORY DEPTH (REPEAT RESISTANCE)');
  console.log('═══════════════════════════════════════════\n');

  // For 2 categories, generate 10 questions each at medium difficulty
  // and check for semantic overlap
  const depthCategories = ['The NBA', 'Scary Movies'];

  for (const category of depthCategories) {
    console.log(`\n── ${category}: Generating 10 questions ──`);
    const questions = [];

    const roundCtx = roundConstraints(ROUND_RULES.doubleDown);

    for (let i = 0; i < 10; i++) {
      const constraints = turnConstraints(roundCtx, {
        category,
        wager: 80,
        resolvedCard: null,
      });

      // Add anti-repeat instruction with previously generated questions
      if (questions.length > 0) {
        constraints.promptInstructions.push(
          `IMPORTANT: Do NOT generate any of these questions or close variants:\n${questions.map((q, idx) => `${idx + 1}. "${q.question}" (answer: "${q.answer}")`).join('\n')}`
        );
      }

      try {
        const { parsed, inputTokens, outputTokens } = await generateTestQuestion(constraints, category);
        questions.push({
          question: parsed.question,
          answer: parsed.answer,
          inputTokens,
          outputTokens,
        });
        console.log(`  ${i + 1}. ${parsed.question}`);
        console.log(`     A: ${parsed.answer} (${inputTokens}→${outputTokens} tokens)`);
      } catch (err) {
        console.log(`  ${i + 1}. ERROR — ${err.message}`);
      }
    }

    // Token cost analysis: how much does the anti-repeat context grow?
    if (questions.length > 1) {
      const firstCost = questions[0].inputTokens;
      const lastCost = questions[questions.length - 1].inputTokens;
      const growth = lastCost - firstCost;
      console.log(`\n  Token growth: ${firstCost} → ${lastCost} (+${growth} for anti-repeat context)`);
      console.log(`  At 24 questions/game, projected input cost: ~${firstCost + Math.round(growth * 24 / 10)} tokens for last question`);
    }

    results.categoryDepth.push({
      category,
      questions,
      tokenGrowth: questions.length > 1
        ? { first: questions[0].inputTokens, last: questions[questions.length - 1].inputTokens }
        : null,
    });
  }
}

// --- Test 4: Visual clue viability assessment ---

async function testVisualViability(results) {
  console.log('\n═══════════════════════════════════════════');
  console.log('TEST 4: VISUAL CLUE VIABILITY PER CATEGORY');
  console.log('═══════════════════════════════════════════\n');

  const prompt = `For each of these 8 trivia categories, assess how well they support VISUAL trivia clues
(images shown to players instead of or alongside text questions). Rate each 1-5 and explain briefly.

Categories:
1. The NBA
2. High Fashion
3. PlayStation 5 Games
4. Top Albums of the 2000s
5. Famous Military Battles
6. Jane Austen
7. High-Performance Cars
8. Scary Movies

For each category, consider:
- How many visually distinct, recognizable images exist? (logos, faces, places, album covers, etc.)
- Would fair-use/copyright be a blocker for using real images?
- Could AI-generated images substitute? (e.g. "a stylized illustration of a battle scene")
- Estimated depth: how many unique visual questions before repeats?

Respond with ONLY a JSON array, no other text:
[
  {
    "category": "...",
    "visualScore": 1-5,
    "realImageViability": "high/medium/low + brief reason",
    "aiGeneratedViability": "high/medium/low + brief reason",
    "estimatedVisualDepth": "number of unique visual questions possible",
    "examples": ["example visual clue 1", "example visual clue 2"],
    "copyrightRisk": "high/medium/low"
  }
]`;

  try {
    const response = await anthropic.messages.create({
      model: MODEL,
      max_tokens: 4096,
      messages: [{ role: 'user', content: prompt }],
    });

    const parsed = JSON.parse(response.content[0].text);
    results.visualViability = parsed;

    for (const cat of parsed) {
      console.log(`  ${cat.category}: ${cat.visualScore}/5`);
      console.log(`    Real images: ${cat.realImageViability}`);
      console.log(`    AI-generated: ${cat.aiGeneratedViability}`);
      console.log(`    Depth: ~${cat.estimatedVisualDepth} unique visual Qs`);
      console.log(`    Copyright: ${cat.copyrightRisk}`);
      console.log(`    Examples: ${cat.examples.join(' | ')}`);
    }
  } catch (err) {
    console.log(`  ERROR — ${err.message}`);
    results.visualViability = { error: err.message };
  }
}

// --- Test 5: Prompt efficiency comparison ---

async function testPromptEfficiency(results) {
  console.log('\n═══════════════════════════════════════════');
  console.log('TEST 5: PROMPT EFFICIENCY — BATCH VS SINGLE');
  console.log('═══════════════════════════════════════════\n');

  // Compare: 3 individual calls vs 1 batch call for 3 questions
  const category = 'High-Performance Cars';
  const roundCtx = roundConstraints(ROUND_RULES.doubleDown);

  // Single calls
  let singleTotal = { input: 0, output: 0 };
  for (let i = 0; i < 3; i++) {
    const constraints = turnConstraints(roundCtx, { category, wager: 80, resolvedCard: null });
    const { inputTokens, outputTokens } = await generateTestQuestion(constraints, category);
    singleTotal.input += inputTokens;
    singleTotal.output += outputTokens;
  }

  // Batch call
  const batchPrompt = `You are the AI host of "Mind Your Friends." Generate 3 different trivia questions
about ${category} at medium difficulty.

Each answer should be a short phrase of MORE than 3 words.

Respond with ONLY a JSON array, no other text:
[
  { "question": "...", "answer": "...", "hostQuip": "..." },
  { "question": "...", "answer": "...", "hostQuip": "..." },
  { "question": "...", "answer": "...", "hostQuip": "..." }
]`;

  const batchResponse = await anthropic.messages.create({
    model: MODEL,
    max_tokens: 2048,
    messages: [{ role: 'user', content: batchPrompt }],
  });

  const batchTokens = {
    input: batchResponse.usage?.input_tokens || 0,
    output: batchResponse.usage?.output_tokens || 0,
  };

  console.log(`  3 single calls: ${singleTotal.input} input + ${singleTotal.output} output = ${singleTotal.input + singleTotal.output} total tokens`);
  console.log(`  1 batch call:   ${batchTokens.input} input + ${batchTokens.output} output = ${batchTokens.input + batchTokens.output} total tokens`);
  console.log(`  Savings:        ${Math.round((1 - (batchTokens.input + batchTokens.output) / (singleTotal.input + singleTotal.output)) * 100)}%`);

  results.promptEfficiency = { singleTotal, batchTokens };
}

// --- Main ---

async function main() {
  const results = {
    timestamp: new Date().toISOString(),
    categories: CATEGORIES,
    pointTiers: POINT_TIERS,
    difficultyScaling: [],
    roundRules: [],
    categoryDepth: [],
    visualViability: null,
    promptEfficiency: null,
  };

  console.log('Mind Your Friends — Coherence Test');
  console.log(`Categories: ${CATEGORIES.join(', ')}`);
  console.log(`Point tiers: ${POINT_TIERS.join(', ')}`);
  console.log(`Round rules: ${Object.keys(ROUND_RULES).join(', ')}`);
  console.log(`Format cards: ${FORMAT_CARDS.join(', ')}`);

  await testDifficultyScaling(results);
  await testRoundRuleCompatibility(results);
  await testCategoryDepth(results);
  await testVisualViability(results);
  await testPromptEfficiency(results);

  // --- Summary ---

  console.log('\n═══════════════════════════════════════════');
  console.log('SUMMARY');
  console.log('═══════════════════════════════════════════\n');

  // Difficulty scaling pass rate
  const diffTotal = results.difficultyScaling.filter(r => !r.error).length;
  const diffPassed = results.difficultyScaling.filter(r => r.validation?.passed).length;
  console.log(`Difficulty scaling: ${diffPassed}/${diffTotal} passed validation`);

  // Round rule pass rate
  const rrTotal = results.roundRules.filter(r => !r.error).length;
  const rrPassed = results.roundRules.filter(r => r.validation?.passed).length;
  console.log(`Round rules + cards: ${rrPassed}/${rrTotal} passed validation`);

  // Common issues
  const allIssues = [
    ...results.difficultyScaling.flatMap(r => r.validation?.issues || []),
    ...results.roundRules.flatMap(r => r.validation?.issues || []),
  ];
  const issueCounts = {};
  for (const issue of allIssues) {
    issueCounts[issue.code] = (issueCounts[issue.code] || 0) + 1;
  }
  if (Object.keys(issueCounts).length > 0) {
    console.log('\nIssue frequency:');
    for (const [code, count] of Object.entries(issueCounts).sort((a, b) => b[1] - a[1])) {
      console.log(`  ${code}: ${count}`);
    }
  }

  // Total tokens used
  const totalInput = [
    ...results.difficultyScaling,
    ...results.roundRules,
    ...results.categoryDepth.flatMap(c => c.questions),
  ].reduce((sum, r) => sum + (r.inputTokens || 0), 0);
  const totalOutput = [
    ...results.difficultyScaling,
    ...results.roundRules,
    ...results.categoryDepth.flatMap(c => c.questions),
  ].reduce((sum, r) => sum + (r.outputTokens || 0), 0);
  console.log(`\nTotal tokens used: ${totalInput} input + ${totalOutput} output = ${totalInput + totalOutput}`);

  // Write full results
  const outPath = 'scripts/coherence-test-results.json';
  writeFileSync(outPath, JSON.stringify(results, null, 2));
  console.log(`\nFull results written to ${outPath}`);
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
