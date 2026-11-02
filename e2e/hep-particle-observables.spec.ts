/**
 * HEP particle observables (P0-06). Every HEP run fixture renders its
 * `particle_obs` in the ParticleObservablesTable: name, value ± σ, units,
 * provider / backend and calibration time, each matching the fixture.
 */
import { expect, test } from "@playwright/test";
import { DOMAINS_URL } from "./urls";
import { fixture, sci3, type RunFixture } from "./fixture-data";

test.use({ baseURL: DOMAINS_URL });

const RUNS = ["schwinger-1plus1d", "zN-lattice", "su2-toy"];

test.describe("HEP particle observables", () => {
  for (const id of RUNS) {
    test(`${id}: table matches the fixture`, async ({ page }) => {
      const run = fixture<RunFixture>(`hep/runs/${id}.json`);
      const obs = Object.entries(run.particle_obs ?? {});
      expect(obs.length, "fixture has particle_obs").toBeGreaterThan(0);

      await page.goto(`/domains/hep.lattice/runs/${id}`);
      const table = page.getByTestId("particle-observables-table");
      await expect(table).toBeVisible();
      await expect(table.locator("tbody tr")).toHaveCount(obs.length);

      for (const [name, o] of obs) {
        const row = table.locator("tbody tr", { hasText: name });
        await expect(row).toHaveCount(1);
        const cells = row.locator("td");
        await expect(cells.nth(0)).toContainText(o.label);
        await expect(cells.nth(1)).toHaveText(`${sci3(o.value)} ± ${sci3(o.uncertainty)}`);
        await expect(cells.nth(2)).toHaveText(o.units);
        await expect(cells.nth(3)).toHaveText(`${o.provider} / ${o.backend}`);
        const cal = new Date(o.calibration_at).toISOString().slice(0, 16).replace("T", " ");
        await expect(cells.nth(4)).toHaveText(`${cal}Z`);
      }
      // Provenance travels with the observables.
      await expect(page.getByRole("heading", { name: "Provenance", exact: true })).toBeVisible();
    });
  }

  test("schwinger-1plus1d: literal values (oracle check)", async ({ page }) => {
    await page.goto("/domains/hep.lattice/runs/schwinger-1plus1d");
    const row = page.getByTestId("particle-observables-table").locator("tbody tr", {
      hasText: "chiral_condensate",
    });
    await expect(row.locator("td").nth(1)).toHaveText("-1.87×10⁻¹ ± 1.20×10⁻²");
    await expect(row.locator("td").nth(2)).toHaveText("g");
  });

  test("compare-to-literature opens the lattice-QCD corpus sheet", async ({ page }) => {
    await page.goto("/domains/hep.lattice/runs/schwinger-1plus1d");
    await page.getByTestId("compare-literature-string_tension").click();
    await expect(page.getByRole("dialog")).toBeVisible();
    // The sheet shows the observable's symbol and the measured value ± σ.
    const dialog = page.getByRole("dialog");
    await expect(dialog).toContainText("Literature comparison");
    await expect(dialog).toContainText("\\sigma");
    await expect(dialog).toContainText("2.14×10⁻¹ ± 1.80×10⁻² g^2");
  });
});
