import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DomainShell, resolveDomain } from "@/components/domain-shell";
import { getRun } from "@/services/qcompass/runs";
import { DomainResult } from "@/components/results/DomainResult";
import type { DomainRunResult } from "@/lib/domains/types";
import { SyntheticBadge } from "@/components/qcompass/synthetic-badge";

export const Route = createFileRoute("/domains/$domain/runs/$id")({
  // Return only serialisable data: the plugin object (components, schemas)
  // can't cross the SSR dehydration boundary (P0-05).
  loader: ({ params }) => {
    const plugin = resolveDomain(params.domain);
    return { domainId: plugin.id, label: plugin.label };
  },
  component: RunDetailPage,
  head: ({ loaderData, params }) => ({
    meta: [{ title: `${loaderData?.label} · ${params.id} — QCompass` }],
  }),
});

function RunDetailPage() {
  const domain = resolveDomain(Route.useLoaderData().domainId);
  const { id } = Route.useParams();
  const [run, setRun] = useState<DomainRunResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getRun(domain.id, id)
      .then(setRun)
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : String(e)));
  }, [domain.id, id]);

  return (
    <DomainShell domain={domain} active="runs">
      {err && <p className="text-sm text-destructive">{err}</p>}
      {!run && !err && <p className="text-xs text-muted-foreground">Loading run…</p>}
      {run && (
        <header className="mb-4 flex flex-wrap items-center gap-2" data-testid="run-detail-header">
          <span className="text-sm font-medium">{run.label}</span>
          <code className="text-xs text-muted-foreground">{run.id}</code>
          {run.synthetic && <SyntheticBadge />}
        </header>
      )}
      {run && <DomainResult domainId={domain.id} run={run} />}
    </DomainShell>
  );
}
