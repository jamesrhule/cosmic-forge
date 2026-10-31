/**
 * Cosmology byte-identity (PROMPT 4 v2, ported to the single config in P0-06).
 *
 * The cosmology routes must not change pixel-for-pixel in the default build
 * (R19). Baselines live under e2e/__screenshots__/<browser>/ and follow the
 * re-anchored R19 baseline (docs/build/evidence/screens/r19-baseline):
 * main's own render of `/` and `/visualizer/kawai-kim-natural` was an error
 * page, so the first correct render is the baseline. The build-stamped
 * footer (commit SHA, build date) is masked.
 */
import { expect, test } from "@playwright/test";
import { buildStamps, ERROR_TEXT, freezeMotion } from "./stable";

test.describe("cosmology byte-identity", () => {
  test("default build: cosmology is the only enabled domain", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: "UCGLE-F1 Workbench" })).toBeVisible();
    // Main ships the domain selector (domainsRegistry on by default). With
    // the QCompass flags off it lists cosmology only, enabled and active.
    const selector = page.getByRole("button", { name: "Select physics domain" });
    await expect(selector).toContainText("Cosmology");
    await selector.click();
    // The QCompass domains don't register at all with their flags off.
    const items = page.getByRole("menuitem");
    await expect(items).toHaveCount(1);
    await expect(items.first()).toContainText("Cosmology · UCGLE-F1");
    await expect(items.first()).not.toHaveAttribute("aria-disabled", "true");
  });

  const ROUTES: Array<{
    path: string;
    name: string;
    ready: (p: import("@playwright/test").Page) => Promise<void>;
  }> = [
    {
      path: "/",
      name: "cosmology-default.png",
      ready: async (p) => {
        await expect(p.getByText(/benchmarks available/)).toBeVisible();
      },
    },
    {
      path: "/visualizer",
      name: "cosmology-visualizer-index.png",
      ready: async (p) => {
        await expect(p.getByRole("heading", { name: /Visualizer — pick a run/ })).toBeVisible();
      },
    },
    {
      path: "/visualizer/kawai-kim-natural",
      name: "cosmology-visualizer-kawai-kim-natural.png",
      ready: async (p) => {
        await expect(p.getByText("kawai-kim-natural").first()).toBeVisible();
        await expect(p.getByText(/F1 · Scalar–GB–CS/)).toBeVisible();
      },
    },
  ];

  for (const r of ROUTES) {
    test(`${r.path} screenshot matches baseline`, async ({ page }) => {
      await page.goto(r.path);
      await r.ready(page);
      await page.waitForLoadState("networkidle");
      await freezeMotion(page);
      await expect(page.getByText(ERROR_TEXT)).toHaveCount(0);
      await expect(page).toHaveScreenshot(r.name, {
        fullPage: true,
        mask: buildStamps(page),
        maxDiffPixelRatio: 0.001,
      });
    });
  }
});
