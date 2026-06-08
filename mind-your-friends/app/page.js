'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { io } from 'socket.io-client';

export default function HomePage() {
  const router = useRouter();
  const [mode, setMode] = useState(null); // 'create' | 'join'
  const [playerName, setPlayerName] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function getSocket() {
    return io({ path: '/socket.io', transports: ['websocket', 'polling'] });
  }

  function handleCreate() {
    if (!playerName.trim()) return setError('Enter your name.');
    setLoading(true);
    setError('');
    const socket = getSocket();
    socket.emit('lobby:create', { playerName: playerName.trim() }, (res) => {
      if (res.error) {
        setError(res.error);
        setLoading(false);
        socket.disconnect();
        return;
      }
      // Store socket id so the game page can reconnect
      sessionStorage.setItem('playerName', playerName.trim());
      sessionStorage.setItem('gameCode', res.code);
      // Disconnect and let game page handle its own socket
      socket.disconnect();
      router.push(`/game/${res.code}`);
    });
  }

  function handleJoin() {
    if (!playerName.trim()) return setError('Enter your name.');
    if (!joinCode.trim()) return setError('Enter the game code.');
    setLoading(true);
    setError('');
    const socket = getSocket();
    socket.emit('lobby:join', { code: joinCode.trim().toUpperCase(), playerName: playerName.trim() }, (res) => {
      if (res.error) {
        setError(res.error);
        setLoading(false);
        socket.disconnect();
        return;
      }
      sessionStorage.setItem('playerName', playerName.trim());
      sessionStorage.setItem('gameCode', joinCode.trim().toUpperCase());
      socket.disconnect();
      router.push(`/game/${joinCode.trim().toUpperCase()}`);
    });
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-6">
      {/* Title */}
      <div className="mb-10 text-center">
        <h1 className="text-6xl font-display uppercase tracking-widest text-game-gold mb-2 drop-shadow-lg">
          Mind Your Friends
        </h1>
        <p className="text-gray-400 text-lg">AI-powered social trivia — outsmart your crew.</p>
      </div>

      {/* Card */}
      <div className="bg-game-card rounded-2xl shadow-2xl p-8 w-full max-w-md border border-game-accent/30">
        {!mode && (
          <div className="space-y-4">
            <button
              onClick={() => setMode('create')}
              className="w-full py-4 rounded-xl bg-game-accent hover:bg-violet-500 text-white font-bold text-xl transition"
            >
              Create Game
            </button>
            <button
              onClick={() => setMode('join')}
              className="w-full py-4 rounded-xl bg-game-card border-2 border-game-accent hover:bg-game-accent/20 text-white font-bold text-xl transition"
            >
              Join Game
            </button>
          </div>
        )}

        {mode && (
          <div className="space-y-4">
            <button
              onClick={() => { setMode(null); setError(''); }}
              className="text-gray-400 hover:text-white text-sm mb-2 flex items-center gap-1"
            >
              ← Back
            </button>

            <div>
              <label className="block text-gray-300 text-sm mb-1">Your Name</label>
              <input
                type="text"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (mode === 'create' ? handleCreate() : handleJoin())}
                placeholder="Enter your name"
                maxLength={20}
                className="w-full bg-gray-800 rounded-lg px-4 py-3 text-white placeholder-gray-500 border border-gray-700 focus:outline-none focus:border-game-accent"
              />
            </div>

            {mode === 'join' && (
              <div>
                <label className="block text-gray-300 text-sm mb-1">Game Code</label>
                <input
                  type="text"
                  value={joinCode}
                  onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                  onKeyDown={(e) => e.key === 'Enter' && handleJoin()}
                  placeholder="e.g. XKQP"
                  maxLength={4}
                  className="w-full bg-gray-800 rounded-lg px-4 py-3 text-white placeholder-gray-500 border border-gray-700 focus:outline-none focus:border-game-accent font-mono text-2xl tracking-widest uppercase text-center"
                />
              </div>
            )}

            {error && <p className="text-game-red text-sm">{error}</p>}

            <button
              onClick={mode === 'create' ? handleCreate : handleJoin}
              disabled={loading}
              className="w-full py-4 rounded-xl bg-game-gold hover:bg-amber-400 text-black font-bold text-xl transition disabled:opacity-50"
            >
              {loading ? 'Connecting...' : mode === 'create' ? 'Create Game' : 'Join Game'}
            </button>
          </div>
        )}
      </div>

      <p className="mt-8 text-gray-600 text-sm">Up to 8 players. No account needed.</p>
    </main>
  );
}
