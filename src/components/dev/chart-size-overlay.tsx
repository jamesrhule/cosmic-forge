import { useEffect, useRef, useState } from "react";
import { isDevOverlayEnabled } from "@/config/dev-overlay";

export interface ChartSizeBadgeProps {
  width: number;
  height: number;
  /** Short tag like "vψ" or "sgwb" so multiple badges are distinguishable. */
  label?: string;
}

/**
 * Tiny diagnostic chip that shows live `width × height` for a chart and
 * an update counter so QA can visually confirm the ResizeObserver is
 * firing during a panel drag.
 *
 * Renders `null` unless the dev-overlay flag is on (see
 * `src/config/dev-overlay.ts`). Zero cost in normal use.
 *
 * Note: deliberately uses raw `bg-black/70 text-white` instead of design
 * tokens — this is debug chrome that must stay legible regardless of
 * the chart's own background and theme.
 */
export function ChartSizeBadge({ width, height, label }: ChartSizeBadgeProps) {
  const [enabled, setEnabled] = useState(false);
  const updates = useRef(0);

  useEffect(() => {
    setEnabled(isDevOverlayEnabled());
  }, []);

  if (enabled) {
    updates.current += 1;
  }

  if (!enabled) return null;

  return (
    <div
      className="pointer-events-none absolute right-1 top-1 z-10 rounded bg-black/70 px-1.5 py-0.5 font-mono text-[10px] leading-none text-white"
      data-testid="chart-size-badge"
      data-chart-label={label ?? ""}
      data-chart-width={width}
      data-chart-height={height}
    >
      {label ? `${label} · ` : ""}
      {width}×{height} · n={updates.current}
    </div>
  );
}
