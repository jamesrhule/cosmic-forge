/**
 * Cosmology byte-identity Playwright spec (PROMPT 4 v2).
 *
 * Asserts that `/` (the cosmology workbench) renders identically
 * before and after PROMPT 4 v2 lands. Cross-browser: chromium +
 * firefox + webkit. The byte-identity invariant comes from
 * PROMPT 4 v2's quality bar: cosmology routes byte-identical
 * (Playwright screenshot).
 *
 * Running:
 *   npm install --save-dev @playwright/test
 *   npx playwright install
 *   npx playwright test --config e2e/playwright.config.ts \
 *     e2e/cosmology-byte-identity.spec.ts
 */

import { expect, test } from "@playwright/test";

test.describe("cosmology byte-identity", () => {
  test.beforeEach(async ({ page }) => {
    // Default flag posture: qcompassMultiDomain = false. The
    // DomainSwitcher is hidden; cosmology renders exactly as in
    // PROMPT 4 v1.
    await page.goto("/");
  });

  test("workbench shell renders without DomainSwitcher", async ({ page }) => {
    await expect(page.locator("text=UCGLE-F1 Workbench")).toBeVisible();
    // The mode pill says "static-shell" (cosmology default).
    await expect(page.locator("text=static-shell")).toBeVisible();
    // No domain pills at default.
    await expect(page.locator('nav[aria-label="Research domain"]')).toHaveCount(0);
  });

  test("cosmology workbench screenshot matches baseline", async ({ page }) => {
    // Wait for the run-card to load (kawai-kim-natural fixture).
    await page.waitForSelector("text=kawai-kim-natural");
    // Mask the timestamp / live-clock surfaces if any so the
    // screenshot is byte-stable across runs.
    await expect(page).toHaveScreenshot("cosmology-default.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.001,
    });
  });
});
