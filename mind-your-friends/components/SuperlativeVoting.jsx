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

  const remaining = categories.filter((c) => !myVotes?.[c.id]).length;

  return (
    <div className="space-y-4 text-left">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xl font-semibold">Superlatives</h3>
        <span className="text-sm text-gray-400">
          {votedCount}/{totalToVote} finished
        </span>
      </div>

      <p className="text-sm text-gray-400">
        {remaining > 0
          ? `Vote on ${remaining} more award${remaining === 1 ? '' : 's'}.`
          : 'Your ballot is in — waiting on everyone else.'}
      </p>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {categories.map((category) => {
        const myVote = myVotes?.[category.id];
        return (
          <div key={category.id} className="rounded bg-game-card p-4">
            <h4 className="font-semibold text-game-gold">{category.title}</h4>
            <p className="mb-3 text-sm text-gray-300">{category.description}</p>

            <div className="flex flex-wrap gap-2">
              {players.map((p) => {
                const selected = myVote === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    disabled={pending === category.id}
                    onClick={() => castVote(category.id, p.id)}
                    className={`rounded px-3 py-1 text-sm transition disabled:opacity-50 ${
                      selected
                        ? 'bg-game-gold text-black'
                        : 'bg-black/30 hover:bg-black/50'
                    }`}
                  >
                    {p.name}
                    {p.id === myId && ' (you)'}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
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
