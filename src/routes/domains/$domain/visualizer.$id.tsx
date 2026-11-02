import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DomainShell, resolveDomain } from "@/components/domain-shell";
import { getDomainVisualization, getVisualization } from "@/services/qcompass/visualizer";
import { openDomainStream } from "@/services/visualizerStream";
import { FEATURES } from "@/config/features";
import { DomainVisualizerSurface } from "@/components/visualizer/domain-layouts/surface";
import type { VisualizationTimeline } from "@/lib/domains/types";
import type { DomainTimelineResponse } from "@/types/manifest";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

/**
 * `/domains/$domain/visualizer/$id` — the one domain visualizer route.
 *
 * P0-02 folded the router-branch `/visualizer/$domain/$id` route in
 * here: every non-cosmology domain renders its panel layout
 * (`DomainVisualizerSurface`); with `FEATURES.liveDomainStream` on,
 * frames from `openDomainStream` are appended live. Cosmology keeps the
 * existing behaviour unchanged (its full surface lives at
 * `/visualizer/$runId`).
 */
export const Route = createFileRoute("/domains/$domain/visualizer/$id")({
  // The loader returns only the (serialisable) domain id: the plugin
  // object carries functions, which SSR dehydration cannot serialise.
  loader: ({ params }) => {
    const plugin = resolveDomain(params.domain);
    return { domainId: plugin.id, label: plugin.label };
  },
  component: VisualizerDetail,
  head: ({ loaderData, params }) => ({
    meta: [
      {
        title: `${loaderData?.label ?? params.domain} · ${params.id} viz — QCompass`,
      },
    ],
  }),
});

function useDomain() {
  const { domainId } = Route.useLoaderData();
  return resolveDomain(domainId);
}

function VisualizerDetail() {
  const domain = useDomain();
  if (domain.id === "cosmology.ucglef1") return <CosmologyVisualizerDetail />;
  return <DomainPanelsDetail />;
}

function DomainPanelsDetail() {
  const domain = useDomain();
  const { id } = Route.useParams();
  const [tl, setTl] = useState<DomainTimelineResponse | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    setTl(undefined);
    getDomainVisualization(domain.id, id)
      .then((r) => !cancelled && setTl(r))
      .catch(() => !cancelled && setTl(null));
    return () => {
      cancelled = true;
    };
  }, [domain.id, id]);

  // Live stream only for backend-sourced runs (never for fixtures).
  const vizDomain = tl && tl.manifest.metadata.synthetic !== true ? tl.manifest.domain : null;
  useEffect(() => {
    if (!FEATURES.liveDomainStream || !vizDomain || vizDomain === "cosmology") return;
    let stream: ReturnType<typeof openDomainStream>;
    try {
      stream = openDomainStream(vizDomain, id);
    } catch {
      return;
    }
    let stopped = false;
    let first = true;
    void (async () => {
      try {
        for await (const frame of stream.frames) {
          if (stopped) break;
          // The stream replays the run from τ = 0: its frames replace
          // the fetched timeline rather than duplicating it.
          const reset = first;
          first = false;
          setTl((prev) =>
            prev ? { ...prev, frames: reset ? [frame] : [...prev.frames, frame] } : prev,
          );
        }
      } catch {
        /* stream ended or transport unavailable — keep the loaded timeline */
      }
    })();
    return () => {
      stopped = true;
      stream.close();
    };
  }, [vizDomain, id]);

  return (
    <DomainShell domain={domain} active="visualizer">
      {tl === undefined ? (
        <p className="text-xs text-muted-foreground">Loading timeline…</p>
      ) : tl === null ? (
        <p className="text-xs text-muted-foreground" data-testid="visualizer-unavailable">
          No visualizer timeline is available for this run.
        </p>
      ) : (
        <div
          className="flex min-h-[640px] flex-col rounded-md border"
          data-testid="domain-visualizer"
        >
          <div className="flex items-center justify-between border-b px-4 py-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-mono uppercase text-muted-foreground">
                {tl.manifest.domain}
              </span>
              <span className="font-mono text-foreground/70">/</span>
              <span className="font-mono text-foreground">{id}</span>
              {tl.manifest.formula_variant ? (
                <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] uppercase">
                  {tl.manifest.formula_variant}
                </span>
              ) : null}
            </div>
            <span className="font-mono text-[11px] text-muted-foreground">
              {tl.frames.length} / {Math.max(tl.manifest.frame_count, tl.frames.length)} frames
            </span>
          </div>
          <DomainVisualizerSurface manifest={tl.manifest} timeline={tl} />
        </div>
      )}
    </DomainShell>
  );
}

function CosmologyVisualizerDetail() {
  const domain = useDomain();
  const { id } = Route.useParams();
  const [tl, setTl] = useState<VisualizationTimeline | null>(null);

  useEffect(() => {
    getVisualization(domain.id, id)
      .then(setTl)
      .catch(() => setTl(null));
  }, [domain.id, id]);

  return (
    <DomainShell domain={domain} active="visualizer">
      {!tl ? (
        <p className="text-xs text-muted-foreground">Loading timeline…</p>
      ) : (
        <Card className="space-y-3 p-4" data-testid="visualizer-coming-online">
          <header className="flex items-center justify-between">
            <h3 className="font-medium">Visualizer panel · coming online</h3>
            <Badge variant="outline" className="font-mono text-[10px]">
              {tl.panelGroupId}
            </Badge>
          </header>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <dt className="text-[10px] uppercase text-muted-foreground">Frames</dt>
              <dd className="font-mono">{tl.frames.length}</dd>
            </div>
            <div>
              <dt className="text-[10px] uppercase text-muted-foreground">τ range</dt>
              <dd className="font-mono">
                [{tl.tau_range[0]}, {tl.tau_range[1]}]
              </dd>
            </div>
          </dl>
          {tl.active_terms.length > 0 && (
            <div>
              <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground">
                Active terms
              </div>
              <div className="flex flex-wrap gap-1">
                {tl.active_terms.map((t) => (
                  <Badge key={t} variant="outline" className="font-mono text-[10px]">
                    {t}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          <p className="border-t pt-2 text-[11px] italic text-muted-foreground">
            Rich 3D / Recharts panels land in the depth pass. The data path is exercised end-to-end.
          </p>
        </Card>
      )}
    </DomainShell>
  );
}
