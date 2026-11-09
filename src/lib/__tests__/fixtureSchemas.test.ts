import { describe, expect, it } from "vitest";
import { RunResultShape } from "@/lib/fixtureSchemas";

// Gate 1 round 4 (R4-FEOPS, FE3 verifier NIT): bundled run fixtures stay
// strict. η_B without a number is accepted only as a refusal with a reason.
const run = (eta_B: Record<string, unknown>) => ({
  id: "r",
  status: "completed",
  audit: { checks: [], summary: { passed: 0, total: 0, blocking: false } },
  eta_B,
});
const ok = (eta_B: Record<string, unknown>) => RunResultShape.safeParse(run(eta_B)).success;

describe("RunResultShape η_B", () => {
  it("accepts a finite value and uncertainty", () => {
    expect(ok({ value: 6.1e-10, uncertainty: 5.4e-11 })).toBe(true);
  });

  it("refuses a missing or null number with no refusal reason", () => {
    expect(ok({})).toBe(false);
    expect(ok({ uncertainty: 5.4e-11 })).toBe(false);
    expect(ok({ value: null, uncertainty: 5.4e-11 })).toBe(false);
    expect(ok({ value: 6.1e-10 })).toBe(false);
    expect(ok({ value: 6.1e-10, uncertainty: null })).toBe(false);
    expect(ok({ value: null, uncertainty: null, refusal: null })).toBe(false);
  });

  it("refuses a blank refusal reason", () => {
    expect(ok({ value: null, uncertainty: null, refusal: "" })).toBe(false);
    expect(ok({ refusal: "   " })).toBe(false);
  });

  it("accepts a null or absent number next to a non-empty refusal", () => {
    const refusal = "ΔN_L depends on the scale-factor normalisation (residual 9)";
    expect(ok({ value: null, uncertainty: null, refusal })).toBe(true);
    expect(ok({ refusal })).toBe(true);
  });

  it("still refuses non-finite numbers", () => {
    expect(ok({ value: Number.NaN, uncertainty: 1 })).toBe(false);
    expect(ok({ value: 1, uncertainty: Number.POSITIVE_INFINITY })).toBe(false);
  });
});
