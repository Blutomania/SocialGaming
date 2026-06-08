/**
 * POST /api/generate-question
 * Body: { category, roundRule, hostPersonality, previousQuestions? }
 * Returns: { question, hint, correctAnswer, hostQuip }
 *
 * This route is also callable directly (e.g., for testing), but in normal
 * gameplay the server.js generates questions server-side via claudeClient.
 */

import { generateQuestion } from '../../../lib/claudeClient.js';
import { ROUND_RULES } from '../../../lib/roundRules.js';
import { NextResponse } from 'next/server';

export async function POST(request) {
  try {
    const body = await request.json();
    const { category, roundRule, hostPersonality, previousQuestions = [] } = body;

    if (!category || !roundRule || !hostPersonality) {
      return NextResponse.json(
        { error: 'category, roundRule, and hostPersonality are required.' },
        { status: 400 }
      );
    }

    const ruleData = ROUND_RULES[roundRule];
    if (!ruleData) {
      return NextResponse.json({ error: `Unknown round rule: ${roundRule}` }, { status: 400 });
    }

    const result = await generateQuestion({
      category,
      roundRule,
      roundRuleName: ruleData.name,
      roundRuleInstruction: ruleData.promptInstruction,
      hostPersonality,
      previousQuestions,
    });

    // Apply Infamous Last Words transform
    if (roundRule === 'INFAMOUS_LAST_WORDS') {
      const words = result.question.trim().split(/\s+/);
      if (words.length > 1) {
        words.pop();
        result.question = words.join(' ') + ' ___?';
      }
    }

    return NextResponse.json(result);
  } catch (err) {
    console.error('generate-question error:', err);
    return NextResponse.json({ error: err.message || 'Internal server error.' }, { status: 500 });
  }
}
