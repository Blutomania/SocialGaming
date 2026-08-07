'use client';

import { useState } from 'react';
import { CARD_INFO } from '../lib/cards';

// Shown to every player during the CARD phase. First card played wins the
// FCFS slot (see GAME_DESIGN.md -> Card Resolution); everyone else's
// attempt is rejected by the server.
export default function CardHand({ game, myId, socket }) {
  const me = game.players.find((p) => p.id === myId);
  const [heckleText, setHeckleText] = useState('');
  const [pendingHeckle, setPendingHeckle] = useState(null);

  if (!me) return null;

  const slotTaken = !!game.cardSlot;

  function play(cardId) {
    if (cardId === 'heckle') {
      setPendingHeckle(cardId);
      return;
    }
    socket.emit('turn:playCard', { cardId });
  }

  function playHeckle() {
    socket.emit('turn:playCard', { cardId: 'heckle', payload: { text: heckleText } });
    setPendingHeckle(null);
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-gray-300">Your hand</h3>
      <div className="flex flex-wrap gap-2">
        {me.hand.map((id) => (
          <button
            key={id}
            disabled={slotTaken}
            onClick={() => play(id)}
            title={CARD_INFO[id].description}
            className="rounded border border-game-accent px-3 py-2 text-sm hover:bg-game-accent/20 disabled:opacity-30"
          >
            {CARD_INFO[id].name}
          </button>
        ))}
        {me.hand.length === 0 && <p className="text-sm text-gray-500">No cards left.</p>}
      </div>

      {pendingHeckle && (
        <div className="flex gap-2">
          <input
            className="flex-1 rounded bg-game-card px-3 py-2"
            placeholder="Type your heckle…"
            value={heckleText}
            onChange={(e) => setHeckleText(e.target.value)}
          />
          <button className="rounded bg-game-accent px-3 py-2" onClick={playHeckle}>
            Send
          </button>
        </div>
      )}

      {slotTaken && (
        <p className="text-sm text-gray-400">
          {CARD_INFO[game.cardSlot.cardId].name} was played — card slot is closed for this question.
        </p>
      )}
    </div>
  );
}
