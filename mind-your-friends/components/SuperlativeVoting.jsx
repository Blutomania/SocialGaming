'use client';

import { useState } from 'react';

// Post-game superlative voting (CLAUDE.md item 35). Two stages, both rendered
// here: 'voting' (cast a ballot per category) and 'results' (the tallies plus
// the host's announcement quips).
//
// Other players' in-progress votes are deliberately not shown — playerView()
// only sends my own ballot plus a count of who's finished. Showing live tallies
// would let the room bandwagon, which makes the awards mean less.
export default function SuperlativeVoting({ postGame, players, myId, socket }) {
  const [pending, setPending] = useState(null);
  const [error, setError] = useState('');

  if (!postGame) return null;

  const { stage, categories, myVotes, votedCount, totalToVote, results } = postGame;

  if (stage === 'results') {
    return <SuperlativeResults results={results} />;
  }

  if (!categories || categories.length === 0) {
    return (
      <div className="rounded bg-game-card p-4 text-center text-sm text-gray-400">
        Tallying up the awards…
      </div>
    );
  }

  const castVote = (categoryId, targetPlayerId) => {
    setPending(categoryId);
    setError('');
    socket.emit('postgame:vote', { categoryId, targetPlayerId }, (ack) => {
      setPending(null);
      if (ack && ack.ok === false) setError(ack.message ?? 'Vote failed');
    });
  };

  const skipAll = () => {
    setPending('__all__');
    setError('');
    socket.emit('postgame:skip', {}, (ack) => {
      setPending(null);
      if (ack && ack.ok === false) setError(ack.message ?? 'Skip failed');
    });
  };

  // One award at a time (playtest note 11): the whole list on one screen read
  // as a form to fill in, and the awards are meant to land one at a time like
  // an announcement. `index` is derived from what's been voted on rather than
  // held in state, so a reconnect resumes on the right card.
  const index = categories.findIndex((c) => !myVotes?.[c.id]);
  const done = index === -1;
  const current = done ? null : categories[index];

  return (
    <div className="space-y-4 text-left">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xl font-semibold">Superlatives</h3>
        <span className="text-sm text-gray-400">
          {votedCount}/{totalToVote} finished
        </span>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {done ? (
        <div className="rounded bg-game-card p-6 text-center">
          <p className="font-semibold text-game-green">Your ballot is in.</p>
          <p className="mt-1 text-sm text-gray-400">Waiting on everyone else…</p>
        </div>
      ) : (
        <>
          <p className="text-sm text-gray-400">
            Award {index + 1} of {categories.length}
          </p>

          {/* The card is keyed by category id, so React tears down the old one
              and mounts a new one on every vote — which is what makes the CSS
              enter animation replay instead of firing once and never again. */}
          <div className="overflow-hidden">
            <div key={current.id} className="slide-in-right rounded bg-game-card p-4">
              <h4 className="text-lg font-semibold text-game-gold">{current.title}</h4>
              <p className="mb-4 text-sm text-gray-300">{current.description}</p>

              <div className="flex flex-wrap gap-2">
                {players.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    disabled={pending !== null}
                    onClick={() => castVote(current.id, p.id)}
                    className="rounded bg-black/30 px-4 py-2 text-sm transition hover:bg-game-gold hover:text-black disabled:opacity-50"
                  >
                    {p.name}
                    {p.id === myId && ' (you)'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={skipAll}
            disabled={pending !== null}
            className="w-full rounded border border-gray-700 px-4 py-2 text-sm text-gray-400 transition hover:text-white disabled:opacity-50"
          >
            Skip all
          </button>
        </>
      )}
    </div>
  );
}

function SuperlativeResults({ results }) {
  const awarded = (results ?? []).filter((r) => r.winnerNames.length > 0);

  if (awarded.length === 0) {
    return (
      <div className="rounded bg-game-card p-4 text-center text-sm text-gray-400">
        No superlatives this time — nobody voted.
      </div>
    );
  }

  return (
    <div className="space-y-3 text-left">
      <h3 className="text-xl font-semibold">Superlatives</h3>
      {awarded.map((r) => (
        <div key={r.id} className="rounded bg-game-card p-4">
          <h4 className="font-semibold text-game-gold">{r.title}</h4>
          <p className="text-lg">
            {r.winnerNames.join(' & ')}
            <span className="ml-2 text-sm text-gray-400">
              {r.voteCount} vote{r.voteCount === 1 ? '' : 's'}
              {r.winnerNames.length > 1 && ' — tied'}
            </span>
          </p>
          {r.quip && <p className="mt-1 text-sm italic text-gray-300">“{r.quip}”</p>}
        </div>
      ))}
    </div>
  );
}
