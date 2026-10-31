/**
 * Statmech estimator trace (QAE / Metropolis / TFD).
 */

import type { StatmechFrame } from "../types";

interface Props {
  frame: StatmechFrame | undefined;
  width?: number;
  height?: number;
}

export function EstimatorTrace({ frame, width = 320, height = 200 }: Props) {
  const history = frame?.history ?? [];
  if (history.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No estimator trace.
      </div>
    );
  }
  const minV = Math.min(...history);
  const maxV = Math.max(...history);
  const span = Math.max(1e-9, maxV - minV);
  const pad = 24;
  const w = width - pad * 2;
  const h = height - pad * 2;
  const points = history.map((v, i) => {
    const x = pad + (i / Math.max(1, history.length - 1)) * w;
    const y = pad + h - ((v - minV) / span) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const truthY = (
    frame?.truth !== null && frame?.truth !== undefined
      ? pad + h - ((frame.truth - minV) / span) * h
      : null
  );
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        Estimate {frame?.estimate?.toFixed(4)} ± {frame?.sigma?.toExponential(2)}
        {frame?.truth !== null && frame?.truth !== undefined
          ? ` (truth ${frame.truth.toFixed(4)})`
          : ""}
      </div>
      <svg width={width} height={height} role="img" aria-label="Estimator trace">
        <polyline
          points={points}
          fill="none"
          stroke="hsl(160 60% 45%)"
          strokeWidth={1.5}
        />
        {truthY !== null ? (
          <line
            x1={pad}
            y1={truthY}
            x2={pad + w}
            y2={truthY}
            stroke="hsl(220 70% 50%)"
            strokeDasharray="4 2"
            strokeOpacity={0.6}
          />
        ) : null}
      </svg>
    </div>
  );
}

export default EstimatorTrace;
