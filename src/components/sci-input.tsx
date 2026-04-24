import { forwardRef, useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export interface SciInputProps {
  value: number;
  onChange: (v: number) => void;
  onBlur?: () => void;
  id?: string;
  placeholder?: string;
  className?: string;
  invalid?: boolean;
  step?: number;
  min?: number;
  max?: number;
}

/**
 * Numeric input that accepts scientific notation (`8.5e-3`, `1e16`).
 * Keeps a string buffer so the user can mid-edit without losing state.
 */
export const SciInput = forwardRef<HTMLInputElement, SciInputProps>(function SciInput(
  { value, onChange, onBlur, invalid, className, ...rest },
  ref,
) {
  const [text, setText] = useState<string>(formatForInput(value));

  useEffect(() => {
    // Sync if external value changes (e.g. benchmark load) and the
    // current text doesn't already represent that number.
    const parsed = Number(text);
    if (!Number.isFinite(parsed) || parsed !== value) {
      setText(formatForInput(value));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <Input
      ref={ref}
      type="text"
      inputMode="decimal"
      value={text}
      onChange={(e) => {
        const next = e.target.value;
        setText(next);
        const n = Number(next);
        if (Number.isFinite(n)) onChange(n);
      }}
      onBlur={() => {
        const n = Number(text);
        if (!Number.isFinite(n)) {
          setText(formatForInput(value));
        } else {
          setText(formatForInput(n));
        }
        onBlur?.();
      }}
      className={cn(
        "font-mono tabular-nums",
        invalid && "border-destructive focus-visible:ring-destructive",
        className,
      )}
      {...rest}
    />
  );
});

function formatForInput(v: number): string {
  if (!Number.isFinite(v)) return "";
  if (v === 0) return "0";
  const abs = Math.abs(v);
  if (abs >= 1e-3 && abs < 1e6) return String(v);
  return v.toExponential(4).replace(/\.?0+e/, "e");
}
