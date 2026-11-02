import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { DomainShell, resolveDomain } from "@/components/domain-shell";
import { getRun, streamRun } from "@/services/qcompass/runs";
import { usesApi } from "@/lib/sdk";
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
    let cancelled = false;
    const ctrl = new AbortController();
    const fail = (e: unknown) => {
      if (!cancelled) setErr(e instanceof Error ? e.message : String(e));
    };
    getRun(domain.id, id)
      .then(async (first) => {
        if (cancelled) return;
        setRun(first);
        // An API run still queued or running: follow its events until it
        // ends, then show the stored result (P4-02).
        if (!usesApi() || first.status === "completed" || first.status === "failed") return;
        for await (const ev of streamRun(domain.id, id, ctrl.signal)) {
          if (cancelled) return;
          if (ev.type === "running") setRun((r) => (r ? { ...r, status: "running" } : r));
          else if (ev.type === "result") setRun(ev.payload);
          else if (ev.type === "error") {
            setErr(ev.message);
            setRun(await getRun(domain.id, id));
          }
        }
      })
      .catch(fail);
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [domain.id, id]);

  return (
    <DomainShell domain={domain} active="runs">
      {err && <p className="text-sm text-destructive">{err}</p>}
      {!run && !err && <p className="text-xs text-muted-foreground">Loading run…</p>}
      {run && (
        <header className="mb-4 flex flex-wrap items-center gap-2" data-testid="run-detail-header">
          <span className="text-sm font-medium">{run.label}</span>
          <code className="text-xs text-muted-foreground">{run.id}</code>
          <span
            data-testid="run-status"
            data-status={run.status}
            className="rounded border px-1.5 py-0.5 text-[11px] text-muted-foreground"
          >
            {run.status}
          </span>
          {run.synthetic && <SyntheticBadge />}
        </header>
      )}
      {run && <DomainResult domainId={domain.id} run={run} />}
    </DomainShell>
  );
}
