/**
 * Global request middleware (security headers).
 *
 * TanStack Start picks this file up via `createStart()` and runs the
 * registered request middleware on every SSR / server-route / server-fn
 * response. We layer the standard security headers at this single
 * choke-point so individual handlers don't have to remember them.
 *
 * CSP notes:
 *   - script-src includes 'self' + Plausible (analytics) and the
 *     Lovable preview iframe shim. We allow 'unsafe-inline' on `style-src`
 *     because Tailwind v4's CSS-in-JS layer + Sonner inject inline styles;
 *     the runtime cost of switching to nonces isn't worth the marginal
 *     gain today.
 *   - connect-src lists Supabase + posthog + plausible so the browser can
 *     actually reach them.
 *   - frame-ancestors 'none' replaces X-Frame-Options for modern browsers
 *     but we still send XFO for older user agents (e.g. corp proxies).
 */

import { createStart, createMiddleware } from "@tanstack/react-start";
import { setResponseHeaders } from "@tanstack/react-start/server";

const SUPABASE_URL = process.env.SUPABASE_URL ?? process.env.VITE_SUPABASE_URL ?? "";
const SUPABASE_HOST = SUPABASE_URL ? new URL(SUPABASE_URL).origin : "";

const CSP_DIRECTIVES = [
  "default-src 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  // Vite dev server + Plausible analytics + Lovable preview chrome.
  // 'unsafe-inline' on script-src is intentionally absent in production;
  // dev mode keeps HMR working via 'unsafe-eval'.
  process.env.NODE_ENV === "production"
    ? "script-src 'self' https://plausible.io"
    : "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://plausible.io",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https:",
  "font-src 'self' data:",
  // wss: needed for the live visualization socket once we cut over.
  `connect-src 'self' ${SUPABASE_HOST} wss: https://plausible.io https://app.posthog.com`.trim(),
  "media-src 'self' blob:",
  "worker-src 'self' blob:",
  "manifest-src 'self'",
  "upgrade-insecure-requests",
].join("; ");

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

const securityHeaders = createMiddleware().server(async ({ next }) => {
  const result = await next();

  setResponseHeaders(
    new Headers({
      "Content-Security-Policy": CSP_DIRECTIVES,
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
  requestMiddleware: [securityHeaders],
}));
