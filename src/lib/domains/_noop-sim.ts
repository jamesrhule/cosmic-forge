/**
 * QCompass — Shared no-op Simulation adapter for scaffolding domains.
 *
 * The seven non-cosmology domains route their actual run lifecycle
 * through `src/services/qcompass/runs.ts`. The legacy `Simulation`
 * interface on `DomainPlugin` predates that service surface — we keep
 * it satisfied with this trampoline so existing consumers keep
 * compiling. The trampoline never executes in production paths;
 * if invoked it throws so misuse is loud.
 *
 * @example
 *   import { qcompassNoopSimulation } from "@/lib/domains/_noop-sim";
 *   export const chemistry: DomainPlugin = { ..., simulation: qcompassNoopSimulation };
 */
import type { Simulation } from "./types";

export const qcompassNoopSimulation: Simulation<unknown, unknown> = {
  async prepare() {
    throw new Error(
      "QCompass scaffolding domain: use src/services/qcompass/runs.ts (startRun/getRun/streamRun) instead of the legacy Simulation protocol.",
    );
  },
  async run() {
    throw new Error("Use src/services/qcompass/runs.ts.");
  },
  async validate() {
    throw new Error("Use src/services/qcompass/runs.ts.");
  },
};
