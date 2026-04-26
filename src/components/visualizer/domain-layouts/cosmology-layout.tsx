import { Link } from "@tanstack/react-router";
import type { VisualizationManifest } from "@/types/manifest";

export interface CosmologyDomainLayoutProps {
  manifest: VisualizationManifest;
}

/**
 * Cosmology layout for the new `/visualizer/$domain/$id` route.
 *
 * The legacy `/visualizer/$runId` path renders the existing 6-panel
 * cosmology surface (PhaseSpace + GBWindow + SGWB + Anomaly +
 * LeptonFlow + Formula). This shim forwards users back there so the
 * cosmology code path stays byte-for-byte identical with the
 * pre-PROMPT-7 build.
 */
export function CosmologyDomainLayout({ manifest }: CosmologyDomainLayoutProps) {
  return (
    <div className="col-span-2 row-span-2 flex items-center justify-center">
      <div className="max-w-md rounded-md border bg-card p-4 text-center text-sm">
        <p className="font-medium">Cosmology runs use the legacy route.</p>
        <p className="mt-1 text-xs text-muted-foreground">
          The full UCGLE-F1 panel surface (phase space, GB window, SGWB,
          anomaly, lepton flow, formula overlay) lives at{" "}
          <code className="font-mono text-[11px]">/visualizer/{manifest.run_id}</code>.
        </p>
        <Link
          to="/visualizer/$runId"
          params={{ runId: manifest.run_id }}
          className="mt-3 inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90"
        >
          Open cosmology visualizer →
        </Link>
      </div>
    </div>
  );
}
