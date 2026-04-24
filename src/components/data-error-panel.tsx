import { AlertTriangle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DataErrorPanelProps {
  /** Headline mirrors the toast title. */
  title: string;
  /** Plain-English explanation; same string passed to the toast description. */
  description: string;
  /** Renders a Retry button when provided. */
  onRetry?: () => void;
  /** Optional secondary CTA (e.g. "Back to runs"). */
  secondaryAction?: React.ReactNode;
  /** Compact layout for narrow split-screen panes. */
  dense?: boolean;
  className?: string;
}

/**
 * Inline placeholder for any surface whose fixture-backed data failed to
 * load or validate. Sibling to `EmptyPanel` — same neutral chrome but a
 * destructive accent and an explicit retry affordance so the user is
 * never left staring at a blank chart.
 */
export function DataErrorPanel({
  title,
  description,
  onRetry,
  secondaryAction,
  dense = false,
  className,
}: DataErrorPanelProps) {
  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        "flex h-full w-full flex-col items-center justify-center gap-2 rounded-md border border-dashed border-destructive/40 bg-destructive/5 text-center",
        dense ? "p-3" : "p-6",
        className,
      )}
    >
      <AlertTriangle
        aria-hidden="true"
        className={cn("text-destructive/80", dense ? "h-3.5 w-3.5" : "h-5 w-5")}
      />
      <p className={cn("font-medium text-foreground", dense ? "text-xs" : "text-sm")}>
        {title}
      </p>
      <p
        className={cn(
          "max-w-prose text-muted-foreground",
          dense ? "text-[10px] leading-tight" : "text-xs",
        )}
      >
        {description}
      </p>
      {(onRetry || secondaryAction) && (
        <div className={cn("mt-1 flex items-center gap-2", dense && "mt-0.5")}>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className={cn(
                "inline-flex items-center gap-1 rounded-md border border-border bg-background font-medium hover:bg-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                dense ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs",
              )}
            >
              <RefreshCw aria-hidden="true" className={dense ? "h-2.5 w-2.5" : "h-3 w-3"} />
              Retry
            </button>
          )}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}
