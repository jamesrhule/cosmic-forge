import { useEffect, useRef } from "react";
import {
  ChevronFirst,
  ChevronLast,
  Pause,
  Play,
  Repeat,
  SkipBack,
  SkipForward,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Toggle } from "@/components/ui/toggle";
import { cn } from "@/lib/utils";
import { SPEED_PRESETS, useVisualizerStore } from "@/store/visualizer";
import { useAnimationFrame } from "@/hooks/useAnimationFrame";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";

export interface TransportBarProps {
  /** Optional label rendered to the left of the controls (e.g. run id). */
  label?: React.ReactNode;
  className?: string;
}

/**
 * The visualizer's playback shelf. Owns:
 *   - the rAF loop that advances `currentFrameIndex` while `playing`,
 *   - keyboard shortcuts for transport (Space / ← / → / 1-5 / L / Home / End),
 *   - the scrub slider, frame counter, speed presets, and loop toggle.
 *
 * It does NOT own panel layout, comparison-mode toggles, or export — those
 * sit on the surrounding `VisualizerLayout` header.
 *
 * Behaviour notes:
 *   - reduced motion → playback advances at half speed.
 *   - shortcuts are no-ops while the user is typing in an input/textarea.
 */
export function TransportBar({ label, className }: TransportBarProps) {
  const playing = useVisualizerStore((s) => s.playing);
  const speed = useVisualizerStore((s) => s.speed);
  const loop = useVisualizerStore((s) => s.loop);
  const totalFrames = useVisualizerStore((s) => s.totalFrames);
  const currentFrameIndex = useVisualizerStore((s) => s.currentFrameIndex);
  const effectiveStride = useVisualizerStore((s) => s.effectiveStride);

  const play = useVisualizerStore((s) => s.play);
  const pause = useVisualizerStore((s) => s.pause);
  const toggle = useVisualizerStore((s) => s.toggle);
  const seek = useVisualizerStore((s) => s.seek);
  const step = useVisualizerStore((s) => s.step);
  const setSpeed = useVisualizerStore((s) => s.setSpeed);
  const setLoop = useVisualizerStore((s) => s.setLoop);

  const reducedMotion = usePrefersReducedMotion();
  const accumulator = useRef(0);

  // Advance frames at `baseFps × speed`. Reduced motion halves both the
  // baseline and the speed multiplier so very fast playbacks are still
  // gentle. `effectiveStride` (1 / 2 / 4) skips frames at high speeds to
  // keep the render budget honest.
  useAnimationFrame(
    (dt) => {
      if (totalFrames === 0) return;
      const baseFps = reducedMotion ? 12 : 24;
      const adjusted = baseFps * speed * (reducedMotion ? 0.5 : 1);
      accumulator.current += dt / 1000;
      const frameTime = 1 / Math.max(0.05, adjusted);
      while (accumulator.current >= frameTime) {
        accumulator.current -= frameTime;
        step(effectiveStride);
      }
    },
    playing && totalFrames > 0,
    {
      // Slow-frame guard: bursts >= 5 sub-30fps frames in a 2s window
      // are reported (rate-limited to once per window) so we can pivot
      // dashboards on transport-loop regressions before users notice.
      onSlowFrames: ({ count, worstDtMs }) => {
        void import("@/lib/telemetry").then((t) =>
          t.reportSlowFrames("transport", count, worstDtMs),
        );
      },
    },
  );

  // Reset accumulator on pause to avoid a "burst" advance after resume.
  useEffect(() => {
    if (!playing) accumulator.current = 0;
  }, [playing]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || e.metaKey || e.ctrlKey) return;

      switch (e.key) {
        case " ":
          e.preventDefault();
          toggle();
          return;
        case "ArrowLeft":
          e.preventDefault();
          step(e.shiftKey ? -10 : -1);
          return;
        case "ArrowRight":
          e.preventDefault();
          step(e.shiftKey ? 10 : 1);
          return;
        case "Home":
          e.preventDefault();
          seek(0);
          return;
        case "End":
          e.preventDefault();
          seek(totalFrames - 1);
          return;
        case "l":
        case "L":
          e.preventDefault();
          setLoop(!loop);
          return;
        case "1":
        case "2":
        case "3":
        case "4":
        case "5": {
          const idx = Number(e.key) - 1;
          const preset = SPEED_PRESETS[idx];
          if (preset !== undefined) {
            e.preventDefault();
            setSpeed(preset);
          }
          return;
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [loop, totalFrames, toggle, step, seek, setLoop, setSpeed]);

  const disabled = totalFrames === 0;

  return (
    <div
      className={cn(
        "flex w-full items-center gap-3 border-t border-border bg-card/60 px-3 py-2",
        className,
      )}
      data-testid="visualizer-transport"
    >
      {label ? (
        <div className="min-w-0 max-w-[12rem] truncate text-xs text-muted-foreground">{label}</div>
      ) : null}

      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="sm"
          aria-label="Seek to start"
          disabled={disabled}
          onClick={() => seek(0)}
        >
          <ChevronFirst className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          aria-label="Step back"
          disabled={disabled}
          onClick={() => step(-1)}
        >
          <SkipBack className="h-4 w-4" />
        </Button>
        <Button
          variant="default"
          size="sm"
          aria-label={playing ? "Pause" : "Play"}
          disabled={disabled}
          onClick={() => (playing ? pause() : play())}
        >
          {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          aria-label="Step forward"
          disabled={disabled}
          onClick={() => step(1)}
        >
          <SkipForward className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          aria-label="Seek to end"
          disabled={disabled}
          onClick={() => seek(totalFrames - 1)}
        >
          <ChevronLast className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex min-w-0 flex-1 items-center gap-3">
        <Slider
          aria-label="Scrub timeline"
          value={[currentFrameIndex]}
          min={0}
          max={Math.max(0, totalFrames - 1)}
          step={1}
          disabled={disabled}
          onValueChange={(v) => seek(v[0] ?? 0)}
          className="flex-1"
        />
        <span className="shrink-0 font-mono text-[11px] tabular-nums text-muted-foreground">
          {disabled
            ? "—"
            : `${currentFrameIndex.toString().padStart(3, "0")} / ${(totalFrames - 1)
                .toString()
                .padStart(3, "0")}`}
        </span>
      </div>

      <div className="flex items-center gap-1" role="group" aria-label="Playback speed">
        {SPEED_PRESETS.map((preset) => (
          <button
            key={preset}
            type="button"
            disabled={disabled}
            onClick={() => setSpeed(preset)}
            aria-pressed={speed === preset}
            className={cn(
              "rounded px-1.5 py-0.5 font-mono text-[10px] tabular-nums transition-colors",
              "hover:bg-accent disabled:opacity-50",
              speed === preset ? "bg-primary text-primary-foreground" : "text-muted-foreground",
            )}
          >
            {preset}×
          </button>
        ))}
      </div>

      <Toggle
        size="sm"
        pressed={loop}
        onPressedChange={setLoop}
        disabled={disabled}
        aria-label="Loop playback"
        title="Loop playback (L)"
      >
        <Repeat className="h-3.5 w-3.5" />
      </Toggle>
    </div>
  );
}
