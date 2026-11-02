/**
 * Content-Security-Policy for every SSR / server-route / server-fn response
 * (applied by the request middleware in `src/start.ts`).
 *
 * Production `script-src` has no 'unsafe-inline'. TanStack Start streams its
 * bootstrap and hydration data as inline `<script>`s, so each response gets a
 * fresh nonce: the middleware puts it in the request context, `getRouter()`
 * hands it to the router (`ssr.nonce`, see `src/lib/csp-nonce.ts`), and Start
 * stamps it on every script it emits plus a `<meta property="csp-nonce">` the
 * client router reads after hydration.
 *
 * Production `script-src` keeps 'unsafe-eval': the QCompass manifest form
 * (`QcompassManifestForm`, every `/domains/$domain/configurator`) validates
 * with `@rjsf/validator-ajv8`, and ajv compiles each JSON Schema with
 * `new Function`. Without it validation fails ("Error compiling schema") and
 * the form never submits.
 *
 * `connect-src` lists every origin the browser talks to: Supabase, the
 * QCompass API (`VITE_API_URL`, plus its ws/wss twin for the visualization
 * socket), PostHog and Plausible.
 *
 * `upgrade-insecure-requests` is sent only on https. On a plain-http origin
 * (local `wrangler dev`, the e2e servers) the document itself is insecure, so
 * the directive secures nothing and only turns same-origin asset loads into
 * https requests that the http server cannot answer.
 */

export interface CspOptions {
  /** Production build: no 'unsafe-inline' on script-src, nonce instead. */
  production: boolean;
  /** Per-response nonce for script-src (production only). */
  nonce?: string;
  /** Supabase origin for connect-src, or "" when not configured. */
  supabaseHost: string;
  /** Further origins for connect-src (API, its socket, a custom PostHog host). */
  connectOrigins?: string[];
  /** The request came in over https. */
  https: boolean;
}

export function buildCsp({
  production,
  nonce,
  supabaseHost,
  connectOrigins = [],
  https,
}: CspOptions): string {
  const extra = connectOrigins.length ? ` ${connectOrigins.join(" ")}` : "";
  return [
    "default-src 'self'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "object-src 'none'",
    // Vite dev server + Plausible analytics + Lovable preview chrome.
    // 'unsafe-inline' on script-src is intentionally absent in production;
    // dev mode keeps HMR working via 'unsafe-inline' and 'unsafe-eval'.
    production
      ? `script-src 'self'${nonce ? ` 'nonce-${nonce}'` : ""} 'unsafe-eval' https://plausible.io`
      : "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://plausible.io",
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

/** 128 random bits, base64 (CSP nonce-source grammar). */
export function createCspNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary);
}
