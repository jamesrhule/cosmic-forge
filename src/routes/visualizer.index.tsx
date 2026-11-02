import { createFileRoute, getRouteApi, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import { SyntheticBadge } from "@/components/qcompass/synthetic-badge";
import type { VisualizationSummary } from "@/services/visualizer";
import { useCosmologyRuns, type CosmologyRuns } from "@/hooks/use-cosmology-runs";
import type { VisualizerSearch } from "@/lib/visualizerSearch";

const parentApi = getRouteApi("/visualizer");

/**
 * `/visualizer` index — landing card grid.
 *
 * Stays in the critical bundle: no R3F / Recharts / KaTeX imports here.
 * Each card links to `/visualizer/$runId`, which lazy-loads the heavy
 * panel surface from `visualizer.$runId.lazy.tsx`.
 */
export const Route = createFileRoute("/visualizer/")({
  head: () => ({
    meta: [
      { title: "Visualizer — Pick a run" },
      {
        name: "description",
        content:
          "Choose a completed UCGLE-F1 run to replay across six synchronized visualization panels.",
      },
      { property: "og:title", content: "Visualizer — UCGLE-F1 Workbench" },
      {
        property: "og:description",
        content:
          "Choose a completed UCGLE-F1 run to replay across six synchronized visualization panels.",
      },
      { property: "og:url", content: "/visualizer" },
      { property: "og:image", content: "/og/default.jpg" },
      { property: "og:image:width", content: "1200" },
      { property: "og:image:height", content: "630" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:image", content: "/og/default.jpg" },
    ],
  }),
  component: VisualizerIndexRoute,
});

function VisualizerIndexRoute() {
  const { summaries, syntheticRunIds } = parentApi.useLoaderData();
  const search = parentApi.useSearch();
  const apiRuns = useCosmologyRuns();

  // API build: the tenant's runs, never the bundled demo catalogue (c5).
  if (apiRuns.state !== "fixtures") return <ApiRunIndex runs={apiRuns} search={search} />;

  if (summaries.length === 0) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <EmptyPanel
          title="No visualizations available"
          reason="No completed runs ship a baked visualization fixture in this build."
          action={
            <Link to="/" className="text-xs font-medium text-primary hover:underline">
              Return to Configurator
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-tight">Visualizer — pick a run</h1>
        <p className="text-xs text-muted-foreground">
          Each card opens the six-panel workbench for a baked timeline. Add a partner run from the{" "}
          <span className="font-medium">Compare with…</span> picker in the workbench header.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {summaries.map((s: VisualizationSummary) => (
          <Link
            key={s.runId}
            to="/visualizer/$runId"
            params={{ runId: s.runId }}
            search={{
              runB: search.runB,
              mode: search.mode,
              phase: search.phase,
              frame: 0,
            }}
            preload="intent"
            className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
          >
            <Card className="h-full transition-colors hover:border-primary/50 hover:bg-accent/30">
              <CardHeader className="pb-2">
                <CardTitle className="font-mono text-sm">{s.runId}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-xs text-muted-foreground">
                <div>
                  {s.frameCount.toLocaleString()} frames · {s.kModes} k-modes · baked GPU buffers
                </div>
                {syntheticRunIds.includes(s.runId) && <SyntheticBadge />}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}

/**
 * `/visualizer` with `VITE_API_URL`: the signed-in tenant's cosmology runs
 * from the compute API, or an honest empty or error state. No frame counts:
 * computed runs have no baked six-panel timeline until P4-04.
 */
function ApiRunIndex({
  runs,
  search,
}: {
  runs: Exclude<CosmologyRuns, { state: "fixtures" }>;
  search: VisualizerSearch;
}) {
  const backToConfigurator = (
    <Link to="/" className="text-xs font-medium text-primary hover:underline">
      Return to Configurator
    </Link>
  );
  return (
    <div className="mx-auto max-w-5xl px-6 py-8" data-testid="visualizer-api-index">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-tight">Visualizer — your cosmology runs</h1>
        <p className="text-xs text-muted-foreground">
          Runs from the compute API. Six-panel timelines for computed runs arrive with P4-04; the
          bundled demo runs are not listed in this build.
        </p>
      </div>
      {runs.state === "loading" && (
        <p className="text-xs text-muted-foreground">Loading your cosmology runs…</p>
      )}
      {runs.state === "error" && (
        <EmptyPanel
          title="Couldn’t list your cosmology runs"
          reason={runs.message}
          action={backToConfigurator}
        />
      )}
      {runs.state === "ready" && runs.runs.length === 0 && (
        <EmptyPanel
          title="No cosmology runs yet"
          reason="Runs you submit from the Configurator are listed here."
          action={backToConfigurator}
        />
      )}
      {runs.state === "ready" && runs.runs.length > 0 && (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {runs.runs.map((r) => (
            <Link
              key={r.id}
              to="/visualizer/$runId"
              params={{ runId: r.id }}
              search={{ runB: search.runB, mode: search.mode, phase: search.phase, frame: 0 }}
              data-testid="visualizer-api-run"
              className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
            >
              <Card className="h-full transition-colors hover:border-primary/50 hover:bg-accent/30">
                <CardHeader className="pb-2">
                  <CardTitle className="font-mono text-sm">{r.id}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-xs text-muted-foreground">
                  <div>
                    {r.status} · {new Date(r.created_at).toLocaleString()}
                  </div>
                  <div>No six-panel timeline yet (P4-04)</div>
                  {r.synthetic === true && <SyntheticBadge />}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
