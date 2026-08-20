'use client';

// The **title treatment** (a.k.a. text treatment) — see CLAUDE.md → Glossary.
// The "logo" is the separate three-emoji mark, not this.
//
// Owner's call, August 20 2026: the metallic SVG logotype is retired in favour
// of two live-type treatments, shown 50/50. It was 2.1MB of path data drawn for
// a LIGHT ground — its 29 grey levels ran #0b0b06 to #f4f3f1, so on slate
// everything below about #9d9c94 fell under 3.5:1 and simply was not there.
// Roughly two-thirds of the artwork was invisible, which is what read as "dim".
// Live type has no such problem, weighs nothing, and stays sharp at any size.
//
// The composition rule is UNCHANGED: this must never appear without the logo
// beside it. The logo may appear alone; the title treatment may not.
//
// The "fixed monochrome, never recoloured" rule is now per treatment rather
// than global — each of the two has its own colour, and that colour is part of
// its identity. Neither is recoloured by its call site, which is what that rule
// was protecting.

import { bebasNeue, oswald } from '../lib/fonts';
import { TREATMENT_IDS, treatmentIdForGame } from '../lib/wordmarkTreatment';

// Both colours are the owner's, sampled from the supplied sheet, and both were
// MEASURED against the slate ground rather than trusted by eye — the same
// discipline lib/difficultyColors.js and the player colours are held to.
//
// They land 6.14:1 and 6.02:1, which is the interesting part: the pair is
// within 0.12 of itself, so neither treatment reads as the heavier or the
// fainter one. A 50/50 mark that changed the page's weight depending on which
// side of the coin came up would be a worse mark than either half.
const TREATMENTS = {
  f1: { font: oswald, color: '#C7CBCC', tracking: '0.02em' },    // 6.14:1 on #2F4459 — AA
  d1: { font: bebasNeue, color: '#D9C79B', tracking: '0.04em' }, // 6.02:1 on #2F4459 — AA
};

// Two sizes, named rather than numeric. The old component took a pixel `width`
// because it was an <img> with a fixed aspect; live type is sized by its type
// size, and a caller passing a width would be setting the one thing it should
// not.
//
// `chrome` is the top bar on every page — it steps up with the viewport,
// because at phone widths that bar holds three things and this is the one with
// room to give. `hero` is the single place the treatment is the subject rather
// than the furniture: the join screen's punchline.
const SIZES = {
  chrome: 'text-[26px] sm:text-[34px] lg:text-[40px]',
  hero: 'text-[34px] sm:text-[56px]',
};

export default function Wordmark({ code, size = 'chrome', className = '', title = 'Mind Your Friends' }) {
  const treatment = TREATMENTS[treatmentIdForGame(code)] ?? TREATMENTS[TREATMENT_IDS[0]];

  return (
    <span
      // Real text, so it is selectable, searchable, readable by a screen
      // reader, and scales with the type ramp. The <img alt> that used to
      // carry this job is gone with the artwork.
      className={`${treatment.font.className} ${SIZES[size] ?? SIZES.chrome} inline-block whitespace-nowrap uppercase leading-none ${className}`}
      style={{ color: treatment.color, letterSpacing: treatment.tracking }}
    data-treatment={treatmentIdForGame(code)}
    >
      {title}
    </span>
  );
}
