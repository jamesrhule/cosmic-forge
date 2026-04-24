import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { ComparisonMode } from "@/types/visualizer";

/**
 * Single source of truth for the visualizer transport. Every panel
 * subscribes to this store; nothing else owns playback state.
 *
 * `currentFrameIndex` is always indexed against the *master* timeline
 * (timeline A). Partner timelines (B) are looked up via the
 * sync-by-phase / sync-by-τ helpers in `useFrameAt.ts` at render time.
 *
 * The `subscribeWithSelector` middleware lets the imperative panels
 * (GBWindowTimeline scrubber line, R3F frame loop) subscribe to a
 * single field without re-running React renders.
 */

const MIN_SPEED = 0.25;
const MAX_SPEED = 5;

export interface VisualizerStore {
  /* timelines */
  runIdA: string | null;
  runIdB: string | null;

  /* transport */
  currentFrameIndex: number;
  totalFrames: number;
  playing: boolean;
  /** 0.25 / 0.5 / 1 / 2 / 5; "realtime" maps to 1 with extra dt scaling. */
  speed: number;
  loop: boolean;
  /** Frame stride applied at high speeds (1 / 2 / 4). */
  effectiveStride: number;

  /* comparison */
  comparisonMode: ComparisonMode;
  /** When true, A ↔ B alignment is by named phase rather than τ. */
  syncByPhase: boolean;

  /* meta */
  fps: number;

  /* actions */
  loadTimelines: (input: {
    runIdA: string;
    runIdB?: string | null;
    totalFrames: number;
    initialFrame?: number;
  }) => void;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  seek: (frameIndex: number) => void;
  step: (delta: number) => void;
  setSpeed: (speed: number) => void;
  setLoop: (loop: boolean) => void;
  setComparisonMode: (mode: ComparisonMode) => void;
  setSyncByPhase: (on: boolean) => void;
  setFps: (fps: number) => void;
}

export const useVisualizerStore = create<VisualizerStore>()(
  subscribeWithSelector((set, get) => ({
    runIdA: null,
    runIdB: null,
    currentFrameIndex: 0,
    totalFrames: 0,
    playing: false,
    speed: 1,
    loop: true,
    effectiveStride: 1,
    comparisonMode: "single",
    syncByPhase: false,
    fps: 0,

    loadTimelines: ({ runIdA, runIdB, totalFrames, initialFrame }) =>
      set({
        runIdA,
        runIdB: runIdB ?? null,
        totalFrames,
        currentFrameIndex: clamp(initialFrame ?? 0, 0, Math.max(0, totalFrames - 1)),
        comparisonMode: runIdB ? get().comparisonMode : "single",
      }),

    play: () => set({ playing: true }),
    pause: () => set({ playing: false }),
    toggle: () => set({ playing: !get().playing }),

    seek: (frameIndex) =>
      set({
        currentFrameIndex: clamp(Math.round(frameIndex), 0, Math.max(0, get().totalFrames - 1)),
      }),

    step: (delta) => {
      const { currentFrameIndex, totalFrames, loop } = get();
      let next = currentFrameIndex + delta;
      const last = Math.max(0, totalFrames - 1);
      if (next > last) next = loop ? next % totalFrames : last;
      if (next < 0) next = loop ? (next + totalFrames) % totalFrames : 0;
      set({ currentFrameIndex: next });
    },

    setSpeed: (speed) => {
      const s = clamp(speed, MIN_SPEED, MAX_SPEED);
      // Drop to every-other frame above 2×, every-fourth above 5×.
      const stride = s > 5 ? 4 : s > 2 ? 2 : 1;
      set({ speed: s, effectiveStride: stride });
    },

    setLoop: (loop) => set({ loop }),

    setComparisonMode: (mode) => set({ comparisonMode: mode }),

    setSyncByPhase: (on) => set({ syncByPhase: on }),

    setFps: (fps) => set({ fps }),
  })),
);

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

/** Stable speed presets for the transport bar (and 1..5 hotkeys). */
export const SPEED_PRESETS = [0.25, 0.5, 1, 2, 5] as const;
