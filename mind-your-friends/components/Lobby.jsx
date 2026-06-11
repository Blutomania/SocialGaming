'use client';

import { useState } from 'react';
import { CARDS, COMMON_CARD_IDS, PICKABLE_CARD_IDS } from '../lib/cards';
import { CATEGORIES_PER_PLAYER } from '../lib/constants';

const PICK_COUNT = 4;

export default function Lobby({ game, myId, socket }) {
  const me = game.players.find((p) => p.id === myId);
  const [categories, setCategories] = useState(Array(CATEGORIES_PER_PLAYER).fill(''));
  const [pickedCardIds, setPickedCardIds] = useState([]);

  if (!me) return null;

  function toggleCard(id) {
    setPickedCardIds((prev) => {
      if (prev.includes(id)) return prev.filter((c) => c !== id);
      if (prev.length >= PICK_COUNT) return prev;
      return [...prev, id];
    });
  }

  function submit() {
    const trimmed = categories.map((c) => c.trim()).filter(Boolean);
    if (trimmed.length !== CATEGORIES_PER_PLAYER) {
      alert(`Enter all ${CATEGORIES_PER_PLAYER} categories`);
      return;
    }
    if (pickedCardIds.length !== PICK_COUNT) {
      alert(`Pick exactly ${PICK_COUNT} cards`);
      return;
    }
    socket.emit('player:register', { categories: trimmed, pickedCardIds });
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

      {!me.registered && (
        <section className="space-y-4">
          <div>
            <h2 className="mb-2 text-xl font-semibold">
              Pick {CATEGORIES_PER_PLAYER} categories you like
            </h2>
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

          <div>
            <h2 className="mb-2 text-xl font-semibold">
              Pick {PICK_COUNT} cards ({pickedCardIds.length}/{PICK_COUNT})
            </h2>
            <p className="mb-2 text-sm text-gray-400">
              Everyone also starts with{' '}
              {COMMON_CARD_IDS.map((id) => CARDS[id].name).join(' and ')} for free.
            </p>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {PICKABLE_CARD_IDS.map((id) => {
                const card = CARDS[id];
                const selected = pickedCardIds.includes(id);
                return (
                  <button
                    key={id}
                    onClick={() => toggleCard(id)}
                    className={`rounded border-2 px-3 py-2 text-left transition ${
                      selected
                        ? 'border-game-accent bg-game-accent/20'
                        : 'border-transparent bg-game-card'
                    }`}
                  >
                    <div className="font-semibold">{card.name}</div>
                    <div className="text-xs text-gray-400">{card.description}</div>
                  </button>
                );
              })}
            </div>
          </div>

          <button
            className="w-full rounded bg-game-accent px-4 py-2 font-semibold hover:opacity-90"
            onClick={submit}
          >
            Ready
          </button>
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
