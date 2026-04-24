import { useEffect, useRef } from "react";

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
 */
export function useAnimationFrame(
  callback: (dt: number, elapsed: number) => void,
  running: boolean,
): void {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  useEffect(() => {
    if (!running) return;
    let raf = 0;
    let prev = performance.now();
    const start = prev;

    const tick = (now: number) => {
      const dt = Math.min(now - prev, 100);
      prev = now;
      cbRef.current(dt, now - start);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [running]);
}
