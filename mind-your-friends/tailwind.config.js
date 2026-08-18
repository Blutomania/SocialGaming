/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './components/**/*.{js,jsx}',
    './app/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        // The ground system (CLAUDE.md item 40). `slate` is THE ground colour,
        // and the question plates are this same value with the question-mark
        // texture switched off — one token, deliberately, so a plate can never
        // drift a shade away from the ground it's cut out of.
        //
        // Marks are full-strength and composited at 10% over the ground; they
        // are not pre-multiplied, so the ground stays re-tunable without
        // re-deriving all five.
        slate: {
          DEFAULT: '#2F4459', // ground + plate
          text:    '#EEF3F7', // 8.99:1 — AAA
          muted:   '#B9C4CF', // 5.67:1 — AA
          accent:  '#E8737F', // 3.44:1 — large text / non-text only
        },
        mark: {
          brick:  '#B03A42',
          deep:   '#8C2730',
          grey:   '#9BA5AD',
          steel:  '#7E9AAB',
          light:  '#C6CCD1',
        },

        // Pre-slate palette. Still referenced across the components; kept until
        // the repaint lands so this commit stays additive.
        game: {
          dark: '#0d0d1a',
          card: '#1a1a2e',
          // Owner's call, August 18 2026: the purple this used to be (#7c3aed)
          // "does not work". Gold reads as the game's own colour rather than a
          // framework default, and it is the one accent that survives both
          // grounds — 12.3:1 on game.dark, 6.41:1 on the slate ground, so it
          // passes AA as body text on either.
          //
          // It is a LIGHT accent, which the purple was not: anything using it
          // as a background needs dark text on top (text-game-dark), never the
          // inherited white. White on this gold is 1.7:1 — illegible.
          accent: '#F7C948',
          gold: '#f59e0b',
          green: '#10b981',
          red: '#ef4444',
          blue: '#3b82f6',
          pink: '#ec4899',
        },
      },
    },
  },
  plugins: [],
};
