import { expect, test } from "@playwright/test";
import { DOMAINS_URL } from "./urls";

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
