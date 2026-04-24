import { cn } from "@/lib/utils";

export interface EmptyPanelProps {
  title: string;
  /** Why the panel can't render right now. */
  reason: string;
  /** Optional CTA — usually a "Pick a run" button or a link to docs. */
  action?: React.ReactNode;
  className?: string;
  /** Compact mode for narrow split-screen panes. */
  dense?: boolean;
}

/**
 * Neutral placeholder for visualizer panels that have no data to draw.
 * Used when no run is loaded, when the loaded run has no fixture for
 * this panel's source, or when a feature flag suppresses the panel
 * (WebGL fallback, missing snapshot, etc.).
 *
 * Stays out of the way: muted background, single line of explanation,
 * optional action slot.
 */
export function EmptyPanel({
  title,
  reason,
  action,
  className,
  dense = false,
}: EmptyPanelProps) {
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "flex h-full w-full flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border bg-muted/30 text-center",
        dense ? "p-3" : "p-6",
        className,
      )}
    >
      <p
        className={cn(
          "font-medium text-foreground",
          dense ? "text-xs" : "text-sm",
        )}
      >
        {title}
      </p>
      <p
        className={cn(
          "max-w-prose text-muted-foreground",
          dense ? "text-[10px] leading-tight" : "text-xs",
        )}
      >
        {reason}
      </p>
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}
