import { defineConfig, devices } from "@playwright/test";
import { LIVE_API_URL, LIVE_WEB_URL } from "./e2e/live/urls";

/**
 * Live-API Playwright project (P4-02): the workbench built with
 * VITE_API_URL against a local compute API + worker on a throwaway Postgres.
 * Every service uses the generated SDK; specs block `/fixtures/` and assert
 * nothing tried to read one.
 *
 * CI: the `e2e-live` job (`bunx playwright test -c playwright.live.config.ts`).
 * Locally: the same command; Postgres is started by the backend's test
 * harness unless TEST_DATABASE_URL is set.
 */
export default defineConfig({
  testDir: "./e2e/live",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // One worker: the dev tenant's plan allows one concurrent job (P3-05).
  workers: 1,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }], ["list"]] : "list",
  // A real UCGLE-F1 run at precision "fast" takes ~15 s on a CI runner.
  timeout: 300_000,
  expect: { timeout: 30_000 },
  use: {
    baseURL: LIVE_WEB_URL,
    viewport: { width: 1440, height: 900 },
    reducedMotion: "reduce",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium-live",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
        launchOptions: process.env.PW_CHROMIUM_PATH
          ? { executablePath: process.env.PW_CHROMIUM_PATH }
          : {},
      },
    },
  ],
  webServer: [
    {
      command: "uv run --frozen python scripts/live_stack.py",
      url: `${LIVE_API_URL}/readyz`,
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command: "bash scripts/e2e_live_serve.sh",
      url: `${LIVE_WEB_URL}/`,
      reuseExistingServer: !process.env.CI,
      timeout: 600_000,
      stdout: "pipe",
      stderr: "pipe",
    },
  ],
});
