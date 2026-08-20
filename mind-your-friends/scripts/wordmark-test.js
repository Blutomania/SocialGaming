// Title treatment distribution. Zero API cost, exhaustive rather than sampled.
//
// WHY THIS EXISTS. The owner asked for the two treatments at "50/50 randomly
// throughout the game". Two separate properties hide inside that sentence, and
// the first implementation got the second one wrong:
//
//   1. 50/50 across games.
//   2. INDEPENDENT of the logo's palette rotation, which hashes the same room
//      code. The naive version was 50.00/50.00 overall — perfectly fair by the
//      obvious measure — and still gave palette 0 one treatment 100% of the
//      time, because every odd multiplier collapses to the same parity bit mod
//      2 and `hash % 6` carries that same parity. Twelve visual combinations
//      silently became six, and nothing about the overall split showed it.
//
// So this checks the joint distribution, not just the marginal one. Room codes
// are 4 characters from a 24-letter alphabet, which is only 331,776 codes —
// small enough to test every one rather than sample.
//
// Run: node scripts/wordmark-test.js

import { treatmentIdForGame, TREATMENT_IDS } from '../lib/wordmarkTreatment.js';

// A copy of Logo.jsx's paletteForGame hash. It lives in a JSX file that node
// cannot import, and duplicating four lines is better than reshaping a
// component to suit a test. If that hash ever changes, this must change with
// it — the whole point is to compare against what the logo ACTUALLY does.
const PALETTE_COUNT = 6;
function paletteIndex(code) {
  let hash = 0;
  for (const char of code) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return hash % PALETTE_COUNT;
}

const CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ'; // must match generateGameCode()
const TOLERANCE = 2; // percentage points

let failures = 0;
const check = (cond, msg) => {
  console.log((cond ? '  PASS  ' : '  FAIL  ') + msg);
  if (!cond) failures++;
};

const counts = Object.fromEntries(TREATMENT_IDS.map((id) => [id, 0]));
const joint = {};
let total = 0;

for (const a of CHARS) for (const b of CHARS) for (const c of CHARS) for (const d of CHARS) {
  const code = a + b + c + d;
  const id = treatmentIdForGame(code);
  const pal = paletteIndex(code);
  counts[id]++;
  total++;
  joint[pal] = joint[pal] ?? Object.fromEntries(TREATMENT_IDS.map((t) => [t, 0]));
  joint[pal][id]++;
}

console.log(`--- every one of ${total.toLocaleString()} possible room codes ---`);
for (const id of TREATMENT_IDS) {
  const pct = (100 * counts[id]) / total;
  check(Math.abs(pct - 50) <= TOLERANCE, `${id} appears ${pct.toFixed(2)}% of the time`);
}

console.log('\n--- independent of the logo palette ---');
let worst = 0;
for (const pal of Object.keys(joint).sort()) {
  const row = joint[pal];
  const sum = TREATMENT_IDS.reduce((n, t) => n + row[t], 0);
  const pct = (100 * row[TREATMENT_IDS[0]]) / sum;
  worst = Math.max(worst, Math.abs(pct - 50));
  check(
    Math.abs(pct - 50) <= TOLERANCE,
    `palette ${pal}: ${TREATMENT_IDS[0]} ${pct.toFixed(2)}% / ${TREATMENT_IDS[1]} ${(100 - pct).toFixed(2)}%`
  );
}
console.log(`  worst deviation within a palette: ${worst.toFixed(2)} points`);

console.log('\n--- stable, which is the point of it being a hash ---');
check(
  treatmentIdForGame('WXYZ') === treatmentIdForGame('WXYZ'),
  'the same room code always gives the same treatment'
);
check(
  TREATMENT_IDS.includes(treatmentIdForGame(null)),
  'no room code (the join screen) still returns a real treatment'
);

console.log(failures === 0 ? '\n=== ALL PASSED ===' : `\n=== ${failures} FAILED ===`);
process.exit(failures === 0 ? 0 : 1);
