/**
 * Gravity provenance guard (P0-06, R18). A learned-Hamiltonian run without a
 * provenance warning must refuse to render; one with a warning renders the
 * warning banner first.
 *
 * The negative case uses a SYNTHETIC fixture (e2e/fixtures, `"synthetic":
 * true`, R7) served by request interception: it deliberately violates the
 * fixture contract, so it must never ship under public/fixtures (where
 * backend/tests/test_lovable_contract.py would rightly reject it).
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import { DOMAINS_URL } from "./urls";
import { fixture, type RunFixture } from "./fixture-data";

test.use({ baseURL: DOMAINS_URL });

const GUARD_FIXTURE = readFileSync(
  join(process.cwd(), "e2e", "fixtures", "gravity-learned-no-warning.json"),
  "utf8",
);

test.describe("gravity provenance guard", () => {
  test("learned Hamiltonian with no warning refuses to render", async ({ page }) => {
    const parsed = JSON.parse(GUARD_FIXTURE) as RunFixture & { synthetic: boolean };
    expect(parsed.synthetic).toBe(true);
    expect(parsed.is_learned_hamiltonian).toBe(true);
    expect(parsed.provenance.provenance_warning).toBe("");

    await page.route("**/fixtures/gravity/runs/guard-learned-no-warning.json", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: GUARD_FIXTURE }),
    );
    await page.goto("/domains/gravity.syk/runs/guard-learned-no-warning");

    await expect(page.getByTestId("gravity-guard-blocked")).toBeVisible();
    await expect(page.getByText("Render blocked — missing provenance warning")).toBeVisible();
    // Nothing from the result itself is shown.
    await expect(page.getByText(/SHOULD NOT RENDER/)).toHaveCount(0);
    await expect(page.getByTestId("gravity-result-with-warning")).toHaveCount(0);
    await expect(page.getByTestId("gravity-result")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Provenance", exact: true })).toHaveCount(0);
  });

  test("learned Hamiltonian with a warning shows the warning", async ({ page }) => {
    const run = fixture<RunFixture>("gravity/runs/learned-syk.json");
    const warning = String(run.provenance.provenance_warning);
    expect(warning.trim().length).toBeGreaterThan(0);

    await page.goto("/domains/gravity.syk/runs/learned-syk");
    await expect(page.getByTestId("gravity-result-with-warning")).toBeVisible();
    await expect(page.getByTestId("gravity-guard-blocked")).toHaveCount(0);
    await expect(page.getByText(warning).first()).toBeVisible();
  });

  test("first-principles SYK renders without the learned warning", async ({ page }) => {
    await page.goto("/domains/gravity.syk/runs/syk-sparse");
    await expect(page.getByTestId("gravity-result")).toBeVisible();
    await expect(page.getByTestId("gravity-guard-blocked")).toHaveCount(0);
  });
});
