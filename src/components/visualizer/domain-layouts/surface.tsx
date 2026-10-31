import { useMemo, useState } from "react";
import type {
  AmoFrame,
  ChemistryFrame,
  CondmatFrame,
  DomainTimelineResponse,
  DomainVisualizationFrame,
  HepFrame,
  NuclearFrame,
  VisualizationManifest,
} from "@/types/manifest";
import { CosmologyDomainLayout } from "./cosmology-layout";
import { ChemistryDomainLayout } from "./chemistry-layout";
import { CondmatDomainLayout } from "./condmat-layout";
import { HepDomainLayout } from "./hep-layout";
import { NuclearDomainLayout } from "./nuclear-layout";
import { AmoDomainLayout } from "./amo-layout";
import { Slider } from "@/components/ui/slider";

export interface DomainVisualizerSurfaceProps {
  manifest: VisualizationManifest;
  timeline: DomainTimelineResponse;
}

/**
 * Top-level dispatcher: picks the per-domain layout, owns the simple
 * frame scrubber. Cosmology delegates to a thin shim around the
 * existing `/visualizer/$runId` UI; the other five domains use their
 * own panel grids.
 */
export function DomainVisualizerSurface({
  manifest,
  timeline,
}: DomainVisualizerSurfaceProps) {
  const total = timeline.frames.length;
  const [frameIdx, setFrameIdx] = useState(0);
  const safeIdx = Math.min(frameIdx, Math.max(0, total - 1));
  const currentFrame = timeline.frames[safeIdx] ?? null;

  const empty = useMemo(() => total === 0, [total]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {empty ? (
        <div className="flex flex-1 items-center justify-center px-6">
          <div className="max-w-md rounded-md border bg-muted/40 p-4 text-center text-sm">
            <p className="font-medium text-foreground">
              No timeline data available.
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              The cosmic-forge-viz backend is offline (or hasn’t been wired up
              for this run yet). Start the backend with{" "}
              <code className="rounded bg-background px-1 py-0.5 font-mono text-[11px]">
                cosmic-forge-viz serve
              </code>{" "}
              and set <code className="font-mono">VITE_API_URL</code> to its
              address.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="grid min-h-0 flex-1 gap-3 p-3 md:grid-cols-2 md:grid-rows-2">
            <DomainPanels manifest={manifest} frame={currentFrame} timeline={timeline} />
          </div>
          <div className="flex items-center gap-3 border-t px-4 py-2">
            <span className="font-mono text-[11px] text-muted-foreground">
              τ {currentFrame?.tau.toFixed(2) ?? "—"} · {currentFrame?.phase ?? "—"}
            </span>
            <Slider
              min={0}
              max={Math.max(0, total - 1)}
              value={[safeIdx]}
              onValueChange={(v) => setFrameIdx(v[0] ?? 0)}
              className="flex-1"
            />
            <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
              {safeIdx + 1}/{total}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function pickFrame<T extends DomainVisualizationFrame["domain"]>(
  frame: DomainVisualizationFrame | null,
  domain: T,
): Extract<DomainVisualizationFrame, { domain: T }> | null {
  if (frame && frame.domain === domain) {
    return frame as Extract<DomainVisualizationFrame, { domain: T }>;
  }
  return null;
}

function DomainPanels({
  manifest,
  frame,
  timeline,
}: {
  manifest: VisualizationManifest;
  frame: DomainVisualizationFrame | null;
  timeline: DomainTimelineResponse;
}) {
  switch (manifest.domain) {
    case "cosmology":
      return <CosmologyDomainLayout manifest={manifest} />;
    case "chemistry":
      return (
        <ChemistryDomainLayout
          manifest={manifest}
          frame={pickFrame(frame, "chemistry") as ChemistryFrame | null}
          timeline={timeline}
        />
      );
    case "condmat":
      return (
        <CondmatDomainLayout
          manifest={manifest}
          frame={pickFrame(frame, "condmat") as CondmatFrame | null}
        />
      );
    case "hep":
      return (
        <HepDomainLayout
          manifest={manifest}
          frame={pickFrame(frame, "hep") as HepFrame | null}
          timeline={timeline}
        />
      );
    case "nuclear":
      return (
        <NuclearDomainLayout
          manifest={manifest}
          frame={pickFrame(frame, "nuclear") as NuclearFrame | null}
          timeline={timeline}
        />
      );
    case "amo":
      return (
        <AmoDomainLayout
          manifest={manifest}
          frame={pickFrame(frame, "amo") as AmoFrame | null}
        />
      );
    default:
      return null;
  }
}
