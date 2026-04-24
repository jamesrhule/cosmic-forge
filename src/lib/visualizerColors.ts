/**
 * Visualizer color helpers. All return RGB in [0, 1] for direct use in
 * Three.js color uniforms, plus a CSS-string variant for 2D panels.
 *
 * Palette is locked to the workbench tokens: indigo (`#4338ca`) for
 * the H_+ end of the chirality axis, amber (`#d97706`) for H_-,
 * neutral muted-foreground for inactive.
 *
 * Color-blind safety: panels also encode chirality via stroke-dash
 * patterns and instance-shape variations — color is never the sole
 * carrier.
 */

const INDIGO = [0x43 / 255, 0x38 / 255, 0xca / 255] as const;
const AMBER = [0xd9 / 255, 0x77 / 255, 0x06 / 255] as const;
const SLATE = [0x64 / 255, 0x74 / 255, 0x8b / 255] as const;

/** KK-level cycle for F3 / F5 — five-tone perceptually distinct ramp. */
const KK_PALETTE: ReadonlyArray<readonly [number, number, number]> = [
  INDIGO,
  [0x06 / 255, 0xb6 / 255, 0xd4 / 255], // cyan
  [0x10 / 255, 0xb9 / 255, 0x81 / 255], // emerald
  AMBER,
  [0xdc / 255, 0x26 / 255, 0x26 / 255], // red
];

export function colorRgbForChirality(
  h_plus_re: number,
  h_plus_im: number,
  h_minus_re: number,
  h_minus_im: number,
): [number, number, number] {
  const plus = Math.hypot(h_plus_re, h_plus_im);
  const minus = Math.hypot(h_minus_re, h_minus_im);
  const total = plus + minus;
  if (total < 1e-30) return [SLATE[0], SLATE[1], SLATE[2]];
  // -1 (pure minus → amber) … +1 (pure plus → indigo)
  const t = (plus - minus) / total;
  return mix3(AMBER, INDIGO, (t + 1) / 2);
}

export function colorRgbForKkLevel(level: number): [number, number, number] {
  const c = KK_PALETTE[Math.abs(level) % KK_PALETTE.length];
  return [c[0], c[1], c[2]];
}

export function colorRgbForCondensate(
  alphaMinusBeta: number,
): [number, number, number] {
  // Saturation grows with amplification; condensate occupation = bright indigo.
  const k = Math.tanh(Math.abs(alphaMinusBeta) / 4);
  return mix3(SLATE, INDIGO, k);
}

export function colorRgbForResonance(
  alphaMinusBeta: number,
  inWindow: boolean,
): [number, number, number] {
  const base = inWindow ? AMBER : INDIGO;
  const k = Math.tanh(Math.abs(alphaMinusBeta) / 4);
  return mix3(SLATE, base, 0.4 + 0.6 * k);
}

export function rgbToCss(rgb: readonly [number, number, number]): string {
  return `rgb(${Math.round(rgb[0] * 255)} ${Math.round(rgb[1] * 255)} ${Math.round(
    rgb[2] * 255,
  )})`;
}

function mix3(
  a: readonly [number, number, number],
  b: readonly [number, number, number],
  t: number,
): [number, number, number] {
  const u = Math.max(0, Math.min(1, t));
  return [
    a[0] * (1 - u) + b[0] * u,
    a[1] * (1 - u) + b[1] * u,
    a[2] * (1 - u) + b[2] * u,
  ];
}
