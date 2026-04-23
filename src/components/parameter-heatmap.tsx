import { useMemo } from "react";
import type { ScanResult } from "@/types/domain";
import { cn } from "@/lib/utils";

export interface ParameterHeatmapProps {
  scan: ScanResult;
  centerValue?: number;
  width?: number;
  height?: number;
  onCellClick?: (xVal: number, yVal: number, eta: number) => void;
  className?: string;
}

/**
 * Custom-SVG ξ × θ heatmap. Color scale is log-distance from the
 * Planck-band center (default 6.1×10⁻¹⁰), perceptually uniform within a
 * ±2 decade window.
 */
export function ParameterHeatmap({
  scan,
  centerValue = 6.1e-10,
  width = 520,
  height = 360,
  onCellClick,
  className,
}: ParameterHeatmapProps) {
  const padL = 56;
  const padB = 36;
  const padT = 12;
  const padR = 16;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const xs = scan.xAxis.values;
  const ys = scan.yAxis.values;
  const cellW = plotW / xs.length;
  const cellH = plotH / ys.length;

  const colorOf = useMemo(() => {
    const logCenter = Math.log10(Math.max(centerValue, 1e-30));
    return (eta: number): string => {
      const v = Math.log10(Math.max(eta, 1e-30));
      const d = (v - logCenter) / 2; // -1..+1 over ±2 decades
      const t = Math.max(-1, Math.min(1, d));
      // diverging: too low → blue, near-target → indigo, too high → orange
      const c1 = [37, 99, 195];   // blue
      const c2 = [67, 56, 202];   // indigo (target)
      const c3 = [217, 119, 6];   // amber
      const a = t < 0 ? c1 : c3;
      const k = Math.abs(t);
      const r = Math.round(c2[0] * (1 - k) + a[0] * k);
      const g = Math.round(c2[1] * (1 - k) + a[1] * k);
      const b = Math.round(c2[2] * (1 - k) + a[2] * k);
      return `rgb(${r} ${g} ${b})`;
    };
  }, [centerValue]);

  const inBand = (eta: number) =>
    eta >= scan.planckBand.low && eta <= scan.planckBand.high;

  const xTicks = [0, Math.floor(xs.length / 4), Math.floor(xs.length / 2), Math.floor((3 * xs.length) / 4), xs.length - 1];
  const yTicks = [0, Math.floor(ys.length / 4), Math.floor(ys.length / 2), Math.floor((3 * ys.length) / 4), ys.length - 1];

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={cn("block w-full text-foreground", className)}
      role="img"
      aria-label={`Parameter scan ${scan.xAxis.field} × ${scan.yAxis.field}`}
    >
      {/* cells */}
      {scan.eta_B_grid.map((row, yi) =>
        row.map((eta, xi) => {
          const x = padL + xi * cellW;
          const y = padT + (ys.length - 1 - yi) * cellH;
          return (
            <rect
              key={`${xi}-${yi}`}
              x={x}
              y={y}
              width={cellW + 0.5}
              height={cellH + 0.5}
              fill={colorOf(eta)}
              stroke={inBand(eta) ? "white" : "none"}
              strokeWidth={inBand(eta) ? 0.6 : 0}
              onClick={() => onCellClick?.(xs[xi], ys[yi], eta)}
              style={{ cursor: onCellClick ? "pointer" : "default" }}
            >
              <title>
                {scan.xAxis.field} = {xs[xi].toExponential(2)} ·{" "}
                {scan.yAxis.field} = {ys[yi].toExponential(2)} → η_B ={" "}
                {eta.toExponential(2)}
              </title>
            </rect>
          );
        }),
      )}
      {/* axes */}
      <line
        x1={padL}
        y1={padT + plotH}
        x2={padL + plotW}
        y2={padT + plotH}
        stroke="currentColor"
        strokeOpacity={0.5}
      />
      <line
        x1={padL}
        y1={padT}
        x2={padL}
        y2={padT + plotH}
        stroke="currentColor"
        strokeOpacity={0.5}
      />
      {xTicks.map((i) => {
        const x = padL + i * cellW + cellW / 2;
        return (
          <g key={`xt-${i}`}>
            <line
              x1={x}
              x2={x}
              y1={padT + plotH}
              y2={padT + plotH + 4}
              stroke="currentColor"
              strokeOpacity={0.5}
            />
            <text
              x={x}
              y={padT + plotH + 16}
              textAnchor="middle"
              fontSize={10}
              fontFamily="var(--font-mono)"
              fill="currentColor"
              opacity={0.65}
            >
              {xs[i].toExponential(1)}
            </text>
          </g>
        );
      })}
      {yTicks.map((i) => {
        const y = padT + (ys.length - 1 - i) * cellH + cellH / 2;
        return (
          <g key={`yt-${i}`}>
            <line
              x1={padL - 4}
              x2={padL}
              y1={y}
              y2={y}
              stroke="currentColor"
              strokeOpacity={0.5}
            />
            <text
              x={padL - 6}
              y={y + 3}
              textAnchor="end"
              fontSize={10}
              fontFamily="var(--font-mono)"
              fill="currentColor"
              opacity={0.65}
            >
              {ys[i].toFixed(2)}
            </text>
          </g>
        );
      })}
      <text
        x={padL + plotW / 2}
        y={height - 6}
        textAnchor="middle"
        fontSize={11}
        fill="currentColor"
        opacity={0.75}
      >
        {scan.xAxis.field}
        {scan.xAxis.log ? " (log)" : ""}
      </text>
      <text
        x={12}
        y={padT + plotH / 2}
        transform={`rotate(-90 12 ${padT + plotH / 2})`}
        textAnchor="middle"
        fontSize={11}
        fill="currentColor"
        opacity={0.75}
      >
        {scan.yAxis.field}
      </text>
    </svg>
  );
}
