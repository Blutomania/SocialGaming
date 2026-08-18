'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { io } from 'socket.io-client';
import BrandBar from '../components/BrandBar';

// A short-lived socket just to create/join — the game page opens its own.
export default function HomePage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState(null);

  function createGame() {
    if (!name.trim()) return setError('Enter your name');
    sessionStorage.setItem('myf:name', name.trim());
    sessionStorage.setItem('myf:action', 'create');
    router.push('/game/new');
  }

  function joinGame() {
    if (!name.trim()) return setError('Enter your name');
    if (!/^[A-Z]{4}$/i.test(code.trim())) return setError('Enter the 4-letter game code');
    sessionStorage.setItem('myf:name', name.trim());
    sessionStorage.setItem('myf:action', 'join');
    router.push(`/game/${code.trim().toUpperCase()}`);
  }

  return (
    // The brand bar sits at the top of every page now, so the title treatment
    // is upper left here exactly as it is in game — this page used to say the
    // game's name in plain purple type instead, which was neither the official
    // treatment nor in the right place.
    <main className="mx-auto min-h-screen max-w-7xl p-4 md:p-8">
      <BrandBar />

      <div className="flex flex-col items-center gap-6 pt-6">
      <p className="text-center max-w-md text-gray-300">
        A real-time multiplayer trivia game. Sabotage your friends, dodge their cards,
        and answer questions a personalized AI host throws your way.
      </p>

      <input
        className="w-64 rounded bg-game-card px-4 py-2 text-white placeholder-gray-400"
        placeholder="Your name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />

      <button
        className="w-64 rounded bg-game-accent px-4 py-2 font-semibold text-game-dark hover:opacity-90"
        onClick={createGame}
      >
        Create Game
      </button>

      <div className="flex w-64 gap-2">
        <input
          className="flex-1 rounded bg-game-card px-4 py-2 text-white placeholder-gray-400 uppercase"
          placeholder="CODE"
          maxLength={4}
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <button
          className="rounded bg-game-blue px-4 py-2 font-semibold hover:opacity-90"
          onClick={joinGame}
        >
          Join
        </button>
      </div>

      {error && <p className="text-game-red">{error}</p>}
      </div>
    </main>
  );
}
