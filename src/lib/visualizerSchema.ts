/**
 * Dev-only invariants for the wire-shape received from the simulator.
 *
 * The Zod schemas in `src/lib/fixtureSchemas.ts` are intentionally
 * lenient (they let the canonical Pydantic models grow without
 * breaking the fixtures-first dev loop). These checks complement them
 * by asserting structural invariants that downstream rendering code
 * implicitly assumes — mismatches are a backend bug, not a UI one,
 * and we want to point at the offending frame index loud and early.
 *
 * Production builds tree-shake the call sites (the only callers gate
 * on `import.meta.env.DEV`).
 */
import type { VisualizationTimeline } from "@/types/visualizer";

export class VisualizationContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "VisualizationContractError";
  }
}

/**
 * Assert per-frame array invariants. Throws a clear,
 * frame-pointing error on the first violation so the developer
 * console in dev shows the exact source.
 */
export function assertVisualizationInvariants(timeline: VisualizationTimeline): void {
  for (let i = 0; i < timeline.frames.length; i++) {
    const frame = timeline.frames[i];

    if (frame.sgwb_snapshot) {
      const { f_Hz, Omega_gw, chirality } = frame.sgwb_snapshot;
      if (f_Hz.length !== Omega_gw.length || f_Hz.length !== chirality.length) {
        throw new VisualizationContractError(
          `Frame ${i} sgwb_snapshot: array lengths disagree ` +
            `(f_Hz=${f_Hz.length}, Omega_gw=${Omega_gw.length}, chirality=${chirality.length})`,
        );
      }
    }

    if (frame.anomaly_integrand) {
      const { k, integrand, running_integral } = frame.anomaly_integrand;
      if (k.length !== integrand.length || k.length !== running_integral.length) {
        throw new VisualizationContractError(
          `Frame ${i} anomaly_integrand: array lengths disagree ` +
            `(k=${k.length}, integrand=${integrand.length}, running_integral=${running_integral.length})`,
        );
      }
    }

    // active_terms must NOT carry the `vfx-` prefix — the formula panel
    // strips it from DOM ids before set-membership tests, so a prefixed
    // value here would silently never glow.
    for (const term of frame.active_terms) {
      if (term.startsWith("vfx-")) {
        throw new VisualizationContractError(
          `Frame ${i} active_terms: "${term}" includes the reserved "vfx-" prefix. ` +
            `Send the bare term id (e.g. "xi") instead.`,
        );
      }
    }
  }
}
