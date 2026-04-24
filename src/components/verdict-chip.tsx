import type { AuditVerdict } from "@/types/domain";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const STYLES: Record<AuditVerdict, { bg: string; text: string; label: string; ring: string }> = {
  PASS_R: {
    bg: "bg-[color:var(--color-verdict-pass)]",
    text: "text-white",
    label: "PASS·R",
    ring: "ring-[color:var(--color-verdict-pass)]/30",
  },
  PASS_P: {
    bg: "bg-[color:var(--color-verdict-pass)]/85",
    text: "text-white",
    label: "PASS·P",
    ring: "ring-[color:var(--color-verdict-pass)]/30",
  },
  PASS_S: {
    bg: "bg-[color:var(--color-verdict-pass)]/70",
    text: "text-white",
    label: "PASS·S",
    ring: "ring-[color:var(--color-verdict-pass)]/30",
  },
  FAIL: {
    bg: "bg-[color:var(--color-verdict-fail)]",
    text: "text-white",
    label: "FAIL",
    ring: "ring-[color:var(--color-verdict-fail)]/30",
  },
  INAPPLICABLE: {
    bg: "bg-[color:var(--color-verdict-na)]",
    text: "text-white",
    label: "N/A",
    ring: "ring-[color:var(--color-verdict-na)]/30",
  },
};

export interface VerdictChipProps {
  verdict: AuditVerdict;
  id?: string;
  name?: string;
  size?: "sm" | "md";
  className?: string;
}

export function VerdictChip({ verdict, id, name, size = "md", className }: VerdictChipProps) {
  const s = STYLES[verdict];
  const chip = (
    <span
      className={cn(
        "inline-flex items-center justify-center font-mono font-medium tracking-tight",
        size === "sm" ? "h-5 px-1.5 text-[10px]" : "h-6 px-2 text-xs",
        s.bg,
        s.text,
        "rounded ring-1",
        s.ring,
        className,
      )}
    >
      {id ?? s.label}
    </span>
  );
  if (!id && !name) return chip;
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>{chip}</TooltipTrigger>
        <TooltipContent>
          <div className="text-xs">
            <div className="font-medium">{name ?? id}</div>
            <div className="text-muted-foreground">{s.label}</div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
