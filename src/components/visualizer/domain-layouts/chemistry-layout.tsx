import type { ChemistryFrame, VisualizationManifest } from "@/types/manifest";
import { OrbitalOccupation3D } from "@/components/visualizer/panels/chemistry/OrbitalOccupation3D";
import { EnergyConvergence } from "@/components/visualizer/panels/chemistry/EnergyConvergence";
import { SlaterSankey } from "@/components/visualizer/panels/chemistry/SlaterSankey";
import { HamiltonianOverlay } from "@/components/visualizer/panels/chemistry/HamiltonianOverlay";

export interface ChemistryDomainLayoutProps {
  manifest: VisualizationManifest;
  frame: ChemistryFrame | null;
  frames: ChemistryFrame[];
}

/**
 * Quantum-chemistry 4-panel grid: orbitals, energy convergence,
 * Slater determinants / flow, Hamiltonian overlay.
 */
export function ChemistryDomainLayout({ manifest, frame }: ChemistryDomainLayoutProps) {
  return (
    <>
      <OrbitalOccupation3D frame={frame} />
      <EnergyConvergence frame={frame} />
      <SlaterSankey frame={frame} />
      <HamiltonianOverlay frame={frame} manifestSummary={manifest.formula_variant ?? undefined} />
    </>
  );
}
