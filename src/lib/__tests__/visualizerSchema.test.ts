import { describe, expect, it } from "vitest";
import {
  assertVisualizationInvariants,
  VisualizationContractError,
} from "@/lib/visualizerSchema";
import type { VisualizationTimeline } from "@/types/visualizer";

function makeTimeline(overrides: Partial<VisualizationTimeline["frames"][number]> = {}): VisualizationTimeline {
  const frame: VisualizationTimeline["frames"][number] = {
    tau: 0,
    t_cosmic_seconds: 0,
    phase: "inflation",
    modes: [],
    B_plus: 0,
    B_minus: 0,
    xi_dot_H: 0,
    lepton_flow: { chiral_gw: 0, anomaly: 0, delta_N_L: 0, eta_B_running: 0 },
    active_terms: [],
    ...overrides,
  };
  return {
    runId: "test",
    formulaVariant: "F1",
    frames: [frame],
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

describe("assertVisualizationInvariants", () => {
  it("accepts a minimal well-formed timeline", () => {
    expect(() => assertVisualizationInvariants(makeTimeline())).not.toThrow();
  });

  it("throws when sgwb_snapshot arrays disagree in length", () => {
    const bad = makeTimeline({
      sgwb_snapshot: { f_Hz: [1, 2], Omega_gw: [1], chirality: [1, 2] },
    });
    expect(() => assertVisualizationInvariants(bad)).toThrow(VisualizationContractError);
    expect(() => assertVisualizationInvariants(bad)).toThrow(/Frame 0 sgwb_snapshot/);
  });

  it("throws when anomaly_integrand arrays disagree", () => {
    const bad = makeTimeline({
      anomaly_integrand: { k: [1, 2, 3], integrand: [1, 2], running_integral: [1, 2, 3], cutoff: 1 },
    });
    expect(() => assertVisualizationInvariants(bad)).toThrow(VisualizationContractError);
  });

  it("throws when active_terms includes the reserved vfx- prefix", () => {
    const bad = makeTimeline({ active_terms: ["xi", "vfx-M1"] });
    expect(() => assertVisualizationInvariants(bad)).toThrow(/vfx-/);
  });

  it("points at the offending frame index in the error message", () => {
    const tl = makeTimeline();
    tl.frames.push({
      ...tl.frames[0],
      active_terms: ["vfx-bad"],
    });
    expect(() => assertVisualizationInvariants(tl)).toThrow(/Frame 1/);
  });
});
