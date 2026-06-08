/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
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
      fontFamily: {
        display: ['Impact', 'Arial Black', 'sans-serif'],
      },
      animation: {
        flicker: 'flicker 0.15s infinite',
        blur: 'none',
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
      },
      keyframes: {
        flicker: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.1' },
        },
      },
    },
  },
  plugins: [],
};
