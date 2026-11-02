/**
 * Learned-Hamiltonian provenance guard for the gravity visualizer.
 *
 * Adapter over the app-wide `@/components/ProvenanceWarningBanner`
 * (one banner per concept, R20). R18: when any frame of the run is a
 * learned Hamiltonian the warning is shown above the panels, and if the
 * warning text is missing the panels are NOT rendered at all.
 */
import type { ReactNode } from "react";
import { ProvenanceWarningBanner as Banner } from "@/components/ProvenanceWarningBanner";
import type { GravityFrame } from "../types";

/** The run is learned if any frame says so; the first warning text found is used. */
export function learnedProvenance(frames: GravityFrame[]): {
  learned: boolean;
  warning: string | null;
} {
  const learned = frames.filter((f) => f.is_learned_hamiltonian);
  const warning =
    learned.map((f) => f.provenance_warning).find((w): w is string => !!w && w.trim() !== "") ??
    null;
  return { learned: learned.length > 0, warning };
}

export interface ProvenanceWarningBannerProps {
  frames: GravityFrame[];
  /** Panels to render once provenance is acceptable. */
  children?: ReactNode;
}

export function ProvenanceWarningBanner({ frames, children }: ProvenanceWarningBannerProps) {
  const { learned, warning } = learnedProvenance(frames);
  const modelDomain = frames[0]?.model_domain;
  if (!learned) {
    return (
      <>
        {modelDomain ? (
          <div className="text-xs text-muted-foreground" data-testid="gravity-first-principles">
            First-principles Hamiltonian (model_domain: {modelDomain}).
          </div>
        ) : null}
        {children}
      </>
    );
  }
  if (!warning) {
    return (
      <div
        role="alert"
        data-testid="gravity-provenance-blocked"
        className="rounded-md border-2 border-destructive p-4 text-sm"
      >
        <p className="font-semibold text-destructive">
          Render blocked — learned Hamiltonian without a provenance warning.
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          This run is flagged <code>is_learned_hamiltonian</code> but carries no{" "}
          <code>provenance_warning</code>, so its panels are withheld.
        </p>
      </div>
    );
  }
  return (
    <>
      <Banner warning={warning} />
      {children}
    </>
  );
}

export default ProvenanceWarningBanner;
