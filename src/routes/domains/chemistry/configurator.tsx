import { useEffect, useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { JsonSchemaForm } from "@/components/qcompass/json-schema-form";
import { getManifestSchema } from "@/services/qcompass/manifestSchema";
import { startChemistryRun } from "@/services/qcompass/chemistry";
import type {
  ChemistryProblem,
  JsonSchema,
  QcompassManifest,
} from "@/types/qcompass";

export const Route = createFileRoute("/domains/chemistry/configurator")({
  component: ChemistryConfigurator,
});

function ChemistryConfigurator() {
  const navigate = useNavigate();
  const [schema, setSchema] = useState<JsonSchema | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getManifestSchema("chemistry")
      .then(setSchema)
      .catch((e) => setError(String(e)));
  }, []);

  const handleSubmit = async (problem: ChemistryProblem) => {
    setSubmitting(true);
    setError(null);
    try {
      const manifest: QcompassManifest<ChemistryProblem> = {
        domain: "chemistry",
        version: "1.0",
        problem,
        backend_request: {
          kind: pickBackendKind(problem.backend_preference),
          target: null,
          priority: [],
          shots: problem.shots,
          seed: problem.seed,
          max_runtime_seconds: 3600,
        },
      };
      const { runId } = await startChemistryRun(manifest);
      void navigate({
        to: "/domains/chemistry/runs/$id",
        params: { id: runId },
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      <Header />
      <Card>
        <CardHeader>
          <CardTitle>Manifest</CardTitle>
        </CardHeader>
        <CardContent>
          {error && (
            <p className="mb-3 text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
          {!schema ? (
            <p className="text-sm text-muted-foreground">Loading schema…</p>
          ) : (
            <JsonSchemaForm<ChemistryProblem>
              schema={schema}
              defaultValues={{
                molecule: "H2",
                basis: "sto-3g",
                active_space: [2, 2],
                backend_preference: "auto",
                reference: "FCI",
                shots: 4096,
                seed: 0,
                geometry: "H 0 0 0\nH 0 0 0.74\n",
                fcidump_path: null,
                charge: 0,
                spin: 0,
              }}
              isSubmitting={submitting}
              onSubmit={handleSubmit}
              submitLabel="Submit run"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Header() {
  return (
    <section className="space-y-2">
      <h1 className="text-2xl font-semibold tracking-tight">
        Chemistry configurator
      </h1>
      <p className="max-w-3xl text-sm text-muted-foreground">
        Build a <code className="font-mono">ChemistryProblem</code> manifest and
        submit it to the <code className="font-mono">qfull-chemistry</code>{" "}
        plugin. Every quantum result is paired with a classical reference
        (PySCF FCI / CCSD(T) / block2 DMRG); FeMoco-toy is the documented
        exception and surfaces a yellow advisory in the Control view.
      </p>
    </section>
  );
}

function pickBackendKind(
  preference: ChemistryProblem["backend_preference"],
): QcompassManifest["backend_request"]["kind"] {
  if (preference === "classical") return "classical";
  if (preference === "sqd" || preference === "dice") return "quantum_simulator";
  return "auto";
}
