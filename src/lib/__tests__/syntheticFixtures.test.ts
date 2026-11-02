import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { RunResultShape } from "@/lib/fixtureSchemas";

// PLAN.md correction 8 (R7): every bundled domain run fixture is synthetic
// and must say so. The cosmology V2 fixture is covered below (Decision 13a).
const DOMAIN_DIRS = ["amo", "chemistry", "condmat", "gravity", "hep", "nuclear", "statmech"];
const root = resolve(__dirname, "../../../public/fixtures");

describe("synthetic run fixtures (R7)", () => {
  for (const dir of DOMAIN_DIRS) {
    it(`every public/fixtures/${dir}/runs/*.json carries "synthetic": true`, () => {
      const files = readdirSync(resolve(root, dir, "runs")).filter((f) => f.endsWith(".json"));
      expect(files.length).toBeGreaterThan(0);
      const missing = files.filter((f) => {
        const blob = JSON.parse(readFileSync(resolve(root, dir, "runs", f), "utf8"));
        return blob.synthetic !== true;
      });
      expect(missing, `${dir} fixtures without "synthetic": true`).toEqual([]);
    });
  }
});

// Decision 16 (R7): every bundled cosmology run fixture that carries
// hand-written results (η_B, audit, validation rows or spectra) says so.
describe("cosmology run fixtures with hand-written results (Decision 16)", () => {
  const RESULT_KEYS = ["eta_B", "F_GB", "audit", "validation", "spectra"];
  const files = readdirSync(resolve(root, "runs")).filter((f) => f.endsWith(".json"));

  it("public/fixtures/runs/ holds the four bundled cosmology runs", () => {
    expect(files.sort()).toEqual([
      "failing-run.json",
      "gb-off-control.json",
      "kawai-kim-natural.json",
      "starobinsky-standard.json",
    ]);
  });

  for (const f of files) {
    it(`runs/${f}: hand-written results carry "synthetic": true through the run schema`, () => {
      const blob = JSON.parse(readFileSync(resolve(root, "runs", f), "utf8"));
      const results = RESULT_KEYS.filter((k) => k in blob);
      expect(results.length, `${f} carries no result field`).toBeGreaterThan(0);
      expect(blob.synthetic, `${f} carries ${results.join(", ")}`).toBe(true);
      expect(RunResultShape.parse(blob).synthetic).toBe(true);
    });
  }
});

// Decision 13a (R7): the cosmology V2 fixture's η_B and validation rows were
// never computed by the pipeline, so it is flagged and the views badge it.
describe("cosmology V2 fixture (Decision 13a)", () => {
  const blob = JSON.parse(readFileSync(resolve(root, "runs", "kawai-kim-natural.json"), "utf8"));

  it('public/fixtures/runs/kawai-kim-natural.json carries "synthetic": true', () => {
    expect(blob.synthetic).toBe(true);
  });

  it("the flag survives the run-fixture schema the cosmology loaders use", () => {
    expect(RunResultShape.parse(blob).synthetic).toBe(true);
  });

  it("is parameterised with M2's natural-potential keys (Decision 11)", () => {
    expect(blob.config.potential.kind).toBe("natural");
    expect(Object.keys(blob.config.potential.params).sort()).toEqual(["Lambda", "f_a"]);
    expect(blob.config.potential.params.f_a).toBe(8.7);
  });
});
