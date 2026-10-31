/**
 * Lepton-number-violation (0νββ) tracker.
 *
 * Shows the per-frame `lnv_tracker` indicator: 1 = LNV signature
 * present, 0 = not yet observed. The trace lets the audit reviewer
 * see when the qualitative signal lights up.
 */

import type { NuclearFrame } from "../types";

interface Props {
  frames: NuclearFrame[];
  width?: number;
  height?: number;
}

export function LNVTracker({ frames, width = 320, height = 80 }: Props) {
  if (!frames || frames.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No LNV trace.
      </div>
    );
  }
  const cellW = (width - 16) / frames.length;
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        Lepton-number-violation indicator across {frames.length} frames
      </div>
      <svg width={width} height={height} role="img" aria-label="LNV tracker">
        {frames.map((f, i) => (
          <rect
            key={i}
            x={8 + i * cellW}
            y={16}
            width={Math.max(1, cellW - 1)}
            height={height - 32}
            fill={f.lnv_tracker > 0.5 ? "hsl(0 70% 55%)" : "hsl(220 10% 80%)"}
            fillOpacity={0.8}
          />
        ))}
        <text x={8} y={12} fontSize={10} fill="currentColor">
          0
        </text>
        <text x={width - 8} y={12} fontSize={10} textAnchor="end" fill="currentColor">
          τ
        </text>
      </svg>
    </div>
  );
}

export default LNVTracker;
