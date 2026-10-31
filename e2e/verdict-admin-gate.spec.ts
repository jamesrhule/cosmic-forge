/**
 * Verdict admin gate (P0-06). A non-admin never sees the Phase-3 verdict.
 *
 * - Default build (auth + multi-domain flags off): the route doesn't exist.
 * - All-domains build: a signed-out visitor gets "Admin only", no verdict
 *   rows, and the verdict data is never requested. Choosing the admin
 *   tenant in the (client-side) tenant picker is not enough: the page also
 *   requires the verified Supabase `admin` role.
 */
import { expect, test } from "@playwright/test";
import { DEFAULT_URL, DOMAINS_URL } from "./urls";

test.describe("verdict admin gate", () => {
  test("default build: /admin/verdict is a 404", async ({ page }) => {
    const response = await page.goto(`${DEFAULT_URL}/admin/verdict`);
    expect(response?.status()).toBe(404);
    await expect(page.getByText("QCompass · Phase-3 verdict")).toHaveCount(0);
  });

  test("signed-out visitor sees Admin only and no verdict data", async ({ page }) => {
    const verdictRequests: string[] = [];
    page.on("request", (r) => {
      if (/\/fixtures\/verdict\/|\/api\/[^?]*verdict/.test(r.url())) verdictRequests.push(r.url());
    });
    await page.goto(`${DOMAINS_URL}/admin/verdict`);
    await expect(page.getByTestId("verdict-blocked")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Admin only" })).toBeVisible();
    await expect(page.getByText("QCompass · Phase-3 verdict")).toHaveCount(0);
    await expect(page.locator("table")).toHaveCount(0);
    await page.waitForLoadState("networkidle");
    expect(verdictRequests, "verdict data requested by a non-admin").toEqual([]);
  });

  test("picking the admin tenant without an admin session is still blocked", async ({ page }) => {
    await page.goto(`${DOMAINS_URL}/admin/verdict`);
    await expect(page.getByTestId("verdict-blocked")).toBeVisible();
    // Tenant picker in the QCompass auth strip.
    await page.getByRole("combobox").first().click();
    const admin = page.getByRole("option", { name: /QCompass admin/ });
    await expect(admin).toBeVisible();
    await admin.click();
    await expect(page.getByTestId("verdict-blocked")).toBeVisible();
    await expect(page.locator("table")).toHaveCount(0);
  });

  // Correction 9 DoD: the verdict data is no longer a public static file.
  for (const base of [DEFAULT_URL, DOMAINS_URL]) {
    for (const path of [
      "/fixtures/verdict/sample-verdict.yaml.json",
      "/fixtures/verdict/sample-verdict.yaml",
      "/fixtures/verdict/sample-verdict.md",
    ]) {
      test(`unauthenticated GET ${path} on ${base} is 404`, async ({ request }) => {
        const res = await request.get(`${base}${path}`);
        expect(res.status()).toBe(404);
      });
    }
  }
});
