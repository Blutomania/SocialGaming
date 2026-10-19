// THE colour roles (CLAUDE.md item 53, docs/STYLE_GUIDE.md §1). Every screen
// reads a colour from here by its JOB, never by its look: tailwind.config.js
// builds the `ui-*` utilities from this object, and scripts/palette-test.mjs
// checks every pairing below against its WCAG floor. Change a value here and
// re-run that script; never type a hex into a component.
//
// No Node-only imports: tailwind.config.js and the browser both load this.
//
// The one rule that matters most: CHOSEN and ACT are never the same colour and
// never swap jobs. If hovering an action filled it with the chosen colour, a
// player would read the action as already selected. Before item 53, gold did
// both — a picked category chip and a hovered button looked identical.

export const PALETTE = {
  // The page. Owner's call (item 40); the plate is this same token.
  ground: '#2F4459',

  // A control at rest. DARKER than the ground, not lighter as the style guide
  // suggests: item 50 already decided controls read as recessed against the
  // plate, and a lighter step pulled faint ink down to 4.51:1 and every
  // semantic colour under its floor. MYF's file wins where they disagree.
  surface: '#24364A',
  // A disabled control's fill — deeper still, so it reads as "not here yet".
  surfaceDeep: '#1E2D3D',

  // The outline that IS an available control's affordance (3:1 floor).
  line: '#9DB0C1',
  // A disabled control's outline. Deliberately under 3:1 — it must not read as
  // an affordance. WCAG exempts disabled controls from contrast floors.
  lineDim: '#5C7389',

  ink: '#EEF3F7',        // body text on ground and surface
  faint: '#B9C4CF',      // captions, small labels — "faint ink"
  inkDisabled: '#8597A8',
  // Text sitting ON a Chosen or Act fill. Both fills are light, so the ink
  // flips dark there — white on this gold is 1.7:1.
  inkOnFill: '#16212D',

  // "This is the selected one." Cool, so it can never be mistaken for Act.
  chosen: '#8EC5E8',

  // "Do this." The gold the game already used for its primary actions.
  act: '#F7C948',
  actDim: '#D9A92E',     // pressed

  // Owed / error / met. The old game.red (#ef4444) measured 2.67:1 on slate
  // and game.green 3.96:1 — both were tuned for the pre-slate near-black and
  // never re-measured, and both were used for text.
  negative: '#FF9B8F',
  positive: '#5CD69B',
  caution: '#F4A259',
};

// Every pairing the screens actually draw, with its floor. 4.5 for body text,
// 3 for large text and for an outline that is a control's affordance. The test
// fails if any pair falls under its floor, so a new pairing belongs here first.
export const CONTRAST_CONTRACT = [
  ['ink', 'ground', 4.5],
  ['ink', 'surface', 4.5],
  ['faint', 'ground', 4.5],
  ['faint', 'surface', 4.5],
  ['inkDisabled', 'surfaceDeep', 4.5],
  ['inkOnFill', 'chosen', 4.5],
  ['inkOnFill', 'act', 4.5],
  ['inkOnFill', 'actDim', 4.5],
  ['line', 'ground', 3],
  ['line', 'surface', 3],
  ['chosen', 'ground', 3],
  ['chosen', 'surface', 3],
  ['act', 'ground', 4.5],   // an outlined action's label is gold text
  ['act', 'surface', 4.5],
  ['negative', 'ground', 4.5],
  ['negative', 'surface', 4.5],
  ['positive', 'ground', 4.5],
  ['positive', 'surface', 4.5],
  ['caution', 'ground', 4.5],
  ['caution', 'surface', 4.5],
];
