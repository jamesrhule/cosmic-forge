/**
 * QCompass — Literature reference service.
 *
 * Powers the [Compare to literature] sheet in the HEP and nuclear
 * observables tables. The compute API serves the references (P4-01);
 * the bundled fixtures are the offline copy, and
 * `backend/tests/test_frontend_contract.py` keeps the two identical.
 *
 * @example
 *   const refs = await getLatticeQCDReferences();
 */
import * as sdk from "@qcompass/frontend-sdk";
import { loadFixture } from "@/lib/fixtures";
import { api, usesApi } from "@/lib/sdk";

export interface LiteratureReference {
  observable: string;
  value: number;
  uncertainty: number;
  units: string;
  source_label: string;
  arxiv_id: string;
  notes?: string;
}

/** @endpoint GET /api/qcompass/literature/lattice-qcd */
export async function getLatticeQCDReferences(): Promise<LiteratureReference[]> {
  if (usesApi()) {
    return (await api((c) => sdk.getLatticeQcdReferences(c))) as LiteratureReference[];
  }
  return loadFixture<LiteratureReference[]>("literature/lattice-qcd-references.json");
}

/** @endpoint GET /api/qcompass/literature/nuclear */
export async function getNuclearReferences(): Promise<LiteratureReference[]> {
  if (usesApi()) {
    return (await api((c) => sdk.getNuclearReferences(c))) as LiteratureReference[];
  }
  return loadFixture<LiteratureReference[]>("literature/nuclear-references.json");
}
