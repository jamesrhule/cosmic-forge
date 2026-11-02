/**
 * Cosmology regression (P0-06): the default production build renders the
 * cosmology workbench with real content, never an error page, and with the
 * fixture's numbers. Complements the pixel baselines in
 * cosmology-byte-identity.spec.ts with assertions that name what broke.
 */
import { expect, test } from "@playwright/test";
import { fixture } from "./fixture-data";
import { ERROR_TEXT } from "./stable";

const benchmarks = fixture<{ benchmarks: unknown[] }>("benchmarks.json");

function collectErrors(page: import("@playwright/test").Page): Error[] {
  const errors: Error[] = [];
  page.on("pageerror", (err) => errors.push(err));
  return errors;
}

test.describe("cosmology regression", () => {
  test("/ renders the configurator from SSR without errors", async ({ page }) => {
    const errors = collectErrors(page);
    const response = await page.goto("/");
    expect(response?.status(), "SSR status").toBe(200);
    // SSR HTML already carries the configurator (P0-05: server fixture reads work).
    const html = (await response?.text()) ?? "";
    expect(html).toContain("F1 — primary mechanism");
    expect(html).not.toMatch(/fetch failed/);

    await expect(page.getByText("F1 — primary mechanism")).toBeVisible();
    await expect(page.locator(".katex").first()).toBeVisible();
    await expect(page.getByText("Active context")).toBeVisible();
    await expect(
      page.getByText(`${benchmarks.benchmarks.length} benchmarks available`),
    ).toBeVisible();
    await expect(page.getByText(ERROR_TEXT)).toHaveCount(0);
    expect(errors, "no uncaught exceptions").toEqual([]);
  });

  test("/visualizer lists the baked cosmology runs", async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto("/visualizer");
    await expect(page.getByRole("heading", { name: /Visualizer — pick a run/ })).toBeVisible();
    await expect(page.getByText("kawai-kim-natural").first()).toBeVisible();
    await expect(page.getByText(ERROR_TEXT)).toHaveCount(0);
    expect(errors).toEqual([]);
  });

  test("/visualizer/kawai-kim-natural renders all six panels", async ({ page }) => {
    const errors = collectErrors(page);
    const response = await page.goto("/visualizer/kawai-kim-natural");
    expect(response?.status()).toBe(200);
    // Panel landmarks from the six-panel workbench.
    await expect(page.getByText("source").first()).toBeVisible();
    await expect(page.getByText(/integrand · running ∫/)).toBeVisible();
    await expect(page.getByText(/chiral GW → η_B/)).toBeVisible();
    await expect(page.getByText(/F1 · Scalar–GB–CS \(primary\)/)).toBeVisible();
    await expect(page.getByText("τ (e-folds)")).toBeVisible();
    // Transport bar at frame 0 of the baked timeline.
    await expect(page.getByText(/^000 \/ \d{3}$/)).toBeVisible();
    // No panel may fall back to its error state (P0-05 fixed the Phase space
    // crash on SSR-dehydrated timelines).
    await expect(page.getByText(ERROR_TEXT)).toHaveCount(0);
    expect(errors).toEqual([]);
  });
});
