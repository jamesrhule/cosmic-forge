import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ChemistryEnergies } from "@/types/qcompass";

/** Chemical accuracy: 1.6 mHa (≈ 1 kcal/mol). */
const CHEMICAL_ACCURACY_HA = 1.6e-3;

interface EnergyComparisonCardProps {
  energies: ChemistryEnergies;
  /** Optional: literature reference shown beside the deltas. */
  reference?: number | null;
}

export function EnergyComparisonCard({
  energies,
  reference,
}: EnergyComparisonCardProps) {
  const { classical_energy, quantum_energy, classical_method, summary } =
    energies;

  const delta =
    classical_energy !== null && quantum_energy !== null
      ? quantum_energy - classical_energy
      : null;
  const withinAccuracy =
    delta !== null && Math.abs(delta) <= CHEMICAL_ACCURACY_HA;
  const deltaToReference =
    reference !== null && reference !== undefined &&
    classical_energy !== null
      ? classical_energy - reference
      : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Energy comparison</span>
          {delta !== null && (
            <Badge
              variant={withinAccuracy ? "default" : "destructive"}
              className="font-mono text-[11px]"
            >
              {withinAccuracy ? "chemical accuracy" : "outside chem. acc."}
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <EnergyTile
            label={`Classical (${classical_method})`}
            energy={classical_energy}
            unavailableHint={
              classical_method === "unavailable"
                ? "No classical reference is feasible at this scale."
                : undefined
            }
          />
          <EnergyTile
            label="Quantum"
            energy={quantum_energy}
            unavailableHint={
              quantum_energy === null && classical_energy !== null
                ? "Run executed on the classical path; no quantum result."
                : undefined
            }
          />
        </div>

        <dl className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <dt className="text-muted-foreground">Δ (Q − C)</dt>
            <dd className="font-mono">
              {delta === null ? "—" : `${formatHartree(delta)} Ha`}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Reference offset</dt>
            <dd className="font-mono">
              {deltaToReference === null
                ? "—"
                : `${formatHartree(deltaToReference)} Ha`}
            </dd>
          </div>
        </dl>

        {summary && (
          <p className="text-xs text-muted-foreground">{summary}</p>
        )}
      </CardContent>
    </Card>
  );
}

function EnergyTile({
  label,
  energy,
  unavailableHint,
}: {
  label: string;
  energy: number | null;
  unavailableHint?: string;
}) {
  return (
    <div className="rounded-md border bg-muted/30 p-3">
      <div className="text-xs uppercase tracking-wide text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 font-mono text-2xl">
        {energy === null ? "—" : `${formatHartree(energy)} Ha`}
      </div>
      {unavailableHint && (
        <div className="mt-1 text-[11px] text-muted-foreground">
          {unavailableHint}
        </div>
      )}
    </div>
  );
}

function formatHartree(v: number): string {
  if (Math.abs(v) >= 1) return v.toFixed(6);
  if (Math.abs(v) >= 1e-4) return v.toFixed(8);
  return v.toExponential(3);
}
