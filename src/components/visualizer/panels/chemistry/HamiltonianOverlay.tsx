/**
 * Hamiltonian metadata overlay (provenance + active terms).
 *
 * Surfaces the active_terms list and provenance_ref so callers
 * can render a side-bar that ties each frame back to its
 * ProvenanceRecord. Pure presentational, no charts.
 */

import type { ChemistryFrame } from "../types";

interface Props {
  frame: ChemistryFrame | undefined;
  manifestSummary?: string;
}

export function HamiltonianOverlay({ frame, manifestSummary }: Props) {
  return (
    <div className="space-y-2 text-sm">
      <div className="font-medium">Hamiltonian context</div>
      <div className="text-xs text-muted-foreground">
        τ = {(frame?.tau ?? 0).toFixed(2)} · phase: {frame?.phase ?? "—"}
      </div>
      {manifestSummary ? (
        <div className="text-xs">{manifestSummary}</div>
      ) : null}
      <div className="flex flex-wrap gap-1 text-xs">
        {(frame?.active_terms ?? []).length === 0 ? (
          <span className="text-muted-foreground">no active terms</span>
        ) : (
          (frame?.active_terms ?? []).map((t) => (
            <span key={t} className="px-2 py-0.5 rounded bg-muted">
              {t}
            </span>
          ))
        )}
      </div>
      {frame?.provenance_ref ? (
        <div className="text-xs text-muted-foreground">
          provenance: {frame.provenance_ref}
        </div>
      ) : null}
    </div>
  );
}

export default HamiltonianOverlay;
