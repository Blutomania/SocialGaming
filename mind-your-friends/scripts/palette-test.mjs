// Colour-role checks (CLAUDE.md item 53, docs/STYLE_GUIDE.md §1). Zero API
// cost, no dependencies. Run: node scripts/palette-test.mjs
//
// Two halves, because a palette can fail in two ways:
//
// 1. A pairing falls under its WCAG floor. Checked by arithmetic rather than
//    by eye, because eyes are what passed the old game.red at 2.67:1 on slate
//    — it looked fine to everyone and failed body text.
// 2. A screen bypasses the palette. A component asking for `text-gray-400`
//    or `bg-game-card` is choosing a colour by its look instead of by its
//    job, which is how MYF ended up with two golds and five greys. Tailwind
//    drops an unknown class silently, so nothing else would notice.

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PALETTE, CONTRAST_CONTRACT } from '../lib/palette.js';

const ROOT = fileURLToPath(new URL('..', import.meta.url));
let failures = 0;
const fail = (msg) => {
  failures += 1;
  console.log(`  FAIL ${msg}`);
};

// --- 1. The contrast contract ----------------------------------------------

function luminance(hex) {
  const n = parseInt(hex.slice(1), 16);
  const channel = (c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(n >> 16) + 0.7152 * channel((n >> 8) & 255) + 0.0722 * channel(n & 255);
}

export function contrast(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

console.log('Contrast contract');
for (const [fg, bg, floor] of CONTRAST_CONTRACT) {
  if (!PALETTE[fg] || !PALETTE[bg]) {
    fail(`${fg} on ${bg}: role not in PALETTE`);
    continue;
  }
  const ratio = contrast(PALETTE[fg], PALETTE[bg]);
  const line = `${fg.padEnd(12)} on ${bg.padEnd(12)} ${ratio.toFixed(2)}:1 (floor ${floor})`;
  if (ratio < floor) fail(line);
  else console.log(`  ok   ${line}`);
}

// The guide's central rule, asserted rather than hoped: Chosen and Act must be
// different colours, or a hovered action reads as already selected.
if (PALETTE.chosen.toLowerCase() === PALETTE.act.toLowerCase()) {
  fail('chosen and act are the same colour');
}

// The test must be able to fail. A deliberately bad pair has to come out
// under its floor, or the arithmetic above is not measuring anything.
if (contrast('#ef4444', PALETTE.ground) >= 4.5) {
  fail('self-check: the retired game.red should measure under 4.5 on slate');
}

// --- 2. Screens read colours by role ----------------------------------------

// Utilities that pick a colour by its look. `ui-*` is the only family allowed.
const RETIRED = /\b(?:bg|text|border|ring|placeholder|from|to|divide|outline)-(?:game|slate|gray|zinc|neutral|black|white|red|green|blue|yellow|amber|pink|purple)(?:-[a-z0-9]+)?(?:\/\d+)?\b/g;

// Cards are objects with their own art (item 40) and keep white type over
// their saturated gradients; that is their identity, not a screen colour.
const EXEMPT = new Set(['components/GameCard.jsx']);

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? walk(path) : [path];
  });
}

console.log('\nScreens use only ui-* colours');
const files = ['app', 'components']
  .flatMap((d) => walk(join(ROOT, d)))
  .filter((p) => /\.(jsx?|css)$/.test(p));

// Namespaces that no longer exist in tailwind.config.js at all. Even an
// exempt file cannot use these: the class is silently dropped and the element
// loses its colour. GameCard's in-hand check mark did exactly that the day
// game.* was removed, and only a grep caught it.
const DELETED = /\b(?:bg|text|border|ring|placeholder|from|to)-(?:game|slate)-[a-zA-Z]+\b/g;

// A `ui-*` class must name a real role. A typo (text-ui-inkfaint) is dropped
// just as silently as a retired token.
const UI_CLASS = /\b(?:bg|text|border|ring|placeholder|outline|from|to|divide)-ui-([a-zA-Z]+)\b/g;

let clean = 0;
for (const path of files) {
  const rel = relative(ROOT, path);
  const source = readFileSync(path, 'utf8');
  const problems = [];

  if (!EXEMPT.has(rel)) {
    problems.push(...[...source.matchAll(RETIRED)].map((m) => m[0]));
  } else {
    problems.push(...[...source.matchAll(DELETED)].map((m) => m[0]));
  }
  for (const [cls, role] of source.matchAll(UI_CLASS)) {
    if (!(role in PALETTE)) problems.push(`${cls} (no such role)`);
  }

  if (problems.length) fail(`${rel}: ${[...new Set(problems)].join(', ')}`);
  else clean += 1;
}
console.log(`  ok   ${clean} files clean`);

// globals.css must take the ground from the palette, never a typed value.
const css = readFileSync(join(ROOT, 'app/globals.css'), 'utf8');
if (/#[0-9a-f]{3,8}\b/i.test(css)) fail('app/globals.css contains a typed hex colour');
if (!css.includes("--ground: theme('colors.ui.ground')")) {
  fail('app/globals.css: --ground is not read from the palette');
}

console.log(failures ? `\n${failures} FAILED` : '\nAll palette checks pass');
process.exit(failures ? 1 : 0);
