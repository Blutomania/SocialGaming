'use client';

// The top bar: title treatment hard left, logo centred, room code right.
// Playtest notes 4 and 5.
//
// Per CLAUDE.md's composition rule the title treatment never appears without
// the logo — which is why the logo is unconditional here and the wordmark is
// the piece that drops on narrow screens, never the other way round.
//
// The title treatment is fixed monochrome (white on this dark ground) and
// never recoloured. The logo is the piece that changes colour per game.

import Logo from './Logo';
import Wordmark from './Wordmark';

export default function BrandBar({ code }) {
  return (
    <header className="mb-4 grid grid-cols-3 items-center gap-2">
      {/* Hidden below sm: at phone widths three elements in one row leaves
          nothing legible. The logo survives, per the composition rule. */}
      <div className="justify-self-start text-white">
        <Wordmark className="hidden sm:block" width={200} />
      </div>

      <div className="justify-self-center">
        <Logo code={code} height={44} />
      </div>

      <div className="justify-self-end">
        {code && (
          <span className="rounded bg-game-card px-3 py-1 font-mono text-lg tracking-widest">
            {code}
          </span>
        )}
      </div>
    </header>
  );
}
