import { useEffect, useState } from "react";

/**
 * Dev-only FPS overlay for the visualizer.
 *
 * Off by default. Enable with:
 *   localStorage.setItem("vfx:fps", "1")  // then reload
 *
 * Renders nothing in production builds and nothing when the flag is
 * absent. Mounted from `__root.tsx` (or the visualizer layout) so it
 * sits above all panels in the bottom-right corner.
 */
export function FpsOverlay() {
  const [enabled, setEnabled] = useState(false);
  const [fps, setFps] = useState(0);
  const [slow, setSlow] = useState(0);

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    if (typeof window === "undefined") return;
    try {
      setEnabled(window.localStorage.getItem("vfx:fps") === "1");
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    let raf = 0;
    let last = performance.now();
    let frames = 0;
    let slowCount = 0;
    let acc = 0;

    const tick = (now: number) => {
      const dt = now - last;
      last = now;
      frames += 1;
      acc += dt;
      if (dt > 33) slowCount += 1;
      if (acc >= 1000) {
        setFps(Math.round((frames * 1000) / acc));
        setSlow(slowCount);
        frames = 0;
        slowCount = 0;
        acc = 0;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [enabled]);

  if (!enabled) return null;

  const tone = fps >= 50 ? "text-emerald-400" : fps >= 30 ? "text-amber-400" : "text-rose-400";
  return (
    <div
      className="pointer-events-none fixed bottom-2 right-2 z-50 rounded-md border border-border bg-card/90 px-2 py-1 font-mono text-[10px] shadow-sm backdrop-blur-sm"
      data-testid="fps-overlay"
    >
      <span className={tone}>{fps} fps</span>
      <span className="ml-2 text-muted-foreground">slow: {slow}/s</span>
    </div>
  );
}
