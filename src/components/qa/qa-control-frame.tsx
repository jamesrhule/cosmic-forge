import { useState } from "react";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { SGWBPlot } from "@/components/sgwb-plot";
import { cn } from "@/lib/utils";
import type { RunResult } from "@/types/domain";

export interface QaControlFrameProps {
  runs: RunResult[];
}

/**
 * Two-panel run-list / detail layout. Selecting a run swaps the SGWB
 * plot's primary spectrum so testers can verify chart re-mount + size
 * preservation.
 */
export function QaControlFrame({ runs }: QaControlFrameProps) {
  const [selectedId, setSelectedId] = useState(runs[0]?.id ?? "");
  const selected = runs.find((r) => r.id === selectedId) ?? runs[0];
  const baseline = runs.find((r) => r.id !== selected?.id);

  const spectra = selected
    ? [
        { id: selected.id, label: selected.id, data: selected.spectra.sgwb },
        ...(baseline
          ? [
              {
                id: baseline.id,
                label: `${baseline.id} (baseline)`,
                data: baseline.spectra.sgwb,
              },
            ]
          : []),
      ]
    : [];

  return (
    <ResizablePanelGroup orientation="horizontal" className="h-full">
      <ResizablePanel defaultSize={26} minSize={20} maxSize={40}>
        <div className="h-full overflow-y-auto border-r bg-muted/30 p-3">
          <div className="mb-2 px-1 text-xs font-medium text-muted-foreground">
            Runs ({runs.length})
          </div>
          <ul className="space-y-1">
            {runs.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(r.id)}
                  className={cn(
                    "w-full rounded-md border px-3 py-2 text-left text-sm transition",
                    r.id === selected?.id
                      ? "border-[color:var(--color-accent-indigo)] bg-accent text-accent-foreground"
                      : "bg-card hover:bg-muted",
                  )}
                >
                  <div className="font-medium">{r.id}</div>
                  <div className="font-mono text-[11px] text-muted-foreground">
                    η_B = {r.eta_B.value.toExponential(2)} · {r.status}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      <ResizablePanel defaultSize={74} minSize={40}>
        <div className="h-full overflow-y-auto p-4">
          <div className="mb-3 flex items-baseline justify-between gap-2">
            <h2 className="text-base font-semibold tracking-tight">
              {selected?.id ?? "—"}
            </h2>
            <span className="font-mono text-[11px] text-muted-foreground">
              SGWB spectrum overlay
            </span>
          </div>
          <div className="rounded-md border bg-card p-3">
            <SGWBPlot spectra={spectra} height={360} />
          </div>
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
