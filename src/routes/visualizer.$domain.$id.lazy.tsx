import { createLazyFileRoute, getRouteApi, Link } from "@tanstack/react-router";
import { DomainVisualizerSurface } from "@/components/visualizer/domain-layouts/surface";
import type { DomainVisualizationLoaderData } from "./visualizer.$domain.$id";

const routeApi = getRouteApi("/visualizer/$domain/$id");

/**
 * Lazy chunk: holds the per-domain panel layouts. Picks the layout
 * via the manifest's `domain` field and hands the timeline frames
 * down to the panels.
 */
export const Route = createLazyFileRoute("/visualizer/$domain/$id")({
  component: DomainVisualizerRoute,
});

function DomainVisualizerRoute() {
  const { manifest, timeline } = routeApi.useLoaderData() as DomainVisualizationLoaderData;
  const params = routeApi.useParams();

  return (
    <div className="flex h-[calc(100vh-3.5rem)] min-h-0 flex-col">
      <div className="flex items-center justify-between border-b px-4 py-2 text-xs">
        <div className="flex items-center gap-2">
          <Link
            to="/visualizer"
            className="rounded-md border px-2 py-1 font-mono text-[11px] hover:bg-muted"
          >
            ← runs
          </Link>
          <span className="font-mono uppercase text-muted-foreground">
            {manifest.domain}
          </span>
          <span className="font-mono text-foreground/70">/</span>
          <span className="font-mono text-foreground">{params.id}</span>
          {manifest.formula_variant ? (
            <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase">
              {manifest.formula_variant}
            </span>
          ) : null}
        </div>
        <span className="font-mono text-[11px] text-muted-foreground">
          {timeline.frames.length} / {manifest.frame_count} frames
        </span>
      </div>
      <DomainVisualizerSurface manifest={manifest} timeline={timeline} />
    </div>
  );
}
