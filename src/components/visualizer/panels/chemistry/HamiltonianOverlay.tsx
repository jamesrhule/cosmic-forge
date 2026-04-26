import type { ChemistryFrame } from "@/types/manifest";
import { Math } from "@/components/math";

export interface HamiltonianOverlayProps {
  frame: ChemistryFrame | null;
}

export function HamiltonianOverlay({ frame }: HamiltonianOverlayProps) {
  const terms = frame?.hamiltonian_terms ?? [];
  const active = new Set(frame?.active_terms ?? []);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        Active Hamiltonian terms
      </div>
      <div className="min-h-0 flex-1 space-y-2 overflow-auto p-3">
        {terms.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
          terms.map((t) => {
            const isActive = active.has(t.label);
            return (
              <div
                key={t.label}
                className={
                  "rounded-md border px-2.5 py-2 text-xs " +
                  (isActive ? "border-primary/60 bg-primary/5" : "bg-muted/30")
                }
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-mono text-[11px] uppercase tracking-wide">
                    {t.label}
                  </span>
                  <span className="font-mono tabular-nums text-muted-foreground">
                    {t.coefficient.toFixed(4)}
                  </span>
                </div>
                <div className="mt-1">
                  <Math tex={t.operator} />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
