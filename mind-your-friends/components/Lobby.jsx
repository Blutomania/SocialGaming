'use client';

import { useState } from 'react';

const PERSONALITIES = ['Funny', 'Sarcastic', 'Encouraging', 'Mysterious', 'Game Show Host'];
const PERSONALITY_ICONS = {
  Funny: '😂',
  Sarcastic: '🙄',
  Encouraging: '🎉',
  Mysterious: '🔮',
  'Game Show Host': '🎙️',
};

export default function Lobby({ gameState, socketId, emit, code }) {
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState('');
  const isHost = gameState.hostId === socketId;

  function setPersonality(p) {
    emit('lobby:setPersonality', { code, personality: p });
  }

  function startGame() {
    setStarting(true);
    setStartError('');
    emit('game:start', { code }, (res) => {
      setStarting(false);
      if (res?.error) setStartError(res.error);
    });
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-2xl space-y-6">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-5xl font-display uppercase tracking-widest text-game-gold mb-1">
            Mind Your Friends
          </h1>
          <p className="text-gray-400">Share the code to invite friends</p>
          <div className="mt-4 inline-flex items-center gap-3 bg-game-card border-2 border-game-accent rounded-xl px-8 py-4">
            <span className="text-gray-400 text-sm uppercase tracking-widest">Game Code</span>
            <span className="font-mono text-4xl font-bold text-white tracking-widest">{code}</span>
          </div>
        </div>

        {/* Players */}
        <div className="bg-game-card rounded-2xl p-6 border border-gray-700">
          <h2 className="text-gray-400 text-sm uppercase tracking-widest mb-4">
            Players ({gameState.players.length})
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {gameState.players.map((p) => (
              <div
                key={p.id}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 ${
                  p.id === socketId ? 'bg-game-accent/20 border border-game-accent' : 'bg-gray-800'
                }`}
              >
                <span className="text-xl">{p.isHost ? '👑' : '🎮'}</span>
                <span className="font-medium truncate">{p.name}</span>
                {!p.connected && <span className="text-gray-500 text-xs">(away)</span>}
              </div>
            ))}
            {/* Empty slots hint */}
            {gameState.players.length < 8 && (
              <div className="flex items-center gap-2 rounded-lg px-3 py-2 bg-gray-900 border border-dashed border-gray-700 text-gray-600 text-sm">
                Waiting...
              </div>
            )}
          </div>
        </div>

        {/* Host personality picker (host only) */}
        {isHost && (
          <div className="bg-game-card rounded-2xl p-6 border border-gray-700">
            <h2 className="text-gray-400 text-sm uppercase tracking-widest mb-4">
              Host Personality
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {PERSONALITIES.map((p) => (
                <button
                  key={p}
                  onClick={() => setPersonality(p)}
                  className={`flex items-center gap-2 rounded-xl px-4 py-3 font-medium transition text-left ${
                    gameState.hostPersonality === p
                      ? 'bg-game-accent text-white'
                      : 'bg-gray-800 hover:bg-gray-700 text-gray-300'
                  }`}
                >
                  <span className="text-xl">{PERSONALITY_ICONS[p]}</span>
                  <span className="text-sm">{p}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Non-host personality display */}
        {!isHost && (
          <div className="bg-game-card rounded-xl p-4 border border-gray-700 text-center">
            <span className="text-gray-400 text-sm">Host personality: </span>
            <span className="font-bold text-white">
              {PERSONALITY_ICONS[gameState.hostPersonality]} {gameState.hostPersonality}
            </span>
          </div>
        )}

        {/* Start button */}
        {isHost ? (
          <div>
            {startError && <p className="text-game-red text-sm mb-2 text-center">{startError}</p>}
            <button
              onClick={startGame}
              disabled={starting || gameState.players.filter((p) => p.connected).length < 2}
              className="w-full py-5 rounded-2xl bg-game-gold hover:bg-amber-400 text-black font-display text-2xl uppercase tracking-widest transition disabled:opacity-40"
            >
              {starting ? 'Starting...' : 'Start Game'}
            </button>
            {gameState.players.filter((p) => p.connected).length < 2 && (
              <p className="text-gray-500 text-sm text-center mt-2">Need at least 2 players</p>
            )}
          </div>
        ) : (
          <div className="text-center text-gray-500 animate-pulse">
            Waiting for host to start the game...
          </div>
        )}
      </div>
    </div>
  );
}
