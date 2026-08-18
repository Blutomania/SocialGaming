'use client';

// The **title treatment** (a.k.a. text treatment) — see CLAUDE.md → Glossary.
// The "logo" is the separate three-emoji mark, not this.
//
// This is the OFFICIAL artwork, public/brand/myf_title_trtmnt_trans.svg
// (owner, August 18 2026: the official title treatment, upper left, on every
// page). It is a textured metallic logotype — 29 stacked grey levels, from
// near-black through to near-white — and the texture is the point of it.
//
// WHY <img> AND NOT A CSS MASK. The previous version rendered
// wordmark-mono.svg as a mask so `currentColor` could recolour it. A mask
// keeps only the silhouette: every one of those 29 levels collapses to one
// flat colour, which throws away exactly what makes this the official mark
// rather than a lettering shape. So the artwork ships as artwork, and the
// colour control goes away with it — correctly, since the treatment is
// fixed and never recoloured anyway (that rule predates this change).
//
// It reads on a dark ground because the texture runs light; on a light ground
// it would need different artwork, not a different fill.
//
// Composition rule (unchanged): this must never appear without the logo
// beside it. The logo may appear alone; the title treatment may not.
//
// Payload note: the asset is ~2.1MB of path data. As an <img> the browser
// fetches it once and caches it across pages, which is the reason it is a
// plain <img> src rather than inlined markup — inlining would put all of it
// in the HTML on every render.

// The source art's aspect. Height is derived, never set independently, so the
// treatment can't be squashed by a stray class.
export const WORDMARK_ASPECT = 587 / 69;

// `width` is for the one place the treatment is the hero rather than chrome —
// the lobby's centre column. Left off, it takes the responsive bar sizes: at
// phone widths the top bar holds three things and this is the one with room to
// shrink. It no longer DISAPPEARS below sm — the owner asked for it on every
// page, and "every page" includes a phone.
//
// An inline width rather than another utility class, because a class passed in
// through `className` doesn't reliably beat the ones below — Tailwind's output
// order decides that, not the order they're written here.
export default function Wordmark({ className = '', width, title = 'Mind Your Friends' }) {
  return (
    <img
      src="/brand/myf_title_trtmnt_trans.svg"
      alt={title}
      style={width ? { width, maxWidth: '100%' } : undefined}
      className={`h-auto ${width ? '' : 'w-[150px] sm:w-[220px] lg:w-[260px]'} ${className}`}
    />
  );
}
