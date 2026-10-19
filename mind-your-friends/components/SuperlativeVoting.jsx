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
      <div className="text-center">
        <span className="live">
          <span className="live-text text-sm">Tallying up the awards</span>
        </span>
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
        <span className="text-sm text-ui-faint">
          {votedCount}/{totalToVote} finished
        </span>
      </div>

      {error && <p className="text-sm text-ui-negative">{error}</p>}

      {done ? (
        // Settled (a stamp), then what is still happening (a live notice),
        // which goes when the last ballot lands and the results replace it.
        <div className="space-y-3 bg-ui-surface p-6 text-center">
          <span className="stamp">Your ballot is in</span>
          <div>
            <span className="live">
              <span className="live-text text-sm">Waiting on everyone else</span>
            </span>
          </div>
        </div>
      ) : (
        <>
          <p className="text-sm text-ui-faint">
            Award {index + 1} of {categories.length}
          </p>

          {/* The card is keyed by category id, so React tears down the old one
              and mounts a new one on every vote — which is what makes the CSS
              enter animation replay instead of firing once and never again. */}
          <div className="overflow-hidden">
            <div key={current.id} className="slide-in-right bg-ui-surface p-4">
              <h4 className="text-lg font-semibold">{current.title}</h4>
              {current.description && (
                <p className="mb-4 text-sm text-ui-faint">{current.description}</p>
              )}

              <div className="flex flex-wrap gap-2">
                {players.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    disabled={pending !== null}
                    onClick={() => castVote(current.id, p.id)}
                    // One tap casts the vote, so each name is an action, not a
                    // choice that stays selected: Act fill under the cursor.
                    className="act text-sm"
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
            className="choice w-full text-sm"
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
      <div className="bg-ui-surface p-4 text-center text-sm text-ui-faint">
        No superlatives this time — nobody voted.
      </div>
    );
  }

  return (
    <div className="space-y-3 text-left">
      <h3 className="text-xl font-semibold">Superlatives</h3>
      {awarded.map((r) => (
        <div key={r.id} className="bg-ui-surface p-4">
          <h4 className="font-semibold">{r.title}</h4>
          <p className="text-lg">
            <span className="stamp text-base normal-case">{r.winnerNames.join(' & ')}</span>
            <span className="ml-2 text-sm text-ui-faint">
              {r.voteCount} vote{r.voteCount === 1 ? '' : 's'}
              {r.winnerNames.length > 1 && ' — tied'}
            </span>
          </p>
          {/* The host's own words, so they earn the quotes (§3c). */}
          {r.quip?.trim() && (
            <p className="mt-1 text-sm italic text-ui-faint">
              “{r.quip.trim().replace(/^["“”]+|["“”]+$/g, '')}”
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
