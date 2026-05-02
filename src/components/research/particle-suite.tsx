/**
 * QCompass — Particle suite research view.
 *
 * Aggregates `qcompass-bench --suite particle` rows across HEP and
 * nuclear, rendering a leaderboard + literature-comparison heatmap.
 * Shared by the HEP and Nuclear Research routes.
 *
 * @example
 *   <ParticleSuite />
 */
import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Sci } from "@/components/sci";
import { loadFixture } from "@/lib/fixtures";

interface SuiteRow {
  domain: string;
  run_id: string;
  observable: string;
  value: number;
  uncertainty: number;
  reference_value: number;
  sigma: number;
}

interface SuitePayload {
  suite: string;
  generated_at: string;
  rows: SuiteRow[];
}

function sigmaCellTone(s: number): string {
  if (s < 1) return "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300";
  if (s < 2) return "bg-amber-500/15 text-amber-700 dark:text-amber-300 [background-image:repeating-linear-gradient(45deg,transparent,transparent_3px,rgb(0_0_0/0.06)_3px,rgb(0_0_0/0.06)_6px)]";
  return "bg-red-500/15 text-red-700 dark:text-red-300 [background-image:repeating-linear-gradient(135deg,transparent,transparent_2px,rgb(0_0_0/0.1)_2px,rgb(0_0_0/0.1)_4px)]";
}

export function ParticleSuite() {
  const [data, setData] = useState<SuitePayload | null>(null);

  useEffect(() => {
    loadFixture<SuitePayload>("benchmarks/particle-suite.json").then(setData);
  }, []);

  if (!data) {
    return <p className="text-xs text-muted-foreground">Loading particle suite…</p>;
  }

  // Heatmap rows: observables; cols: backend (here approximated by domain).
  const observables = Array.from(new Set(data.rows.map((r) => r.observable)));
  const domains = Array.from(new Set(data.rows.map((r) => r.domain)));

  return (
    <section className="space-y-4" data-testid="particle-suite">
      <header>
        <h2 className="font-medium">Particle suite — cross-domain leaderboard</h2>
        <p className="text-xs text-muted-foreground">
          Generated {new Date(data.generated_at).toLocaleString()}
        </p>
      </header>

      <Card className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-3 py-2 text-left">Domain · Run</th>
              <th className="px-3 py-2 text-left">Observable</th>
              <th className="px-3 py-2 text-right">Measured</th>
              <th className="px-3 py-2 text-right">Reference</th>
              <th className="px-3 py-2 text-right">σ</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r) => (
              <tr key={`${r.domain}-${r.run_id}-${r.observable}`} className="border-t">
                <td className="px-3 py-2 font-mono text-xs">
                  {r.domain}
                  <span className="text-muted-foreground"> · {r.run_id}</span>
                </td>
                <td className="px-3 py-2">{r.observable}</td>
                <td className="px-3 py-2 text-right font-mono">
                  <Sci value={r.value} /> ± <Sci value={r.uncertainty} />
                </td>
                <td className="px-3 py-2 text-right font-mono">
                  <Sci value={r.reference_value} />
                </td>
                <td className="px-3 py-2 text-right">
                  <Badge variant="outline" className={`font-mono text-[10px] ${sigmaCellTone(r.sigma)}`}>
                    {r.sigma.toFixed(2)}σ
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card className="overflow-x-auto p-3">
        <h3 className="mb-2 text-sm font-medium">Literature-comparison heatmap</h3>
        <table className="text-xs">
          <thead>
            <tr>
              <th className="px-2 py-1 text-left text-muted-foreground">Observable \\ Domain</th>
              {domains.map((d) => (
                <th key={d} className="px-2 py-1 text-left font-mono text-muted-foreground">
                  {d}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {observables.map((obs) => (
              <tr key={obs}>
                <td className="px-2 py-1 font-mono">{obs}</td>
                {domains.map((d) => {
                  const cell = data.rows.find((r) => r.domain === d && r.observable === obs);
                  return (
                    <td key={d} className="px-2 py-1">
                      {cell ? (
                        <span
                          className={`inline-block rounded px-2 py-0.5 font-mono ${sigmaCellTone(cell.sigma)}`}
                          title={`${cell.run_id}: ${cell.sigma.toFixed(2)}σ`}
                        >
                          {cell.sigma.toFixed(2)}σ
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </section>
  );
}
