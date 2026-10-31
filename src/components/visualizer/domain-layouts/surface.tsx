import { useState } from "react";
import type {
  DomainTimelineResponse,
  DomainVisualizationFrame,
  VisualizationManifest,
} from "@/types/manifest";
import { CosmologyDomainLayout } from "./cosmology-layout";
import { ChemistryDomainLayout } from "./chemistry-layout";
import { CondmatDomainLayout } from "./condmat-layout";
import { HepDomainLayout } from "./hep-layout";
import { NuclearDomainLayout } from "./nuclear-layout";
import { AmoDomainLayout } from "./amo-layout";
import { GravityDomainLayout } from "./gravity-layout";
import { StatmechDomainLayout } from "./statmech-layout";
import { Slider } from "@/components/ui/slider";

export interface DomainVisualizerSurfaceProps {
  manifest: VisualizationManifest;
  timeline: DomainTimelineResponse;
}

/**
 * Top-level dispatcher: picks the per-domain layout and owns the frame
 * scrubber. Fixture-sourced timelines (`metadata.synthetic`) are
 * labelled as such (R7).
 */
export function DomainVisualizerSurface({ manifest, timeline }: DomainVisualizerSurfaceProps) {
  const total = timeline.frames.length;
  const [frameIdx, setFrameIdx] = useState(0);
  const safeIdx = Math.min(frameIdx, Math.max(0, total - 1));
  const currentFrame = timeline.frames[safeIdx] ?? null;
  const synthetic = manifest.metadata.synthetic === true;

  if (manifest.domain === "cosmology") {
    return (
      <div className="grid min-h-0 flex-1 gap-3 p-3 md:grid-cols-2">
        <CosmologyDomainLayout manifest={manifest} />
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {synthetic ? (
        <div
          data-testid="synthetic-fixture-label"
          className="mx-3 mt-3 rounded-md border border-amber-500/50 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-700 dark:text-amber-400"
        >
          {manifest.metadata.source === "synthetic-bake"
            ? "Synthetic frames — not a computed result. Real-run timelines arrive with P4-04."
            : "Synthetic fixture — illustrative frames bundled with the app, not a run result."}
        </div>
      ) : null}
      {total === 0 ? (
        <div className="flex flex-1 items-center justify-center px-6">
          <div className="max-w-md rounded-md border bg-muted/40 p-4 text-center text-sm">
            <p className="font-medium text-foreground">No timeline data available.</p>
            <p className="mt-1 text-xs text-muted-foreground">
              The cosmic-forge-viz backend is offline (or hasn’t been wired up for this run yet).
              Start the backend with{" "}
              <code className="rounded bg-background px-1 py-0.5 font-mono text-[11px]">
                cosmic-forge-viz serve
              </code>{" "}
              and set <code className="font-mono">VITE_API_URL</code> to its address.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex min-h-0 flex-1 flex-col">
          <div
            data-testid="domain-visualizer-panels"
            className="grid min-h-0 flex-1 auto-rows-[minmax(240px,1fr)] gap-3 overflow-auto p-3 md:grid-cols-2"
          >
            <DomainPanels manifest={manifest} frame={currentFrame} frames={timeline.frames} />
          </div>
          <div className="flex items-center gap-3 border-t px-4 py-2">
            <span className="font-mono text-[11px] text-muted-foreground">
              τ {currentFrame?.tau.toFixed(2) ?? "—"} · {currentFrame?.phase || "—"}
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

type FrameOf<D extends DomainVisualizationFrame["domain"]> = Extract<
  DomainVisualizationFrame,
  { domain: D }
>;

function ofDomain<D extends DomainVisualizationFrame["domain"]>(
  frames: DomainVisualizationFrame[],
  domain: D,
): FrameOf<D>[] {
  return frames.filter((f): f is FrameOf<D> => f.domain === domain);
}

function pick<D extends DomainVisualizationFrame["domain"]>(
  frame: DomainVisualizationFrame | null,
  domain: D,
): FrameOf<D> | null {
  return frame && frame.domain === domain ? (frame as FrameOf<D>) : null;
}

function DomainPanels({
  manifest,
  frame,
  frames,
}: {
  manifest: VisualizationManifest;
  frame: DomainVisualizationFrame | null;
  frames: DomainVisualizationFrame[];
}) {
  switch (manifest.domain) {
    case "chemistry":
      return (
        <ChemistryDomainLayout
          manifest={manifest}
          frame={pick(frame, "chemistry")}
          frames={ofDomain(frames, "chemistry")}
        />
      );
    case "condmat":
      return (
        <CondmatDomainLayout
          manifest={manifest}
          frame={pick(frame, "condmat")}
          frames={ofDomain(frames, "condmat")}
        />
      );
    case "hep":
      return (
        <HepDomainLayout
          manifest={manifest}
          frame={pick(frame, "hep")}
          frames={ofDomain(frames, "hep")}
        />
      );
    case "nuclear":
      return (
        <NuclearDomainLayout
          manifest={manifest}
          frame={pick(frame, "nuclear")}
          frames={ofDomain(frames, "nuclear")}
        />
      );
    case "amo":
      return (
        <AmoDomainLayout
          manifest={manifest}
          frame={pick(frame, "amo")}
          frames={ofDomain(frames, "amo")}
        />
      );
    case "gravity":
      return (
        <GravityDomainLayout
          manifest={manifest}
          frame={pick(frame, "gravity")}
          frames={ofDomain(frames, "gravity")}
        />
      );
    case "statmech":
      return (
        <StatmechDomainLayout
          manifest={manifest}
          frame={pick(frame, "statmech")}
          frames={ofDomain(frames, "statmech")}
        />
      );
    default:
      return null;
  }
}
