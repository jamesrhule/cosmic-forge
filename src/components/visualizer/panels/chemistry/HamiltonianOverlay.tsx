/**
 * Hamiltonian overlay (chemistry).
 *
 * Merged panel (P0-02): the router-branch term list (label, coefficient,
 * KaTeX operator, highlighted when active) plus the agent-branch context
 * strip (τ, phase, active-term chips, provenance reference). When the
 * frame lists no Hamiltonian terms the active-term chips stand alone.
 */
import type { ChemistryFrame } from "../types";
import { Math as TeX } from "@/components/math";
import { PanelShell } from "../PanelShell";

export interface HamiltonianOverlayProps {
  frame: ChemistryFrame | null;
  manifestSummary?: string;
}

export function HamiltonianOverlay({ frame, manifestSummary }: HamiltonianOverlayProps) {
  const terms = frame?.hamiltonian_terms ?? [];
  const activeList = frame?.active_terms ?? [];
  const active = new Set(activeList);

  return (
    <PanelShell
      title="Active Hamiltonian terms"
      empty={!frame}
      bodyClassName="space-y-2 overflow-auto p-3"
      caption={frame?.provenance_ref ? <>provenance: {frame.provenance_ref}</> : null}
    >
      <div className="text-[11px] text-muted-foreground">
        τ = {(frame?.tau ?? 0).toFixed(2)} · phase: {frame?.phase || "—"}
        {manifestSummary ? <> · {manifestSummary}</> : null}
      </div>
      {terms.length === 0 ? (
        <div className="flex flex-wrap gap-1 text-xs">
          {activeList.length === 0 ? (
            <span className="text-muted-foreground">no active terms</span>
          ) : (
            activeList.map((t) => (
              <span key={t} className="rounded bg-muted px-2 py-0.5 font-mono text-[11px]">
                {t}
              </span>
            ))
          )}
        </div>
      ) : (
        terms.map((t) => (
          <div
            key={t.label}
            className={
              "rounded-md border px-2.5 py-2 text-xs " +
              (active.has(t.label) ? "border-primary/60 bg-primary/5" : "bg-muted/30")
            }
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-mono text-[11px] uppercase tracking-wide">{t.label}</span>
              <span className="font-mono tabular-nums text-muted-foreground">{t.coefficient.toFixed(4)}</span>
            </div>
            {t.operator ? (
              <div className="mt-1">
                <TeX tex={t.operator} />
              </div>
            ) : null}
          </div>
        ))
      )}
    </PanelShell>
  );
}

export default HamiltonianOverlay;
