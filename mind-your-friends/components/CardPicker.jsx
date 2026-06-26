'use client';

import { useState, useEffect, useCallback } from 'react';
import { CARDS, ALL_CARD_IDS, HALF_OFF } from '../lib/cards';
import { CARD_PICK_TIMER_MS } from '../lib/constants';

const TIMER_SECONDS = CARD_PICK_TIMER_MS / 1000;

export default function CardPicker({ onPick }) {
  const [selectedId, setSelectedId] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  const [secondsLeft, setSecondsLeft] = useState(TIMER_SECONDS);

  const confirmPick = useCallback((id) => {
    setConfirmed(true);
    onPick(id);
  }, [onPick]);

  useEffect(() => {
    if (confirmed) return;
    const interval = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          const pick = selectedId || ALL_CARD_IDS[Math.floor(Math.random() * ALL_CARD_IDS.length)];
          confirmPick(pick);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [confirmed, selectedId, confirmPick]);

  if (confirmed) {
    return (
      <div className="text-center py-8">
        <p className="text-game-green text-lg font-semibold">Card selected!</p>
        <p className="text-gray-400 mt-2">Waiting for other players...</p>
      </div>
    );
  }

  const urgent = secondsLeft <= 10;

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h2 className="text-xl font-semibold mb-1">Card Selection</h2>
        <p className="text-gray-400 text-sm">
          Please select a card you will have throughout the game.
          You can play your card one time every round.
        </p>
        <div className={`mt-2 text-2xl font-bold tabular-nums ${urgent ? 'text-game-red animate-pulse' : 'text-game-accent'}`}>
          {secondsLeft}s
        </div>
      </div>

      <div className="rounded bg-game-card/50 px-3 py-2 text-center text-sm text-gray-400">
        You also have <span className="text-game-green font-semibold">{HALF_OFF.name}</span> every round — {HALF_OFF.description.toLowerCase()}
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {ALL_CARD_IDS.map((id) => {
          const card = CARDS[id];
          const isSelected = selectedId === id;
          return (
            <button
              key={id}
              onClick={() => setSelectedId(id)}
              className={`rounded border-2 px-3 py-3 text-left transition ${
                isSelected
                  ? 'border-game-accent bg-game-accent/20'
                  : 'border-transparent bg-game-card hover:border-gray-600'
              }`}
            >
              <div className="font-semibold">
                {card.name}
                <span className={`ml-2 text-xs ${card.type === 'anti-sabotage' ? 'text-game-green' : 'text-game-red'}`}>
                  {card.type === 'anti-sabotage' ? 'Defense' : 'Sabotage'}
                </span>
              </div>
              <div className="mt-1 text-xs text-gray-400">{card.description}</div>
            </button>
          );
        })}
      </div>

      <button
        disabled={!selectedId}
        onClick={() => confirmPick(selectedId)}
        className="w-full rounded bg-game-accent px-4 py-2 font-semibold hover:opacity-90 disabled:opacity-40"
      >
        {selectedId ? `Pick ${CARDS[selectedId].name}` : 'Tap a card to select'}
      </button>
    </div>
  );
}
