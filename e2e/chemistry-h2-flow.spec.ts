/**
 * Chemistry H2 manifest → run flow (PROMPT 4 v2, ported in P0-06).
 *
 * DoD: "Submitting H2/STO-3G manifest displays the h2-sto3g fixture's
 * provenance panel." Runs against the all-domains production build (the
 * chemistry domain is behind VITE_QCOMPASS_MULTIDOMAIN + _CHEMISTRY).
 */
import { expect, test } from "@playwright/test";
import { DOMAINS_URL } from "./urls";

test.use({ baseURL: DOMAINS_URL });

test.describe("chemistry H2/STO-3G flow", () => {
  test("configurator submits H2 manifest and renders provenance", async ({ page }) => {
    await page.goto("/domains/chemistry.molecular/configurator");
    await expect(
      page.getByRole("heading", { level: 1, name: "Chemistry · Molecular" }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: "Configurator" })).toHaveClass(/border-primary/);

    // Submit at default values; the fixture path resolves to h2-sto3g.
    await page.getByRole("button", { name: /^Submit$/ }).click();
    await page.waitForURL(/\/domains\/chemistry\.molecular\/runs\/h2-sto3g$/);

    // Provenance panel with the fixture's classical-reference hash, and the
    // energy comparison with the FCI classical reference.
    await expect(page.getByRole("heading", { name: "Provenance", exact: true })).toBeVisible();
    await expect(page.getByText("Classical reference")).toBeVisible();
    await expect(page.getByText("cls-8a54a2e7")).toBeVisible();
    await expect(page.getByText("Energy comparison")).toBeVisible();
    await expect(page.getByText("-1.137158 Ha")).toBeVisible();
  });
});
