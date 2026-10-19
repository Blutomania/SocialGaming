'use client';

import { useState } from 'react';
import { CARD_INFO } from '../lib/cards';
import GameCard from './GameCard';

// Shown to every player during the CARD phase. First card played wins the
// FCFS slot (see GAME_DESIGN.md -> Card Resolution); everyone else's
// attempt is rejected by the server.
export default function CardHand({ game, myId, socket }) {
  const me = game.players.find((p) => p.id === myId);
  const [heckleText, setHeckleText] = useState('');
  const [pendingHeckle, setPendingHeckle] = useState(null);

  if (!me) return null;

  const slotTaken = !!game.cardSlot;
  const playedBy = slotTaken
    ? game.players.find((p) => p.id === game.cardSlot.playerId)?.name
    : null;

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
      <h3 className="text-sm font-semibold text-ui-ink">Your hand</h3>
      {/* Wrap, not fixed columns: the card carries its own width now
          (GameCard.CARD_WIDTH), so every card is the same size by
          construction — which is what the old fixed-column grid was for, and
          it did it only within a single layout. */}
      <div className="flex flex-wrap gap-2">
        {me.hand.map((id) => (
          <GameCard key={id} cardId={id} disabled={slotTaken} onClick={play} />
        ))}
        {me.hand.length === 0 && <p className="text-sm text-ui-faint">No cards left.</p>}
      </div>

      {pendingHeckle && (
        <div className="flex gap-2">
          <input
            className="field min-w-0 flex-1"
            placeholder="Type your heckle…"
            value={heckleText}
            onChange={(e) => setHeckleText(e.target.value)}
          />
          <button className="act" disabled={!heckleText.trim()} onClick={playHeckle}>
            Send
          </button>
        </div>
      )}

      {/* Name the person (§3f). Who played it is the social part — "a card
          was played" throws away the one fact the room wants to argue about. */}
      {slotTaken && (
        <p className="text-sm text-ui-faint">
          {playedBy ? `${playedBy} played ` : ''}
          {CARD_INFO[game.cardSlot.cardId].name} — the card slot is closed for this question.
        </p>
      )}
    </div>
  );
}
