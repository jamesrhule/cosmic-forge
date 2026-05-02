import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DomainShell, resolveDomain } from "@/components/domain-shell";
import { getVisualization } from "@/services/qcompass/visualizer";
import type { VisualizationTimeline } from "@/lib/domains/types";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/domains/$domain/visualizer/$id")({
  loader: ({ params }) => ({ domain: resolveDomain(params.domain) }),
  component: VisualizerDetail,
  head: ({ loaderData, params }) => ({
    meta: [{ title: `${loaderData?.domain.label} · ${params.id} viz — QCompass` }],
  }),
});

function VisualizerDetail() {
  const { domain } = Route.useLoaderData();
  const { id } = Route.useParams();
  const [tl, setTl] = useState<VisualizationTimeline | null>(null);

  useEffect(() => {
    getVisualization(domain.id, id).then(setTl).catch(() => setTl(null));
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
            Rich 3D / Recharts panels land in the depth pass. The data path
            is exercised end-to-end.
          </p>
        </Card>
      )}
    </DomainShell>
  );
}
