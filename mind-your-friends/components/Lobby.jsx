'use client';

import { useState } from 'react';
import { CATEGORIES_PER_PLAYER } from '../lib/constants';
import CardPicker from './CardPicker';

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

      {me.registered && (
        <section className="text-center py-4">
          <p className="text-game-green font-semibold">You're ready!</p>
          <p className="text-gray-400 text-sm mt-1">Waiting for everyone else…</p>
        </section>
      )}

      {isHost && (
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
