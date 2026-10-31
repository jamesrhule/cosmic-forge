/**
 * Per-domain visualization panel barrel.
 *
 * Every panel consumes the canonical frame types in `./types`
 * (normalised by `@/lib/visualizer/domainFrames`).
 */

export type {
  AmoFrame,
  BaseFrame,
  ChemistryFrame,
  CondmatFrame,
  CosmologyFrame,
  DomainName,
  DomainVisualizationFrame,
  GravityFrame,
  HepFrame,
  NuclearFrame,
  ParticleObservable,
  StatmechFrame,
  VisualizationFrame,
  VisualizationTimeline,
} from "./types";

export { PanelShell } from "./PanelShell";

// Chemistry
export { default as OrbitalOccupation3D } from "./chemistry/OrbitalOccupation3D";
export { default as EnergyConvergence } from "./chemistry/EnergyConvergence";
export { default as SlaterSankey } from "./chemistry/SlaterSankey";
export { default as HamiltonianOverlay } from "./chemistry/HamiltonianOverlay";

// Condmat
export { default as LatticeWithBondColors } from "./condmat/LatticeWithBondColors";
export { default as OtocButterflyCone } from "./condmat/OtocButterflyCone";
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

// Gravity
export {
  default as ProvenanceWarningBanner,
  learnedProvenance,
} from "./gravity/ProvenanceWarningBanner";
export { default as SpectralFormFactor } from "./gravity/SpectralFormFactor";

// Statmech
export { default as EstimatorTrace } from "./statmech/EstimatorTrace";
