'use client';

const CATEGORIES = [
  { name: 'Pop Culture', emoji: '🎬' },
  { name: 'Science', emoji: '🔬' },
  { name: 'History', emoji: '🏛️' },
  { name: 'Sports', emoji: '⚽' },
  { name: 'Music', emoji: '🎵' },
  { name: 'Food & Drink', emoji: '🍕' },
  { name: 'Tech', emoji: '💻' },
  { name: 'Wild Card', emoji: '🃏' },
];

export default function CategoryPicker({ onSelect }) {
  return (
    <div className="w-full max-w-lg mx-auto">
      <h2 className="text-center text-gray-400 uppercase tracking-widest text-sm mb-6">
        Pick a Category
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.name}
            onClick={() => onSelect(cat.name)}
            className="flex flex-col items-center gap-2 bg-game-card hover:bg-game-accent border border-gray-700 hover:border-game-accent rounded-xl p-4 transition group"
          >
            <span className="text-3xl group-hover:scale-110 transition">{cat.emoji}</span>
            <span className="text-sm font-medium text-gray-300 group-hover:text-white text-center">
              {cat.name}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
