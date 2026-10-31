/**
 * QCompass — Chemistry Result.
 *
 * Hosts the energy-comparison card that previously lived on the
 * agent branch's dedicated `/domains/chemistry/runs/$id` page. The
 * generic `domains/$domain/*` routes render this through
 * `DomainResult`.
 */
import type { DomainRunResult } from "@/lib/domains/types";
import { ProvenancePanel } from "@/components/ProvenancePanel";
import { EnergyComparisonCard } from "@/components/qcompass/energy-comparison-card";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ChemistryEnergies } from "@/types/qcompass";

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export function toChemistryEnergies(run: DomainRunResult): ChemistryEnergies {
  const p = (run.payload ?? {}) as Record<string, unknown>;
  const classical = num(p.classical_energy) ?? num(p.classical_reference_hartree);
  const quantum = num(p.quantum_energy) ?? num(p.energy_hartree);
  const method =
    typeof p.classical_method === "string"
      ? p.classical_method
      : classical !== null
        ? "reference"
        : "unavailable";
  return {
    classical_energy: classical,
    quantum_energy: quantum,
    classical_method: method,
    summary: typeof p.summary === "string" ? p.summary : "",
  };
}

export function ChemistryResult({ run }: { run: DomainRunResult }) {
  return (
    <div className="space-y-4" data-testid="chemistry-result">
      <EnergyComparisonCard energies={toChemistryEnergies(run)} />
      <ProvenancePanel provenance={run.provenance} />
      <Card>
        <CardHeader>
          <CardTitle>Run payload</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="overflow-auto rounded-md bg-muted/40 p-3 font-mono text-[11px]">
            {JSON.stringify(run.payload ?? {}, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
