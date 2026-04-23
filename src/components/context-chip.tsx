import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ContextChipProps {
  kind: string;
  label: string;
  onRemove?: () => void;
  className?: string;
}

export function ContextChip({ kind, label, onRemove, className }: ContextChipProps) {
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center gap-1.5 rounded-full border bg-accent/40 px-2 py-0.5 text-xs",
        className,
      )}
    >
      <span className="font-mono uppercase tracking-tight text-[10px] text-muted-foreground">
        {kind}
      </span>
      <span className="truncate text-foreground">{label}</span>
      {onRemove && (
        <button
          type="button"
          aria-label="Remove context"
          onClick={onRemove}
          className="rounded-full p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </span>
  );
}
