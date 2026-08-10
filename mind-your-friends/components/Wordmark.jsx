'use client';

// The "Mind Your Friends" logotype.
//
// Deliberately monochrome — black or white depending on background, never
// recoloured (owner decision, August 2026). Only the emoji lockup varies in
// colour per game.
//
// Rendered as a CSS mask rather than an <img> or an inlined <svg>, for two
// reasons:
//
//   1. `currentColor` cannot cross an <img src> boundary. An externally
//      loaded SVG renders with its own baked-in fill, so `<img>` gives no
//      colour control at all — the logo would be stuck one colour on every
//      background.
//   2. Inlining the markup would work, but the asset is ~1.2MB of path data;
//      inlining puts all of it in the HTML payload on every render. As a mask
//      the browser fetches it once and caches it, and `background-color` (which
//      defaults to `currentColor` here) drives the colour.
//
// The source art is an auto-traced textured logotype — 29 stacked grey levels
// flattened into a single silhouette. See public/brand/wordmark-mono.svg.
export default function Wordmark({ className = '', width = 320, title = 'Mind Your Friends' }) {
  const height = Math.round((width * 69) / 587); // preserve the 587x69 aspect

  return (
    <span
      role="img"
      aria-label={title}
      className={className}
      style={{
        display: 'inline-block',
        width,
        height,
        backgroundColor: 'currentColor',
        WebkitMaskImage: 'url(/brand/wordmark-mono.svg)',
        maskImage: 'url(/brand/wordmark-mono.svg)',
        WebkitMaskRepeat: 'no-repeat',
        maskRepeat: 'no-repeat',
        WebkitMaskSize: 'contain',
        maskSize: 'contain',
        WebkitMaskPosition: 'center',
        maskPosition: 'center',
      }}
    />
  );
}
