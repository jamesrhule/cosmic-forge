/**
 * QCompass — Stat-mech sampling domain plugin (scaffolding).
 */
import type { DomainPlugin } from "./types";
import { FEATURES } from "@/config/features";
import { qcompassNoopSimulation } from "./_noop-sim";
import { registerDomain } from "./registry";

export const statmechPlugin: DomainPlugin = {
  id: "statmech.sampling",
  label: "Stat Mech · Sampling",
  description: "QAE, quantum Metropolis, thermofield-double preparation.",
  capability: { classical: true, quantum: true, audited: false },
  enabled: FEATURES.qcompassMultiDomain && FEATURES.qcompassStatmech,
  disabledReason: "Enable in feature flags (qcompassMultiDomain + qcompassStatmech).",
  manifestSchemaUrl: "statmech/manifest-schema.json",
  fixturePathPrefix: "statmech/",
  resultRendererId: "statmech",
  visualizerPanelGroupId: "statmech",
  requiresProvenanceWarning: false,
  simulation: qcompassNoopSimulation,
};

registerDomain(statmechPlugin);
