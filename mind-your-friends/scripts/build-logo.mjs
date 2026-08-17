// Splits the logo (public/brand/MYF_emoji_two_trans.svg) into three
// independently colourable emoji, and writes the result to
// public/brand/logo-split.svg + lib/logoPaths.js.
//
// Why this exists: the source art has the three emoji merged into two <path>
// elements — one for the dark linework, one for the light fill — so no
// per-emoji colour is possible as-is. But each path is really a bag of
// disconnected subpaths (89 and 31 of them), and the three emoji don't
// overlap horizontally. So the split is just clustering subpaths by their x
// extent and finding the two widest gaps.
//
// Run: node scripts/build-logo.mjs
//
// Re-run this if the source art changes. The generated files are committed,
// so nothing at runtime depends on this script.

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const SOURCE = path.join(root, 'public/brand/MYF_emoji_two_trans.svg');

const svg = fs.readFileSync(SOURCE, 'utf8');
const viewBox = svg.match(/viewBox="([^"]*)"/)[1];

// Every path element, split into its subpaths. A subpath starts at an M/m
// command and runs to the next one.
const pathData = [...svg.matchAll(/<path[^>]*?d="([^"]*)"/g)].map((m) => m[1]);
const subpaths = pathData.flatMap((d, layer) =>
  (d.match(/[Mm][^Mm]*/g) ?? []).map((sub) => ({ layer, d: sub }))
);

// Horizontal extent of a subpath. Needs a real command parser rather than
// "every other number is an x": H and V take a single coordinate each, and
// treating their arguments as an x/y pair puts y values on the x axis, which
// smears every extent across the whole artboard and destroys the clustering.
const ARITY = { M: 2, L: 2, T: 2, C: 6, S: 4, Q: 4, A: 7, H: 1, V: 1, Z: 0 };

function xExtent(d) {
  const tokens = d.match(/[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:e[-+]?\d+)?/gi) ?? [];
  let cmd = null;
  let x = 0;
  let y = 0;
  const xs = [];
  let i = 0;

  while (i < tokens.length) {
    if (/[A-Za-z]/.test(tokens[i])) {
      cmd = tokens[i];
      i += 1;
      if (cmd.toUpperCase() === 'Z') continue;
    }
    if (cmd === null) break;
    const upper = cmd.toUpperCase();
    const relative = cmd !== upper;
    const args = tokens.slice(i, i + ARITY[upper]).map(Number);
    if (args.length < ARITY[upper]) break;
    i += ARITY[upper];

    if (upper === 'H') {
      x = relative ? x + args[0] : args[0];
    } else if (upper === 'V') {
      y = relative ? y + args[0] : args[0];
    } else if (upper === 'A') {
      x = relative ? x + args[5] : args[5];
      y = relative ? y + args[6] : args[6];
    } else {
      // Every other command ends on an x,y pair.
      x = relative ? x + args[args.length - 2] : args[args.length - 2];
      y = relative ? y + args[args.length - 1] : args[args.length - 1];
      // Control points count too — a curve can bulge past its endpoints.
      for (let k = 0; k + 1 < args.length; k += 2) {
        xs.push(relative ? x + args[k] - args[args.length - 2] : args[k]);
      }
    }
    xs.push(x);
  }

  return xs.length ? { min: Math.min(...xs), max: Math.max(...xs) } : null;
}

const artboardWidth = Number(viewBox.split(/[\s,]+/)[2]);

// Hairline artifacts hard against the left and right edges of the artboard —
// a few px wide, part of the export rather than part of the mark. Left in,
// they render as a thin coloured line beside the outermost emoji once the
// emoji start taking their own colours.
const isEdgeArtifact = (e) =>
  e.max - e.min < artboardWidth * 0.01 && (e.min <= 1 || e.max >= artboardWidth - 1);

const withExtent = subpaths
  .map((s) => ({ ...s, extent: xExtent(s.d) }))
  .filter((s) => s.extent && !isEdgeArtifact(s.extent));

// Find the horizontal gaps in the coverage — the spaces between the emoji.
const width = artboardWidth;
const sorted = [...withExtent].sort((a, b) => a.extent.min - b.extent.min);
const gaps = [];
let reach = sorted[0].extent.max;
for (const s of sorted.slice(1)) {
  if (s.extent.min > reach) gaps.push({ at: (reach + s.extent.min) / 2, size: s.extent.min - reach });
  reach = Math.max(reach, s.extent.max);
}

// The art carries hairline artifacts hard against both edges of the artboard
// (a few px wide, at x≈0 and x≈976), which produce two large "gaps" that are
// really just the margins. Those outrank the real inter-emoji gaps on width,
// so cutting on the widest two lands both cuts in the margins and leaves all
// three emoji in one group. Only interior gaps are candidates.
const MARGIN = width * 0.12;
const interior = gaps.filter((g) => g.at > MARGIN && g.at < width - MARGIN);
const cuts = interior
  .sort((a, b) => b.size - a.size)
  .slice(0, 2)
  .map((g) => g.at)
  .sort((a, b) => a - b);

if (cuts.length !== 2) {
  console.error(
    `Expected 2 interior gaps between emoji, found ${interior.length}. Art changed?`
  );
  process.exit(1);
}

// Assign by midpoint so the edge artifacts land in the nearest emoji rather
// than being dropped — they're part of the mark, just not part of the split.
const groupOf = (s) => {
  const mid = (s.extent.min + s.extent.max) / 2;
  return mid < cuts[0] ? 0 : mid > cuts[1] ? 2 : 1;
};

// [emoji][layer] -> concatenated path data. Layer 0 is the dark linework,
// layer 1 the light fill; keeping them separate is what lets each emoji take
// a colour without losing its outline.
const groups = [0, 1, 2].map((g) =>
  [0, 1].map((layer) =>
    withExtent
      .filter((s) => groupOf(s) === g && s.layer === layer)
      .map((s) => s.d.trim())
      .join(' ')
  )
);

const counts = [0, 1, 2].map((g) => withExtent.filter((s) => groupOf(s) === g).length);
console.log(`viewBox ${viewBox}`);
console.log(`cuts at x=${cuts.map((c) => c.toFixed(1)).join(', ')}`);
console.log(`subpaths per emoji: ${counts.join(', ')} (total ${withExtent.length})`);

const stamp = 'Generated by scripts/build-logo.mjs — do not edit by hand.';

fs.writeFileSync(
  path.join(root, 'lib/logoPaths.js'),
  `// ${stamp}
// Source art: public/brand/MYF_emoji_two_trans.svg
//
// The three emoji of the logo, split apart so each can be coloured on its
// own (see components/Logo.jsx). Each entry is [linework, fill] — two layers,
// because colouring a single merged silhouette loses the outlines that make
// the emoji readable.
export const LOGO_VIEWBOX = '${viewBox}';

export const LOGO_EMOJI = ${JSON.stringify(groups)};
`
);

fs.writeFileSync(
  path.join(root, 'public/brand/logo-split.svg'),
  `<!-- ${stamp} -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="${viewBox}">
${groups
  .map(
    (layers, i) => `  <g id="emoji-${i + 1}">
    <path fill="#090907" d="${layers[0]}"/>
    <path fill="#ffffff" d="${layers[1]}"/>
  </g>`
  )
  .join('\n')}
</svg>
`
);

console.log('wrote lib/logoPaths.js and public/brand/logo-split.svg');
