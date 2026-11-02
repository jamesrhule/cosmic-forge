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
            config: { potential: { kind: string; params: Record<string, number> } };
            audit: { checks: unknown[] };
            eta_B: { value: number | string | null; refusal?: string | null };
          } & { config: { precision: string } };
        };
      };
    };
    expect(run.status).toBe("completed");
    expect(run.synthetic ?? false).toBe(false);
    expect(run.payload.result.run_result.config.precision).toBe("fast");
    // The DEFAULT config ran: Decision 15's paper benchmark in Configurator units.
    const potential = run.payload.result.run_result.config.potential;
    expect(potential.kind).toBe("natural");
    expect(potential.params).toEqual({ f: 2.118624e19, Lambda4: 2.563334027300118e-9 });
    expect(run.payload.result.run_result.audit.checks.length).toBeGreaterThan(0);
    // The page shows the engine's η_B, never a fixture's: the published value,
    // or, while the engine refuses it (pipeline.eta_B_refusal; P1-04), the
    // refusal with its reason and no number.
    const eta = run.payload.result.run_result.eta_B;
    const shown = page.getByTestId("workbench-run-eta-b");
    if (eta.refusal) {
      expect(eta.value === null || eta.value === "NaN").toBe(true);
      await expect(shown).toHaveText(`η_B not published — ${eta.refusal}`);
    } else {
      expect(typeof eta.value).toBe("number");
      expect(Number.isFinite(eta.value)).toBe(true);
      await expect(shown).toContainText("η_B =");
    }

    expect(apiCalls.some((c) => c.startsWith("GET ") && c.includes("/stream"))).toBe(true);
    expect(fixtureReads, "no /fixtures/ request was attempted").toEqual([]);
  });

  // Critic BLOCKER 3 / c5: the cosmology visualizer views in an API build list
  // the tenant's real runs (or say there are none) and read no fixture: no
  // bundled demo catalogue, no "240 frames" metadata, no crash on the API's
  // visualization shape, and the synthetic bake is labelled as such.
  test("cosmology visualizers list real runs with zero fixture reads", async ({
    page,
    request,
  }) => {
    const { fixtureReads, apiCalls } = guardFixtures(page);
    const listed = await request.get(`${LIVE_API_URL}/api/qcompass/domains/cosmology.ucglef1/runs`);
    expect(listed.status()).toBe(200);
    const runIds = ((await listed.json()) as Array<{ id: string }>).map((r) => r.id);

    await page.goto("/visualizer");
    await expect(page.getByTestId("visualizer-api-index")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Visualizer — your cosmology runs" }),
    ).toBeVisible();
    if (runIds.length === 0) {
      await expect(page.getByText("No cosmology runs yet")).toBeVisible();
    } else {
      const cards = page.getByTestId("visualizer-api-run");
      await expect(cards).toHaveCount(runIds.length);
      for (const id of runIds) await expect(cards.filter({ hasText: id })).toHaveCount(1);
    }
    const index = (await page.textContent("main")) ?? "";
    expect(index).not.toMatch(/240 frames|k-modes|baked GPU buffers/);
    for (const bundled of ["kawai-kim-natural", "starobinsky-standard", "gb-off-control"]) {
      expect(index).not.toContain(bundled);
    }
    expect(apiCalls.some((c) => c.endsWith("/api/qcompass/domains/cosmology.ucglef1/runs"))).toBe(
      true,
    );

    if (runIds.length > 0) {
      // A computed run has no baked six-panel timeline until P4-04: the page
      // says so instead of replaying a demo.
      await page.getByTestId("visualizer-api-run").filter({ hasText: runIds[0] }).click();
      await expect(page.getByTestId("visualizer-run-not-found")).toContainText("P4-04");

      // The cosmology domain visualizer renders the API's (synthetic) bake,
      // labelled, without crashing on its shape.
      await page.goto("/domains/cosmology.ucglef1/visualizer");
      await page
        .getByRole("link", { name: new RegExp(runIds[0]) })
        .first()
        .click();
      const card = page.getByTestId("visualizer-coming-online");
      await expect(card).toBeVisible();
      await expect(card.getByTestId("synthetic-fixture-label")).toHaveText(
        "Synthetic frames — not a computed result. Real-run timelines arrive with P4-04.",
      );
    } else {
      await page.goto("/domains/cosmology.ucglef1/visualizer");
      await expect(page.getByText("Pick a run to visualize.")).toBeVisible();
    }
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
