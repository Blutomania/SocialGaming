'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { io } from 'socket.io-client';
import BrandBar from '../components/BrandBar';
import Wordmark from '../components/Wordmark';

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
        {/* Four imperatives, and the fourth is the game's name doing double
            duty as the punchline of the list — so it is set as the mark
            itself, not as type imitating it. The break before it is the beat,
            which is why it is a separate block rather than a fourth line.

            There is deliberately no hero treatment above this any more: with
            the mark in the top-left chrome AND here, a third copy at hero size
            made one screen say the game's name three times. The punchline is
            the copy worth keeping, because it is the one the sentence is
            walking towards. */}
        <div className="flex flex-col items-center pt-6 text-center">
          <p className="text-lg leading-relaxed text-gray-300">
            Prove Your Knowledge
            <br />
            Play Your Cards
            <br />
            Use Your Strategy
          </p>
          <Wordmark width={300} className="mt-6" />
        </div>

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
