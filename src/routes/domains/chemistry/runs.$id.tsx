import { useEffect, useState } from "react";
import { createFileRoute, useParams, Link } from "@tanstack/react-router";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EnergyComparisonCard } from "@/components/qcompass/energy-comparison-card";
import { ProvenancePanel } from "@/components/qcompass/provenance-panel";
import {
  getChemistryRun,
  streamChemistryRun,
} from "@/services/qcompass/chemistry";
import type {
  ChemistryRunEvent,
  ChemistryRunResult,
} from "@/types/qcompass";

export const Route = createFileRoute("/domains/chemistry/runs/$id")({
  component: ChemistryRunDetail,
});

function ChemistryRunDetail() {
  const { id } = useParams({ from: "/domains/chemistry/runs/$id" });
  const [run, setRun] = useState<ChemistryRunResult | null>(null);
  const [events, setEvents] = useState<ChemistryRunEvent[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getChemistryRun(id)
      .then((r) => {
        if (!cancelled) setRun(r);
      })
      .catch((e) => setError(String(e)));
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        for await (const ev of streamChemistryRun(id)) {
          if (cancelled) break;
          setEvents((prev) => [...prev, ev]);
        }
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <div className="space-y-6">
      <Header runId={id} run={run} />
      {error && (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      )}
      {!run ? (
        <p className="text-sm text-muted-foreground">Loading run…</p>
      ) : (
        <>
          <EnergyComparisonCard energies={run.energies} />
          <ProvenancePanel
            provenance={run.provenance}
            warning={run.provenance_warning}
          />
          <ManifestCard run={run} />
          <EventsCard events={events} />
        </>
      )}
    </div>
  );
}

function Header({
  runId,
  run,
}: {
  runId: string;
  run: ChemistryRunResult | null;
}) {
  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">
          Run <span className="font-mono text-base">{runId}</span>
        </h1>
        {run && (
          <Badge variant="outline" className="text-[11px]">
            {run.pathTaken}
          </Badge>
        )}
      </div>
      <p className="text-sm text-muted-foreground">
        <Link
          to="/domains/chemistry/runs"
          className="text-[color:var(--accent-indigo)] underline"
        >
          ← All chemistry runs
        </Link>
      </p>
    </section>
  );
}

function ManifestCard({ run }: { run: ChemistryRunResult }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Manifest</CardTitle>
      </CardHeader>
      <CardContent>
        <pre className="overflow-auto rounded-md bg-muted/40 p-3 font-mono text-[11px]">
          {JSON.stringify(run.manifest, null, 2)}
        </pre>
      </CardContent>
    </Card>
  );
}

function EventsCard({ events }: { events: ChemistryRunEvent[] }) {
  if (events.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Run events</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-1 font-mono text-[11px]">
          {events.map((ev, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-muted-foreground">{ev.type}</span>
              <span>{describeEvent(ev)}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function describeEvent(ev: ChemistryRunEvent): string {
  switch (ev.type) {
    case "status":
      return ev.status;
    case "log":
      return `[${ev.level}] ${ev.text}`;
    case "metric":
      return `${ev.name} = ${ev.value}${ev.unit ? ` ${ev.unit}` : ""}`;
    case "result":
      return `result for ${ev.payload.id}`;
    default:
      return JSON.stringify(ev);
  }
}
