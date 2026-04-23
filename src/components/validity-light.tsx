import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import type { ValidityResult } from "@/lib/validity";

const COLORS: Record<ValidityResult["level"], string> = {
  ok: "var(--color-verdict-pass)",
  warn: "var(--color-status-canceled)",
  error: "var(--color-destructive)",
};

const LABEL: Record<ValidityResult["level"], string> = {
  ok: "Admissible",
  warn: "Unusual",
  error: "Violates constraint",
};

export interface ValidityLightProps {
  result: ValidityResult;
  className?: string;
}

export function ValidityLight({ result, className }: ValidityLightProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center gap-2 rounded-full border bg-background px-3 py-1 text-xs font-medium transition hover:bg-muted",
            className,
          )}
        >
          <span
            className="h-2.5 w-2.5 rounded-full"
            style={{ background: COLORS[result.level] }}
            aria-hidden
          />
          <span>{LABEL[result.level]}</span>
          {result.details.length > 0 && (
            <span className="text-muted-foreground">
              · {result.details.length} note{result.details.length > 1 ? "s" : ""}
            </span>
          )}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80 text-xs">
        <p className="font-medium">{result.message}</p>
        {result.details.length === 0 ? (
          <p className="mt-2 text-muted-foreground">All checks pass.</p>
        ) : (
          <ul className="mt-2 space-y-1">
            {result.details.map((d, i) => (
              <li key={i} className="flex items-start gap-2">
                <span
                  className="mt-1 h-2 w-2 shrink-0 rounded-full"
                  style={{ background: COLORS[d.level] }}
                />
                <div>
                  <span className="font-mono">{d.field}</span>
                  <span className="text-muted-foreground"> — {d.message}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </PopoverContent>
    </Popover>
  );
}
