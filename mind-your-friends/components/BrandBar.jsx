'use client';

// The top bar: title treatment hard left, logo centred, room code right.
// Playtest notes 4 and 5; owner's August 18 2026 aesthetics pass moved it onto
// every page rather than the game page alone.
//
// Per CLAUDE.md's composition rule the title treatment never appears without
// the logo — which is why the logo is unconditional here. Neither piece drops
// on narrow screens any more; the title treatment shrinks instead.
//
// The title treatment is the official artwork and is never recoloured. The
// logo is the piece that changes colour per game.

import Logo, { LOGO_HEIGHT } from './Logo';
import Wordmark from './Wordmark';

export default function BrandBar({ code }) {
  return (
    // Two shapes, one set of elements — no duplicated markup, because a
    // second copy of the bar is a second copy to forget to update.
    //
    // Phone (2 columns): title treatment and room code share the top row, the
    // logo takes the full width beneath them. That row split exists because
    // the logo is a fixed 73px on EVERY screen (owner's call) — three things
    // will not fit across 390px, and the logo is not the one that gives.
    //
    // sm and up (3 columns): the familiar single row, with the logo genuinely
    // centred on the page rather than centred in whatever space the other two
    // leave over — hence explicit column starts rather than justify-between.
    <header className="mb-4 grid grid-cols-[1fr_auto] items-center gap-x-2 gap-y-3 sm:grid-cols-3">
      <div className="justify-self-start sm:col-start-1 sm:row-start-1">
        <Wordmark />
      </div>

      <div className="justify-self-end sm:col-start-3 sm:row-start-1">
        {code && (
          <span className="rounded bg-game-card px-3 py-1 font-mono text-lg tracking-widest">
            {code}
          </span>
        )}
      </div>

      <div className="col-span-2 justify-self-center sm:col-span-1 sm:col-start-2 sm:row-start-1">
        <Logo code={code} height={LOGO_HEIGHT} />
      </div>
    </header>
  );
}
