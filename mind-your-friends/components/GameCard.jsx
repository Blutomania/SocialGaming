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

// One size for every card, everywhere. The aspect ratio is explicit rather
// than a fixed height so the same card works in a hand, in a picker, and on a
// result screen without three sets of numbers drifting apart.
export const CARD_ASPECT = '5 / 7';

// The width is explicit too, as of August 18 2026 (owner: cards 33% smaller).
// It used to be whatever `w-full` in the picker's 5-up grid worked out to —
// about 146px on a desktop, and something else in the hand's 6-up grid, so
// "every card the same size" was only true within one layout. A number here
// makes it true across all of them, and makes "33% smaller" a thing that can
// be asked for and checked.
export const CARD_WIDTH = 98; // 146 x 0.67

// The name is set as large as the card can actually hold, capped at 2x the
// old 14px (owner, August 18 2026: "all card names 2x bigger").
//
// It has to be computed rather than fixed, because 2x and "33% smaller cards"
// were asked for together and they fight: at 28px, "Language Barrier" breaks
// mid-word into "Lang / uage / Barri / er" inside a 98px card. So 28px is the
// CEILING, applied to every name short enough to take it (Skip, Heckle,
// 50% Off), and longer names step down to whatever fits.
//
// The measurement is the longest WORD, not the whole name. Two lines are fine
// (owner, August 18 2026: "Whoa Nellie can go on two lines"), so a name wraps
// between words for free and it is the unbreakable word that sets the limit —
// which is why "Whoa Nellie" is sized by "Nellie" and gets 20px, not by its
// full 11 characters.
//
// Hyphens count as break points too, since a browser will wrap there: it is
// "Half-" that has to fit, not "Half-Off". The +1 is the hyphen it keeps.
//
// 0.70em per character is a measured bold-sans average, not a guess from
// first principles — 0.58 was the guess, and it clipped Heckle and Boxed by a
// character each.
const NAME_MAX_PX = 28;   // 2x the old text-sm
const NAME_MIN_PX = 13;
const CARD_PAD_PX = 16;   // p-2 either side
const CHAR_EM = 0.7;
const BADGE_PX = 22;      // the in-hand check, plus its inset

function nameSizePx(name) {
  const chunks = name
    .split(/\s+/)
    .flatMap((word) => word.split('-').map((part, i, all) => part.length + (i < all.length - 1 ? 1 : 0)));
  const longest = Math.max(...chunks);
  const fits = (CARD_WIDTH - CARD_PAD_PX) / (longest * CHAR_EM);
  return Math.round(Math.min(NAME_MAX_PX, Math.max(NAME_MIN_PX, fits)));
}

export default function GameCard({
  cardId,
  onClick,
  disabled = false,
  selected = false,
  inHand = false,
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
      style={{
        width: CARD_WIDTH,
        aspectRatio: CARD_ASPECT,
        backgroundImage: `linear-gradient(160deg, ${art.from}, ${art.to})`,
      }}
      className={`relative flex flex-col justify-between overflow-hidden rounded-xl border-2 p-2 text-left transition ${
        selected ? 'border-white shadow-lg' : 'border-white/20'
      } ${interactive ? 'hover:-translate-y-1 hover:border-white/60 disabled:opacity-30 disabled:hover:translate-y-0' : ''} ${className}`}
    >
      {/* Name on top, type at the bottom (owner, August 18 2026) — the name is
          what a player is looking for, so it gets the first line and the size.
          `break-words` because the longest name (Language Barrier) does not
          fit this width on one line at this size and clipping it silently
          would be worse than wrapping it. */}
      <span
        style={{ fontSize: nameSizePx(info.name) }}
        className="relative font-bold leading-[0.95] text-white drop-shadow"
      >
        {/* A floated spacer, not padding: the check mark only obstructs the
            FIRST line, so only the first line should give up the width.
            Padding would indent every line of a two-line name for a badge
            that isn't next to them, and shrinking the type to fit beside the
            badge makes the longest names (Spotlight, Insurance) illegible
            before it makes them fit. */}
        {inHand && <span aria-hidden className="float-right h-5 w-[22px]" />}
        {info.name}
      </span>

      {/* Oversized, low-contrast glyph as the card's "illustration" — the
          thing the eye lands on before any text. */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-4 flex items-center justify-center text-4xl opacity-80"
      >
        {art.glyph}
      </span>

      <span className="relative text-[0.6rem] font-bold uppercase tracking-wider text-white/70">
        {info.type === 'anti-sabotage' ? 'Defence' : info.type === 'universal' ? 'Every round' : 'Sabotage'}
      </span>

      {/* "This one is yours." Sits above the glyph and outside the text flow so
          it reads the same on every card whatever the name does. */}
      {inHand && (
        <span
          aria-label="in hand"
          className="absolute right-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-white text-xs font-black text-game-dark shadow"
        >
          ✓
        </span>
      )}
    </Tag>
  );
}
