/**
 * Nuclear observables (P0-06). Every nuclear run fixture renders the
 * ModelDomainBadge for its `model_domain` (R18: users see whether a result
 * is a toy) and its observables table.
 */
import { expect, test } from "@playwright/test";
import { DOMAINS_URL } from "./urls";
import { fixture, sci3, type RunFixture } from "./fixture-data";

test.use({ baseURL: DOMAINS_URL });

const RUNS = ["ovbb-1plus1d", "ncsm-4he", "sterile-osc"];

test.describe("nuclear observables", () => {
  for (const id of RUNS) {
    test(`${id}: model_domain badge and observables match the fixture`, async ({ page }) => {
      const run = fixture<RunFixture>(`nuclear/runs/${id}.json`);
      expect(run.model_domain, "fixture carries model_domain").toBeTruthy();

      await page.goto(`/domains/nuclear.structure/runs/${id}`);
      await expect(page.getByRole("heading", { name: "Nuclear observables" })).toBeVisible();
      // Badge in the observables header (and the provenance copy agrees).
      const header = page.getByRole("heading", { name: "Nuclear observables" }).locator("..");
      await expect(header.getByText(`model_domain · ${run.model_domain}`)).toBeVisible();
      await expect(page.getByText(`model_domain · ${run.model_domain}`)).toHaveCount(2);

      const obs = Object.entries(run.particle_obs ?? {});
      if (obs.length === 0) {
        await expect(page.getByText("No nuclear observables reported.")).toBeVisible();
        return;
      }
      const table = page.getByTestId("nuclear-observables-table");
      await expect(table.locator("tbody tr")).toHaveCount(obs.length);
      for (const [name, o] of obs) {
        const cells = table.locator("tbody tr", { hasText: name }).locator("td");
        await expect(cells.nth(1)).toHaveText(`${sci3(o.value)} ± ${sci3(o.uncertainty)}`);
        await expect(cells.nth(2)).toHaveText(o.units);
        await expect(cells.nth(3)).toHaveText(`${o.provider} / ${o.backend}`);
      }
    });
  }
});
