'use client';

export default function CategoryPicker({ game, myId, socket }) {
  const isActive = game.players[game.activePlayerIndex].id === myId;

  if (!isActive) {
    return (
      <p className="text-center text-gray-300">
        {game.players[game.activePlayerIndex].name} is choosing a category…
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="text-center text-xl font-semibold">Pick a category</h2>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {game.categoryOptions.map((opt) => (
          <button
            key={opt.category}
            className="rounded bg-game-card px-4 py-3 text-left hover:bg-game-accent/30"
            onClick={() => socket.emit('turn:pickCategory', { category: opt.category })}
          >
            <div>{opt.category}</div>
            <div className="text-xs text-gray-400">via {opt.submittedBy}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
