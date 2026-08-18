'use client';

import GameCard from './GameCard';
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

  // What's in your hand sits at the front of the array, newest first: the card
  // you just picked, then Half-Off (which you always have), then everything
  // still on offer in its usual order. The explainer line that used to say
  // "you also have Half-Off" is gone — the card is in the grid with a check on
  // it, which says the same thing without a sentence.
  const orderedIds = [
    ...(selectedId ? [selectedId] : []),
    HALF_OFF.id,
    ...ALL_CARD_IDS.filter((id) => id !== selectedId),
  ];

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

      {/* Same card component, same size, as the in-game hand — so the card you
          picked here is visually the card you play later.
          Fixed-width cards in a wrap rather than a column count: the card owns
          its size now (GameCard.CARD_WIDTH), so a grid would only stretch it
          back out to whatever the column happens to be. */}
      <div className="flex flex-wrap justify-center gap-2">
        {orderedIds.map((id) => (
          <GameCard
            key={id}
            cardId={id}
            selected={selectedId === id}
            inHand={id === HALF_OFF.id || id === selectedId}
            // Half-Off is not a choice — everyone has it — so it is shown
            // rather than offered. No onClick means it renders as a div and
            // can't be tapped or focused.
            onClick={id === HALF_OFF.id ? undefined : setSelectedId}
          />
        ))}
      </div>

      {selectedId && (
        <p className="text-center text-sm text-gray-400">{CARDS[selectedId].description}</p>
      )}

      <button
        disabled={!selectedId}
        onClick={() => confirmPick(selectedId)}
        className="w-full rounded bg-game-accent px-4 py-2 font-semibold text-game-dark hover:opacity-90 disabled:opacity-40"
      >
        {selectedId ? `Pick ${CARDS[selectedId].name}` : 'Tap a card to select'}
      </button>
    </div>
  );
}
