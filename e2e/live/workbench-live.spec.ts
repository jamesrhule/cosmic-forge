/**
 * P4-02 done-when: against a locally started compute API and worker (on a
 * throwaway Postgres), the workbench completes a cosmology run and a
 * chemistry run with zero fixture reads.
 *
 * - The build has VITE_API_URL set (scripts/e2e_live_serve.sh), so every
 *   service uses the generated SDK.
 * - Every `/fixtures/` request is aborted AND recorded; each test asserts
 *   none was attempted. Server-side (SSR) fixture reads are impossible in
 *   this build: `loadFixture` refuses them when VITE_API_URL is set.
 * - The results are real: the test reads the same run back from the API and
 *   checks it was computed by the worker (UCGLE-F1 pipeline output with its
 *   S1–S15 audit; PySCF FCI for H2), never a fixture (R7).
 */
import { expect, test, type Page, type Request } from "@playwright/test";
import { LIVE_API_URL } from "./urls";

function guardFixtures(page: Page): { fixtureReads: string[]; apiCalls: string[] } {
  const fixtureReads: string[] = [];
  const apiCalls: string[] = [];
  void page.route("**/fixtures/**", (route) => {
    fixtureReads.push(route.request().url());
    return route.abort();
  });
  page.on("request", (req: Request) => {
    if (req.url().startsWith(LIVE_API_URL)) apiCalls.push(`${req.method()} ${req.url()}`);
  });
  return { fixtureReads, apiCalls };
}

test.describe("workbench on the live API (P4-02)", () => {
  test("the API and worker are up on Postgres", async ({ request }) => {
    const ready = await request.get(`${LIVE_API_URL}/readyz`);
    expect(ready.status()).toBe(200);
    const body = (await ready.json()) as {
      status: string;
      checks: Record<string, { ok: boolean }>;
    };
    expect(body.status).toBe("ready");
    expect(body.checks.database.ok).toBe(true);
    expect(body.checks.queue.ok).toBe(true);
  });

  test("cosmology: Configurator run completes with zero fixture reads", async ({
    page,
    request,
  }) => {
    const { fixtureReads, apiCalls } = guardFixtures(page);
    await page.goto("/");
    // The benchmark catalog comes from GET /api/benchmarks.
    await expect(page.getByText(/benchmarks available/)).toBeVisible();

    // Smallest real configuration the pipeline supports: V2 defaults at "fast".
    // (The radio labels overlap in the narrow form column, so use the keyboard.)
    const fast = page.locator("#prec-fast");
    await fast.focus();
    await page.keyboard.press("Space");
    await expect(fast).toHaveAttribute("aria-checked", "true");
    const submitted = page.waitForResponse(
      (r) =>
        r.url().startsWith(`${LIVE_API_URL}/api/qcompass/domains/cosmology.ucglef1/runs`) &&
        r.request().method() === "POST",
    );
    await page.getByRole("button", { name: /Run simulation/ }).click();
    const response = await submitted;
    expect(response.status(), "API enqueues and answers 202").toBe(202);
    const { runId } = (await response.json()) as { runId: string };

    const status = page.getByTestId("workbench-run-status");
    await expect(status).toContainText(runId);
    await expect(status).toHaveAttribute("data-status", "completed", { timeout: 240_000 });
    await expect(status).toContainText("η_B =");

    // The worker computed it: the stored run is the UCGLE-F1 pipeline's
    // output, with its audit and the requested precision.
    const stored = await request.get(
      `${LIVE_API_URL}/api/qcompass/domains/cosmology.ucglef1/runs/${runId}`,
    );
    expect(stored.status()).toBe(200);
    const run = (await stored.json()) as {
      status: string;
      synthetic?: boolean;
      payload: {
        result: {
          eta_B: unknown;
          run_result: {
            config: { precision: string };
            audit: { checks: unknown[] };
            eta_B: { value: number | string };
          };
        };
      };
    };
    expect(run.status).toBe("completed");
    expect(run.synthetic ?? false).toBe(false);
    expect(run.payload.result.run_result.config.precision).toBe("fast");
    expect(run.payload.result.run_result.audit.checks.length).toBeGreaterThan(0);
    // The page shows the engine's η_B (a number, or a stored non-finite
    // marker such as "NaN" while P1-08 is open), never a fixture's.
    const etaB = run.payload.result.run_result.eta_B.value;
    expect(["number", "string"]).toContain(typeof etaB);
    if (typeof etaB === "string") await expect(status).toContainText(`η_B = ${etaB}`);

    expect(apiCalls.some((c) => c.startsWith("GET ") && c.includes("/stream"))).toBe(true);
    expect(fixtureReads, "no /fixtures/ request was attempted").toEqual([]);
  });

  test("chemistry: H2 manifest run completes with zero fixture reads", async ({
    page,
    request,
  }) => {
    const { fixtureReads } = guardFixtures(page);
    await page.goto("/domains/chemistry.molecular/configurator");
    await expect(
      page.getByRole("heading", { level: 1, name: "Chemistry · Molecular" }),
    ).toBeVisible();

    // The form is the chemistry plugin's schema from GET …/schema.
    await page.locator("#root_molecule").fill("H2");
    await page.locator("#root_backend_preference").selectOption("classical");
    const submitted = page.waitForResponse(
      (r) =>
        r.url().startsWith(`${LIVE_API_URL}/api/qcompass/domains/chemistry.molecular/runs`) &&
        r.request().method() === "POST",
    );
    await page.getByRole("button", { name: /^Submit$/ }).click();
    const response = await submitted;
    expect(response.status()).toBe(202);
    const { runId } = (await response.json()) as { runId: string };

    await page.waitForURL(new RegExp(`/domains/chemistry\\.molecular/runs/${runId}$`));
    await expect(page.getByTestId("run-status")).toHaveAttribute("data-status", "completed", {
      timeout: 180_000,
    });
    await expect(page.getByRole("heading", { name: "Provenance", exact: true })).toBeVisible();

    const stored = await request.get(
      `${LIVE_API_URL}/api/qcompass/domains/chemistry.molecular/runs/${runId}`,
    );
    const run = (await stored.json()) as {
      status: string;
      provenance: { classical_reference_hash: string };
      payload: { result: unknown; classical_reference_hash: string };
    };
    expect(run.status).toBe("completed");
    expect(run.payload.result).toBeTruthy();
    // The classical reference the worker computed is what the page shows.
    expect(run.provenance.classical_reference_hash).not.toBe("");
    await expect(page.getByText(run.provenance.classical_reference_hash)).toBeVisible();

    expect(fixtureReads, "no /fixtures/ request was attempted").toEqual([]);
  });
});
