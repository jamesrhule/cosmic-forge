/**
 * QCompass — HEP (lattice) domain plugin (scaffolding).
 *
 * First-class fundamental-particle research target. Result renderer
 * ships the full <ParticleObservablesTable> in this pass.
 */
import type { DomainPlugin } from "./types";
import { FEATURES } from "@/config/features";
import { qcompassNoopSimulation } from "./_noop-sim";
import { registerDomain } from "./registry";

export const hepPlugin: DomainPlugin = {
  id: "hep.lattice",
  label: "HEP · Lattice",
  description: "Real-time 1+1D Schwinger and 2+1D abelian gauge theories.",
  capability: { classical: true, quantum: true, audited: false },
  enabled: FEATURES.qcompassMultiDomain && FEATURES.qcompassHep,
  disabledReason: "Enable in feature flags (qcompassMultiDomain + qcompassHep).",
  manifestSchemaUrl: "hep/manifest-schema.json",
  fixturePathPrefix: "hep/",
  resultRendererId: "hep",
  visualizerPanelGroupId: "hep",
  requiresProvenanceWarning: false,
  simulation: qcompassNoopSimulation,
};

registerDomain(hepPlugin);
