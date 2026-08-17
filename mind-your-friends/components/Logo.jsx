'use client';

// The **logo** — the three-emoji mark (brain / pointing finger / group).
// Not the title treatment; that's components/Wordmark.jsx. Per CLAUDE.md's
// composition rule the logo may appear on its own, so this component takes no
// dependency on the wordmark.
//
// Each emoji is coloured independently, and the palette changes per game
// (playtest note 5). The source art has all three merged into two paths, so
// they're split apart ahead of time by scripts/build-logo.mjs — see
// lib/logoPaths.js. Inlined as real <path> elements rather than an <img>,
// because a colour can't cross an <img src> boundary.
//
// The linework layer takes the colour and the fill layer stays light: colour
// the fill instead and the emoji lose the outlines that make them readable at
// header size.

import { LOGO_EMOJI, LOGO_VIEWBOX } from '../lib/logoPaths';

// Picked to stay legible on the dark ground and distinct from each other at
// ~40px tall. Each game draws one triple, so the mark is recognisably the
// same shape every time but never quite the same colour twice in a row.
export const LOGO_PALETTES = [
  ['#ef4444', '#f59e0b', '#3b82f6'],
  ['#7c3aed', '#ec4899', '#10b981'],
  ['#10b981', '#3b82f6', '#f59e0b'],
  ['#f59e0b', '#ef4444', '#7c3aed'],
  ['#3b82f6', '#10b981', '#ec4899'],
  ['#ec4899', '#7c3aed', '#f59e0b'],
];

// Deterministic in the room code, so every player in the same game sees the
// same colours — a mark that differs per screen reads as a rendering bug, and
// "what colour is yours?" is not a conversation this needs to start.
export function paletteForGame(code) {
  if (!code) return LOGO_PALETTES[0];
  let hash = 0;
  for (const char of code) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return LOGO_PALETTES[hash % LOGO_PALETTES.length];
}

export default function Logo({ code, height = 40, className = '', title = 'Mind Your Friends' }) {
  const [vbX, vbY, vbW, vbH] = LOGO_VIEWBOX.split(/[\s,]+/).map(Number);
  const palette = paletteForGame(code);

  return (
    <svg
      role="img"
      aria-label={title}
      viewBox={LOGO_VIEWBOX}
      height={height}
      width={Math.round((height * vbW) / vbH)}
      className={className}
    >
      <title>{title}</title>
      {LOGO_EMOJI.map(([linework, highlights], i) => (
        <g key={i}>
          {/* Order matters: the coloured body goes down first and the light
              layer sits on top of it. Reversed, the body covers the details
              (the brain's folds, the fist's knuckles) and each emoji flattens
              into an unreadable blob. */}
          <path fill={palette[i]} d={linework} />
          <path fill="#f8fafc" d={highlights} />
        </g>
      ))}
    </svg>
  );
}
