/**
 * QCompass — Nuclear (structure) domain plugin (scaffolding).
 *
 * First-class fundamental-particle research target. Result renderer
 * ships the full <NuclearObservablesTable> + <ModelDomainBadge>.
 */
import type { DomainPlugin } from "./types";
import { FEATURES } from "@/config/features";
import { qcompassNoopSimulation } from "./_noop-sim";
import { registerDomain } from "./registry";

export const nuclearPlugin: DomainPlugin = {
  id: "nuclear.structure",
  label: "Nuclear · Structure",
  description: "Few-body NCSM and 1+1D 0νββ toy.",
  capability: { classical: true, quantum: true, audited: false },
  enabled: FEATURES.qcompassMultiDomain && FEATURES.qcompassNuclear,
  disabledReason: "Enable in feature flags (qcompassMultiDomain + qcompassNuclear).",
  manifestSchemaUrl: "nuclear/manifest-schema.json",
  fixturePathPrefix: "nuclear/",
  resultRendererId: "nuclear",
  visualizerPanelGroupId: "nuclear",
  requiresProvenanceWarning: false,
  simulation: qcompassNoopSimulation,
};

registerDomain(nuclearPlugin);
