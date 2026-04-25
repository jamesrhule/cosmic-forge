import { describe, expect, it } from "vitest";
import { visualizerSearchSchema } from "@/lib/visualizerSearch";

describe("visualizerSearchSchema", () => {
  it("supplies defaults when the URL has no params", () => {
    const parsed = visualizerSearchSchema.parse({});
    expect(parsed.mode).toBe("single");
    expect(parsed.phase).toBe(false);
    expect(parsed.frame).toBe(0);
    expect(parsed.runB).toBeUndefined();
  });

  it("falls back instead of throwing on malformed values", () => {
    const parsed = visualizerSearchSchema.parse({
      mode: "not_a_mode",
      phase: "yes",
      frame: -3,
    });
    expect(parsed.mode).toBe("single");
    expect(parsed.phase).toBe(false);
    expect(parsed.frame).toBe(0);
  });

  it("preserves valid inputs verbatim", () => {
    const parsed = visualizerSearchSchema.parse({
      runB: "run-42",
      mode: "ab_overlay",
      phase: true,
      frame: 100,
    });
    expect(parsed).toEqual({
      runB: "run-42",
      mode: "ab_overlay",
      phase: true,
      frame: 100,
    });
  });

  it("rejects non-integer frame indexes via the fallback path", () => {
    const parsed = visualizerSearchSchema.parse({ frame: 3.7 });
    expect(parsed.frame).toBe(0);
  });
});
