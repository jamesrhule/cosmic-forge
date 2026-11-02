/**
 * Domain shell "coming online" (P0-06).
 *
 * Domains without a dedicated result renderer (condmat, amo, statmech) show
 * the DomainShell with the coming-online card, which still consumes the run
 * fixture end to end. A domain whose flag is off is not reachable at all
 * (404 from `resolveDomain`), and never renders a half-built shell.
 */
import { expect, test } from "@playwright/test";
import { DEFAULT_URL, DOMAINS_URL } from "./urls";
import { fixture, sci3, type RunFixture } from "./fixture-data";

const CASES: Array<{ domain: string; dir: string; id: string; label: string }> = [
  { domain: "condmat.lattice", dir: "condmat", id: "hubbard-4x4", label: "Condensed Matter" },
  { domain: "amo.rydberg", dir: "amo", id: "rydberg-mis", label: "AMO" },
  { domain: "statmech.sampling", dir: "statmech", id: "qae-toy", label: "Stat Mech" },
];

const FOOTER = "Rich rendering coming online in a follow-up pass.";

test.describe("domain shell coming online", () => {
  for (const c of CASES) {
    test(`${c.domain}/${c.id}: shell + coming-online card with fixture fields`, async ({
      page,
    }) => {
      const run = fixture<RunFixture>(`${c.dir}/runs/${c.id}.json`);
      await page.goto(`${DOMAINS_URL}/domains/${c.domain}/runs/${c.id}`);

      // The shell: domain heading and the four section tabs.
      await expect(page.getByRole("heading", { level: 1 })).toContainText(c.label);
      const tabs = page.getByRole("navigation", { name: /sections/ });
      for (const t of ["Configurator", "Runs", "Research", "Visualizer"]) {
        await expect(tabs.getByRole("link", { name: t })).toBeVisible();
      }

      // The coming-online card, fed by the fixture.
      await expect(page.getByText(FOOTER)).toBeVisible();
      await expect(page.getByRole("heading", { name: run.label })).toBeVisible();
      for (const [k, v] of Object.entries(run.payload)) {
        if (k === "summary" || (typeof v !== "number" && typeof v !== "string")) continue;
        const shown = typeof v === "number" ? sci3(v) : v;
        await expect(page.getByText(k, { exact: true })).toBeVisible();
        await expect(page.getByText(shown, { exact: true }).first()).toBeVisible();
      }
      await expect(page.getByRole("heading", { name: "Provenance", exact: true })).toBeVisible();
    });

    test(`${c.domain}: flag off → not reachable`, async ({ page }) => {
      const response = await page.goto(`${DEFAULT_URL}/domains/${c.domain}/runs/${c.id}`);
      expect(response?.status()).toBe(404);
      await expect(page.getByText(FOOTER)).toHaveCount(0);
    });
  }
});
