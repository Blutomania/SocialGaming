// Generates the question-mark background field — public/brand/question-field.svg.
//
// The field is the game's ground texture (CLAUDE.md item 40): faded question
// marks scattered over the slate ground, present on every screen. It is
// TEXTURE, NOT CONTENT — nothing in it is meant to be read.
//
// Generated rather than hand-placed, for the same reason the difficulty ramp
// and the player colours are: the spec is a set of numbers (five mark colours
// in fixed proportions, one mark strength, one density), and a hand-placed
// field silently drifts from all of them the first time someone nudges it.
//
// Run: node scripts/build-question-field.mjs
// The output is committed; nothing at runtime depends on this script.
//
// THREE THINGS THAT ARE LOAD-BEARING, all from item 40:
//
//   1. The ground colour is NOT baked in. The tile is transparent and the
//      ground is a background-color underneath it, so the ground stays
//      re-tunable without regenerating the field. Same reason the mark
//      colours below are full-strength values composited at MARK_STRENGTH
//      rather than pre-multiplied against slate.
//   2. Mark strength is 10% and the field is dense. Those two trade off, and
//      the plate device depends on the balance: a plate is only visible
//      because the texture around it isn't. **If this ever needs adjusting,
//      add density, not opacity** — 10% is close enough to the floor that a
//      dim projector could push plates toward invisible.
//   3. The tile wraps. Marks that cross an edge are drawn again on the
//      opposite side, so the field repeats without seams at any size.

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const OUT = path.join(root, 'public/brand/question-field.svg');

const TILE = 600;
const MARK_STRENGTH = 0.1;

// Item 40's five marks and their share of the field. Full-strength values —
// see note 1 above.
const MARKS = [
  { hex: '#B03A42', share: 0.34 }, // brick — dominant
  { hex: '#9BA5AD', share: 0.22 }, // cool grey
  { hex: '#8C2730', share: 0.16 }, // deep red
  { hex: '#7E9AAB', share: 0.16 }, // steel
  { hex: '#C6CCD1', share: 0.12 }, // light grey
];

const COUNT = 44;          // marks per tile — this is the density dial
const SIZE_MIN = 54;
const SIZE_MAX = 132;
const TILT = 24;           // max rotation either way, degrees

// Seeded so the committed asset is reproducible: re-running this script must
// produce a byte-identical file, or every regeneration is a diff nobody can
// review.
function mulberry32(seed) {
  return function random() {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// The question mark itself, drawn in a 100x100 box as a stroked hook plus a
// dot rather than as text: a <text> element in a background SVG renders in
// whatever font the viewing machine happens to have, which is not something a
// style guide can specify. Geometry renders identically everywhere.
const GLYPH_HOOK = 'M 22 34 A 28 28 0 1 1 50 62 L 50 71';
const GLYPH_DOT = { cx: 50, cy: 89, r: 9 };
const GLYPH_STROKE = 15;

function markColours(random) {
  // Build the exact proportions as a bag and shuffle it, rather than rolling
  // per mark: at 44 marks a per-mark roll misses the published shares badly
  // enough to see (the 12% mark can vanish entirely).
  const bag = [];
  MARKS.forEach(({ hex, share }) => {
    const n = Math.round(share * COUNT);
    for (let i = 0; i < n; i++) bag.push(hex);
  });
  while (bag.length < COUNT) bag.push(MARKS[0].hex);
  bag.length = COUNT;
  for (let i = bag.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [bag[i], bag[j]] = [bag[j], bag[i]];
  }
  return bag;
}

const random = mulberry32(0x4d5946); // "MYF"
const colours = markColours(random);

const marks = [];
for (let i = 0; i < COUNT; i++) {
  marks.push({
    x: random() * TILE,
    y: random() * TILE,
    size: SIZE_MIN + random() * (SIZE_MAX - SIZE_MIN),
    tilt: (random() * 2 - 1) * TILT,
    hex: colours[i],
  });
}

function draw({ x, y, size, tilt, hex }) {
  const scale = size / 100;
  // Centre the glyph on (x, y) so the wrap test below can use one radius.
  const tx = x - size / 2;
  const ty = y - size / 2;
  return [
    `  <g transform="translate(${tx.toFixed(2)} ${ty.toFixed(2)}) scale(${scale.toFixed(4)}) rotate(${tilt.toFixed(2)} 50 50)"`,
    ` fill="none" stroke="${hex}" stroke-width="${GLYPH_STROKE}" stroke-linecap="round" opacity="${MARK_STRENGTH}">`,
    `<path d="${GLYPH_HOOK}"/>`,
    `<circle cx="${GLYPH_DOT.cx}" cy="${GLYPH_DOT.cy}" r="${GLYPH_DOT.r}" fill="${hex}" stroke="none"/>`,
    `</g>`,
  ].join('');
}

// Wrap: anything crossing an edge is drawn again on the far side. Without
// this the tile seams are visible as bands of empty ground.
const body = [];
for (const mark of marks) {
  for (const dx of [-TILE, 0, TILE]) {
    for (const dy of [-TILE, 0, TILE]) {
      if (dx === 0 && dy === 0) {
        body.push(draw(mark));
        continue;
      }
      const shifted = { ...mark, x: mark.x + dx, y: mark.y + dy };
      const r = mark.size / 2;
      const visible =
        shifted.x + r > 0 && shifted.x - r < TILE && shifted.y + r > 0 && shifted.y - r < TILE;
      if (visible) body.push(draw(shifted));
    }
  }
}

const svg = `<!-- Generated by scripts/build-question-field.mjs — do not edit by hand. -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${TILE} ${TILE}" width="${TILE}" height="${TILE}">
${body.join('\n')}
</svg>
`;

fs.writeFileSync(OUT, svg);
console.log(`Wrote ${path.relative(root, OUT)} — ${marks.length} marks, ${body.length} drawn (wrap included), ${MARK_STRENGTH * 100}% strength.`);
