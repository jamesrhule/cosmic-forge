/**
 * Particle-research observables table (PROMPT 7 v2 §"PARTICLE-RESEARCH UI HOOK").
 *
 * Renders the per-frame `particle_obs` block with units, value,
 * uncertainty, and a "compare to literature" affordance that
 * fetches `public/fixtures/literature/lattice-qcd-references.json`
 * and surfaces the matching observable's reference value.
 */

import { useEffect, useState } from "react";
import type { HepFrame, ParticleObservable } from "../types";

interface LiteratureEntry {
  system: string;
  value: number;
  uncertainty: number;
  unit: string;
  method: string;
  reference: string;
}

interface LiteratureBundle {
  schema_version: number;
  description: string;
  observables: Record<string, LiteratureEntry>;
}

interface Props {
  frame: HepFrame | undefined;
  literatureUrl?: string;
}

export function ParticleObservablesTable({
  frame,
  literatureUrl = "/fixtures/literature/lattice-qcd-references.json",
}: Props) {
  const [literature, setLiterature] = useState<LiteratureBundle | null>(null);
  const [showCompare, setShowCompare] = useState(false);

  useEffect(() => {
    if (!showCompare || literature) return;
    let cancelled = false;
    fetch(literatureUrl)
      .then((r) => (r.ok ? r.json() : Promise.reject(r)))
      .then((data) => {
        if (!cancelled) setLiterature(data as LiteratureBundle);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [showCompare, literature, literatureUrl]);

  const entries: Array<[string, ParticleObservable]> = Object.entries(
    frame?.particle_obs ?? {},
  );

  return (
    <div className="space-y-2 text-sm">
      <div className="flex items-center justify-between">
        <div className="font-medium">Particle observables</div>
        <button
          type="button"
          onClick={() => setShowCompare((s) => !s)}
          className="text-xs px-2 py-1 rounded border hover:bg-muted"
        >
          {showCompare ? "Hide literature" : "Compare to literature"}
        </button>
      </div>
      {entries.length === 0 ? (
        <div className="text-xs text-muted-foreground">
          No particle_obs for this frame.
        </div>
      ) : (
        <table className="w-full text-xs">
          <thead className="text-muted-foreground">
            <tr>
              <th className="text-left">observable</th>
              <th className="text-left">value</th>
              <th className="text-left">unit</th>
              <th className="text-left">uncertainty</th>
              <th className="text-left">status</th>
              {showCompare ? <th className="text-left">literature</th> : null}
            </tr>
          </thead>
          <tbody>
            {entries.map(([name, obs]) => {
              const lit = literature?.observables?.[name];
              return (
                <tr key={name} className="border-t border-border/50">
                  <td className="py-1">{name}</td>
                  <td>{obs.value === null ? "—" : obs.value.toExponential(3)}</td>
                  <td>{obs.unit}</td>
                  <td>{obs.uncertainty === null ? "—" : obs.uncertainty.toExponential(2)}</td>
                  <td>
                    <span
                      className={
                        obs.status === "ok"
                          ? "text-green-600"
                          : "text-amber-600"
                      }
                    >
                      {obs.status}
                    </span>
                  </td>
                  {showCompare ? (
                    <td className="text-xs text-muted-foreground">
                      {lit ? `${lit.value} ± ${lit.uncertainty} ${lit.unit}` : "—"}
                    </td>
                  ) : null}
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {showCompare && literature ? (
        <div className="text-[10px] text-muted-foreground italic">
          {literature.description}
        </div>
      ) : null}
    </div>
  );
}

export default ParticleObservablesTable;
