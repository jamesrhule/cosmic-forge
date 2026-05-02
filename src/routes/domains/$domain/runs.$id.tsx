import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DomainShell, resolveDomain } from "@/components/domain-shell";
import { getRun } from "@/services/qcompass/runs";
import { DomainResult } from "@/components/results/DomainResult";
import type { DomainRunResult } from "@/lib/domains/types";

export const Route = createFileRoute("/domains/$domain/runs/$id")({
  loader: ({ params }) => ({ domain: resolveDomain(params.domain) }),
  component: RunDetailPage,
  head: ({ loaderData, params }) => ({
    meta: [{ title: `${loaderData?.domain.label} · ${params.id} — QCompass` }],
  }),
});

function RunDetailPage() {
  const { domain } = Route.useLoaderData();
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
      {run && <DomainResult domainId={domain.id} run={run} />}
    </DomainShell>
  );
}
