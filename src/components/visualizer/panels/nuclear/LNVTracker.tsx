/**
 * Lepton-number-violation tracker (nuclear, 0νββ).
 *
 * Merged panel (P0-02): when frames carry the structured ΔL/ΔB/rate
 * tracker, the router-branch readout + ΔL(τ) chart; when they carry
 * only the scalar indicator (flat wire shape), the agent-branch
 * per-frame indicator strip (1 = LNV signature present).
 */
import { useMemo } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import type { NuclearFrame } from "../types";
import { PanelShell, TOOLTIP_STYLE } from "../PanelShell";

export interface LNVTrackerProps {
  frames: NuclearFrame[];
  frame: NuclearFrame | null;
}

export function LNVTracker({ frames, frame }: LNVTrackerProps) {
  const structured = useMemo(() => frames.some((f) => f.lnv_tracker !== null), [frames]);
  const indicator = useMemo(() => frames.some((f) => f.lnv_indicator !== null), [frames]);
  const data = useMemo(
    () =>
      frames.flatMap((f) =>
        f.lnv_tracker ? [{ tau: Number(f.tau.toFixed(2)), delta_L: f.lnv_tracker.delta_L }] : [],
      ),
    [frames],
  );
  const lnv = frame?.lnv_tracker ?? null;

  return (
    <PanelShell
      title={structured ? "LNV tracker (ΔL, ΔB, rate)" : "LNV indicator"}
      empty={!structured && !indicator}
      bodyClassName="grid grid-rows-[auto_1fr] gap-2 p-2"
      caption={
        indicator && !structured ? (
          <>
            lepton-number-violation indicator across {frames.length} frames · current{" "}
            {frame?.lnv_indicator ?? "—"}
          </>
        ) : null
      }
    >
      {structured ? (
        <>
          <div className="flex flex-wrap items-center gap-3 font-mono text-[11px]">
            <span className="rounded bg-muted px-2 py-0.5">
              ΔL <span className="ml-1 tabular-nums">{lnv?.delta_L.toFixed(2) ?? "—"}</span>
            </span>
            <span className="rounded bg-muted px-2 py-0.5">
              ΔB <span className="ml-1 tabular-nums">{lnv?.delta_B.toFixed(2) ?? "—"}</span>
            </span>
            <span className="rounded bg-muted px-2 py-0.5">
              rate <span className="ml-1 tabular-nums">{lnv ? lnv.rate.toExponential(2) : "—"}</span>
            </span>
          </div>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 8, bottom: 16, left: 24 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.25} />
              <XAxis
                dataKey="tau"
                stroke="currentColor"
                fontSize={10}
                tickLine={false}
                label={{ value: "τ", position: "insideBottom", offset: -2, fontSize: 10 }}
              />
              <YAxis stroke="currentColor" fontSize={10} tickLine={false} />
              <Tooltip contentStyle={TOOLTIP_STYLE} />
              <Line type="monotone" dataKey="delta_L" stroke="hsl(var(--primary))" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </>
      ) : (
        <>
          <div className="text-[11px] text-muted-foreground">0 → τ</div>
          <svg viewBox={`0 0 ${Math.max(1, frames.length)} 1`} preserveAspectRatio="none" className="h-full w-full" role="img" aria-label="LNV tracker">
            {frames.map((f, i) => (
              <rect
                key={i}
                x={i}
                y={0}
                width={0.92}
                height={1}
                fill={f.lnv_indicator === null ? "transparent" : f.lnv_indicator > 0.5 ? "hsl(0 70% 55%)" : "hsl(220 10% 80%)"}
                fillOpacity={0.8}
                stroke={f.tau === frame?.tau ? "currentColor" : "none"}
                strokeWidth={0.04}
              />
            ))}
          </svg>
        </>
      )}
    </PanelShell>
  );
}

export default LNVTracker;
