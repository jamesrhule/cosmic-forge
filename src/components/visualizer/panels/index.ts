/**
 * Per-domain visualization panel barrel (PROMPT 7 v2 §PART C).
 *
 * Each panel consumes a typed VisualizationFrame from
 * `cosmic_forge_viz` and renders the matching observable.
 */

export type {
  AmoFrame,
  BaseFrame,
  ChemistryFrame,
  CondmatFrame,
  CosmologyFrame,
  DomainName,
  HepFrame,
  NuclearFrame,
  ParticleObservable,
  VisualizationFrame,
  VisualizationTimeline,
} from "./types";

// Chemistry
export { default as OrbitalOccupation3D } from "./chemistry/OrbitalOccupation3D";
export { default as EnergyConvergence } from "./chemistry/EnergyConvergence";
export { default as SlaterSankey } from "./chemistry/SlaterSankey";
export { default as HamiltonianOverlay } from "./chemistry/HamiltonianOverlay";

// Condmat
export { default as LatticeBonds } from "./condmat/LatticeBonds";
export { default as OtocButterfly } from "./condmat/OtocButterfly";
export { default as SpectralHeatmap } from "./condmat/SpectralHeatmap";

// HEP
export { default as GaugePlaquettes } from "./hep/GaugePlaquettes";
export { default as ChiralCondensateTrace } from "./hep/ChiralCondensateTrace";
export { default as StringBreakingAnim } from "./hep/StringBreakingAnim";
export { default as ParticleObservablesTable } from "./hep/ParticleObservablesTable";

// Nuclear
export { default as ShellOccupation } from "./nuclear/ShellOccupation";
export { default as LNVTracker } from "./nuclear/LNVTracker";
export { default as ModelDomainBadge } from "./nuclear/ModelDomainBadge";

// AMO
export { default as AtomArray3D } from "./amo/AtomArray3D";
export { default as BlockadeCorrelations } from "./amo/BlockadeCorrelations";
