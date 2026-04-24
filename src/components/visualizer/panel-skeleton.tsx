import { cn } from "@/lib/utils";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";

/**
 * Shared loading state for lazy-loaded panel chunks (R3F, Recharts, KaTeX).
 * Renders a subtle pulsing surface so the panel grid never collapses while
 * the matching JS chunk streams in. Honours `prefers-reduced-motion` by
 * dropping the pulse animation in favour of a static bar.
 */
export function PanelSkeleton({
  label,
  className,
}: {
  label?: string;
  className?: string;
}) {
  const reducedMotion = usePrefersReducedMotion();
  return (
    <div
      className={cn(
        "flex h-full w-full items-center justify-center rounded-md border border-dashed bg-muted/30",
        className,
      )}
      aria-busy="true"
      aria-live="polite"
    >
      <div className="flex flex-col items-center gap-2 text-[11px] font-mono text-muted-foreground">
        <div
          className={cn("h-1.5 w-24 rounded bg-muted", !reducedMotion && "animate-pulse")}
        />
        <span>{label ?? "Loading…"}</span>
      </div>
    </div>
  );
}
