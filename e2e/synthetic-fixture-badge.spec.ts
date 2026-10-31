import { expect, test } from "@playwright/test";
import { DEFAULT_URL, DOMAINS_URL } from "./urls";

// PLAN.md correction 8 (R7): every domain run page that renders a bundled
// synthetic fixture says so in its header, and the run list says so per row.
const RUNS: Array<[string, string]> = [
  ["amo.rydberg", "blockade-ground"],
  ["chemistry.molecular", "femoco-toy"],
  ["condmat.lattice", "heisenberg-1d"],
  ["gravity.syk", "jt-gravity"],
  ["hep.lattice", "schwinger-1plus1d"],
  ["nuclear.structure", "ncsm-4he"],
  ["statmech.sampling", "qae-toy"],
];

const LABEL = "Synthetic fixture — not a computed result";

test.use({ baseURL: DOMAINS_URL });

test.describe("synthetic fixture badge (R7)", () => {
  for (const [domain, run] of RUNS) {
    test(`${domain}/runs/${run} header shows the synthetic badge`, async ({ page }) => {
      await page.goto(`/domains/${domain}/runs/${run}`);
      const header = page.getByTestId("run-detail-header");
      await expect(header).toBeVisible();
      await expect(header.getByTestId("synthetic-fixture-badge")).toHaveText(LABEL);
    });
  }

  test("run list rows carry the badge", async ({ page }) => {
    await page.goto(`/domains/hep.lattice/runs`);
    const badges = page.getByTestId("synthetic-fixture-badge");
    await expect(badges.first()).toBeVisible();
    await expect(badges.first()).toHaveText(LABEL);
  });
});

// Decision 13a (R7): the cosmology V2 fixture (kawai-kim-natural) carries
// results the pipeline never computed. Its run views and the home-page F1
// summary that shows its numbers carry the badge. Default build (no flags).
test.describe("cosmology synthetic fixture badge (Decision 13a)", () => {
  test.use({ baseURL: DEFAULT_URL });

  test("cosmology run page header shows the badge", async ({ page }) => {
    await page.goto("/visualizer/kawai-kim-natural");
    const header = page.getByTestId("cosmology-run-header");
    await expect(header).toBeVisible();
    await expect(header.getByTestId("synthetic-fixture-badge")).toHaveText(LABEL);
  });

  test("cosmology run list row shows the badge", async ({ page }) => {
    await page.goto("/visualizer");
    const row = page.getByRole("link", { name: /kawai-kim-natural/ });
    await expect(row.getByTestId("synthetic-fixture-badge")).toHaveText(LABEL);
  });

  test("home-page F1 summary of the fixture's numbers shows the badge", async ({ page }) => {
    await page.goto("/");
    const summary = page.getByTestId("f1-summary-header");
    await expect(summary).toBeVisible();
    await expect(summary.getByTestId("synthetic-fixture-badge")).toHaveText(LABEL);
  });
});
