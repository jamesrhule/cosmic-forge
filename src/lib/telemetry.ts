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

/* ─── Release stamping ────────────────────────────────────────────── */

const RELEASE = {
  commit: typeof __APP_COMMIT__ !== "undefined" ? __APP_COMMIT__ : "unknown",
  builtAt: typeof __APP_BUILD_DATE__ !== "undefined" ? __APP_BUILD_DATE__ : "unknown",
};

function dispatch(event: TelemetryEvent): void {
  const stamped = { ...(event.props ?? {}), release: RELEASE.commit };
  if (DEBUG) {
    // eslint-disable-next-line no-console
    console.debug("[telemetry]", event.name, stamped);
  }
  if (typeof window === "undefined") return;

  if (PLAUSIBLE_DOMAIN && typeof window.plausible === "function") {
    window.plausible(event.name, { props: stamped });
  }

  const ph = getPosthog();
  if (ph) {
    void ph.then((client) => {
      if (event.name === "page_view") {
        client.capture("$pageview", stamped);
      } else {
        client.capture(event.name, stamped);
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

/**
 * Soft-warning channel: routes any `console.warn`-equivalent call through
 * the same telemetry pipeline as errors so production dashboards see the
 * full picture. In dev we *also* mirror to `console.warn` so the warning
 * still shows up in the dev tools panel without polluting production
 * console output.
 *
 * Use a stable enum of `scope` values so dashboards can pivot cleanly.
 */
export type TelemetryWarnScope =
  | "audit_insert"
  | "audit_logger"
  | "katex_render"
  | "katex_error_span"
  | "math_error_boundary"
  | "panel_export"
  | "visualizer_export"
  | "root_error_boundary"
  | "rate_limit_rpc"
  | "rate_limit_burst"
  | "email_verify_block"
  | "timeline_size_block"
  | "status_probe";

export function trackWarn(scope: TelemetryWarnScope, message: string, props?: Record<string, unknown>): void {
  if (DEBUG) {
    // eslint-disable-next-line no-console
    console.warn(`[${scope}]`, message, props ?? "");
  }
  dispatch({ name: "client_warn", props: { scope, message, ...props } });
}

/**
 * Failure-path helpers — kept narrow so dashboards can pivot on a small
 * stable enum of `name` values instead of free-form strings.
 */
export function trackError(
  name:
    | "run_failed"
    | "visualization_error"
    | "chat_error"
    | "chunk_load_error"
    | "service_error"
    | "slow_frames",
  props?: Record<string, unknown>,
): void {
  dispatch({ name, props });
}

/**
 * Slow-frame report. Fired by the visualizer transport loop when a
 * sustained drop below ~30fps is detected. We expose a thin wrapper
 * over `trackError` so dashboards can pivot on a single event name and
 * the (panel, count, p95) shape stays stable across callers.
 */
export function reportSlowFrames(panel: string, count: number, worstDtMs: number): void {
  trackError("slow_frames", { panel, count, worstDtMs });
}

/**
 * Best-effort listener that turns dynamic-import failures (network drop,
 * stale chunk after a deploy) into a `chunk_load_error` event. Mounted
 * once from `__root.tsx`.
 */
export function installChunkErrorListener(): () => void {
  if (typeof window === "undefined") return () => {};
  const onError = (evt: ErrorEvent) => {
    const msg = evt.message || "";
    if (/Loading chunk|Failed to fetch dynamically imported module|Importing a module script failed/i.test(msg)) {
      trackError("chunk_load_error", { message: msg, filename: evt.filename });
    }
  };
  const onRejection = (evt: PromiseRejectionEvent) => {
    const reason = evt.reason;
    const msg = reason instanceof Error ? reason.message : String(reason ?? "");
    if (/Loading chunk|Failed to fetch dynamically imported module|Importing a module script failed/i.test(msg)) {
      trackError("chunk_load_error", { message: msg });
    }
  };
  window.addEventListener("error", onError);
  window.addEventListener("unhandledrejection", onRejection);
  return () => {
    window.removeEventListener("error", onError);
    window.removeEventListener("unhandledrejection", onRejection);
  };
}

/** True when at least one analytics provider is configured at build time. */
export const TELEMETRY_ENABLED: boolean = Boolean(PLAUSIBLE_DOMAIN || POSTHOG_KEY);

/** Plausible domain (read-only) — used by the root head() to inject the script. */
export const PLAUSIBLE: string | undefined = PLAUSIBLE_DOMAIN;
