import { useEffect, useRef } from "react";
import { createLazyFileRoute, getRouteApi, Link, useNavigate } from "@tanstack/react-router";
import { VisualizerLayout } from "@/components/visualizer/visualizer-layout";
import { RunPicker } from "@/components/visualizer/run-picker";
import { useVisualizerStore } from "@/store/visualizer";
import type { ComparisonMode } from "@/types/visualizer";
import type { VisualizerSearch } from "@/lib/visualizerSearch";
import type { RunVisualizationLoaderData } from "./visualizer.$runId";

const routeApi = getRouteApi("/visualizer/$runId");
const parentApi = getRouteApi("/visualizer");

/**
 * Lazy chunk: holds the entire visualizer surface (R3F PhaseSpaceCanvas,
 * Recharts plots, KaTeX FormulaOverlay, TransportBar, KeymapOverlay).
 *
 * The split keeps `/visualizer` (the index) free of WebGL/charts code.
 * `getRouteApi` is used instead of `import { Route }` so importing this
 * chunk does NOT pull the route-config file into the same bundle.
 */
export const Route = createLazyFileRoute("/visualizer/$runId")({
  component: VisualizerRunRoute,
});

function VisualizerRunRoute() {
  const { a, b } = routeApi.useLoaderData() as unknown as RunVisualizationLoaderData;
  const params = routeApi.useParams();
  const search = routeApi.useSearch() as unknown as VisualizerSearch;
  const navigate = useNavigate({ from: "/visualizer/$runId" });
  const { runIds: availableRunIds } = parentApi.useLoaderData();

  const handlePartnerChange = (runB: string | null) => {
    navigate({
      to: "/visualizer/$runId",
      params: { runId: params.runId },
      search: (prev: VisualizerSearch) => ({
        ...prev,
        runB: runB ?? undefined,
        // Snap back to single view when clearing the partner.
        mode: runB ? prev.mode : "single",
      }),
      replace: true,
    });
  };

  // Hydrate the transport store from URL search params on mount + when
  // the partner run / initial frame change. The layout itself also calls
  // `loadTimelines`, but that one always seeds frame=0; we override the
  // initial frame here so a refreshed URL restores the user's scrub
  // position before any rAF tick runs.
  const setMode = useVisualizerStore((s) => s.setComparisonMode);
  const setSyncByPhase = useVisualizerStore((s) => s.setSyncByPhase);
  const seek = useVisualizerStore((s) => s.seek);

  useEffect(() => {
    setMode(b ? (search.mode as ComparisonMode) : "single");
  }, [b, search.mode, setMode]);

  useEffect(() => {
    setSyncByPhase(search.phase);
  }, [search.phase, setSyncByPhase]);

  // Seed initial frame after the layout's `loadTimelines` runs.
  // `loadTimelines` resets frame=0; this effect runs after and snaps to
  // the URL's `frame` value (clamped by the store's seek).
  const seededRef = useRef(false);
  useEffect(() => {
    if (seededRef.current) return;
    if (a.frames.length === 0) return;
    seededRef.current = true;
    seek(search.frame);
    // intentionally only on first mount per timeline
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [a.runId]);

  // Push transport state back to the URL with a debounce so scrubbing
  // doesn't spam history. `replace: true` keeps the browser back stack
  // anchored to the route entry, not every frame.
  useEffect(() => {
    let lastFrame = -1;
    let lastMode: ComparisonMode | "" = "";
    let lastPhase: boolean | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const flush = () => {
      const s = useVisualizerStore.getState();
      navigate({
        to: "/visualizer/$runId",
        params: { runId: params.runId },
        search: (prev: VisualizerSearch) => ({
          ...prev,
          frame: s.currentFrameIndex,
          mode: s.comparisonMode,
          phase: s.syncByPhase,
        }),
        replace: true,
      });
    };

    const unsub = useVisualizerStore.subscribe(
      (s) => ({
        f: s.currentFrameIndex,
        m: s.comparisonMode,
        p: s.syncByPhase,
      }),
      ({ f, m, p }) => {
        const changed = f !== lastFrame || m !== lastMode || p !== lastPhase;
        if (!changed) return;
        lastFrame = f;
        lastMode = m;
        lastPhase = p;
        if (timer) clearTimeout(timer);
        timer = setTimeout(flush, 150);
      },
      {
        equalityFn: (prev, next) => prev.f === next.f && prev.m === next.m && prev.p === next.p,
      },
    );
    return () => {
      unsub();
      if (timer) clearTimeout(timer);
    };
  }, [navigate, params.runId]);

  return (
    <div className="h-[calc(100vh-3.5rem)] min-h-0">
      <VisualizerLayout
        timelineA={a}
        timelineB={b}
        toolbarLead={
          <div className="flex items-center gap-2 text-xs">
            <Link
              to="/visualizer"
              className="rounded-md border px-2 py-1 font-mono text-[11px] hover:bg-muted"
            >
              ← runs
            </Link>
            <span className="font-mono text-muted-foreground">{params.runId}</span>
            <span className="font-mono text-foreground/60">↔</span>
            <RunPicker
              currentRunId={params.runId}
              partnerRunId={b?.runId ?? null}
              availableRunIds={availableRunIds}
              onChange={handlePartnerChange}
            />
          </div>
        }
      />
    </div>
  );
}
