/**
 * Telemetry shim with two opt-in providers, both gated by
 * build-time env vars so the production bundle stays free of network
 * calls when the keys are absent.
 *
 *   - VITE_PLAUSIBLE_DOMAIN  → loads plausible.io/js/script.js
 *   - VITE_POSTHOG_KEY       → lazy-imports posthog-js on first event
 *
 * Both providers are mutually compatible (you can wire one, both, or
 * neither). When neither is set the module remains a no-op (with a
 * dev-only console mirror).
 *
 * Events fired today:
 *   - "page_view"            — every route mount
 *   - "run_started"          — ActionsRail.onRun success
 *   - "visualization_opened" — visualizer.$runId.lazy mount
 */

export interface TelemetryEvent {
  name: string;
  props?: Record<string, unknown>;
}

const DEBUG = import.meta.env.DEV;
const PLAUSIBLE_DOMAIN: string | undefined = import.meta.env.VITE_PLAUSIBLE_DOMAIN;
const POSTHOG_KEY: string | undefined = import.meta.env.VITE_POSTHOG_KEY;
const POSTHOG_HOST: string =
  (import.meta.env.VITE_POSTHOG_HOST as string | undefined) ?? "https://app.posthog.com";

interface PlausibleFn {
  (event: string, opts?: { props?: Record<string, unknown> }): void;
}

declare global {
  interface Window {
    plausible?: PlausibleFn;
  }
}

/* ─── PostHog (lazy) ──────────────────────────────────────────────── */

let posthogPromise: Promise<typeof import("posthog-js").default> | null = null;

function getPosthog() {
  if (!POSTHOG_KEY || typeof window === "undefined") return null;
  if (!posthogPromise) {
    // Lazy import: keeps posthog-js out of the initial bundle for users
    // on builds that didn't configure it.
    posthogPromise = import("posthog-js").then((mod) => {
      const ph = mod.default;
      ph.init(POSTHOG_KEY!, {
        api_host: POSTHOG_HOST,
        capture_pageview: false, // we drive page_view manually
        persistence: "localStorage+cookie",
      });
      return ph;
    });
  }
  return posthogPromise;
}

/* ─── Public API ──────────────────────────────────────────────────── */

function dispatch(event: TelemetryEvent): void {
  if (DEBUG) {
    // eslint-disable-next-line no-console
    console.debug("[telemetry]", event.name, event.props ?? {});
  }
  if (typeof window === "undefined") return;

  // Plausible — script tag is injected from __root.tsx head() when
  // VITE_PLAUSIBLE_DOMAIN is set; window.plausible becomes a function
  // once it loads. We tolerate it being undefined briefly.
  if (PLAUSIBLE_DOMAIN && typeof window.plausible === "function") {
    window.plausible(event.name, event.props ? { props: event.props } : undefined);
  }

  // PostHog — lazy import + capture.
  const ph = getPosthog();
  if (ph) {
    void ph.then((client) => {
      if (event.name === "page_view") {
        client.capture("$pageview", event.props);
      } else {
        client.capture(event.name, event.props);
      }
    });
  }
}

export function track(name: string, props?: Record<string, unknown>): void {
  dispatch({ name, props });
}

export function pageview(path: string): void {
  dispatch({ name: "page_view", props: { path } });
}

/** True when at least one analytics provider is configured at build time. */
export const TELEMETRY_ENABLED: boolean = Boolean(PLAUSIBLE_DOMAIN || POSTHOG_KEY);

/** Plausible domain (read-only) — used by the root head() to inject the script. */
export const PLAUSIBLE: string | undefined = PLAUSIBLE_DOMAIN;
