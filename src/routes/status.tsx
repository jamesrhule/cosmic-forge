/**
 * Public health dashboard. Polls `/api/public/status` every 30s and
 * shows DB / storage probe latency, build version, and any open
 * incidents from the `system_incidents` table.
 *
 * SEO: indexable but lightweight; meaningful for users (and uptime
 * monitors) but not a marketing page.
 */

import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { trackWarn } from "@/lib/telemetry";

interface ProbeResult {
  ok: boolean;
  latencyMs: number;
  message?: string;
}

interface IncidentSummary {
  id: string;
  title: string;
  status: string;
  severity: string;
  startedAt: string;
  resolvedAt: string | null;
}

interface StatusPayload {
  ok: boolean;
  build: { commit: string; builtAt: string };
  checks: { database: ProbeResult; storage: ProbeResult };
  incidents: { open: number; latest: IncidentSummary | null };
  timestamp: string;
}

const POLL_INTERVAL_MS = 30_000;

export const Route = createFileRoute("/status")({
  head: () => ({
    meta: [
      { title: "System status · UCGLE-F1 Workbench" },
      {
        name: "description",
        content:
          "Live health of the UCGLE-F1 Workbench: database, storage, and any open incidents.",
      },
      { property: "og:title", content: "System status · UCGLE-F1 Workbench" },
      {
        property: "og:description",
        content: "Live health of the UCGLE-F1 Workbench backend services.",
      },
    ],
  }),
  component: StatusPage,
});

function StatusPage() {
  const [data, setData] = useState<StatusPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastFetched, setLastFetched] = useState<Date | null>(null);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function probe() {
      try {
        const res = await fetch("/api/public/status", { signal: controller.signal });
        // Both 200 and 503 carry valid JSON; only network failures throw.
        const payload = (await res.json()) as StatusPayload;
        if (cancelled) return;
        setData(payload);
        setError(null);
        setLastFetched(new Date());
      } catch (err) {
        if (cancelled) return;
        const msg = err instanceof Error ? err.message : String(err);
        if (msg.includes("aborted")) return;
        trackWarn("status_probe", msg);
        setError(msg);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void probe();
    const id = window.setInterval(probe, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      controller.abort();
      window.clearInterval(id);
    };
  }, []);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Operations</p>
          <h1 className="mt-1 text-3xl font-semibold">System status</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Live probe of database, storage, and active incidents. Polls every 30s.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link to="/">Back to app</Link>
        </Button>
      </header>

      {loading && !data && (
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            Probing services…
          </CardContent>
        </Card>
      )}

      {error && (
        <Card className="border-destructive/40">
          <CardContent className="py-6 text-sm">
            <p className="font-medium text-destructive">Status endpoint unreachable</p>
            <p className="mt-1 text-muted-foreground">{error}</p>
          </CardContent>
        </Card>
      )}

      {data && (
        <div className="space-y-6">
          <OverallBanner ok={data.ok} incidents={data.incidents.open} />
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base">Service probes</CardTitle>
              {lastFetched && (
                <span className="text-xs text-muted-foreground">
                  Updated {lastFetched.toLocaleTimeString()}
                </span>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              <ProbeRow label="Database" probe={data.checks.database} />
              <ProbeRow label="Storage" probe={data.checks.storage} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Open incidents</CardTitle>
            </CardHeader>
            <CardContent>
              {data.incidents.open === 0 ? (
                <p className="text-sm text-muted-foreground">No open incidents reported.</p>
              ) : data.incidents.latest ? (
                <IncidentRow incident={data.incidents.latest} totalOpen={data.incidents.open} />
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Build</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>
                Commit:{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 text-xs text-foreground">
                  {data.build.commit}
                </code>
              </p>
              <p>Built at: {data.build.builtAt}</p>
            </CardContent>
          </Card>
        </div>
      )}
    </main>
  );
}

function OverallBanner({ ok, incidents }: { ok: boolean; incidents: number }) {
  return (
    <div
      className={cn(
        "rounded-lg border px-4 py-3 text-sm",
        ok
          ? "border-emerald-600/40 bg-emerald-500/10 text-emerald-100"
          : "border-amber-600/40 bg-amber-500/10 text-amber-100",
      )}
      role="status"
      aria-live="polite"
    >
      <strong className="font-semibold">{ok ? "All systems operational" : "Degraded service"}</strong>
      {!ok && incidents > 0 && (
        <span className="ml-2 text-muted-foreground">
          {incidents} open incident{incidents === 1 ? "" : "s"}
        </span>
      )}
    </div>
  );
}

function ProbeRow({ label, probe }: { label: string; probe: ProbeResult }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border bg-card/50 px-3 py-2">
      <div className="flex items-center gap-2">
        <span
          aria-hidden
          className={cn(
            "inline-block h-2.5 w-2.5 rounded-full",
            probe.ok ? "bg-emerald-500" : "bg-destructive",
          )}
        />
        <span className="font-medium">{label}</span>
      </div>
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        {probe.message && <span className="max-w-[16rem] truncate">{probe.message}</span>}
        <span>{probe.latencyMs} ms</span>
        <Badge variant={probe.ok ? "secondary" : "destructive"}>{probe.ok ? "ok" : "down"}</Badge>
      </div>
    </div>
  );
}

function IncidentRow({ incident, totalOpen }: { incident: IncidentSummary; totalOpen: number }) {
  return (
    <div className="space-y-1 text-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">{incident.title}</span>
        <Badge variant={incident.severity === "critical" ? "destructive" : "secondary"}>
          {incident.severity}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground">
        Status: {incident.status} · Started {new Date(incident.startedAt).toLocaleString()}
      </p>
      {totalOpen > 1 && (
        <p className="text-xs text-muted-foreground">
          + {totalOpen - 1} more open incident{totalOpen - 1 === 1 ? "" : "s"}
        </p>
      )}
    </div>
  );
}
