import { Clock } from "lucide-react";
import type { Precision, RunConfig } from "@/types/domain";

const BASE_MIN: Record<Precision, number> = {
  fast: 4,
  standard: 18,
  high: 95,
};

/**
 * Deterministic estimated CPU-minute cost. The real backend will return
 * a calibrated estimate from a benchmarking table; this is a stable
 * mock that depends only on precision + a couple of couplings so the
 * badge moves visibly when the user edits the form.
 */
export function estimateCost(config: RunConfig): number {
  const base = BASE_MIN[config.precision];
  const xi = Math.max(config.couplings.xi, 1e-6);
  const mult = 1 + 0.3 * Math.log10(1 + xi * 1e3);
  return Math.max(1, Math.round(base * mult));
}

export function CostBadge({ config }: { config: RunConfig }) {
  const minutes = estimateCost(config);
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border bg-card px-3 py-1 text-xs">
      <Clock className="h-3 w-3 text-muted-foreground" aria-hidden />
      <span className="font-medium">~{minutes}</span>
      <span className="text-muted-foreground">CPU·min</span>
    </span>
  );
}
