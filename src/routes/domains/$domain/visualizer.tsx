import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DomainShell, resolveDomain } from "@/components/domain-shell";
import { listRuns } from "@/services/qcompass/runs";
import type { RunSummary } from "@/lib/domains/types";
import { Card } from "@/components/ui/card";

export const Route = createFileRoute("/domains/$domain/visualizer")({
  loader: ({ params }) => ({ domain: resolveDomain(params.domain) }),
  component: VisualizerIndex,
  head: ({ loaderData }) => ({
    meta: [{ title: `${loaderData?.domain.label} · Visualizer — QCompass` }],
  }),
});

function VisualizerIndex() {
  const { domain } = Route.useLoaderData();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  useEffect(() => {
    listRuns(domain.id).then(setRuns).catch(() => setRuns([]));
  }, [domain.id]);

  return (
    <DomainShell domain={domain} active="visualizer">
      <p className="mb-3 text-sm text-muted-foreground">Pick a run to visualize.</p>
      <ul className="grid gap-2 sm:grid-cols-2">
        {runs.map((r) => (
          <li key={r.id}>
            <Link
              to="/domains/$domain/visualizer/$id"
              params={{ domain: domain.id, id: r.id }}
            >
              <Card className="p-3 hover:bg-accent">
                <div className="font-medium">{r.label}</div>
                <code className="text-[10px] text-muted-foreground">{r.id}</code>
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </DomainShell>
  );
}
