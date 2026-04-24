import { createFileRoute, notFound } from "@tanstack/react-router";
import { useRouter } from "@tanstack/react-router";
import { Link } from "@tanstack/react-router";
import { getVisualization } from "@/services/visualizer";
import { ServiceError } from "@/types/domain";
import type { BakedVisualizationTimeline } from "@/types/visualizer";
import type { VisualizerSearch } from "@/lib/visualizerSearch";

export interface RunVisualizationLoaderData {
  a: BakedVisualizationTimeline;
  b: BakedVisualizationTimeline | null;
}

/**
 * `/visualizer/$runId` — critical config only.
 *
 * The component lives in the sibling `.lazy.tsx` so the R3F + Recharts +
 * KaTeX panel surface is split out of the main bundle. The loader stays
 * here per TanStack guidance (avoids the double-async cost of fetching
 * a chunk just to start fetching data).
 */
export const Route = createFileRoute("/visualizer/$runId")({
  head: ({ params }) => ({
    meta: [
      { title: `${params.runId} — Visualizer` },
      {
        name: "description",
        content: `Six-panel visualization of UCGLE-F1 run ${params.runId}.`,
      },
      {
        property: "og:title",
        content: `${params.runId} — UCGLE-F1 Visualizer`,
      },
      {
        property: "og:description",
        content: `Replay the gravitational-leptogenesis run ${params.runId} across six synchronized panels.`,
      },
      { property: "og:url", content: `/visualizer/${params.runId}` },
      {
        name: "twitter:title",
        content: `${params.runId} — UCGLE-F1 Visualizer`,
      },
      {
        name: "twitter:description",
        content: `Replay the gravitational-leptogenesis run ${params.runId} across six synchronized panels.`,
      },
    ],
  }),
  // Re-run the loader when the partner run changes; ignore frame/mode/phase
  // — those are pure UI state and would otherwise trigger a full refetch
  // on every scrub.
  loaderDeps: ({ search }) => ({
    runB: (search as VisualizerSearch).runB,
  }),
  loader: async ({ params, deps }): Promise<RunVisualizationLoaderData> => {
    const { runB } = deps as { runB: string | undefined };
    try {
      const wantPartner = runB && runB !== params.runId;
      const [a, b] = await Promise.all([
        getVisualization(params.runId),
        wantPartner ? getVisualization(runB!) : Promise.resolve(null),
      ]);
      return { a, b };
    } catch (err) {
      if (err instanceof ServiceError && err.code === "NOT_FOUND") {
        throw notFound();
      }
      throw err;
    }
  },
  errorComponent: RunErrorComponent,
  notFoundComponent: RunNotFoundComponent,
});

function RunErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  const router = useRouter();
  return (
    <div className="flex h-full min-h-[60vh] items-center justify-center px-4">
      <div className="max-w-md text-center">
        <h2 className="text-base font-semibold text-foreground">
          Couldn’t load this visualization
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
        <div className="mt-4 flex items-center justify-center gap-2">
          <button
            type="button"
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
          >
            Retry
          </button>
          <Link
            to="/visualizer"
            className="inline-flex items-center justify-center rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted"
          >
            Back to runs
          </Link>
        </div>
      </div>
    </div>
  );
}

function RunNotFoundComponent() {
  const params = Route.useParams();
  return (
    <div className="flex h-full min-h-[60vh] items-center justify-center px-4">
      <div className="max-w-md text-center">
        <h2 className="text-base font-semibold text-foreground">
          No visualization for <span className="font-mono">{params.runId}</span>
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          This run either doesn’t exist or completed before the visualizer integration shipped. Pick
          another from the index.
        </p>
        <Link
          to="/visualizer"
          className="mt-4 inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
        >
          Back to runs
        </Link>
      </div>
    </div>
  );
}
