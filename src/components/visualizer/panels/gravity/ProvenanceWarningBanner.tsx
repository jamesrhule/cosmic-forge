/**
 * Provenance-warning banner for learned-Hamiltonian gravity runs.
 *
 * PROMPT 9 v2 §A mandates this banner be surfaced PROMINENTLY
 * whenever ``is_learned_hamiltonian`` is true. The styling is
 * intentionally loud (amber border + bold "Learned Hamiltonian"
 * heading) so reviewers can't miss it during audit.
 */

import type { GravityFrame } from "../types";

interface Props {
  frame: GravityFrame | undefined;
}

export function ProvenanceWarningBanner({ frame }: Props) {
  if (!frame) return null;
  if (!frame.is_learned_hamiltonian) {
    return (
      <div className="text-xs text-muted-foreground">
        First-principles Hamiltonian (model_domain: {frame.model_domain}).
      </div>
    );
  }
  return (
    <div
      role="alert"
      className="border-2 border-amber-500 bg-amber-50 dark:bg-amber-950/30 rounded p-3 space-y-2"
    >
      <div className="font-bold text-amber-900 dark:text-amber-200">
        ⚠ Learned Hamiltonian — interpret with caution
      </div>
      {frame.provenance_warning ? (
        <div className="text-xs text-amber-900 dark:text-amber-100">
          {frame.provenance_warning}
        </div>
      ) : null}
      <div className="text-[10px] text-amber-700 dark:text-amber-300">
        model_domain: {frame.model_domain}
      </div>
    </div>
  );
}

export default ProvenanceWarningBanner;
