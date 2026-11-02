import { defineConfig, devices } from "@playwright/test";
import { DEFAULT_URL, DOMAINS_URL } from "./e2e/urls";

/**
 * The single Playwright config (P0-06): Chromium, Firefox and WebKit against
 * the PRODUCTION Worker build served by workerd (`wrangler dev`), via
 * `scripts/e2e_serve.sh`. That script serves two builds: the default
 * (no flags) at DEFAULT_URL and all QCompass domains at DOMAINS_URL.
 *
 * CI: `bunx playwright test`. Locally: `bun run test:e2e`.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }], ["list"]] : "list",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  // Snapshot baselines are committed per browser under e2e/__screenshots__.
  // A browser with no committed baseline yet writes one instead of failing.
  // Firefox and WebKit baselines come from the first CI run (they can't be
  // generated in the authoring sandbox); see docs/build/lanes/P0-06-e2e.md.
  updateSnapshots: "missing",
  snapshotPathTemplate: "{testDir}/__screenshots__/{projectName}/{testFilePath}/{arg}{ext}",
  use: {
    baseURL: DEFAULT_URL,
    viewport: { width: 1440, height: 900 },
    reducedMotion: "reduce",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 900 },
        // Sandboxes with a preinstalled Chromium of a different revision set
        // PW_CHROMIUM_PATH; CI uses the browser `playwright install` fetched.
        launchOptions: process.env.PW_CHROMIUM_PATH
          ? { executablePath: process.env.PW_CHROMIUM_PATH }
          : {},
      },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"], viewport: { width: 1440, height: 900 } },
    },
    {
      name: "webkit",
      use: { ...devices["Desktop Safari"], viewport: { width: 1440, height: 900 } },
    },
  ],
  webServer: {
    command: "bash scripts/e2e_serve.sh",
    // The script starts the domains server only after the default one answers.
    url: `${DOMAINS_URL}/`,
    reuseExistingServer: !process.env.CI,
    timeout: 600_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
