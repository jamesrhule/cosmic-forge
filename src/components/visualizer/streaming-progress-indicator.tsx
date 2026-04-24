import { cn } from "@/lib/utils";
import type { StreamStatus } from "@/hooks/useVisualizationStream";

export interface StreamingProgressIndicatorProps {
  status: StreamStatus;
  framesReceived: number;
  framesExpected: number | null;
  className?: string;
}

interface StatusVisual {
  label: string;
  /** Inline background color for the status dot. */
  dotColor: string;
  /** Add `animate-status-pulse` while active. */
  pulse: boolean;
  /** Inline background color for the determinate fill bar. */
  fillColor: string;
}

const STATUS_VISUAL: Record<StreamStatus, StatusVisual> = {
  idle: {
    label: "Idle",
    dotColor: "color-mix(in oklab, var(--color-muted-foreground) 40%, transparent)",
    pulse: false,
    fillColor: "var(--color-muted-foreground)",
  },
  connecting: {
    label: "Connecting…",
    dotColor: "var(--color-chart-4)",
    pulse: true,
    fillColor: "var(--color-chart-4)",
  },
  streaming: {
    label: "Streaming",
    dotColor: "var(--color-primary)",
    pulse: true,
    fillColor: "var(--color-primary)",
  },
  complete: {
    label: "Complete",
    dotColor: "var(--color-verdict-pass)",
    pulse: false,
    fillColor: "var(--color-verdict-pass)",
  },
  error: {
    label: "Stream failed",
    dotColor: "var(--color-verdict-fail)",
    pulse: false,
    fillColor: "var(--color-verdict-fail)",
  },
  cancelled: {
    label: "Cancelled",
    dotColor: "color-mix(in oklab, var(--color-muted-foreground) 60%, transparent)",
    pulse: false,
    fillColor: "var(--color-muted-foreground)",
  },
};

/**
 * Compact streaming progress pill for the visualizer header.
 *
 * Shows a status dot, a determinate progress bar (or indeterminate
 * shimmer when the upstream can't tell us a denominator yet), and a
 * tabular-nums "received / expected" counter.
 *
 * Renders nothing in `idle` state with zero frames so the header chrome
 * stays quiet until the user actually starts the stream.
 */
export function StreamingProgressIndicator({
  status,
  framesReceived,
  framesExpected,
  className,
}: StreamingProgressIndicatorProps) {
  if (status === "idle" && framesReceived === 0) return null;

  const visual = STATUS_VISUAL[status];
  const pct =
    framesExpected && framesExpected > 0
      ? Math.min(100, Math.round((framesReceived / framesExpected) * 100))
      : null;
  const indeterminate = pct === null && (status === "connecting" || status === "streaming");

  const counterText =
    framesExpected != null
      ? `${framesReceived} / ${framesExpected}`
      : `${framesReceived}`;

  // Screen-reader-friendly summary; drives aria-live announcements.
  const srSummary =
    framesExpected != null
      ? `${visual.label}: ${framesReceived} of ${framesExpected} frames received`
      : `${visual.label}: ${framesReceived} frames received`;

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label={srSummary}
      className={cn(
        "inline-flex h-8 items-center gap-2 rounded-md border border-border bg-card/60 px-2",
        className,
      )}
      data-testid="streaming-progress-indicator"
    >
      <span className="inline-flex items-center gap-1.5">
        <span
          aria-hidden="true"
          className={cn("h-1.5 w-1.5 rounded-full", visual.pulse && "animate-status-pulse")}
          style={{ backgroundColor: visual.dotColor }}
        />
        <span className="text-[11px] font-medium text-foreground">{visual.label}</span>
      </span>

      <div
        aria-hidden="true"
        className="relative h-1.5 w-24 overflow-hidden rounded-full bg-muted"
      >
        {indeterminate ? (
          <div className="stream-shimmer absolute inset-0 rounded-full" />
        ) : (
          <div
            className="h-full rounded-full transition-[width] duration-150 ease-out"
            style={{
              width: `${pct ?? 0}%`,
              backgroundColor: visual.fillColor,
            }}
          />
        )}
      </div>

      <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
        {counterText}
      </span>
    </div>
  );
}
