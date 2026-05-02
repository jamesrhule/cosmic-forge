/**
 * QCompass — Condensed matter (lattice) domain plugin (scaffolding).
 */
import type { DomainPlugin } from "./types";
import { FEATURES } from "@/config/features";
import { qcompassNoopSimulation } from "./_noop-sim";
import { registerDomain } from "./registry";

export const condmatPlugin: DomainPlugin = {
  id: "condmat.lattice",
  label: "Condensed Matter · Lattice",
  description: "2D Hubbard dynamics, frustrated magnets, spectral functions.",
  capability: { classical: true, quantum: true, audited: false },
  enabled: FEATURES.qcompassMultiDomain && FEATURES.qcompassCondmat,
  disabledReason: "Enable in feature flags (qcompassMultiDomain + qcompassCondmat).",
  manifestSchemaUrl: "condmat/manifest-schema.json",
  fixturePathPrefix: "condmat/",
  resultRendererId: "condmat",
  visualizerPanelGroupId: "condmat",
  requiresProvenanceWarning: false,
  simulation: qcompassNoopSimulation,
};

registerDomain(condmatPlugin);
