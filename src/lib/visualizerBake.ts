import type {
  BakedTimelineBuffers,
  ParticleColorMode,
  VisualizationModeSample,
  VisualizationTimeline,
} from "@/types/visualizer";
import {
  colorRgbForChirality,
  colorRgbForKkLevel,
  colorRgbForCondensate,
  colorRgbForResonance,
} from "@/lib/visualizerColors";

/**
 * Pre-bake the per-frame particle positions and colors into typed
 * Float32Arrays. R3F's InstancedMesh consumes these directly via a
 * `useFrame` matrix update — per-particle data never goes through React.
 *
 * Position layout (3 floats per mode):
 *   x = log10(k)              (normalised at draw time)
 *   y = h_plus_re             (raw)
 *   z = h_plus_im             (raw)
 *
 * Color layout (3 floats per mode, RGB in [0, 1]).
 *
 * Modes that are absent from a frame have their positions written as
 * NaN; the GPU shader / R3F draw loop skips them via `modeCount[frame]`
 * which is the count of valid leading entries.
 */
export function bakeTimelineBuffers(timeline: VisualizationTimeline): BakedTimelineBuffers {
  const colorMode = timeline.meta.visualizationHints.particleColorMode;
  const frames = timeline.frames;
  const maxModes = frames.reduce((acc, f) => Math.max(acc, f.modes.length), 0);

  const positions: Float32Array[] = new Array(frames.length);
  const colors: Float32Array[] = new Array(frames.length);
  const modeCount = new Uint32Array(frames.length);

  for (let f = 0; f < frames.length; f++) {
    const frame = frames[f];
    const pos = new Float32Array(maxModes * 3);
    const col = new Float32Array(maxModes * 3);
    const n = frame.modes.length;
    modeCount[f] = n;

    for (let i = 0; i < n; i++) {
      const m = frame.modes[i];
      const off = i * 3;
      pos[off] = Math.log10(Math.max(m.k, 1e-30));
      pos[off + 1] = m.h_plus_re;
      pos[off + 2] = m.h_plus_im;

      const rgb = colorForMode(m, colorMode);
      col[off] = rgb[0];
      col[off + 1] = rgb[1];
      col[off + 2] = rgb[2];
    }
    // Pad unused slots with NaN positions so the instance is collapsed to a
    // zero-area triangle when the matrix uniform is recomputed (cheap clip).
    for (let i = n; i < maxModes; i++) {
      const off = i * 3;
      pos[off] = NaN;
      pos[off + 1] = NaN;
      pos[off + 2] = NaN;
    }

    positions[f] = pos;
    colors[f] = col;
  }

  return { positions, colors, modeCount, maxModes };
}

function colorForMode(
  m: VisualizationModeSample,
  mode: ParticleColorMode,
): [number, number, number] {
  switch (mode) {
    case "kk_level":
      return colorRgbForKkLevel(m.kk_level ?? 0);
    case "condensate":
      return colorRgbForCondensate(m.alpha_sq_minus_beta_sq);
    case "resonance":
      return colorRgbForResonance(m.alpha_sq_minus_beta_sq, m.in_tachyonic_window);
    case "chirality":
    default:
      return colorRgbForChirality(m.h_plus_re, m.h_plus_im, m.h_minus_re, m.h_minus_im);
  }
}
