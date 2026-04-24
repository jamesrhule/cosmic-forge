import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { SGWBPlot } from "@/components/sgwb-plot";
import { ParameterHeatmap } from "@/components/parameter-heatmap";
import type { RunResult, ScanResult } from "@/types/domain";

export interface QaResearchFrameProps {
  scan: ScanResult;
  runs: RunResult[];
}

/**
 * Two-panel research layout: left ξ×θ heatmap, right grid of two SGWB
 * tiles. Useful for confirming multiple `<ResponsiveChart>` instances
 * each track their own container width.
 */
export function QaResearchFrame({ scan, runs }: QaResearchFrameProps) {
  const a = runs[0];
  const b = runs[1] ?? runs[0];

  return (
    <ResizablePanelGroup orientation="horizontal" className="h-full">
      <ResizablePanel defaultSize={50} minSize={30}>
        <div className="h-full overflow-y-auto p-4">
          <div className="mb-2 flex items-baseline justify-between gap-2">
            <h2 className="text-base font-semibold tracking-tight">
              ξ × θ scan
            </h2>
            <span className="font-mono text-[11px] text-muted-foreground">
              {scan.xAxis.field} × {scan.yAxis.field}
            </span>
          </div>
          <div className="rounded-md border bg-card p-3">
            <ParameterHeatmap scan={scan} />
          </div>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      <ResizablePanel defaultSize={50} minSize={30}>
        <div className="grid h-full grid-rows-2 gap-3 overflow-y-auto p-4">
          {[a, b].map((r, i) => (
            <div key={`${r.id}-${i}`} className="rounded-md border bg-card p-3">
              <div className="mb-2 text-xs font-medium text-muted-foreground">
                {r.id}
              </div>
              <SGWBPlot
                spectra={[{ id: r.id, label: r.id, data: r.spectra.sgwb }]}
                height={220}
              />
            </div>
          ))}
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}
