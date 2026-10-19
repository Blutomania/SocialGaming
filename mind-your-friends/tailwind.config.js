import { PALETTE } from './lib/palette.js';

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './components/**/*.{js,jsx}',
    './app/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Every colour a screen may use, named by its job (item 53). The
        // values live in lib/palette.js and are contrast-checked there by
        // scripts/palette-test.mjs — this file only exposes them as `ui-*`
        // utilities (bg-ui-surface, text-ui-faint, border-ui-line, …).
        //
        // The pre-slate `game.*` tokens and the `slate.*` text tokens are
        // gone rather than aliased: an alias would let a screen keep asking
        // for "red" instead of "negative", which is the habit being retired.
        // The question-mark field's five mark colours live in
        // scripts/build-question-field.mjs, which is the only thing that
        // draws them.
        ui: PALETTE,
      },
    },
  },
  plugins: [],
};
