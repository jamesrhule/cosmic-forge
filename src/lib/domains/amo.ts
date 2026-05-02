/**
 * QCompass — AMO (Rydberg) domain plugin (scaffolding).
 */
import type { DomainPlugin } from "./types";
import { FEATURES } from "@/config/features";
import { qcompassNoopSimulation } from "./_noop-sim";
import { registerDomain } from "./registry";

export const amoPlugin: DomainPlugin = {
  id: "amo.rydberg",
  label: "AMO · Rydberg",
  description: "Neutral-atom analog quantum simulation (QuEra / Pasqal).",
  capability: { classical: true, quantum: true, audited: false },
  enabled: FEATURES.qcompassMultiDomain && FEATURES.qcompassAmo,
  disabledReason: "Enable in feature flags (qcompassMultiDomain + qcompassAmo).",
  manifestSchemaUrl: "amo/manifest-schema.json",
  fixturePathPrefix: "amo/",
  resultRendererId: "amo",
  visualizerPanelGroupId: "amo",
  requiresProvenanceWarning: false,
  simulation: qcompassNoopSimulation,
};

registerDomain(amoPlugin);
