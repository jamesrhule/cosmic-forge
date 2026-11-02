import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { ETA_B_NO_REASON, etaBNotPublished, readEtaB } from "@/lib/etaB";
import type { RunResult } from "@/types/domain";

// W1 FE3: how a run's η_B reads (display only). A refused η_B
// (pipeline.eta_B_refusal) is never shown as a number.
const REASON =
  "ΔN_L depends on the scale-factor normalisation (residual 9); M4 does not yet match a to reheating (P1-04)";

const fixture = (id: string) =>
  JSON.parse(
    readFileSync(resolve(__dirname, `../../../public/fixtures/runs/${id}.json`), "utf8"),
  ) as RunResult;

describe("readEtaB", () => {
  it("a fixture's finite η_B is published as is", () => {
    expect(readEtaB(fixture("kawai-kim-natural").eta_B)).toEqual({
      kind: "published",
      value: 6.1e-10,
    });
  });

  it("a refused η_B is never a number, with or without its reason", () => {
    for (const value of [null, "NaN", undefined, Number.NaN]) {
      expect(readEtaB({ value, refusal: REASON })).toEqual({ kind: "refused", reason: REASON });
      expect(readEtaB({ value })).toEqual({ kind: "refused", reason: ETA_B_NO_REASON });
    }
    expect(readEtaB({ value: 6.1e-10, refusal: REASON })).toEqual({
      kind: "refused",
      reason: REASON,
    });
    expect(readEtaB(undefined)).toBeNull();
    expect(etaBNotPublished(REASON)).toBe(`η_B not published — ${REASON}`);
  });
});
