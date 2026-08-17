'use client';

// The wager, drawn as a pie. On the nose on purpose — a new player has to
// understand the stake without being told, and "how much of the pie" is a
// thing everyone already knows. The number and the picture say the same thing,
// which is what the old 50–500 slider could never do.
//
// 12 is one slice of eight, 100 is the whole pie, and 200 is a pie bigger than
// a pie. That last one is the only tier that breaks the shape's own scale, and
// that break IS the meaning of it.

const SIZE = 100;
const R = 44;
const CX = SIZE / 2;
const CY = SIZE / 2;

// Eighth-slice guides, so a pie always reads as a pie rather than as a
// pac-man. Drawn faintly under the filled wedge.
function sliceGuides() {
  return Array.from({ length: 8 }, (_, i) => {
    const angle = (i / 8) * 2 * Math.PI - Math.PI / 2;
    return (
      <line
        key={i}
        x1={CX}
        y1={CY}
        x2={CX + R * Math.cos(angle)}
        y2={CY + R * Math.sin(angle)}
        stroke="currentColor"
        strokeWidth="1"
        opacity="0.18"
      />
    );
  });
}

// An SVG arc for `fraction` of the circle, starting at 12 o'clock. A full
// circle can't be drawn as one arc (start and end coincide), so it falls back
// to a plain circle.
function wedgePath(fraction) {
  if (fraction >= 1) return null;
  const end = fraction * 2 * Math.PI - Math.PI / 2;
  const x = CX + R * Math.cos(end);
  const y = CY + R * Math.sin(end);
  const largeArc = fraction > 0.5 ? 1 : 0;
  return `M ${CX} ${CY} L ${CX} ${CY - R} A ${R} ${R} 0 ${largeArc} 1 ${x} ${y} Z`;
}

export default function WagerPie({ tier, selected = false, size = 100 }) {
  const wedge = wedgePath(tier.fraction);
  // The super-wager is drawn oversized and ringed. Scaling the whole SVG
  // rather than the radius keeps it centred in whatever box it's given.
  const scale = tier.super ? 1.18 : 1;

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      width={size * scale}
      height={size * scale}
      className={selected ? 'text-slate-text' : 'text-slate-muted'}
      role="img"
      aria-label={`${tier.label}: ${tier.value} points`}
    >
      <circle
        cx={CX}
        cy={CY}
        r={R}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        opacity={selected ? 1 : 0.5}
      />
      {sliceGuides()}

      {wedge ? (
        <path d={wedge} fill="currentColor" opacity={selected ? 0.9 : 0.45} />
      ) : (
        <circle cx={CX} cy={CY} r={R} fill="currentColor" opacity={selected ? 0.9 : 0.45} />
      )}

      {/* More pie than there is. A second ring outside the crust, because the
          wedge itself has nowhere left to go once the pie is full. */}
      {tier.super && (
        <circle
          cx={CX}
          cy={CY}
          r={R + 5}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          opacity={selected ? 0.85 : 0.4}
          strokeDasharray="4 3"
        />
      )}
    </svg>
  );
}
