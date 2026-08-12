'use client';

import { useEffect, useRef, useState } from 'react';
import { CATEGORIES_PER_PLAYER } from '../lib/constants';
import { CATEGORY_SUGGESTIONS } from '../lib/categories';
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

// Tap to pick, type only if you want to. Five typed category boxes was the
// most laborious moment in the game (playtest, Aug 12); this is the fix,
// alongside dropping 5 to 3. The free-text field stays because a category
// credited to "Bob's Divorce" is the joke — attribution is a designed beat,
// and a fixed list can't produce it.
function CategoryChooser({ chosen, onChange, onDone }) {
  const [own, setOwn] = useState('');

  function toggle(category) {
    if (chosen.includes(category)) {
      onChange(chosen.filter((c) => c !== category));
    } else if (chosen.length < CATEGORIES_PER_PLAYER) {
      onChange([...chosen, category]);
    }
  }

  function addOwn() {
    const value = own.trim();
    if (!value || chosen.includes(value) || chosen.length >= CATEGORIES_PER_PLAYER) return;
    onChange([...chosen, value]);
    setOwn('');
  }

  const full = chosen.length >= CATEGORIES_PER_PLAYER;

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">
          Pick {CATEGORIES_PER_PLAYER} categories
        </h2>
        <p className="mt-1 text-sm text-gray-400">
          They go into the shared pool, with your name on them — everyone sees who picked what.
        </p>
      </div>

      {/* Chosen row doubles as the counter: three slots, filled or empty. */}
      <div className="flex flex-wrap gap-2">
        {Array.from({ length: CATEGORIES_PER_PLAYER }).map((_, i) => {
          const value = chosen[i];
          return value ? (
            <button
              key={value}
              onClick={() => onChange(chosen.filter((c) => c !== value))}
              className="rounded-full bg-game-accent px-3 py-1 text-sm font-semibold"
              title="Remove"
            >
              {value} ✕
            </button>
          ) : (
            <span
              key={`empty-${i}`}
              className="rounded-full border border-dashed border-gray-600 px-3 py-1 text-sm text-gray-500"
            >
              empty
            </span>
          );
        })}
      </div>

      <div className="space-y-3">
        {CATEGORY_SUGGESTIONS.map(({ group, items }) => (
          <div key={group}>
            <p className="mb-1 text-xs uppercase tracking-wide text-gray-500">{group}</p>
            <div className="flex flex-wrap gap-2">
              {items.map((item) => {
                const isChosen = chosen.includes(item);
                return (
                  <button
                    key={item}
                    onClick={() => toggle(item)}
                    disabled={!isChosen && full}
                    className={`rounded-full px-3 py-1 text-sm transition ${
                      isChosen
                        ? 'bg-game-accent font-semibold'
                        : 'bg-game-card hover:bg-gray-700 disabled:opacity-30'
                    }`}
                  >
                    {item}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-2">
        <input
          className="flex-1 rounded bg-game-card px-3 py-2 placeholder-gray-400"
          placeholder="Or enter your own…"
          value={own}
          disabled={full}
          onChange={(e) => setOwn(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addOwn()}
        />
        <button
          className="rounded bg-game-blue px-4 py-2 font-semibold disabled:opacity-40"
          disabled={full || !own.trim()}
          onClick={addOwn}
        >
          Add
        </button>
      </div>

      <button
        className="w-full rounded bg-game-accent px-4 py-2 font-semibold hover:opacity-90 disabled:opacity-40"
        disabled={!full}
        onClick={onDone}
      >
        {full ? 'Next — Pick Your Card' : `Pick ${CATEGORIES_PER_PLAYER - chosen.length} more`}
      </button>
    </section>
  );
}

export default function Lobby({ game, myId, socket }) {
  const me = game.players.find((p) => p.id === myId);
  const [categories, setCategories] = useState([]);
  const [step, setStep] = useState('categories'); // 'categories' | 'cards' | 'done'

  if (!me) return null;

  function submitCategories() {
    if (categories.length !== CATEGORIES_PER_PLAYER) return;
    setStep('cards');
  }

  function handleCardPick(pickedCardId) {
    socket.emit('player:register', { categories, pickedCardId });
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
        <CategoryChooser chosen={categories} onChange={setCategories} onDone={submitCategories} />
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
