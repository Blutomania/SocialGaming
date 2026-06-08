'use client';

import { useState } from 'react';

const CARD_INFO = {
  WHOA_NELLIE: { name: 'Whoa Nellie', emoji: '🐴', description: 'Skip question, get new one.', target: 'none' },
  REDIRECT: { name: 'Redirect', emoji: '↩️', description: 'Pass question to another player.', target: 'other' },
  HINT_ME_UP: { name: 'Hint Me Up', emoji: '💡', description: 'AI reveals a hint.', target: 'none' },
  BEAR_MARKET: { name: 'Bear Market', emoji: '🐻', description: 'Wager goes up 50%.', target: 'none' },
  BULL_MARKET: { name: 'Bull Market', emoji: '🐂', description: 'Wager goes down 50%.', target: 'none' },
  PINCH_PENNY: { name: 'Pinch Penny', emoji: '💰', description: 'Active player loses 25% of total if wrong.', target: 'other' },
  SAFETY_NET: { name: 'Safety Net', emoji: '🛡️', description: 'No point loss if wrong.', target: 'none' },
  MUTED: { name: 'Muted', emoji: '🔇', description: 'Target player skips next turn.', target: 'other' },
  HALFTIME: { name: 'Halftime', emoji: '⏱️', description: "Timer is cut in half.", target: 'other' },
};

export default function CardHand({
  cardId,
  players,
  socketId,
  onPlay,
  onSkip,
  alreadyPlayed,
  phase,
}) {
  const [showTargetPicker, setShowTargetPicker] = useState(false);
  const [played, setPlayed] = useState(false);

  const card = cardId ? CARD_INFO[cardId] : null;
  const otherPlayers = players.filter((p) => p.connected && p.id !== socketId);

  if (!card || alreadyPlayed || played) {
    return (
      <div className="text-center text-gray-600 text-sm py-4">
        {alreadyPlayed || played ? 'Card played this round.' : 'No card in hand.'}
      </div>
    );
  }

  function handlePlay(targetId = null) {
    setPlayed(true);
    setShowTargetPicker(false);
    onPlay(targetId);
  }

  return (
    <div className="w-full max-w-sm mx-auto">
      <p className="text-center text-gray-500 text-xs uppercase tracking-widest mb-3">Your Card</p>
      <div className="bg-gradient-to-br from-game-accent/40 to-game-card border-2 border-game-accent rounded-2xl p-5 shadow-xl">
        <div className="text-center mb-3">
          <span className="text-5xl">{card.emoji}</span>
          <h3 className="text-white font-bold text-lg mt-2">{card.name}</h3>
          <p className="text-gray-400 text-sm mt-1">{card.description}</p>
        </div>

        {showTargetPicker ? (
          <div className="space-y-2">
            <p className="text-gray-400 text-xs text-center mb-2">Choose target:</p>
            {otherPlayers.map((p) => (
              <button
                key={p.id}
                onClick={() => handlePlay(p.id)}
                className="w-full py-2 bg-game-accent rounded-lg text-white font-medium hover:bg-violet-500 transition"
              >
                {p.name}
              </button>
            ))}
            <button
              onClick={() => setShowTargetPicker(false)}
              className="w-full py-2 bg-gray-800 rounded-lg text-gray-400 hover:bg-gray-700 transition text-sm"
            >
              Cancel
            </button>
          </div>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => {
                if (card.target === 'other') {
                  setShowTargetPicker(true);
                } else {
                  handlePlay(null);
                }
              }}
              className="flex-1 py-2 bg-game-gold rounded-xl text-black font-bold hover:bg-amber-400 transition"
            >
              Play Card
            </button>
            <button
              onClick={() => setPlayed(true)}
              className="px-4 py-2 bg-gray-800 rounded-xl text-gray-400 hover:bg-gray-700 transition text-sm"
            >
              Hold
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
