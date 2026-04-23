import { formatSci } from "@/lib/utils";
import { cn } from "@/lib/utils";

export interface SciProps {
  value: number;
  sig?: number;
  className?: string;
}

export function Sci({ value, sig = 3, className }: SciProps) {
  return (
    <span className={cn("font-mono tabular-nums", className)}>
      {formatSci(value, sig)}
    </span>
  );
}
