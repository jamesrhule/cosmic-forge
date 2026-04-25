import { beforeEach, describe, expect, it } from "vitest";
import { useVisualizerStore, SPEED_PRESETS } from "@/store/visualizer";

describe("useVisualizerStore", () => {
  beforeEach(() => {
    // Reset store to initial state between tests.
    useVisualizerStore.setState({
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
    });
  });

  it("loadTimelines clamps initialFrame to [0, totalFrames-1]", () => {
    useVisualizerStore.getState().loadTimelines({
      runIdA: "a",
      totalFrames: 10,
      initialFrame: 999,
    });
    expect(useVisualizerStore.getState().currentFrameIndex).toBe(9);

    useVisualizerStore.getState().loadTimelines({
      runIdA: "a",
      totalFrames: 10,
      initialFrame: -5,
    });
    expect(useVisualizerStore.getState().currentFrameIndex).toBe(0);
  });

  it("seek clamps to bounds and rounds fractional values", () => {
    useVisualizerStore.setState({ totalFrames: 100 });
    useVisualizerStore.getState().seek(5.7);
    expect(useVisualizerStore.getState().currentFrameIndex).toBe(6);
    useVisualizerStore.getState().seek(-10);
    expect(useVisualizerStore.getState().currentFrameIndex).toBe(0);
    useVisualizerStore.getState().seek(1000);
    expect(useVisualizerStore.getState().currentFrameIndex).toBe(99);
  });

  it("step wraps around when loop=true and clamps when loop=false", () => {
    useVisualizerStore.setState({ totalFrames: 5, loop: true, currentFrameIndex: 4 });
    useVisualizerStore.getState().step(1);
    expect(useVisualizerStore.getState().currentFrameIndex).toBe(0);

    useVisualizerStore.setState({ currentFrameIndex: 0, loop: true });
    useVisualizerStore.getState().step(-1);
    expect(useVisualizerStore.getState().currentFrameIndex).toBe(4);

    useVisualizerStore.setState({ totalFrames: 5, loop: false, currentFrameIndex: 4 });
    useVisualizerStore.getState().step(10);
    expect(useVisualizerStore.getState().currentFrameIndex).toBe(4);

    useVisualizerStore.setState({ currentFrameIndex: 0, loop: false });
    useVisualizerStore.getState().step(-10);
    expect(useVisualizerStore.getState().currentFrameIndex).toBe(0);
  });

  it("setSpeed clamps to [0.25, 5] and updates effectiveStride", () => {
    useVisualizerStore.getState().setSpeed(0.1);
    expect(useVisualizerStore.getState().speed).toBe(0.25);
    expect(useVisualizerStore.getState().effectiveStride).toBe(1);

    useVisualizerStore.getState().setSpeed(100);
    expect(useVisualizerStore.getState().speed).toBe(5);
    expect(useVisualizerStore.getState().effectiveStride).toBe(2);

    useVisualizerStore.getState().setSpeed(1);
    expect(useVisualizerStore.getState().effectiveStride).toBe(1);
  });

  it("toggle flips playing", () => {
    useVisualizerStore.getState().toggle();
    expect(useVisualizerStore.getState().playing).toBe(true);
    useVisualizerStore.getState().toggle();
    expect(useVisualizerStore.getState().playing).toBe(false);
  });

  it("setComparisonMode is overridden by loadTimelines when no partner runId", () => {
    useVisualizerStore.getState().setComparisonMode("ab_overlay");
    useVisualizerStore.getState().loadTimelines({ runIdA: "a", totalFrames: 5 });
    // No runIdB → comparison snaps back to single.
    expect(useVisualizerStore.getState().comparisonMode).toBe("single");
  });

  it("SPEED_PRESETS are sorted ascending and contain 1×", () => {
    const sorted = [...SPEED_PRESETS].sort((a, b) => a - b);
    expect(SPEED_PRESETS).toEqual(sorted);
    expect(SPEED_PRESETS).toContain(1);
  });
});
