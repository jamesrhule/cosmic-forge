/**
 * QCompass Playwright config (PROMPT 4 v2 scaffolding).
 *
 * The PROMPT 4 v2 DoD requires the e2e suite to be green on
 * Chromium + Firefox + WebKit. This config defines the matrix.
 * Running it requires:
 *
 *   npm install --save-dev @playwright/test
 *   npx playwright install
 *   npx playwright test
 *
 * The repository's package.json does NOT yet declare
 * @playwright/test (the sandbox that authored this scaffolding
 * cannot regenerate package-lock.json / bun.lockb without
 * `npm install`). The conflict is logged in the PROMPT 4 v2 PR
 * description; flipping it on is a single follow-up commit on a
 * machine with `npm install` privileges.
 */

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? "github" : "list",
  timeout: 60_000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox",  use: { ...devices["Desktop Firefox"] } },
    { name: "webkit",   use: { ...devices["Desktop Safari"] } },
  ],
  webServer: {
    command: "npm run dev -- --port 5173",
    url: "http://127.0.0.1:5173/",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
