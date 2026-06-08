'use client';

import { useState } from 'react';

const PRESETS = [50, 100, 200, 300, 500];

export default function WagerModal({ category, onSetWager }) {
  const [wager, setWager] = useState(100);

  return (
    <div className="w-full max-w-md mx-auto">
      <div className="bg-game-card rounded-2xl p-6 border border-game-accent shadow-2xl">
        <h2 className="text-center text-gray-400 uppercase tracking-widest text-sm mb-1">
          Set the Wager
        </h2>
        <p className="text-center text-gray-500 text-sm mb-6">
          Category: <strong className="text-white">{category}</strong>
        </p>

        {/* Slider */}
        <div className="mb-4">
          <div className="text-center text-game-gold font-display text-5xl mb-3">{wager}</div>
          <input
            type="range"
            min={50}
            max={500}
            step={50}
            value={wager}
            onChange={(e) => setWager(Number(e.target.value))}
            className="w-full accent-game-accent"
          />
          <div className="flex justify-between text-gray-600 text-xs mt-1">
            <span>50</span>
            <span>500</span>
          </div>
        </div>

        {/* Presets */}
        <div className="flex gap-2 mb-6">
          {PRESETS.map((p) => (
            <button
              key={p}
              onClick={() => setWager(p)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition ${
                wager === p
                  ? 'bg-game-accent text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {p}
            </button>
          ))}
        </div>

        <button
          onClick={() => onSetWager(wager)}
          className="w-full py-4 rounded-xl bg-game-gold hover:bg-amber-400 text-black font-bold text-xl transition"
        >
          Lock It In!
        </button>
      </div>
    </div>
  );
}
