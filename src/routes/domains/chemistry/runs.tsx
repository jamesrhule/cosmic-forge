import { useEffect, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { listChemistryRuns } from "@/services/qcompass/chemistry";
import type { ChemistryRunResult } from "@/types/qcompass";

export const Route = createFileRoute("/domains/chemistry/runs")({
  component: ChemistryRunsList,
});

function ChemistryRunsList() {
  const [runs, setRuns] = useState<ChemistryRunResult[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listChemistryRuns()
      .then(setRuns)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          Chemistry runs
        </h1>
        <p className="text-sm text-muted-foreground">
          Every run carries its own provenance sidecar; click through to
          inspect the energy comparison + ProvenanceRecord details.
        </p>
      </section>
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {runs.map((run) => (
          <RunCard key={run.id} run={run} />
        ))}
      </div>
    </div>
  );
}

function RunCard({ run }: { run: ChemistryRunResult }) {
  const { manifest, energies, pathTaken, provenance_warning } = run;
  return (
    <Link to="/domains/chemistry/runs/$id" params={{ id: run.id }}>
      <Card className="h-full transition-colors hover:bg-muted/30">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="font-mono text-sm">{run.id}</span>
            <Badge variant="outline" className="text-[11px]">
              {pathTaken}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="text-muted-foreground">
            {manifest.problem.molecule} · {manifest.problem.basis} ·{" "}
            {manifest.problem.reference}
          </div>
          <div className="font-mono text-xs">
            classical:{" "}
            {energies.classical_energy === null
              ? "—"
              : `${energies.classical_energy.toFixed(6)} Ha`}
            {energies.quantum_energy !== null && (
              <>
                {" "}
                · quantum: {energies.quantum_energy.toFixed(6)} Ha
              </>
            )}
          </div>
          <p className="text-xs text-muted-foreground">{energies.summary}</p>
          {provenance_warning === "no_classical_reference" && (
            <Badge variant="outline" className="text-[11px]">
              no classical reference
            </Badge>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
