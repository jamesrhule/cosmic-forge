/**
 * Global request middleware (security headers).
 *
 * TanStack Start picks this file up via `createStart()` and runs the
 * registered request middleware on every SSR / server-route / server-fn
 * response. We layer the standard security headers at this single
 * choke-point so individual handlers don't have to remember them.
 *
 * CSP notes (the policy itself is built in src/lib/csp.ts):
 *   - script-src includes 'self' + Plausible (analytics) and the
 *     Lovable preview iframe shim. In production it also carries a fresh
 *     per-response nonce, because Start streams its bootstrap and hydration
 *     data as inline scripts; the nonce reaches the router through the
 *     request context (`cspNonce`, read in src/lib/csp-nonce.ts).
 *     We allow 'unsafe-inline' on `style-src`
 *     because Tailwind v4's CSS-in-JS layer + Sonner inject inline styles;
 *     the runtime cost of switching to nonces isn't worth the marginal
 *     gain today.
 *   - connect-src lists Supabase + posthog + plausible so the browser can
 *     actually reach them, plus the QCompass API (VITE_API_URL) and a custom
 *     PostHog host when they are configured.
 *   - script-src keeps 'unsafe-eval' in production for the RJSF/ajv manifest
 *     form (see src/lib/csp.ts).
 *   - frame-ancestors 'none' replaces X-Frame-Options for modern browsers
 *     but we still send XFO for older user agents (e.g. corp proxies).
 *   - setResponseHeaders() receives a Headers object. The locked
 *     @tanstack/start-server-core 1.167.19 iterated it with Object.entries(),
 *     which yields nothing for a Headers instance, so none of these headers
 *     was sent. 1.169.39 (the GHSA-qx66-fv34-fjm8 fix) iterates the Headers,
 *     so they are sent from then on, which is why the nonce exists (lane
 *     W0-npm).
 */

import { createStart, createMiddleware } from "@tanstack/react-start";
import { setResponseHeaders } from "@tanstack/react-start/server";
import { attachSupabaseAuth } from "@/integrations/supabase/auth-attacher";
import { API_BASE_URL } from "@/config/features";
import { buildCsp, connectOriginsFor, createCspNonce } from "@/lib/csp";

const SUPABASE_URL = process.env.SUPABASE_URL ?? process.env.VITE_SUPABASE_URL ?? "";
const SUPABASE_HOST = SUPABASE_URL ? new URL(SUPABASE_URL).origin : "";

const PRODUCTION = process.env.NODE_ENV === "production";
// The QCompass API (and its visualization socket) and a custom PostHog host,
// when configured, must be reachable from the browser too.
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST as string | undefined;
const CONNECT_ORIGINS = [
  ...connectOriginsFor(API_BASE_URL),
  ...connectOriginsFor(POSTHOG_HOST).slice(0, 1),
];

const PERMISSIONS_POLICY = [
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

const securityHeaders = createMiddleware().server(async ({ next, request }) => {
  const cspNonce = createCspNonce();
  const result = await next({ context: { cspNonce } });

  const csp = buildCsp({
    production: PRODUCTION,
    nonce: cspNonce,
    supabaseHost: SUPABASE_HOST,
    connectOrigins: CONNECT_ORIGINS,
    https: new URL(request.url).protocol === "https:",
  });

  setResponseHeaders(
    new Headers({
      "Content-Security-Policy": csp,
      "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
      "X-Content-Type-Options": "nosniff",
      "X-Frame-Options": "DENY",
      "Referrer-Policy": "strict-origin-when-cross-origin",
      "Permissions-Policy": PERMISSIONS_POLICY,
      "Cross-Origin-Opener-Policy": "same-origin",
      "X-DNS-Prefetch-Control": "off",
    }),
  );

  return result;
});

export const startInstance = createStart(() => ({
  functionMiddleware: [attachSupabaseAuth],
  requestMiddleware: [securityHeaders],
}));
