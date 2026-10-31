import type {
  ChemistryFrame,
  DomainTimelineResponse,
  VisualizationManifest,
} from "@/types/manifest";
import { OrbitalOccupation3D } from "@/components/visualizer/panels/chemistry/OrbitalOccupation3D";
import { EnergyConvergence } from "@/components/visualizer/panels/chemistry/EnergyConvergence";
import { SlaterSankey } from "@/components/visualizer/panels/chemistry/SlaterSankey";
import { HamiltonianOverlay } from "@/components/visualizer/panels/chemistry/HamiltonianOverlay";

export interface ChemistryDomainLayoutProps {
  manifest: VisualizationManifest;
  frame: ChemistryFrame | null;
  timeline: DomainTimelineResponse;
}

/**
 * Quantum-chemistry 4-panel grid: orbitals, energy convergence,
 * Slater determinant weights, Hamiltonian overlay.
 */
export function ChemistryDomainLayout({ frame }: ChemistryDomainLayoutProps) {
  return (
    <>
      <OrbitalOccupation3D frame={frame} />
      <EnergyConvergence frame={frame} />
      <SlaterSankey frame={frame} />
      <HamiltonianOverlay frame={frame} />
    </>
  );
}
