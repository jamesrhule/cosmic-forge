/**
 * Security headers, Content-Security-Policy included, for every SSR /
 * server-route / server-fn response (applied by the request middleware in
 * `src/start.ts`).
 *
 * Production `script-src` has no 'unsafe-inline'. TanStack Start streams its
 * bootstrap and hydration data as inline `<script>`s, so each response gets a
 * fresh nonce: the middleware puts it in the request context, `getRouter()`
 * hands it to the router (`ssr.nonce`, see `src/lib/csp-nonce.ts`), and Start
 * stamps it on every script it emits plus a `<meta property="csp-nonce">` the
 * client router reads after hydration.
 *
 * Production `script-src` carries 'unsafe-eval' only in builds that can render
 * the RJSF configurator form (`rjsfFormReachable`): `QcompassManifestForm` on
 * `/domains/$domain/configurator` validates with `@rjsf/validator-ajv8`, and
 * ajv compiles each JSON Schema with `new Function`. Without it validation
 * fails ("Error compiling schema") and the form never submits. A build that
 * cannot render that form (the default, cosmology-only build) gets no
 * 'unsafe-eval'.
 *
 * `connect-src` lists every origin the browser talks to: Supabase (the origin
 * the Worker is configured with at runtime and the one the browser client was
 * built with), the QCompass API (`VITE_API_URL`, plus its ws/wss twin for the
 * visualization socket), PostHog and Plausible. When PostHog is configured
 * (`VITE_POSTHOG_KEY`), its API and assets origins are added to `connect-src`
 * and its assets origin to `script-src`, because posthog-js loads its
 * recorder, surveys and remote config as external scripts (`posthogOrigins`).
 *
 * Framing: production sends `frame-ancestors 'none'` and `X-Frame-Options:
 * DENY`. Dev (`vite dev`) sends neither, so an editor preview (Lovable shows
 * the dev server in an iframe on another origin) can frame it. Before the
 * TanStack Start upgrade (lane W0-npm) no header from the middleware was sent
 * at all, so dev had no framing restriction then either.
 *
 * `upgrade-insecure-requests` is sent only on https. On a plain-http origin
 * (local `wrangler dev`, the e2e servers) the document itself is insecure, so
 * the directive secures nothing and only turns same-origin asset loads into
 * https requests that the http server cannot answer.
 */

import type { FeatureFlags } from "@/config/features";

export interface CspOptions {
  /** Production build: no 'unsafe-inline' on script-src, nonce instead. */
  production: boolean;
  /** Per-response nonce for script-src (production only). */
  nonce?: string;
  /** Supabase origin for connect-src, or "" when not configured. */
  supabaseHost: string;
  /** Further origins for connect-src (API, its socket, Supabase, PostHog). */
  connectOrigins?: string[];
  /** The request came in over https. */
  https: boolean;
  /**
   * Production only: the build can render the RJSF configurator form, so
   * script-src needs 'unsafe-eval' for ajv (`rjsfFormReachable`). When omitted,
   * the policy keeps 'unsafe-eval' as before this option existed;
   * `src/start.ts` always passes it.
   */
  rjsfForm?: boolean;
  /** Further origins for script-src (PostHog's assets host when configured). */
  scriptOrigins?: string[];
}

const unique = (xs: string[]) => [...new Set(xs.filter(Boolean))];

export function buildCsp({
  production,
  nonce,
  supabaseHost,
  connectOrigins = [],
  https,
  rjsfForm = true,
  scriptOrigins = [],
}: CspOptions): string {
  const connect = unique(connectOrigins).filter((o) => o !== supabaseHost);
  const extra = connect.length ? ` ${connect.join(" ")}` : "";
  const scripts = unique(scriptOrigins).filter((o) => o !== "https://plausible.io");
  const extraScripts = scripts.length ? ` ${scripts.join(" ")}` : "";
  return [
    "default-src 'self'",
    "base-uri 'self'",
    "form-action 'self'",
    // Production only: dev must stay frameable by an editor preview.
    ...(production ? ["frame-ancestors 'none'"] : []),
    "object-src 'none'",
    // Plausible analytics (+ PostHog's assets host when PostHog is configured).
    // 'unsafe-inline' on script-src is intentionally absent in production;
    // dev mode keeps Vite's HMR working via 'unsafe-inline' and 'unsafe-eval'.
    production
      ? `script-src 'self'${nonce ? ` 'nonce-${nonce}'` : ""}${rjsfForm ? " 'unsafe-eval'" : ""} https://plausible.io${extraScripts}`
      : `script-src 'self' 'unsafe-inline' 'unsafe-eval' https://plausible.io${extraScripts}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data:",
    // wss: needed for the live visualization socket once we cut over.
    `connect-src 'self' ${supabaseHost}${extra} wss: https://plausible.io https://app.posthog.com`.trim(),
    "media-src 'self' blob:",
    "worker-src 'self' blob:",
    "manifest-src 'self'",
    ...(https ? ["upgrade-insecure-requests"] : []),
  ].join("; ");
}

/**
 * The connect-src origins for a base URL: its origin and the matching
 * WebSocket origin (http → ws, https → wss). Empty for an unset or invalid URL.
 */
export function connectOriginsFor(url: string | undefined): string[] {
  if (!url) return [];
  try {
    const u = new URL(url);
    if (u.protocol !== "http:" && u.protocol !== "https:") return [];
    return [u.origin, `${u.protocol === "https:" ? "wss:" : "ws:"}//${u.host}`];
  } catch {
    return [];
  }
}

