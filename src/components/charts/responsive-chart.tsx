import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { ChartSizeBadge } from "@/components/dev/chart-size-overlay";

export interface ResponsiveChartSize {
  width: number;
  height: number;
}

export interface ResponsiveChartProps {
  /** Pixel height (number) or any CSS height value (e.g. "100%", "20rem"). */
  height: number | string;
  /** Suppress render until the container reaches this width. Default 0. */
  minWidth?: number;
  className?: string;
  /** Short tag for the dev-overlay badge (e.g. "vψ", "sgwb"). */
  label?: string;
  children: (size: ResponsiveChartSize) => React.ReactNode;
}

// useLayoutEffect during SSR warns; fall back to useEffect on the server.
const useIsomorphicLayoutEffect =
  typeof window !== "undefined" ? useLayoutEffect : useEffect;

/**
 * ResizeObserver-driven sizing for chart libraries that need explicit
 * width/height (e.g. Recharts). Unlike Recharts' built-in
 * `ResponsiveContainer`, this tracks parent box-size changes — so charts
 * resize correctly when a `react-resizable-panels` handle is dragged
 * (which never fires `window.resize`).
 *
 * Coalesces rapid observer callbacks via `requestAnimationFrame`.
 */
export function ResponsiveChart({
  height,
  minWidth = 0,
  className,
  children,
}: ResponsiveChartProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const rafRef = useRef<number | null>(null);
  const [size, setSize] = useState<ResponsiveChartSize>({ width: 0, height: 0 });

  useIsomorphicLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    const measure = (w: number, h: number) => {
      setSize((prev) =>
        prev.width === w && prev.height === h ? prev : { width: w, height: h },
      );
    };

    // Seed initial dimensions synchronously to avoid a 0×0 first paint.
    const rect = el.getBoundingClientRect();
    measure(Math.round(rect.width), Math.round(rect.height));

    if (typeof ResizeObserver === "undefined") return;

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width: w, height: h } = entry.contentRect;
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null;
        measure(Math.round(w), Math.round(h));
      });
    });
    ro.observe(el);

    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      ro.disconnect();
    };
  }, []);

  const style: React.CSSProperties = {
    width: "100%",
    height: typeof height === "number" ? `${height}px` : height,
  };

  const ready = size.width > minWidth && size.height > 0;

  return (
    <div ref={ref} className={cn("relative", className)} style={style}>
      {ready ? children(size) : null}
    </div>
  );
}
