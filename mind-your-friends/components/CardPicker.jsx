'use client';

import GameCard from './GameCard';
import { useState, useEffect, useCallback } from 'react';
import { CARDS, CARD_INFO, ALL_CARD_IDS, HALF_OFF } from '../lib/cards';
import { CARD_PICK_TIMER_MS } from '../lib/constants';

const TIMER_SECONDS = CARD_PICK_TIMER_MS / 1000;

export default function CardPicker({ onPick }) {
  const [selectedId, setSelectedId] = useState(null);
  const [confirmed, setConfirmed] = useState(false);
  // What was actually confirmed — the timer can auto-pick a card the player
  // never touched, so `selectedId` is not always the answer.
  const [pickedId, setPickedId] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(TIMER_SECONDS);

  const confirmPick = useCallback((id) => {
    setConfirmed(true);
    setPickedId(id);
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
      // Done and unchangeable, so a stamp; then the live notice for what is
      // still happening. The card's name rather than "Card selected!" — the
      // stamp should say what was settled.
      <div className="space-y-4 py-8 text-center">
        <span className="stamp">{CARD_INFO[pickedId]?.name ?? 'Card'} is yours</span>
        <div>
          <span className="live">
            <span className="live-text">Waiting for the others to pick</span>
          </span>
        </div>
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
        <p className="text-sm text-ui-faint">
          Please select a card you will have throughout the game.
          You can play your card one time every round.
        </p>
        <div className={`mt-2 text-2xl font-bold tabular-nums ${urgent ? 'text-ui-caution animate-pulse' : 'text-ui-ink'}`}>
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
        <p className="text-center text-sm text-ui-faint">{CARDS[selectedId].description}</p>
      )}

      <button
        disabled={!selectedId}
        onClick={() => confirmPick(selectedId)}
        className="act w-full"
      >
        {selectedId ? `Pick ${CARDS[selectedId].name}` : 'Tap a card to select'}
      </button>
    </div>
  );
}
