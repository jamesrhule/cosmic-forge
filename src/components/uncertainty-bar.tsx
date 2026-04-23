import type { UncertaintyBudget } from "@/types/domain";
import { Sci } from "@/components/sci";
import { cn } from "@/lib/utils";

export interface UncertaintyBarProps {
  budget: UncertaintyBudget;
  className?: string;
}

const SEGMENTS = [
  { key: "statistical", label: "Stat", className: "bg-[color:var(--color-accent-indigo)]" },
  { key: "gridSystematic", label: "Grid", className: "bg-[color:var(--color-accent-indigo)]/75" },
  { key: "schemeSystematic", label: "Scheme", className: "bg-[color:var(--color-accent-indigo)]/55" },
  { key: "inputPropagation", label: "Input", className: "bg-[color:var(--color-accent-indigo)]/35" },
] as const;

export function UncertaintyBar({ budget, className }: UncertaintyBarProps) {
  const total =
    budget.total ||
    SEGMENTS.reduce(
      (sum, s) => sum + (budget[s.key as keyof UncertaintyBudget] as number),
      0,
    );
  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex h-2 overflow-hidden rounded bg-muted">
        {SEGMENTS.map((s) => {
          const v = budget[s.key as keyof UncertaintyBudget] as number;
          const pct = total ? (v / total) * 100 : 0;
          return (
            <div
              key={s.key}
              style={{ width: `${pct}%` }}
              className={cn("h-full transition-all", s.className)}
              title={`${s.label}: ${v.toExponential(2)}`}
            />
          );
        })}
      </div>
      <div className="flex flex-wrap gap-3 text-[11px] text-muted-foreground">
        {SEGMENTS.map((s) => (
          <span key={s.key} className="inline-flex items-center gap-1.5">
            <span className={cn("h-2 w-2 rounded-sm", s.className)} />
            {s.label}{" "}
            <Sci
              value={budget[s.key as keyof UncertaintyBudget] as number}
              sig={2}
            />
          </span>
        ))}
        <span className="ml-auto inline-flex items-center gap-1.5">
          Σ <Sci value={budget.total} sig={2} />
        </span>
      </div>
    </div>
  );
}
