// Color flavor for The Lineup round rule (see GAME_DESIGN.md → The Lineup).
// No Claude call needed: the correct color is a curated real-world fact
// (verifying a hex code live is exactly the hallucination risk generation
// can't be trusted with), and decoys are cheap to generate procedurally by
// nudging the real color's hue/saturation/lightness a small amount.
//
// This pool is intentionally small to start — add more { entity, label, hex }
// entries any time. `label` is the plain-language color name used in the
// question template ("Which one is {entity} {label}?").

export const LINEUP_COLORS = [
  { entity: 'the Philadelphia Eagles', label: 'green', hex: '#004C54' },
  { entity: 'the Boston Celtics', label: 'green', hex: '#007A33' },
  { entity: 'the Seattle Seahawks', label: 'green', hex: '#69BE28' },
  { entity: 'the Green Bay Packers', label: 'green', hex: '#203731' },
  { entity: 'Spotify', label: 'green', hex: '#1DB954' },
  { entity: 'Starbucks', label: 'green', hex: '#00704A' },
  { entity: 'Coca-Cola', label: 'red', hex: '#F40009' },
  { entity: "McDonald's", label: 'red', hex: '#DA291C' },
  { entity: 'Facebook', label: 'blue', hex: '#1877F2' },
  { entity: 'the Golden State Warriors', label: 'blue', hex: '#1D428A' },
  { entity: 'Duke University', label: 'blue', hex: '#001A57' },
  { entity: 'the LA Lakers', label: 'purple', hex: '#552583' },
  { entity: 'the Minnesota Vikings', label: 'purple', hex: '#4F2683' },
  { entity: 'Home Depot', label: 'orange', hex: '#F96302' },
  { entity: 'the Tennessee Volunteers', label: 'orange', hex: '#FF8200' },
];

function hexToRgb(hex) {
  const clean = hex.replace('#', '');
  const bigint = parseInt(clean, 16);
  return { r: (bigint >> 16) & 255, g: (bigint >> 8) & 255, b: bigint & 255 };
}

function rgbToHex({ r, g, b }) {
  return (
    '#' +
    [r, g, b]
      .map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0'))
      .join('')
  );
}

function rgbToHsl({ r, g, b }) {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h, s;
  const l = (max + min) / 2;
  if (max === min) {
    h = s = 0;
  } else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      default: h = (r - g) / d + 4; break;
    }
    h /= 6;
  }
  return { h: h * 360, s: s * 100, l: l * 100 };
}

function hslToRgb({ h, s, l }) {
  h /= 360;
  s /= 100;
  l /= 100;
  let r, g, b;
  if (s === 0) {
    r = g = b = l;
  } else {
    const hue2rgb = (p, q, t) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }
  return { r: r * 255, g: g * 255, b: b * 255 };
}

// Nudges hue/saturation/lightness a small, perceptible-but-close amount so
// the decoy reads as "almost the real color" rather than an obviously
// different one.
function perturbHex(hex) {
  const hsl = rgbToHsl(hexToRgb(hex));
  const sign = () => (Math.random() < 0.5 ? -1 : 1);
  const perturbed = {
    h: (hsl.h + sign() * (4 + Math.random() * 10) + 360) % 360,
    s: Math.max(10, Math.min(100, hsl.s + sign() * (2 + Math.random() * 8))),
    l: Math.max(5, Math.min(90, hsl.l + sign() * (2 + Math.random() * 8))),
  };
  return rgbToHex(hslToRgb(perturbed));
}

function shuffle(arr) {
  return [...arr].sort(() => Math.random() - 0.5);
}

export function pickColorLineupEntry() {
  return LINEUP_COLORS[Math.floor(Math.random() * LINEUP_COLORS.length)];
}

// Builds a shuffled option list for a color entry: the real hex plus
// `optionCount - 1` procedurally-perturbed decoys, none matching the real
// color or each other.
export function buildColorOptions(entry, optionCount = 5) {
  const decoys = [];
  let guard = 0;
  while (decoys.length < optionCount - 1 && guard < 100) {
    guard++;
    const candidate = perturbHex(entry.hex);
    const taken = [entry.hex, ...decoys].some((h) => h.toLowerCase() === candidate.toLowerCase());
    if (!taken) decoys.push(candidate);
  }

  const options = shuffle([entry.hex, ...decoys]).map((hex, i) => ({ id: `opt${i}`, hex }));
  const correctOptionId = options.find((o) => o.hex.toLowerCase() === entry.hex.toLowerCase()).id;
  return { options, correctOptionId };
}
