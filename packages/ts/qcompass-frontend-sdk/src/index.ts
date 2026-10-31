/**
 * @qcompass/frontend-sdk — typed clients for the qcompass HTTP /
 * WS surface (PROMPT 8 v2 §C).
 *
 * Usage:
 *   import { QcompassClient, chemistryService } from "@qcompass/frontend-sdk";
 *
 *   const client = new QcompassClient({ baseUrl: import.meta.env.VITE_API_URL });
 *   const chem   = chemistryService(client);
 *   const sub    = await chem.submit(manifest);
 *   const result = await chem.get(sub.runId);
 *   for await (const ev of chem.stream(sub.runId)) console.log(ev);
 *
 * Whether the call hits the live backend or a fixture is decided
 * at the React layer (FEATURES.liveBackend); the SDK itself never
 * reads the flag.
 */

export {
  QcompassClient,
  QcompassError,
  decodeFrame,
} from "./client";
export type { ClientConfig } from "./client";

export {
  // Domains
  listDomains,
  getDomainSchema,
  // Runs
  submitRun,
  getRun,
  streamRun,
  // Visualization
  getVisualization,
  openVisualizationStream,
  // Scans
  listScans,
  getScan,
  createScan,
  deleteScan,
  // Domain namespaces
  chemistryService,
  cosmologyService,
  hepService,
  nuclearService,
} from "./services";

export type {
  AmoFrame,
  BackendRequest,
  BaseFrame,
  ChemistryFrame,
  CondmatFrame,
  CosmologyFrame,
  CreateScanRequest,
  DomainId,
  DomainSummary,
  DomainsResponse,
  HepFrame,
  NuclearFrame,
  ParticleObservable,
  ProvenanceRecord,
  ProvenanceSidecar,
  QcompassManifest,
  ScanEnvelope,
  SubmitRunRequest,
  SubmitRunResponse,
  VisualizationFrame,
  VisualizationTimeline,
} from "./types";
