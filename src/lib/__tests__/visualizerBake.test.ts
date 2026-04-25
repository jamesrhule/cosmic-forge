import { describe, expect, it } from "vitest";
import { bakeTimelineBuffers } from "@/lib/visualizerBake";
import type { VisualizationTimeline, VisualizationModeSample } from "@/types/visualizer";

function mode(k: number, kk: number = 0): VisualizationModeSample {
  return {
    k,
    h_plus_re: 0.1,
    h_plus_im: 0.2,
    h_minus_re: -0.1,
    h_minus_im: -0.2,
    alpha_sq_minus_beta_sq: 0.5,
    in_tachyonic_window: false,
    kk_level: kk,
  };
}

function makeTimeline(modesPerFrame: number[]): VisualizationTimeline {
  return {
    runId: "bake-test",
    formulaVariant: "F1",
    frames: modesPerFrame.map((n, idx) => ({
      tau: idx,
      t_cosmic_seconds: idx,
      phase: "inflation" as const,
      modes: Array.from({ length: n }, (_, i) => mode(1e-3 * (i + 1))),
      B_plus: 0,
      B_minus: 0,
      xi_dot_H: 0,
      lepton_flow: { chiral_gw: 0, anomaly: 0, delta_N_L: 0, eta_B_running: 0 },
      active_terms: [],
    })),
    meta: {
      durationSeconds: 1,
      tauRange: [0, 1],
      phaseBoundaries: {},
      visualizationHints: {
        panelEmphasis: {},
        particleColorMode: "chirality",
        extraOverlays: [],
        formulaTermIds: [],
      },
    },
  };
}

describe("bakeTimelineBuffers", () => {
  it("allocates max-mode buffers across all frames (uniform stride)", () => {
    const baked = bakeTimelineBuffers(makeTimeline([2, 5, 3]));
    expect(baked.maxModes).toBe(5);
    // Each frame should have positions/colors of length maxModes * 3.
    expect(baked.positions[0].length).toBe(5 * 3);
    expect(baked.positions[1].length).toBe(5 * 3);
    expect(baked.colors[2].length).toBe(5 * 3);
  });

  it("records the active mode count per frame", () => {
    const baked = bakeTimelineBuffers(makeTimeline([2, 5, 3]));
    expect(Array.from(baked.modeCount)).toEqual([2, 5, 3]);
  });

  it("pads unused instance slots with NaN positions (collapsed triangles)", () => {
    const baked = bakeTimelineBuffers(makeTimeline([1, 4]));
    // Frame 0 has 1 active mode of 4 capacity → indices 1..3 must be NaN.
    const pos = baked.positions[0];
    expect(Number.isFinite(pos[0])).toBe(true);
    expect(Number.isNaN(pos[3])).toBe(true);
    expect(Number.isNaN(pos[6])).toBe(true);
    expect(Number.isNaN(pos[9])).toBe(true);
  });

  it("encodes log10(k) into the x channel", () => {
    const baked = bakeTimelineBuffers(makeTimeline([1]));
    // First mode has k = 1e-3 → log10(1e-3) = -3.
    expect(baked.positions[0][0]).toBeCloseTo(-3, 6);
  });

  it("emits RGB triplets in [0, 1] for every active instance", () => {
    const baked = bakeTimelineBuffers(makeTimeline([3, 3]));
    for (let f = 0; f < 2; f++) {
      const cols = baked.colors[f];
      const active = baked.modeCount[f];
      for (let i = 0; i < active * 3; i++) {
        expect(cols[i]).toBeGreaterThanOrEqual(0);
        expect(cols[i]).toBeLessThanOrEqual(1);
      }
    }
  });

  it("throws a friendly error when the timeline exceeds MAX_INSTANCES", () => {
    const huge = makeTimeline([5000]);
    expect(() => bakeTimelineBuffers(huge)).toThrow(/MAX_INSTANCES/);
  });
});
