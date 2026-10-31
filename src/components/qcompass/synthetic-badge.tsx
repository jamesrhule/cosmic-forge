import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/** Exact wording required by PLAN.md correction 8 (R7). */
export const SYNTHETIC_FIXTURE_LABEL = "Synthetic fixture — not a computed result";

/**
 * Shown on run-list rows and the run detail header whenever a run carries
 * `synthetic: true` (R7: synthetic data is always labelled as such).
 */
export function SyntheticBadge({ className }: { className?: string }) {
  return (
    <Badge
      variant="outline"
      data-testid="synthetic-fixture-badge"
      className={cn(
        "border-amber-500/60 bg-amber-500/10 text-amber-800 dark:text-amber-300",
        className,
      )}
    >
      {SYNTHETIC_FIXTURE_LABEL}
    </Badge>
  );
}
