import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// PLAN.md correction 8 (R7): every bundled domain run fixture is synthetic
// and must say so. Cosmology fixtures (public/fixtures/runs etc.) are out of
// scope here (R19).
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
