import { test, expect } from "@playwright/test";

/**
 * `/visualizer/$domain/$id` — domain visualizer route smoke tests.
 *
 * The route falls back to an empty timeline when `VITE_API_URL` is
 * not configured (the cosmic-forge-viz backend is opt-in for dev).
 * The empty-state banner is what we assert on; the multi-browser
 * matrix run is the user's CI step.
 */

test.describe("visualizer domain route", () => {
  test("/visualizer/chemistry/test renders the chemistry layout shell", async ({ page }) => {
    const errors: Error[] = [];
    page.on("pageerror", (err) => errors.push(err));

    const response = await page.goto("/visualizer/chemistry/test");
    expect(response?.status(), "SSR status").toBe(200);
    await expect(page).toHaveTitle(/chemistry\/test — Visualizer/);
    // Domain breadcrumb pill is a stable post-hydration landmark.
    await expect(page.getByText(/chemistry/i, { exact: false })).toBeVisible();
    expect(errors, "no uncaught exceptions").toEqual([]);
  });

  test("/visualizer/cosmology/ucgle-f1-demo points back to legacy route", async ({ page }) => {
    await page.goto("/visualizer/cosmology/ucgle-f1-demo");
    await expect(
      page.getByRole("link", { name: /Open cosmology visualizer/i }),
    ).toBeVisible();
  });

  test("/visualizer/phantom/x returns 404", async ({ page }) => {
    const response = await page.goto("/visualizer/phantom/x");
    expect(response?.status()).toBe(404);
  });
});
