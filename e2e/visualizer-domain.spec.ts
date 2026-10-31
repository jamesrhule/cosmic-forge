import { test, expect } from "@playwright/test";

/**
 * `/domains/$domain/visualizer/$id` — the domain visualizer route.
 *
 * P0-02 folded the router-branch `/visualizer/$domain/$id` route into
 * this one. Without `VITE_API_URL` the route renders the bundled
 * `public/fixtures/visualizations/<id>.json` timeline, labelled as a
 * synthetic fixture (R7). Every domain with a bundled timeline is
 * checked for its panel titles; cosmology keeps its existing view.
 *
 * The QCompass domains are behind build-time flags
 * (`VITE_QCOMPASS_MULTIDOMAIN` + one `VITE_QCOMPASS_<DOMAIN>` each,
 * default off → 404). The per-domain tests run when the server under
 * test was started with those flags and `E2E_QCOMPASS_DOMAINS=1` is set
 * for the test runner; the flag-independent tests always run.
 */

const DOMAINS_ENABLED = process.env.E2E_QCOMPASS_DOMAINS === "1";

const DOMAINS: Array<{ domain: string; id: string; panels: RegExp[] }> = [
  {
    domain: "chemistry.molecular",
    id: "h2-sto3g",
    panels: [
      /Orbital occupation/,
      /SCF energy convergence/,
      /Slater flow/,
      /Active Hamiltonian terms/,
    ],
  },
  {
    domain: "condmat.lattice",
    id: "hubbard-4x4",
    panels: [/Lattice \+ bond strengths/, /OTOC butterfly cone/, /Spectral function A\(k, ω\)/],
  },
  {
    domain: "hep.lattice",
    id: "schwinger-1plus1d",
    panels: [
      /Gauge plaquettes/,
      /Chiral condensate/,
      /String tension \/ breaking/,
      /^Particle observables$/,
    ],
  },
  {
    domain: "nuclear.structure",
    id: "0nbb-1plus1d-toy",
    panels: [/Shell occupation/, /LNV indicator/, /model_domain · 1\+1D_toy/],
  },
  {
    domain: "amo.rydberg",
    id: "rydberg-mis",
    panels: [/Neutral-atom array/, /Blockade correlations/],
  },
];

test.describe("domain visualizer route", () => {
  for (const { domain, id, panels } of DOMAINS) {
    test.describe(() => {
      test.skip(!DOMAINS_ENABLED, "server built without VITE_QCOMPASS_* domain flags");
      test(`/domains/${domain}/visualizer/${id} renders its panels`, async ({ page }) => {
        const errors: Error[] = [];
        page.on("pageerror", (err) => errors.push(err));

        const response = await page.goto(`/domains/${domain}/visualizer/${id}`);
        expect(response?.status(), "SSR status").toBe(200);
        await expect(page).toHaveTitle(new RegExp(`${id} viz — QCompass`));
        await expect(page.getByTestId("domain-visualizer")).toBeVisible();
        await expect(page.getByTestId("synthetic-fixture-label")).toBeVisible();
        for (const title of panels) {
          await expect(page.getByText(title).first()).toBeVisible();
        }
        expect(errors, "no uncaught exceptions").toEqual([]);
      });
    });
  }

  test("a run with no timeline shows the empty state, not invented frames", async ({ page }) => {
    test.skip(!DOMAINS_ENABLED, "server built without VITE_QCOMPASS_* domain flags");
    await page.goto("/domains/chemistry.molecular/visualizer/no-such-run");
    await expect(page.getByText(/No timeline data available/)).toBeVisible();
  });

  test("cosmology keeps its existing visualizer view", async ({ page }) => {
    await page.goto("/domains/cosmology.ucglef1/visualizer/kawai-kim-natural");
    await expect(page.getByTestId("domain-visualizer")).toHaveCount(0);
    await expect(
      page.getByTestId("visualizer-coming-online").or(page.getByText(/Loading timeline/)),
    ).toBeVisible();
  });

  test("/domains/phantom/visualizer/x returns 404", async ({ page }) => {
    const response = await page.goto("/domains/phantom/visualizer/x");
    expect(response?.status()).toBe(404);
  });

  test("the folded /visualizer/$domain/$id path no longer exists", async ({ page }) => {
    const response = await page.goto("/visualizer/chemistry/test");
    expect(response?.status()).toBe(404);
  });
});
