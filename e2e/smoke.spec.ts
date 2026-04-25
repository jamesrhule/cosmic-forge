import { test, expect } from "@playwright/test";

/**
 * Smoke tests — the bare minimum we don't want to ship broken.
 *
 * Each test asserts:
 *   1. HTTP 200 from the SSR response
 *   2. The expected <title> made it into the document
 *   3. A route-level landmark element exists after hydration
 *   4. No fatal page errors (uncaught exceptions, failed chunks)
 */

test.describe("smoke", () => {
  test("/ — Configurator route renders", async ({ page }) => {
    const errors: Error[] = [];
    page.on("pageerror", (err) => errors.push(err));

    const response = await page.goto("/");
    expect(response?.status(), "SSR status").toBe(200);
    await expect(page).toHaveTitle(/Configurator — UCGLE-F1 Workbench/);
    await expect(page.getByRole("link", { name: /UCGLE-F1 Workbench/ })).toBeVisible();
    expect(errors, "no uncaught exceptions").toEqual([]);
  });

  test("/visualizer — index lists baked runs", async ({ page }) => {
    const errors: Error[] = [];
    page.on("pageerror", (err) => errors.push(err));

    const response = await page.goto("/visualizer");
    expect(response?.status(), "SSR status").toBe(200);
    await expect(page).toHaveTitle(/Visualizer/);
    // Either run cards or the empty-state — both prove the route mounted.
    const heading = page.getByRole("heading", { name: /Visualizer — pick a run|No visualizations available/ });
    await expect(heading).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("/login — sign-in form renders with email + password fields", async ({ page }) => {
    const errors: Error[] = [];
    page.on("pageerror", (err) => errors.push(err));

    const response = await page.goto("/login");
    expect(response?.status()).toBe(200);
    await expect(page).toHaveTitle(/Sign in — UCGLE-F1 Workbench/);
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: /Sign in/i })).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("/nope — 404 route renders the not-found shell with noindex", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    await expect(page).toHaveTitle(/404 — Page not found/);
    const robots = page.locator('meta[name="robots"]');
    await expect(robots).toHaveAttribute("content", /noindex/);
  });
});
