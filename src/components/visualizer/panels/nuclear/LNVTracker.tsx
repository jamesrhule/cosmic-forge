import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import type { DomainTimelineResponse, NuclearFrame } from "@/types/manifest";

export interface LNVTrackerProps {
  timeline: DomainTimelineResponse;
  frame: NuclearFrame | null;
}

/**
 * Lepton-number-violation tracker: cumulative ΔL trace + a live
 * ΔL/ΔB/rate readout pulled from the current frame.
 */
export function LNVTracker({ timeline, frame }: LNVTrackerProps) {
  const data = useMemo(() => {
    const frames = timeline.frames as NuclearFrame[];
    return frames.map((f) => ({
      tau: Number(f.tau.toFixed(2)),
      delta_L: f.lnv_tracker?.delta_L ?? 0,
      rate: f.lnv_tracker?.rate ?? 0,
    }));
  }, [timeline]);

  const lnv = frame?.lnv_tracker ?? null;

  return (
    <div className="flex h-full min-h-0 flex-col rounded-md border bg-card">
      <div className="border-b px-3 py-1.5 text-xs font-medium text-muted-foreground">
        LNV tracker (ΔL, ΔB, rate)
      </div>
      <div className="grid min-h-0 flex-1 grid-rows-[auto_1fr] gap-2 p-2">
        <div className="flex flex-wrap items-center gap-3 text-[11px] font-mono">
          <span className="rounded bg-muted px-2 py-0.5">
            ΔL <span className="ml-1 tabular-nums">{lnv?.delta_L.toFixed(2) ?? "—"}</span>
          </span>
          <span className="rounded bg-muted px-2 py-0.5">
            ΔB <span className="ml-1 tabular-nums">{lnv?.delta_B.toFixed(2) ?? "—"}</span>
          </span>
          <span className="rounded bg-muted px-2 py-0.5">
            rate{" "}
            <span className="ml-1 tabular-nums">
              {lnv ? lnv.rate.toExponential(2) : "—"}
            </span>
          </span>
        </div>
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
            no data
          </div>
        ) : (
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
              <Tooltip
                contentStyle={{
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  borderRadius: 6,
                }}
              />
              <Line
                type="monotone"
                dataKey="delta_L"
                stroke="hsl(var(--primary))"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
