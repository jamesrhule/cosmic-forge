/**
 * QCompass — HEP particle observables table (CARVE-OUT 1).
 *
 * Renders the `particle_obs` dict from a HEP RunResult. Each row has
 * a [Compare to literature] button that opens a side Sheet with the
 * lattice-QCD literature corpus.
 *
 * @example
 *   <ParticleObservablesTable obs={run.particle_obs} />
 */
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Sci } from "@/components/sci";
import { LiteratureCompareSheet } from "@/components/LiteratureCompareSheet";
import type { ParticleObservable } from "@/lib/domains/types";

export interface ParticleObservablesTableProps {
  obs: Record<string, ParticleObservable> | undefined | null;
}

export function ParticleObservablesTable({ obs }: ParticleObservablesTableProps) {
  const [active, setActive] = useState<{
    name: string;
    o: ParticleObservable;
  } | null>(null);

  const entries = obs ? Object.entries(obs).filter(([, v]) => v !== null && v !== undefined) : [];

  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No particle observables reported.</p>
    );
  }

  return (
    <>
      <div className="overflow-x-auto rounded border">
        <table className="w-full text-sm" data-testid="particle-observables-table">
          <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
            <tr>
              <th className="px-3 py-2 text-left">Observable</th>
              <th className="px-3 py-2 text-right">Value ± σ</th>
              <th className="px-3 py-2 text-left">Units</th>
              <th className="px-3 py-2 text-left">Backend</th>
              <th className="px-3 py-2 text-left">Calibration</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([name, o]) => (
              <tr key={name} className="border-t">
                <td className="px-3 py-2">
                  <div className="font-medium">{name}</div>
                  <code className="text-[11px] text-muted-foreground">{o.label}</code>
                </td>
                <td className="px-3 py-2 text-right font-mono">
                  <Sci value={o.value} /> ± <Sci value={o.uncertainty} />
                </td>
                <td className="px-3 py-2 font-mono text-xs">{o.units}</td>
                <td className="px-3 py-2 text-xs">
                  {o.provider}
                  <span className="text-muted-foreground"> / {o.backend}</span>
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground">
                  {new Date(o.calibration_at).toISOString().slice(0, 16).replace("T", " ")}Z
                </td>
                <td className="px-3 py-2 text-right">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setActive({ name, o })}
                    data-testid={`compare-literature-${name}`}
                  >
                    Compare to literature
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {active && (
        <LiteratureCompareSheet
          open={!!active}
          onOpenChange={(o) => !o && setActive(null)}
          observable={active.name}
          observableLabel={active.o.label}
          measured={{
            value: active.o.value,
            uncertainty: active.o.uncertainty,
            units: active.o.units,
          }}
          corpus="lattice-qcd"
        />
      )}
    </>
  );
}
