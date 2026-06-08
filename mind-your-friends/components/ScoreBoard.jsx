'use client';

const MEDALS = ['🥇', '🥈', '🥉'];

export default function ScoreBoard({ gameState, moments = [], onHome }) {
  const sorted = [...gameState.players]
    .filter((p) => p.connected || gameState.scores[p.id] !== undefined)
    .sort((a, b) => (gameState.scores[b.id] || 0) - (gameState.scores[a.id] || 0));

  const winner = sorted[0];

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-lg space-y-6">
        {/* Winner announce */}
        <div className="text-center">
          <div className="text-8xl mb-4">🏆</div>
          <h1 className="text-5xl font-display uppercase tracking-widest text-game-gold mb-2">
            Game Over!
          </h1>
          {winner && (
            <p className="text-2xl text-white">
              <strong className="text-game-gold">{winner.name}</strong> wins with{' '}
              <strong>{gameState.scores[winner.id]}</strong> points!
            </p>
          )}
        </div>

        {/* Leaderboard */}
        <div className="bg-game-card rounded-2xl overflow-hidden border border-gray-700">
          {sorted.map((p, i) => (
            <div
              key={p.id}
              className={`flex items-center justify-between px-6 py-4 border-b border-gray-700/50 last:border-b-0 ${
                i === 0 ? 'bg-game-gold/10' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{MEDALS[i] || `${i + 1}.`}</span>
                <span className={`font-bold text-lg ${i === 0 ? 'text-game-gold' : 'text-white'}`}>
                  {p.name}
                </span>
              </div>
              <span className={`font-mono text-xl font-bold ${i === 0 ? 'text-game-gold' : 'text-gray-300'}`}>
                {gameState.scores[p.id] ?? 0} pts
              </span>
            </div>
          ))}
        </div>

        {/* Highlight Reel — shareable moments */}
        {moments.length > 0 && (
          <div className="bg-game-card rounded-2xl border border-gray-700 overflow-hidden">
            <div className="px-5 py-3 border-b border-gray-700 flex items-center gap-2">
              <span className="text-lg">🎬</span>
              <h2 className="text-white font-bold tracking-wide uppercase text-sm">Highlight Reel</h2>
            </div>
            <ul className="divide-y divide-gray-700/50">
              {moments.map((m, i) => (
                <li key={i} className="flex items-start gap-3 px-5 py-3 text-gray-300 text-sm">
                  <span className="text-xl shrink-0">{m.emoji}</span>
                  <span>{m.text}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <button
          onClick={onHome}
          className="w-full py-4 rounded-2xl bg-game-accent hover:bg-violet-500 text-white font-bold text-xl transition"
        >
          Play Again
        </button>
      </div>
    </div>
  );
}
