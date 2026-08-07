'use client';

export default function ScoreBoard({ game, myId }) {
  const sorted = [...game.players].sort((a, b) => b.score - a.score);
  const topScore = sorted[0]?.score;
  const winners = sorted.filter((p) => p.score === topScore);

  return (
    <div className="mx-auto max-w-xl space-y-6 text-center">
      <h2 className="text-3xl font-bold text-game-gold">Game Over!</h2>
      <p className="text-lg">
        {winners.length > 1
          ? `It's a tie! Congrats to ${winners.map((w) => w.name).join(' & ')}!`
          : `${winners[0].name} wins!`}
      </p>

      <ul className="space-y-2">
        {sorted.map((p) => (
          <li
            key={p.id}
            className={`flex items-center justify-between rounded px-4 py-2 ${
              p.score === topScore ? 'bg-game-gold/30' : 'bg-game-card'
            }`}
          >
            <span>{p.name}{p.id === myId && ' (you)'}</span>
            <span className="font-mono">{p.score}</span>
          </li>
        ))}
      </ul>

      {game.highlightReel.length > 0 && (
        <div className="text-left">
          <h3 className="mb-2 text-xl font-semibold">Highlight Reel</h3>
          <ul className="space-y-1 text-sm text-gray-300">
            {game.highlightReel.map((moment, i) => (
              <li key={i}>• {moment}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
