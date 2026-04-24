import { useEffect, useRef } from "react";

export interface UseAnimationFrameOptions {
  /**
   * Fired when the loop detects a sustained slow-frame burst:
   * more than `slowFrameThreshold` frames in `slowFrameWindowMs`
   * exceed `slowFrameMs`. Reported with the burst's count and the
   * worst dt observed inside the window so callers can rate-limit
   * downstream telemetry.
   */
  onSlowFrames?: (info: { count: number; worstDtMs: number }) => void;
  /** dt threshold (ms) above which a frame counts as "slow". Default 33ms (~<30fps). */
  slowFrameMs?: number;
  /** Sliding window length (ms) for slow-frame detection. Default 2000ms. */
  slowFrameWindowMs?: number;
  /** Minimum slow frames in the window to fire `onSlowFrames`. Default 5. */
  slowFrameThreshold?: number;
}

/**
 * RequestAnimationFrame loop that pauses when `running` is false.
 *
 * Callback receives:
 *   - `dt`: milliseconds since the previous tick (clamped to ≤100 to
 *     avoid jumps when a tab regains focus).
 *   - `elapsed`: total ms since the loop started this run.
 *
 * The callback is held in a ref so the loop never has to re-subscribe
 * when the closure changes — important for high-frequency transport
 * updates where a stale callback would silently drop frames.
 *
 * Optional slow-frame detection (`onSlowFrames`) lets visualizer
 * surfaces report dropped-frame bursts to telemetry without each
 * panel re-implementing the same FPS guard.
 */
export function useAnimationFrame(
  callback: (dt: number, elapsed: number) => void,
  running: boolean,
  options: UseAnimationFrameOptions = {},
): void {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  const optsRef = useRef(options);
  optsRef.current = options;

  useEffect(() => {
    if (!running) return;
    let raf = 0;
    let prev = performance.now();
    const start = prev;

    // Sliding window of recent slow-frame dts (timestamps + dt).
    const slowFrames: { at: number; dt: number }[] = [];
    let lastReportAt = 0;

    const tick = (now: number) => {
      const dt = Math.min(now - prev, 100);
      prev = now;
      cbRef.current(dt, now - start);

      const opts = optsRef.current;
      if (opts.onSlowFrames) {
        const threshold = opts.slowFrameMs ?? 33;
        const windowMs = opts.slowFrameWindowMs ?? 2000;
        const minCount = opts.slowFrameThreshold ?? 5;
        if (dt > threshold) slowFrames.push({ at: now, dt });
        // Drop entries older than the window.
        const cutoff = now - windowMs;
        while (slowFrames.length > 0 && slowFrames[0].at < cutoff) slowFrames.shift();
        // Fire at most once per window to avoid telemetry spam.
        if (slowFrames.length >= minCount && now - lastReportAt > windowMs) {
          const worstDtMs = slowFrames.reduce((acc, e) => Math.max(acc, e.dt), 0);
          opts.onSlowFrames({ count: slowFrames.length, worstDtMs });
          lastReportAt = now;
        }
      }

      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [running]);
}
