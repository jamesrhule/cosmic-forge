import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sci } from "@/components/sci";
import { VerdictChip } from "@/components/verdict-chip";
import { FEATURES } from "@/config/features";
import { DomainSwitcher } from "@/components/qcompass/domain-switcher";
import { StatusChip } from "@/components/status-chip";
import { ArxivLink } from "@/components/arxiv-link";
import { UncertaintyBar } from "@/components/uncertainty-bar";
import { EquationBlock } from "@/components/equation-block";
import { SGWBPlot } from "@/components/sgwb-plot";
import { ParameterHeatmap } from "@/components/parameter-heatmap";
import { BogoliubovGauge } from "@/components/bogoliubov-gauge";
import { ContextChip } from "@/components/context-chip";
import { ModelBadge } from "@/components/model-badge";
import { ToolCallCard } from "@/components/tool-call-card";
import { getRun, getScan } from "@/services/simulator";
import { listModels } from "@/services/assistant";
import type {
  ModelDescriptor,
  RunResult,
  ScanResult,
} from "@/types/domain";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "UCGLE-F1 Workbench" },
      {
        name: "description",
        content:
          "Research shell for the UCGLE-F1 gravitational-leptogenesis simulator.",
      },
    ],
  }),
  component: WorkbenchShell,
});

function WorkbenchShell() {
  const [run, setRun] = useState<RunResult | null>(null);
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [models, setModels] = useState<ModelDescriptor[]>([]);

  useEffect(() => {
    getRun("kawai-kim-natural").then(setRun).catch(console.error);
    getScan("xi-theta-32x32").then(setScan).catch(console.error);
    listModels().then(setModels).catch(console.error);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 flex h-14 items-center gap-4 border-b bg-background/80 px-6 backdrop-blur">
        <span className="font-semibold tracking-tight">UCGLE-F1 Workbench</span>
        <span className="rounded-full border bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
          static-shell
        </span>
        {FEATURES.qcompassMultiDomain && (
          <div className="ml-2">
            <DomainSwitcher />
          </div>
        )}
        <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--color-status-canceled)]" />
            fixture mode
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-6 py-8">
        <section className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Frontend shell scaffold. Service layer, types, fixtures, and
            shared components are wired and ready for the FastAPI backend
            handoff. The full three-view application (Configurator / Control /
            Research) is the next implementation pass.
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <StatusChip status="completed" />
            <StatusChip status="running" />
            <StatusChip status="failed" />
            <StatusChip status="queued" />
            <StatusChip status="canceled" />
          </div>
        </section>

        {run && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>
                  Run{" "}
                  <span className="font-mono text-sm text-muted-foreground">
                    {run.id}
                  </span>
                </span>
                <StatusChip status={run.status} />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">
                    η_B
                  </div>
                  <div className="mt-1 text-3xl font-semibold">
                    <Sci value={run.eta_B.value} sig={3} />
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    ± <Sci value={run.eta_B.uncertainty} sig={2} />
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">
                    Uncertainty budget
                  </div>
                  <div className="mt-2">
                    <UncertaintyBar budget={run.eta_B.budget} />
                  </div>
                </div>
              </div>

              <div>
                <div className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">
                  Audit (S1–S15)
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {run.audit.checks.map((c) => (
                    <VerdictChip
                      key={c.id}
                      verdict={c.verdict}
                      id={c.id}
                      name={c.name}
                      size="sm"
                    />
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {run.audit.checks[0]?.references.map((r) => (
                  <ArxivLink key={r} id={r} />
                ))}
              </div>

              <BogoliubovGauge drift={7e-4} />
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>F1 — primary mechanism</CardTitle>
          </CardHeader>
          <CardContent>
            <EquationBlock
              copyable
              latex={String.raw`\boxed{\,\eta_B \;=\; \mathcal{N}\,\xi\,\theta_{\text{grav}}\;\langle R\widetilde{R}\rangle_\Psi\;\frac{S_{\!E2}\,M_1}{f_a\,M_\star^2}\,}`}
            />
          </CardContent>
        </Card>

        {run && (
          <Card>
            <CardHeader>
              <CardTitle>SGWB spectrum</CardTitle>
            </CardHeader>
            <CardContent>
              <SGWBPlot
                spectra={[
                  {
                    id: run.id,
                    label: run.id,
                    data: run.spectra.sgwb,
                  },
                ]}
              />
            </CardContent>
          </Card>
        )}

        {scan && (
          <Card>
            <CardHeader>
              <CardTitle>Parameter scan ξ × θ_grav</CardTitle>
            </CardHeader>
            <CardContent>
              <ParameterHeatmap scan={scan} />
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Assistant primitives</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <ContextChip kind="run" label="kawai-kim-natural" />
              <ContextChip kind="benchmark" label="V2 Kawai-Kim" />
              <ContextChip kind="config" label="Natural inflation, ξ=8.5e-3" />
            </div>
            <div className="flex flex-wrap gap-2">
              {models.slice(0, 4).map((m) => (
                <ModelBadge key={m.id} descriptor={m} />
              ))}
            </div>
            <ToolCallCard
              call={{
                id: "demo",
                name: "summarize_audit",
                arguments: { runId: "kawai-kim-natural" },
              }}
              result={{
                id: "demo",
                ok: true,
                output: { passed: 15, total: 15, closest_to_fail: "S6" },
              }}
              onApply={() => undefined}
            />
          </CardContent>
        </Card>
      </main>

      <footer className="mx-auto max-w-6xl px-6 py-4 text-xs text-muted-foreground">
        build static-shell-2025.04 · fixture mode · see README for handoff
        contract
      </footer>
    </div>
  );
}
