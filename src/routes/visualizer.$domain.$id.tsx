import { createFileRoute, notFound } from "@tanstack/react-router";
import { ServiceError } from "@/types/domain";
import { getDomainTimeline, getManifest } from "@/services/manifest";
import type {
  DomainTimelineResponse,
  VisualizationDomain,
  VisualizationManifest,
} from "@/types/manifest";
import { VisualizerRunSkeleton } from "@/components/loading/route-skeletons";

const VALID_DOMAINS: ReadonlySet<VisualizationDomain> = new Set([
  "cosmology",
  "chemistry",
  "condmat",
  "hep",
  "nuclear",
  "amo",
]);

export interface DomainVisualizationLoaderData {
  manifest: VisualizationManifest;
  timeline: DomainTimelineResponse;
}

/**
 * `/visualizer/$domain/$id` — cross-domain visualizer entry point.
 *
 * Distinct from `/visualizer/$runId` (the cosmology-only legacy path);
 * dispatches to per-domain panel layouts via the manifest's `domain`
 * field.
 */
export const Route = createFileRoute("/visualizer/$domain/$id")({
  beforeLoad: ({ params }) => {
    if (!VALID_DOMAINS.has(params.domain as VisualizationDomain)) {
      throw notFound();
    }
  },
  head: ({ params }) => ({
    meta: [
      { title: `${params.domain}/${params.id} — Visualizer` },
      {
        name: "description",
        content: `Domain visualizer for ${params.domain} run ${params.id}.`,
      },
    ],
  }),
  loader: async ({ params }): Promise<DomainVisualizationLoaderData> => {
    const domain = params.domain as VisualizationDomain;
    try {
      const [manifest, timeline] = await Promise.all([
        getManifest(domain, params.id),
        getDomainTimeline(domain, params.id),
      ]);
      return { manifest, timeline };
    } catch (err) {
      if (err instanceof ServiceError && err.code === "NOT_FOUND") {
        throw notFound();
      }
      throw err;
    }
  },
  pendingComponent: VisualizerRunSkeleton,
  pendingMs: 200,
});
