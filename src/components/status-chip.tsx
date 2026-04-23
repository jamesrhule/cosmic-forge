import type { RunStatus } from "@/types/domain";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<RunStatus, string> = {
  queued: "bg-[color:var(--color-status-queued)]/15 text-[color:var(--color-status-queued)]",
  running:
    "bg-[color:var(--color-status-running)]/15 text-[color:var(--color-status-running)] animate-status-pulse",
  completed:
    "bg-[color:var(--color-status-completed)]/15 text-[color:var(--color-status-completed)]",
  failed: "bg-[color:var(--color-status-failed)]/15 text-[color:var(--color-status-failed)]",
  canceled:
    "bg-[color:var(--color-status-canceled)]/15 text-[color:var(--color-status-canceled)]",
};

const STATUS_DOT: Record<RunStatus, string> = {
  queued: "bg-[color:var(--color-status-queued)]",
  running: "bg-[color:var(--color-status-running)]",
  completed: "bg-[color:var(--color-status-completed)]",
  failed: "bg-[color:var(--color-status-failed)]",
  canceled: "bg-[color:var(--color-status-canceled)]",
};

export function StatusChip({
  status,
  className,
}: {
  status: RunStatus;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium",
        STATUS_STYLES[status],
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", STATUS_DOT[status])} />
      {status}
    </span>
  );
}
