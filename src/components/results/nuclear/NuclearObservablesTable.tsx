/**
 * QCompass — Nuclear observables table (CARVE-OUT 1).
 *
 * Mirror of <ParticleObservablesTable> for the nuclear domain, keyed
 * to the nuclear literature corpus. Adds a <ModelDomainBadge> in the
 * header so reviewers can see at a glance whether a result is a toy
 * or a few-body 3D NCSM run.
 *
 * @example
 *   <NuclearObservablesTable obs={run.particle_obs} modelDomain={run.model_domain} />
 */
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Sci } from "@/components/sci";
import { LiteratureCompareSheet } from "@/components/LiteratureCompareSheet";
import { ModelDomainBadge } from "@/components/ModelDomainBadge";
import type { ParticleObservable } from "@/lib/domains/types";

export interface NuclearObservablesTableProps {
  obs: Record<string, ParticleObservable> | undefined | null;
  modelDomain?: string | null;
}

export function NuclearObservablesTable({ obs, modelDomain }: NuclearObservablesTableProps) {
  const [active, setActive] = useState<{
    name: string;
    o: ParticleObservable;
  } | null>(null);

  const entries = obs ? Object.entries(obs).filter(([, v]) => v !== null && v !== undefined) : [];

  return (
    <>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="font-medium">Nuclear observables</h3>
        <ModelDomainBadge value={modelDomain} />
      </div>

      {entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">No nuclear observables reported.</p>
      ) : (
        <div className="overflow-x-auto rounded border">
          <table className="w-full text-sm" data-testid="nuclear-observables-table">
            <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left">Observable</th>
                <th className="px-3 py-2 text-right">Value ± σ</th>
                <th className="px-3 py-2 text-left">Units</th>
                <th className="px-3 py-2 text-left">Backend</th>
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
      )}

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
          corpus="nuclear"
        />
      )}
    </>
  );
}
