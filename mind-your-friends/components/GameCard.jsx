'use client';

// One playing card. Every card is the same size and every card has its own
// art (playtest note 7) — a hand of identically-sized illustrated cards is
// readable at a glance, which a row of same-looking text buttons never was.
//
// The art is drawn here in CSS/emoji rather than shipped as images: eleven
// bespoke illustrations is an art commission, and this gets the layout,
// sizing and feel right first so that commission has a frame to fill. Each
// card's colour and glyph are fixed per card id, so a player learns "the red
// one with the boot" as a shape long before they've read its name.

import { CARD_INFO } from '../lib/cards';

// id -> { glyph, from, to }. Colours run warm for sabotage, cool for
// defence, neutral for the universal card, so the type reads before the name
// does.
const CARD_ART = {
  skip: { glyph: '⏭️', from: '#7f1d1d', to: '#ef4444' },
  redirect: { glyph: '🎯', from: '#7c2d12', to: '#f97316' },
  whoaNellie: { glyph: '🐴', from: '#78350f', to: '#f59e0b' },
  fiftyOff: { glyph: '✂️', from: '#831843', to: '#ec4899' },
  spotlight: { glyph: '🔦', from: '#713f12', to: '#eab308' },
  heckle: { glyph: '📣', from: '#4c1d95', to: '#a855f7' },
  languageBarrier: { glyph: '🗣️', from: '#581c87', to: '#c026d3' },
  boxedIn: { glyph: '📦', from: '#7c2d12', to: '#ea580c' },
  insurance: { glyph: '🛡️', from: '#064e3b', to: '#10b981' },
  fixer: { glyph: '🧰', from: '#14532d', to: '#22c55e' },
  halfOff: { glyph: '🏷️', from: '#1e3a8a', to: '#3b82f6' },
};

const FALLBACK = { glyph: '❓', from: '#1f2937', to: '#4b5563' };

// One size for every card, everywhere. Passed as an explicit aspect ratio
// rather than a fixed height so the same card works in a hand, in a picker,
// and on a result screen without three sets of numbers drifting apart.
export const CARD_ASPECT = '5 / 7';

export default function GameCard({
  cardId,
  onClick,
  disabled = false,
  selected = false,
  className = '',
}) {
  const info = CARD_INFO[cardId];
  const art = CARD_ART[cardId] ?? FALLBACK;
  if (!info) return null;

  const interactive = typeof onClick === 'function';
  const Tag = interactive ? 'button' : 'div';

  return (
    <Tag
      {...(interactive ? { onClick: () => onClick(cardId), disabled } : {})}
      title={info.description}
      style={{ aspectRatio: CARD_ASPECT, backgroundImage: `linear-gradient(160deg, ${art.from}, ${art.to})` }}
      className={`relative flex w-full flex-col justify-between overflow-hidden rounded-xl border-2 p-2 text-left transition ${
        selected ? 'border-white shadow-lg' : 'border-white/20'
      } ${interactive ? 'hover:-translate-y-1 hover:border-white/60 disabled:opacity-30 disabled:hover:translate-y-0' : ''} ${className}`}
    >
      <span className="text-[0.6rem] font-bold uppercase tracking-wider text-white/70">
        {info.type === 'anti-sabotage' ? 'Defence' : info.type === 'universal' ? 'Every round' : 'Sabotage'}
      </span>

      {/* Oversized, low-contrast glyph as the card's "illustration" — the
          thing the eye lands on before any text. */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 flex items-center justify-center text-6xl opacity-80"
      >
        {art.glyph}
      </span>

      <span className="relative text-sm font-bold leading-tight text-white drop-shadow">
        {info.name}
      </span>
    </Tag>
  );
}
