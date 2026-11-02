import type { Page } from "@playwright/test";

/**
 * Deterministic-render helpers shared by the screenshot specs (P0-06).
 */

/** Freeze CSS animations/transitions and the caret. */
export async function freezeMotion(page: Page): Promise<void> {
  await page.addStyleTag({
    content:
      "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}",
  });
}

/**
 * Build-stamped surfaces that legitimately change on every commit or day
 * (commit SHA and build date in the footer). Masked in screenshots.
 */
export function buildStamps(page: Page) {
  return [page.locator("footer")];
}

/** Text that only appears when a page failed to load. */
export const ERROR_TEXT =
  /Something went wrong|fetch failed|Couldn't load|Couldn't render|Cannot read properties/;
