import { defineConfig, devices } from "@playwright/test";

/**
 * Smoke-only Playwright config. Boots the production build via
 * `bun run preview`, then walks the public-facing routes to confirm
 * the SSR shell renders, JS hydrates, and key landmarks exist.
 *
 * CI invokes: `bunx playwright test`. Locally: `bun run test:e2e`.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:4173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "bun run build && bun run preview --port 4173 --host 127.0.0.1",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    stdout: "pipe",
    stderr: "pipe",
  },
});
