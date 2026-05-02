/**
 * QCompass — Chemistry domain plugin (scaffolding).
 *
 * Strongly-correlated transition-metal catalysis class (FeMoco / P450).
 * Disabled unless `qcompassMultiDomain && qcompassChemistry`.
 */
import type { DomainPlugin } from "./types";
import { FEATURES } from "@/config/features";
import { qcompassNoopSimulation } from "./_noop-sim";
import { registerDomain } from "./registry";

export const chemistryPlugin: DomainPlugin = {
  id: "chemistry.molecular",
  label: "Chemistry · Molecular",
  description: "Strongly correlated transition-metal catalysis (FeMoco / P450 class).",
  capability: { classical: true, quantum: true, audited: false },
  enabled: FEATURES.qcompassMultiDomain && FEATURES.qcompassChemistry,
  disabledReason: "Enable in feature flags (qcompassMultiDomain + qcompassChemistry).",
  manifestSchemaUrl: "chemistry/manifest-schema.json",
  fixturePathPrefix: "chemistry/",
  resultRendererId: "chemistry",
  visualizerPanelGroupId: "chemistry",
  requiresProvenanceWarning: false,
  simulation: qcompassNoopSimulation,
};

registerDomain(chemistryPlugin);
