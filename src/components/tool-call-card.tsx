import { useState } from "react";
import { Check, ChevronRight, Wrench, X } from "lucide-react";
import type { ToolCall, ToolResult } from "@/types/domain";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface ToolCallCardProps {
  call: ToolCall;
  result?: ToolResult;
  onApply?: (call: ToolCall) => void;
}

export function ToolCallCard({ call, result, onApply }: ToolCallCardProps) {
  const [argsOpen, setArgsOpen] = useState(false);
  const [resOpen, setResOpen] = useState(false);
  const ok = result?.ok ?? true;

  return (
    <div className="rounded-md border bg-card text-card-foreground">
      <div className="flex items-center justify-between gap-2 px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          <Wrench className="h-3.5 w-3.5 text-[color:var(--color-accent-indigo)]" />
          <span className="font-mono text-xs">{call.name}</span>
          {result &&
            (ok ? (
              <Check className="h-3.5 w-3.5 text-[color:var(--color-verdict-pass)]" />
            ) : (
              <X className="h-3.5 w-3.5 text-[color:var(--color-verdict-fail)]" />
            ))}
        </div>
        {result && ok && onApply && (
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="h-6 px-2 text-xs"
            onClick={() => onApply(call)}
          >
            Apply
          </Button>
        )}
      </div>
      <Section
        label="arguments"
        open={argsOpen}
        onToggle={() => setArgsOpen((v) => !v)}
      >
        <pre className="overflow-x-auto bg-muted/50 px-3 py-2 font-mono text-[11px] leading-relaxed">
          {JSON.stringify(call.arguments, null, 2)}
        </pre>
      </Section>
      {result && (
        <Section
          label={ok ? "result" : "error"}
          open={resOpen}
          onToggle={() => setResOpen((v) => !v)}
        >
          <pre
            className={cn(
              "overflow-x-auto px-3 py-2 font-mono text-[11px] leading-relaxed",
              ok ? "bg-muted/50" : "bg-destructive/10",
            )}
          >
            {JSON.stringify(result.output, null, 2)}
          </pre>
        </Section>
      )}
    </div>
  );
}

function Section({
  label,
  open,
  onToggle,
  children,
}: {
  label: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border-t">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-1.5 px-3 py-1.5 text-left text-[11px] uppercase tracking-wide text-muted-foreground hover:text-foreground"
      >
        <ChevronRight
          className={cn("h-3 w-3 transition-transform", open && "rotate-90")}
        />
        {label}
      </button>
      {open && children}
    </div>
  );
}