/**
 * The origins posthog-js talks to for an `api_host`, mirroring its
 * `RequestRouter` (posthog-js 1.371.4, `lib/src/utils/request-router.js`):
 * - `https://app.posthog.com` is rewritten to `https://us.i.posthog.com`;
 * - a US or EU cloud host sends API calls to `https://<region>.i.posthog.com`
 *   and loads assets (`/static/*.js` for the recorder, surveys and the other
 *   lazily loaded extensions, `/array/<token>/config(.js)` for remote config)
 *   from `https://<region>-assets.i.posthog.com`;
 * - any other host (a reverse proxy, self-hosted PostHog) serves both itself.
 * Undefined for an unset or invalid host.
 */
export function posthogOrigins(
  apiHost: string | undefined,
): { api: string; assets: string } | undefined {
  let host = (apiHost ?? "").trim().replace(/\/$/, "");
  if (host === "https://app.posthog.com") host = "https://us.i.posthog.com";
  const region = /https:\/\/(app|us|us-assets)(\.i)?\.posthog\.com/i.test(host)
    ? "us"
    : /https:\/\/(eu|eu-assets)(\.i)?\.posthog\.com/i.test(host)
      ? "eu"
      : undefined;
  if (region) {
    return {
      api: `https://${region}.i.posthog.com`,
      assets: `https://${region}-assets.i.posthog.com`,
    };
  }
  const [origin] = connectOriginsFor(host);
  return origin ? { api: origin, assets: origin } : undefined;
}

/** The feature flags that decide whether a build can render the RJSF form. */
export type RjsfFormFlags = Pick<
  FeatureFlags,
  | "liveBackend"
  | "qcompassMultiDomain"
  | "qcompassChemistry"
  | "qcompassCondmat"
  | "qcompassAmo"
  | "qcompassHep"
  | "qcompassNuclear"
  | "qcompassGravity"
  | "qcompassStatmech"
>;

/**
 * Can this build render the RJSF configurator form (and so run ajv's
 * `new Function` codegen)? `/domains/$domain/configurator` renders the form
 * only once a manifest schema loads (`getManifestSchema`):
 * - from a fixture, which exists only for the seven QCompass domains; each is
 *   reachable only with `qcompassMultiDomain` and its own flag on
 *   (`src/lib/domains/*.ts`, `resolveDomain`);
 * - from the live API (`liveBackend`, i.e. `VITE_API_URL` set), which also
 *   serves a schema for `cosmology.ucglef1`, the one domain every build
 *   registers.
 * Built from the build-time `FEATURES`, so it is fixed per build.
 */
export function rjsfFormReachable(flags: RjsfFormFlags): boolean {
  const domainOn =
    flags.qcompassChemistry ||
    flags.qcompassCondmat ||
    flags.qcompassAmo ||
    flags.qcompassHep ||
    flags.qcompassNuclear ||
    flags.qcompassGravity ||
    flags.qcompassStatmech;
  return flags.liveBackend || (flags.qcompassMultiDomain && domainOn);
}

export interface CspSourceInputs {
  /** `VITE_API_URL` (build time). */
  apiUrl?: string;
  /** `VITE_SUPABASE_URL` as the browser client was built with. */
  supabaseBuildUrl?: string;
  /** `VITE_POSTHOG_KEY` (build time): PostHog runs only when it is set. */
  posthogKey?: string;
  /** posthog-js `api_host` as `src/lib/telemetry.ts` resolves it. */
  posthogApiHost?: string;
  /** `VITE_POSTHOG_HOST` (build time), kept in connect-src when set. */
  posthogHostSetting?: string;
}

/** The connect-src and script-src origins a build needs, beyond the fixed ones. */
export function cspSources({
  apiUrl,
  supabaseBuildUrl,
  posthogKey,
  posthogApiHost,
  posthogHostSetting,
}: CspSourceInputs): { connectOrigins: string[]; scriptOrigins: string[] } {
  const posthog = posthogKey ? posthogOrigins(posthogApiHost) : undefined;
  return {
    connectOrigins: unique([
      ...connectOriginsFor(apiUrl),
      ...connectOriginsFor(posthogHostSetting).slice(0, 1),
      ...connectOriginsFor(supabaseBuildUrl),
      ...(posthog ? [posthog.api, posthog.assets] : []),
    ]),
    scriptOrigins: posthog ? [posthog.assets] : [],
  };
}

export const PERMISSIONS_POLICY = [
  "accelerometer=()",
  "camera=()",
  "geolocation=()",
  "gyroscope=()",
  "magnetometer=()",
  "microphone=()",
  "payment=()",
  "usb=()",
  "interest-cohort=()",
].join(", ");

/**
 * Every security header of a response. `X-Frame-Options: DENY` (for user
 * agents without `frame-ancestors`) is production only, like
 * `frame-ancestors 'none'`.
 */
export function securityHeaders(options: CspOptions): Record<string, string> {
  return {
    "Content-Security-Policy": buildCsp(options),
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    ...(options.production ? { "X-Frame-Options": "DENY" } : {}),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": PERMISSIONS_POLICY,
    "Cross-Origin-Opener-Policy": "same-origin",
    "X-DNS-Prefetch-Control": "off",
  };
}

/** 128 random bits, base64 (CSP nonce-source grammar). */
export function createCspNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary);
}
