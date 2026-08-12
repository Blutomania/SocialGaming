'use client';

import { useEffect, useRef, useState } from 'react';
import { CATEGORIES_PER_PLAYER } from '../lib/constants';
import CardPicker from './CardPicker';

// Shown while the server builds the fact bank on game:start. That takes ~50s
// even with the batches running concurrently, and a Lobby that says nothing
// for that long reads as a hang — which is exactly how the "Start Game does
// nothing" bug was reported. See CLAUDE.md item 36.
//
// The elapsed counter is the point as much as the bar is: five concurrent
// batches all land within a few seconds of each other, so the bar sits at 0/5
// for most of the wait. A ticking clock is what tells a player the room is
// alive; the bar only confirms it at the end.
function StartProgress({ progress }) {
  const [elapsed, setElapsed] = useState(0);
  const startedAt = useRef(Date.now());

  useEffect(() => {
    const id = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt.current) / 1000)), 1000);
    return () => clearInterval(id);
  }, []);

  const total = progress.total || 0;
  const completed = progress.completed || 0;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  return (
    <section className="rounded bg-game-card px-4 py-5 text-center space-y-3">
      <p className="font-semibold">{progress.label || 'Starting the game…'}</p>
      <div className="h-2 w-full overflow-hidden rounded bg-black/40">
        <div
          className="h-full bg-game-accent transition-all duration-500"
          // 6% floor so there's a visible sliver of bar from the first frame —
          // otherwise the whole widget looks broken until the first batch lands.
          style={{ width: `${Math.max(pct, 6)}%` }}
        />
      </div>
      <p className="text-sm text-gray-400">
        {total > 0 ? `${completed} of ${total} batches · ` : ''}
        {elapsed}s elapsed
      </p>
      <p className="text-xs text-gray-500">
        Every question in the game is written from real facts about your categories.
        Hang tight — this only happens once.
      </p>
    </section>
  );
}

export default function Lobby({ game, myId, socket }) {
  const me = game.players.find((p) => p.id === myId);
  const [categories, setCategories] = useState(Array(CATEGORIES_PER_PLAYER).fill(''));
  const [step, setStep] = useState('categories'); // 'categories' | 'cards' | 'done'

  if (!me) return null;

  function submitCategories() {
    const trimmed = categories.map((c) => c.trim()).filter(Boolean);
    if (trimmed.length !== CATEGORIES_PER_PLAYER) {
      alert(`Enter all ${CATEGORIES_PER_PLAYER} categories`);
      return;
    }
    setStep('cards');
  }

  function handleCardPick(pickedCardId) {
    const trimmed = categories.map((c) => c.trim()).filter(Boolean);
    socket.emit('player:register', { categories: trimmed, pickedCardId });
    setStep('done');
  }

  const allRegistered = game.players.length >= 2 && game.players.every((p) => p.registered);
  const isHost = game.players[0]?.id === myId;
  // Room-wide, pushed by the server — every player sees the same thing while
  // the host's Start Game is working, not just the host.
  const starting = !!game.startProgress?.active;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <section>
        <h2 className="mb-2 text-xl font-semibold">Players ({game.players.length})</h2>
        <ul className="space-y-1">
          {game.players.map((p) => (
            <li key={p.id} className="flex items-center justify-between rounded bg-game-card px-3 py-2">
              <span>{p.name}{p.id === myId && ' (you)'}</span>
              <span className={p.registered ? 'text-game-green' : 'text-gray-400'}>
                {p.registered ? 'Ready' : 'Registering…'}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {!me.registered && step === 'categories' && (
        <section className="space-y-4">
          <div>
            <h2 className="mb-2 text-xl font-semibold">
              Pick {CATEGORIES_PER_PLAYER} categories you like
            </h2>
            <p className="text-sm text-gray-400 mb-3">
              These go into the shared pool — questions will be drawn from everyone's categories.
            </p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {categories.map((val, i) => (
                <input
                  key={i}
                  className="rounded bg-game-card px-3 py-2 placeholder-gray-400"
                  placeholder={`Category ${i + 1} (e.g. Pop Music)`}
                  value={val}
                  onChange={(e) => {
                    const next = [...categories];
                    next[i] = e.target.value;
                    setCategories(next);
                  }}
                />
              ))}
            </div>
          </div>

          <button
            className="w-full rounded bg-game-accent px-4 py-2 font-semibold hover:opacity-90"
            onClick={submitCategories}
          >
            Next — Pick Your Card
          </button>
        </section>
      )}

      {!me.registered && step === 'cards' && (
        <section>
          <CardPicker onPick={handleCardPick} />
        </section>
      )}

      {me.registered && !starting && (
        <section className="text-center py-4">
          <p className="text-game-green font-semibold">You're ready!</p>
          <p className="text-gray-400 text-sm mt-1">Waiting for everyone else…</p>
        </section>
      )}

      {starting && <StartProgress progress={game.startProgress} />}

      {isHost && !starting && (
        <button
          disabled={!allRegistered}
          className="w-full rounded bg-game-green px-4 py-2 font-semibold disabled:opacity-40"
          onClick={() => socket.emit('game:start')}
        >
          {allRegistered ? 'Start Game' : 'Waiting for everyone to register…'}
        </button>
      )}
    </div>
  );
}
