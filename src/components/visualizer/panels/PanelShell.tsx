import type { ReactNode } from "react";

export interface PanelShellProps {
  title: string;
  /** Render the "no data" empty state instead of `children`. */
  empty?: boolean;
  /** One-line summary under the body (counts, ranges, caveats). */
  caption?: ReactNode;
  /** Extra classes for the body (e.g. padding, overflow). */
  bodyClassName?: string;
  children?: ReactNode;
}

/** Shared frame for every domain visualizer panel (one shape per concern). */
export function PanelShell({ title, empty, caption, bodyClassName = "p-2", children }: PanelShellProps) {
  return (
    <div className="flex h-full min-h-[220px] flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">{title}</div>
      <div className={`min-h-0 flex-1 ${bodyClassName}`}>
        {empty ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">no data</div>
        ) : (
          children
        )}
      </div>
      {caption && !empty ? (
        <div className="border-t px-3 py-1 font-mono text-[10px] text-muted-foreground">{caption}</div>
      ) : null}
    </div>
  );
}

export const TOOLTIP_STYLE = { fontSize: 11, fontFamily: "var(--font-mono)", borderRadius: 6 } as const;

/** Format a recharts tooltip value (which may be a string or array). */
export function tooltipNumber(v: unknown): string {
  return typeof v === "number" ? String(v) : Array.isArray(v) ? v.join(", ") : String(v ?? "—");
}

export function hslToHex(h: number, s: number, l: number): string {
  const f = (n: number) => {
    const k = (n + h * 12) % 12;
    const a = s * Math.min(l, 1 - l);
    const x = l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
    return Math.round(255 * x);
  };
  return `#${[f(0), f(8), f(4)].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}
