/**
 * QCompass — Gravity (SYK / JT) domain plugin (scaffolding).
 *
 * `requiresProvenanceWarning: true` — the result renderer REFUSES to
 * render when a learned-Hamiltonian run is missing its warning string.
 */
import type { DomainPlugin } from "./types";
import { FEATURES } from "@/config/features";
import { qcompassNoopSimulation } from "./_noop-sim";
import { registerDomain } from "./registry";

export const gravityPlugin: DomainPlugin = {
  id: "gravity.syk",
  label: "Gravity · SYK / JT",
  description: "Sparsified SYK and JT dynamics — provenance-flagged toy models.",
  capability: { classical: false, quantum: true, audited: false },
  enabled: FEATURES.qcompassMultiDomain && FEATURES.qcompassGravity,
  disabledReason: "Enable in feature flags (qcompassMultiDomain + qcompassGravity).",
  manifestSchemaUrl: "gravity/manifest-schema.json",
  fixturePathPrefix: "gravity/",
  resultRendererId: "gravity",
  visualizerPanelGroupId: "gravity",
  requiresProvenanceWarning: true,
  simulation: qcompassNoopSimulation,
};

registerDomain(gravityPlugin);
