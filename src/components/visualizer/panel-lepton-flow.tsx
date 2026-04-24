import { useMemo, useRef } from "react";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import { PanelContextMenu } from "@/components/visualizer/panel-context-menu";
import { useVisualizerStore } from "@/store/visualizer";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import { cn } from "@/lib/utils";
import type { BakedVisualizationTimeline } from "@/types/visualizer";

export interface LeptonFlowSankeyProps {
  timelineA: BakedVisualizationTimeline | null;
  timelineB?: BakedVisualizationTimeline | null;
}

interface NodeDef {
  id: string;
  label: string;
  /** Read this magnitude out of `LeptonFlow` for the active frame. */
  key: "chiral_gw" | "anomaly" | "delta_N_L" | "eta_B_running";
}

const NODES: NodeDef[] = [
  { id: "gw", label: "Chiral GW", key: "chiral_gw" },
  { id: "anom", label: "Anomaly", key: "anomaly" },
  { id: "lepton", label: "ΔN_L", key: "delta_N_L" },
  { id: "bau", label: "η_B", key: "eta_B_running" },
];

/**
 * Panel 5 — lepton flow.
 *
 * Custom four-node SVG Sankey: GW → anomaly → ΔN_L → η_B. Stroke widths
 * are normalised to the largest magnitude across both timelines so the
 * comparison stays visually honest. No external Sankey library — keeps
 * the bundle slim and the colours fully token-driven.
 */
export function LeptonFlowSankey({
  timelineA,
  timelineB,
}: LeptonFlowSankeyProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const frameIdx = useVisualizerStore((s) => s.currentFrameIndex);
  const reducedMotion = usePrefersReducedMotion();

  const flow = useMemo(() => {
    if (!timelineA) return null;
    const fa = timelineA.frames[
      Math.min(frameIdx, timelineA.frames.length - 1)
    ]?.lepton_flow;
    const fb = timelineB?.frames[
      Math.min(frameIdx, timelineB.frames.length - 1)
    ]?.lepton_flow;
    if (!fa) return null;
    const valuesA = NODES.map((n) => Math.abs(fa[n.key] ?? 0));
    const valuesB = fb ? NODES.map((n) => Math.abs(fb[n.key] ?? 0)) : null;
    const maxAbs = Math.max(
      1e-30,
      ...valuesA,
      ...(valuesB ?? []),
    );
    return { valuesA, valuesB, maxAbs };
  }, [timelineA, timelineB, frameIdx]);

  if (!timelineA || !flow) {
    return (
      <PanelContextMenu
        panelId="lepton-flow"
        label="Lepton flow"
        timelineA={timelineA}
      >
        <div className="h-full w-full">
          <EmptyPanel
            title="Lepton flow"
            reason="Pick a run to see the chiral GW → η_B Sankey."
          />
        </div>
      </PanelContextMenu>
    );
  }

  return (
    <PanelContextMenu
      panelId="lepton-flow"
      label="Lepton flow"
      timelineA={timelineA}
      timelineB={timelineB}
      getExportTarget={() => svgRef.current}
    >
      <div
        ref={containerRef}
        className="flex h-full w-full flex-col"
        data-testid="visualizer-lepton-flow"
      >
        <div className="flex items-center justify-between px-2 pt-1 text-[10px] font-mono text-muted-foreground">
          <span>chiral GW → η_B</span>
          <span>frame {frameIdx}</span>
        </div>
        <div className="min-h-0 flex-1">
          <svg
            ref={svgRef}
            viewBox="0 0 400 200"
            preserveAspectRatio="xMidYMid meet"
            className="h-full w-full"
            role="img"
            aria-label="Sankey diagram of chiral lepton asymmetry flow"
          >
            <SankeyGraph
              values={flow.valuesA}
              maxAbs={flow.maxAbs}
              variant="A"
              animate={!reducedMotion}
            />
            {flow.valuesB ? (
              <g transform="translate(0,12)">
                <SankeyGraph
                  values={flow.valuesB}
                  maxAbs={flow.maxAbs}
                  variant="B"
                  animate={!reducedMotion}
                />
              </g>
            ) : null}
          </svg>
        </div>
      </div>
    </PanelContextMenu>
  );
}

interface SankeyGraphProps {
  values: number[];
  maxAbs: number;
  variant: "A" | "B";
  animate: boolean;
}

function SankeyGraph({ values, maxAbs, variant, animate }: SankeyGraphProps) {
  // Node positions (x centres) and a fixed y centreline.
  const xs = [50, 150, 250, 350];
  const cy = 100;
  const stroke =
    variant === "A"
      ? "var(--color-accent-indigo)"
      : "var(--color-chart-4)";
  const opacity = variant === "A" ? 0.85 : 0.55;

  // Width of each link is proportional to the smaller of its two endpoint
  // magnitudes — preserves a flow interpretation (you can't transmit more
  // than either reservoir holds).
  const links = [];
  for (let i = 0; i < NODES.length - 1; i++) {
    const w = Math.min(values[i], values[i + 1]);
    const norm = (w / maxAbs) * 36 + 1.2;
    links.push({ from: xs[i], to: xs[i + 1], width: norm });
  }

  return (
    <g
      className={cn(
        "transition-opacity",
        animate ? "[animation:visualizer-sankey-pulse_2.4s_ease-in-out_infinite]" : "",
      )}
      style={{ opacity }}
    >
      {links.map((l, i) => {
        const midX = (l.from + l.to) / 2;
        const d = `M ${l.from} ${cy} C ${midX} ${cy} ${midX} ${cy} ${l.to} ${cy}`;
        return (
          <path
            key={`l${i}`}
            d={d}
            stroke={stroke}
            strokeWidth={l.width}
            fill="none"
            strokeLinecap="round"
          />
        );
      })}
      {NODES.map((n, i) => (
        <g key={n.id} transform={`translate(${xs[i]} ${cy})`}>
          <rect
            x={-22}
            y={-18}
            width={44}
            height={36}
            rx={6}
            fill="var(--color-card)"
            stroke={stroke}
            strokeWidth={1.2}
          />
          <text
            x={0}
            y={4}
            textAnchor="middle"
            className="font-mono"
            style={{
              fontSize: 9,
              fill: "var(--color-foreground)",
            }}
          >
            {n.label}
          </text>
          <text
            x={0}
            y={32}
            textAnchor="middle"
            className="font-mono"
            style={{
              fontSize: 8,
              fill: "var(--color-muted-foreground)",
            }}
          >
            {formatNumber(values[i])}
          </text>
        </g>
      ))}
    </g>
  );
}

function formatNumber(v: number): string {
  if (!Number.isFinite(v)) return "—";
  if (v === 0) return "0";
  const abs = Math.abs(v);
  if (abs < 1e-3 || abs >= 1e4) return v.toExponential(2);
  return v.toFixed(3);
}
