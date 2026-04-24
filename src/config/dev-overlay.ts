/**
 * Dev-only overlay flag.
 *
 * Enable by either:
 *   - localStorage.setItem("ucgle.devOverlay", "1") then reload, or
 *   - append `?devOverlay=1` to the URL once (persisted to localStorage
 *     by `persistDevOverlayFromUrl()` so it survives navigation).
 *
 * Disable with `localStorage.removeItem("ucgle.devOverlay")`.
 *
 * SSR-safe: returns false on the server. No effect on production
 * bundle size beyond the small badge component, which renders `null`
 * when this returns false.
 */
const KEY = "ucgle.devOverlay";

export function isDevOverlayEnabled(): boolean {
  if (typeof window === "undefined") return false;
  try {
    if (window.localStorage.getItem(KEY) === "1") return true;
  } catch {
    /* private mode or storage disabled */
  }
  try {
    return new URLSearchParams(window.location.search).has("devOverlay");
  } catch {
    return false;
  }
}

/** Copy `?devOverlay=1` from the URL into localStorage on first load. */
export function persistDevOverlayFromUrl(): void {
  if (typeof window === "undefined") return;
  try {
    if (new URLSearchParams(window.location.search).has("devOverlay")) {
      window.localStorage.setItem(KEY, "1");
    }
  } catch {
    /* ignore */
  }
}

/**
 * Force-enable the overlay for the current session (used by `/qa` so a
 * tester sees badges immediately on landing). Persists to localStorage
 * so a reload keeps the flag.
 */
export function enableDevOverlay(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, "1");
  } catch {
    /* ignore */
  }
}

/** Remove the overlay flag and disable the badge. */
export function disableDevOverlay(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
