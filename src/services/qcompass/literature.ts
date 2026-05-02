/**
 * QCompass — Literature reference service (fixture-only today).
 *
 * Powers the [Compare to literature] sheet in the HEP and nuclear
 * observables tables.
 *
 * @example
 *   const refs = await getLatticeQCDReferences();
 */
import { loadFixture } from "@/lib/fixtures";

export interface LiteratureReference {
  observable: string;
  value: number;
  uncertainty: number;
  units: string;
  source_label: string;
  arxiv_id: string;
  notes?: string;
}

/** @endpoint GET /api/qcompass/literature/lattice-qcd  (fixture today) */
export async function getLatticeQCDReferences(): Promise<LiteratureReference[]> {
  return loadFixture<LiteratureReference[]>("literature/lattice-qcd-references.json");
}

/** @endpoint GET /api/qcompass/literature/nuclear  (fixture today) */
export async function getNuclearReferences(): Promise<LiteratureReference[]> {
  return loadFixture<LiteratureReference[]>("literature/nuclear-references.json");
}
