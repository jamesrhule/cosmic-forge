import { cn } from "@/lib/utils";

export interface BogoliubovGaugeProps {
  drift: number;
  tolerance?: number;
  className?: string;
}

export function BogoliubovGauge({
  drift,
  tolerance = 1e-3,
  className,
}: BogoliubovGaugeProps) {
  const pct = Math.min(100, (Math.abs(drift) / tolerance) * 100);
  const status: "ok" | "warn" | "fail" =
    pct < 60 ? "ok" : pct < 90 ? "warn" : "fail";
  const color =
    status === "ok"
      ? "bg-[color:var(--color-verdict-pass)]"
      : status === "warn"
        ? "bg-[color:var(--color-status-canceled)]"
        : "bg-[color:var(--color-verdict-fail)]";
  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span>Bogoliubov drift</span>
        <span className="font-mono">
          {drift.toExponential(2)} / {tolerance.toExponential(0)}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded bg-muted">
        <div
          className={cn("h-full transition-all", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
