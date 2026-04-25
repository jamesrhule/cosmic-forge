import { createFileRoute, getRouteApi, Link } from "@tanstack/react-router";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import type { VisualizationSummary } from "@/services/visualizer";

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
  const { summaries } = parentApi.useLoaderData();
  const search = parentApi.useSearch();

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
              <CardContent className="text-xs text-muted-foreground">
                {s.frameCount.toLocaleString()} frames · {s.kModes} k-modes · baked GPU buffers
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
