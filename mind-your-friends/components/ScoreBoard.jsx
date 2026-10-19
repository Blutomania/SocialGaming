'use client';

import SuperlativeVoting from './SuperlativeVoting';
import ShareableQuestion from './ShareableQuestion';

export default function ScoreBoard({ game, myId, socket }) {
  const sorted = [...game.players].sort((a, b) => b.score - a.score);
  const topScore = sorted[0]?.score;
  const winners = sorted.filter((p) => p.score === topScore);

  return (
    <div className="mx-auto max-w-xl space-y-6 text-center">
      <h2 className="text-3xl font-bold">Game Over!</h2>
      <p className="text-lg">
        {winners.length > 1
          ? `It's a tie! Congrats to ${winners.map((w) => w.name).join(' & ')}!`
          : `${winners[0].name} wins!`}
      </p>

      <ul className="space-y-2">
        {sorted.map((p) => (
          // The final standings are settled, so the winner's row is a stamp —
          // the Chosen fill, not a button and not gold (gold means "do this").
          <li
            key={p.id}
            className={`flex items-center justify-between border-2 px-4 py-2 ${
              p.score === topScore
                ? 'border-ui-chosen bg-ui-chosen font-semibold text-ui-inkOnFill'
                : 'border-transparent bg-ui-surface'
            }`}
          >
            <span>{p.name}{p.id === myId && ' (you)'}</span>
            <span className="font-mono">{p.score}</span>
          </li>
        ))}
      </ul>

      {/* Post-game social layer. Both of these degrade to nothing if the
          server couldn't build them, so a failed superlative generation
          costs the flavor, not the whole end-of-game screen. */}
      <SuperlativeVoting
        postGame={game.postGame}
        players={game.players}
        myId={myId}
        socket={socket}
      />

      <ShareableQuestion questionLog={game.questionLog} gameCode={game.code} />

      {game.highlightReel.length > 0 && (
        <div className="text-left">
          <h3 className="mb-2 text-xl font-semibold">Highlight Reel</h3>
          <ul className="space-y-1 text-sm text-ui-faint">
            {game.highlightReel.map((moment, i) => (
              <li key={i}>• {moment}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
