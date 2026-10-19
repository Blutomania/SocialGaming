'use client';

export default function CategoryPicker({ game, myId, socket }) {
  const isActive = game.players[game.activePlayerIndex].id === myId;

  if (!isActive) {
    return (
      <div className="text-center">
        <span className="live">
          <span className="live-text">
            {game.players[game.activePlayerIndex].name} is choosing a category
          </span>
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="text-center text-xl font-semibold">Pick a category</h2>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {game.categoryOptions.map((opt) => (
          <button
            key={opt.category}
            // The whole box is the hit target (§5), and it is a choice — one
            // tap commits it, so it brightens on hover rather than filling.
            className="choice px-4 py-3 text-left"
            onClick={() => socket.emit('turn:pickCategory', { category: opt.category })}
          >
            <div>{opt.category}</div>
            {/* Attribution is the social beat ("Bob's Divorce"), so it is
                shown — but only when there is a name to show (§3a). */}
            {opt.submittedBy?.trim() && (
              <div className="text-xs text-ui-faint">via {opt.submittedBy}</div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
