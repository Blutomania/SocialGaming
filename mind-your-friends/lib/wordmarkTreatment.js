// Which of the two title treatments a given game gets. Pure — no fonts, no
// JSX — so it can be imported and checked by scripts/wordmark-test.js.
// components/Wordmark.jsx maps the id returned here onto a face and a colour.

export const TREATMENT_IDS = ['f1', 'd1'];

// A bit-mixer (the murmur3 finaliser). Not decoration, and NOT optional:
//
// Logo.jsx picks a colour palette with `hash % 6` over a polynomial hash of
// the same room code. This picks between two treatments. The obvious
// implementation — a second polynomial hash, then `% 2` — produces a mark
// that is 50/50 overall and yet PERFECTLY correlated with the logo palette:
// every odd multiplier collapses to the same parity bit mod 2, and because 6
// is even, `hash % 6` carries that identical parity. Palette 0 would always
// draw one treatment, palette 1 always the other, turning twelve combinations
// into six. Salting the seed does not help, because the seed's parity just
// flips which half is which.
//
// This was written the naive way first and caught by actually measuring it
// across all 331,776 possible room codes, which is why the test exists.
// Mixing the bits before taking the modulus is what makes the two axes
// independent: the low bit then depends on the whole hash, not on a parity
// that another consumer is also reading.
function mix(h) {
  h ^= h >>> 16;
  h = Math.imul(h, 0x45d9f3b);
  h ^= h >>> 16;
  h = Math.imul(h, 0x45d9f3b);
  h ^= h >>> 16;
  return h >>> 0;
}

// Deterministic in the room code, exactly like Logo.jsx's palette rotation and
// for exactly its reason: every player in one game must see the same mark. A
// treatment that differed per screen — or per re-render — reads as a rendering
// bug, not as variety. So "50/50 random" means across GAMES; inside one game
// it is fixed for the whole session.
export function treatmentIdForGame(code) {
  if (!code) return TREATMENT_IDS[0];
  let hash = 5381;
  for (const char of code) hash = (hash * 33 + char.charCodeAt(0)) >>> 0;
  return TREATMENT_IDS[mix(hash) % TREATMENT_IDS.length];
}
