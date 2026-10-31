/**
 * Energy-convergence trace per SCF / VQE iteration.
 */

import type { ChemistryFrame } from "../types";

interface Props {
  frame: ChemistryFrame | undefined;
  width?: number;
  height?: number;
}

export function EnergyConvergence({ frame, width = 320, height = 200 }: Props) {
  const energies = frame?.energy_convergence ?? [];
  if (energies.length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 border rounded">
        No energy trace yet.
      </div>
    );
  }
  const min = Math.min(...energies);
  const max = Math.max(...energies);
  const span = Math.max(1e-9, max - min);
  const pad = 24;
  const w = width - pad * 2;
  const h = height - pad * 2;
  const points = energies.map((e, i) => {
    const x = pad + (i / Math.max(1, energies.length - 1)) * w;
    const y = pad + h - ((e - min) / span) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <div className="space-y-2">
      <div className="text-xs text-muted-foreground">
        Energy convergence — {energies.length} iters, ΔE_final
        = {(energies[energies.length - 1] - energies[0]).toExponential(2)}
      </div>
      <svg width={width} height={height} role="img" aria-label="Energy convergence">
        <polyline
          points={points}
          fill="none"
          stroke="hsl(var(--primary, 220 70% 50%))"
          strokeWidth={1.5}
        />
        <text x={pad} y={pad - 4} fontSize={10} fill="currentColor">
          E (Ha)
        </text>
        <text x={width - pad} y={height - 4} fontSize={10} textAnchor="end" fill="currentColor">
          iter
        </text>
      </svg>
    </div>
  );
}

export default EnergyConvergence;
