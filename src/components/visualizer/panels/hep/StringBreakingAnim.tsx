import type { HepFrame } from "@/types/manifest";

export interface StringBreakingAnimProps {
  frame: HepFrame | null;
}

/**
 * Compact string-tension readout. The full motion-driven animation
 * (a quark-pair separation tube that fades to a meson pair when
 * tension drops below threshold) is the planned `motion`-backed
 * upgrade; the baseline view is a numeric trace + tension bar so
 * the panel is non-empty while string_tension data is available.
 */
export function StringBreakingAnim({ frame }: StringBreakingAnimProps) {
  const tension = frame?.string_tension ?? 0;
  const phaseStr = frame?.phase ?? "—";
  const broken = phaseStr === "string_break";

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        String tension / breaking
      </div>
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 p-3">
        {!frame ? (
          <div className="text-xs text-muted-foreground">no data</div>
        ) : (
          <>
            <div className="font-mono text-2xl tabular-nums">{tension.toFixed(3)}</div>
            <div className="text-[11px] text-muted-foreground">
              phase: <span className="font-mono">{phaseStr}</span>
            </div>
            <div className="h-2 w-3/4 overflow-hidden rounded-full bg-muted">
              <div
                className={
                  "h-full transition-all " +
                  (broken ? "bg-amber-500" : "bg-primary")
                }
                style={{ width: `${Math.min(100, Math.max(0, tension * 200))}%` }}
              />
            </div>
            {broken ? (
              <div className="rounded-md bg-amber-500/10 px-2 py-1 text-[11px] text-amber-700 dark:text-amber-400">
                string breaking event
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
