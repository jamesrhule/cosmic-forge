/**
 * QCompass — Cosmology adapter.
 *
 * Wraps the existing UCGLE-F1 simulator in the `Simulation` protocol so
 * the domain registry can dispatch through it. This adapter is a pure
 * one-way delegation: it imports from `services/simulator.ts`, never
 * the other way around.
 *
 * Behaviour MUST be byte-identical to invoking `services/simulator.ts`
 * directly. The S1–S15 audit and η_B = 6.1×10⁻¹⁰ (Planck 2018) target
 * remain the acceptance test for this domain.
 */

import { startRun, getRun } from "@/services/simulator";
import type {
  CosmologyProblem,
  CosmologyResult,
  DomainPlugin,
  Manifest,
  PreparedInstance,
  Simulation,
  ValidationOutcome,
} from "./types";
import { registerDomain } from "./registry";

const cosmologySimulation: Simulation<CosmologyProblem, CosmologyResult> = {
  async prepare(manifest: Manifest<CosmologyProblem>): Promise<PreparedInstance<CosmologyProblem>> {
    // For cosmology there is no separate "prepare" step — the run
    // config IS the instance. We mint a deterministic handle so tests
    // can correlate prepare/run/validate calls.
    const handle = `cosmology:${manifest.problem.potential.kind}:${manifest.problem.precision}`;
    return { manifest, handle };
  },

  async run(instance: PreparedInstance<CosmologyProblem>): Promise<CosmologyResult> {
    const { runId } = await startRun(instance.manifest.problem);
    const result = await getRun(runId);
    return result;
  },

  async validate(result: CosmologyResult): Promise<ValidationOutcome> {
    // The S1–S15 audit lives inside the simulator's own pipeline; the
    // adapter just re-exposes it. The "classical reference" for a
    // cosmology run is its own audit report (no external solver to
    // cross-check against — the Friedmann + Boltzmann path is already
    // canonical at machine precision).
    const blocking = result.audit.summary.blocking;
    return {
      ok: !blocking,
      audit: result.audit,
      notes: blocking
        ? "S1–S15 audit reports a blocking failure."
        : "S1–S15 audit passed (or non-blocking).",
    };
  },
};

export const cosmologyUcglef1: DomainPlugin<CosmologyProblem, CosmologyResult> = {
  id: "cosmology.ucglef1",
  label: "Cosmology · UCGLE-F1",
  description:
    "Gravitational leptogenesis with scalar-Gauss-Bonnet-Chern-Simons couplings. η_B audited against Planck 2018.",
  capability: { classical: true, quantum: false, audited: true },
  enabled: true,
  simulation: cosmologySimulation,
};

// Self-register on module load. Importing this module anywhere in the
// app (e.g. via the domain selector) is sufficient to populate the
// registry. The cosmology service path keeps working independently
// even if this module is never imported.
registerDomain(cosmologyUcglef1);
