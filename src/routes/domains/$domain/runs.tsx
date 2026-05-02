import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DomainShell, resolveDomain } from "@/components/domain-shell";
import { listRuns } from "@/services/qcompass/runs";
import type { RunSummary } from "@/lib/domains/types";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const Route = createFileRoute("/domains/$domain/runs")({
  loader: ({ params }) => ({ domain: resolveDomain(params.domain) }),
  component: RunsPage,
  head: ({ loaderData }) => ({
    meta: [{ title: `${loaderData?.domain.label} · Runs — QCompass` }],
  }),
});

function RunsPage() {
  const { domain } = Route.useLoaderData();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  useEffect(() => {
    listRuns(domain.id).then(setRuns).catch(() => setRuns([]));
  }, [domain.id]);

  return (
    <DomainShell domain={domain} active="runs">
      {runs.length === 0 ? (
        <p className="text-sm text-muted-foreground">No runs yet.</p>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {runs.map((r) => (
            <li key={r.id}>
              <Link
                to="/domains/$domain/runs/$id"
                params={{ domain: domain.id, id: r.id }}
                className="block focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <Card className="space-y-1 p-3 hover:bg-accent">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{r.label}</span>
                    <Badge variant="outline">{r.status}</Badge>
                  </div>
                  {r.summary && (
                    <p className="text-xs text-muted-foreground">{r.summary}</p>
                  )}
                  <code className="text-[10px] text-muted-foreground">{r.id}</code>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </DomainShell>
  );
}
