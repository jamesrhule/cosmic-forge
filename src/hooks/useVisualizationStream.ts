import { useCallback, useEffect, useRef, useState } from "react";
import { getStreamFrameCount, streamVisualization } from "@/services/visualizer";
import { notifyServiceError } from "@/lib/serviceErrors";
import type { VisualizationFrame } from "@/types/visualizer";

export type StreamStatus =
  | "idle"
  | "connecting"
  | "streaming"
  | "complete"
  | "error"
  | "cancelled";

export interface UseVisualizationStreamResult {
  status: StreamStatus;
  framesReceived: number;
  /** `null` when the upstream can't tell us a denominator. */
  framesExpected: number | null;
  lastFrame: VisualizationFrame | null;
  error: Error | null;
  start: () => void;
  stop: () => void;
}

/**
 * Drives the JSONL `streamVisualization` async iterable for a given run
 * and exposes UI-friendly counters for the streaming progress indicator.
 *
 * - One in-flight stream at a time: a second `start()` cancels the
 *   previous one before opening the new generator.
 * - Auto-aborts on unmount so navigating away never leaks a generator.
 * - `notifyServiceError(err, "visualization")` for non-abort failures so
 *   the toast UX stays consistent with the rest of the visualizer.
 */
export function useVisualizationStream(runId: string | null): UseVisualizationStreamResult {
  const [status, setStatus] = useState<StreamStatus>("idle");
  const [framesReceived, setFramesReceived] = useState(0);
  const [framesExpected, setFramesExpected] = useState<number | null>(null);
  const [lastFrame, setLastFrame] = useState<VisualizationFrame | null>(null);
  const [error, setError] = useState<Error | null>(null);

  // Single AbortController per active stream. Refs (not state) because
  // start/stop are imperative and shouldn't trigger re-renders.
  const controllerRef = useRef<AbortController | null>(null);
  // Generation token: bumped on every start() / stop() so a late
  // setState from a cancelled stream is silently dropped.
  const genRef = useRef(0);

  const stop = useCallback(() => {
    if (controllerRef.current) {
      controllerRef.current.abort();
      controllerRef.current = null;
    }
    genRef.current += 1;
    setStatus((prev) => (prev === "streaming" || prev === "connecting" ? "cancelled" : prev));
  }, []);

  const start = useCallback(() => {
    if (!runId) return;
    // Cancel any in-flight stream first.
    if (controllerRef.current) controllerRef.current.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    const myGen = ++genRef.current;

    setStatus("connecting");
    setFramesReceived(0);
    setFramesExpected(null);
    setLastFrame(null);
    setError(null);

    // Probe the denominator in parallel so the indicator can render
    // "0 / 60" before the first frame arrives.
    void getStreamFrameCount(runId).then((count) => {
      if (genRef.current !== myGen) return;
      if (count != null) setFramesExpected(count);
    });

    void (async () => {
      try {
        for await (const frame of streamVisualization(runId, { signal: controller.signal })) {
          if (genRef.current !== myGen) return;
          setLastFrame(frame);
          setFramesReceived((n) => n + 1);
          // Flip from "connecting" to "streaming" on the first frame —
          // gives the indicator dot a meaningful colour change.
          setStatus((prev) => (prev === "connecting" ? "streaming" : prev));
        }
        if (genRef.current !== myGen) return;
        setStatus("complete");
      } catch (err) {
        if (genRef.current !== myGen) return;
        if (err instanceof Error && err.name === "AbortError") {
          setStatus("cancelled");
          return;
        }
        const e = err instanceof Error ? err : new Error(String(err));
        setError(e);
        setStatus("error");
        notifyServiceError(e, "visualization", { extra: { phase: "stream", runId } });
      } finally {
        if (controllerRef.current === controller) controllerRef.current = null;
      }
    })();
  }, [runId]);

  // Auto-cancel when the component unmounts or the runId changes.
  useEffect(() => {
    return () => {
      if (controllerRef.current) {
        controllerRef.current.abort();
        controllerRef.current = null;
      }
      genRef.current += 1;
    };
  }, [runId]);

  return { status, framesReceived, framesExpected, lastFrame, error, start, stop };
}
