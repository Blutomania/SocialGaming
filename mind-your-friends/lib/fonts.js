// The title treatment's two faces (owner, August 20 2026), replacing the
// metallic SVG logotype.
//
// Loaded through next/font/google, which downloads and SELF-HOSTS the woff2 at
// build time. Nothing is fetched from fonts.googleapis.com at runtime: no
// third-party request on the critical path, no layout shift from a late font,
// and the game still renders correctly on a machine with no internet. Verified
// in .next/static/media — both faces ship as local woff2, not as a fallback.
//
// `display: 'swap'` plus next/font's generated fallback metrics means the
// treatment is readable immediately in a size-matched system face rather than
// invisible while the woff2 arrives. For a mark that sits in the top-left of
// every screen, a flash of nothing is worse than a flash of the fallback.

import { Bebas_Neue, Oswald } from 'next/font/google';

// D1's title face, named by the owner.
export const bebasNeue = Bebas_Neue({
  weight: '400',
  subsets: ['latin'],
  display: 'swap',
});

// F1. The owner's sheet labels this one "Modern Geometric Serif", but the
// artwork on it is unmistakably a heavy condensed SANS — no serifs on any
// glyph — so the label and the rendering disagree and the RENDERING is what
// was approved. Oswald 700 is the closest Google face to what that sample
// actually shows. If the label was the intent and a real geometric serif is
// wanted, this is the one line that changes.
export const oswald = Oswald({
  weight: '700',
  subsets: ['latin'],
  display: 'swap',
});
