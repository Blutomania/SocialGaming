/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './components/**/*.{js,jsx}',
    './app/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        game: {
          dark: '#0d0d1a',
          card: '#1a1a2e',
          accent: '#7c3aed',
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
