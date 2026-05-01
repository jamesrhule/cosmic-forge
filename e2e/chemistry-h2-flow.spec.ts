/**
 * Chemistry H2 manifest → run flow Playwright spec (PROMPT 4 v2).
 *
 * Walks the PROMPT 4 v2 DoD assertion: "Submitting H2/STO-3G
 * manifest displays the h2-sto3g fixture's provenance panel."
 *
 * The test flips `FEATURES.qcompassMultiDomain` in dev-mode by
 * intercepting the bundled features.ts response. (The
 * production workbench gates on the compiled-in flag; this spec
 * is dev-only and runs against `npm run dev`.)
 *
 * Running:
 *   npm install --save-dev @playwright/test
 *   npx playwright test --config e2e/playwright.config.ts \
 *     e2e/chemistry-h2-flow.spec.ts
 */

import { expect, test } from "@playwright/test";

test.describe("chemistry H2/STO-3G flow", () => {
  test.beforeEach(async ({ page }) => {
    // Force qcompassMultiDomain = true via a localStorage marker
    // that the FEATURES module checks in dev. (PROMPT 4 v2's
    // DoD assumes the flag is settable at the test boundary;
    // this hook is the cleanest dev-mode override.)
    await page.addInitScript(() => {
      window.localStorage.setItem("qcompass:overrideMultiDomain", "1");
    });
  });

  test("configurator submits H2 manifest and renders provenance", async ({ page }) => {
    await page.goto("/domains/chemistry/configurator");
    // Configurator should load the JSON Schema and render a
    // form with a "molecule" select.
    await expect(page.locator("text=Chemistry configurator")).toBeVisible();

    // Submit at default values (which match the H2 fixture).
    await page.getByRole("button", { name: /Submit run/i }).click();

    // Land on the H2 run detail.
    await page.waitForURL(/domains\/chemistry\/runs\/h2-sto3g/);

    // The provenance panel renders with a non-empty hash and
    // the energy comparison card shows the FCI reference.
    await expect(page.locator("text=Provenance")).toBeVisible();
    await expect(page.locator("text=classical_reference_hash")).toBeVisible();
    await expect(page.locator("text=Energy comparison")).toBeVisible();
    await expect(page.locator('text=/-1\\.137274/')).toBeVisible();
  });
});
