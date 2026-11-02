import { cn } from "@/lib/utils";

/**
 * R7 label for domain-visualizer frames that are not computed from the run:
 * the API's synthetic bake (`source: "synthetic-bake"`, B2) or a bundled
 * fixture. One component for every domain visualizer, cosmology included.
 */
export function SyntheticFramesLabel({
  source,
  className,
}: {
  source?: unknown;
  className?: string;
}) {
  return (
    <div
      data-testid="synthetic-fixture-label"
      className={cn(
        "rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-700 dark:text-amber-400",
        className,
      )}
    >
      {source === "synthetic-bake"
        ? "Synthetic frames — not a computed result. Real-run timelines arrive with P4-04."
        : "Synthetic fixture — illustrative frames bundled with the app, not a run result."}
    </div>
  );
}
