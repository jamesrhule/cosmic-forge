/**
 * Global request middleware (security headers).
 *
 * TanStack Start picks this file up via `createStart()` and runs the
 * registered request middleware on every SSR / server-route / server-fn
 * response. We layer the standard security headers at this single
 * choke-point so individual handlers don't have to remember them.
 *
 * The headers and the CSP are built in src/lib/csp.ts (`securityHeaders`);
 * its header comment explains each directive. In short:
 *   - script-src: 'self' + Plausible (analytics), and PostHog's assets host
 *     when PostHog is configured. In production it also carries a fresh
 *     per-response nonce, because Start streams its bootstrap and hydration
 *     data as inline scripts; the nonce reaches the router through the
 *     request context (`cspNonce`, read in src/lib/csp-nonce.ts). Production
 *     adds 'unsafe-eval' only in builds that can render the RJSF/ajv
 *     configurator form (`rjsfFormReachable(FEATURES)`); dev keeps
 *     'unsafe-inline' and 'unsafe-eval' for Vite's HMR.
 *     We allow 'unsafe-inline' on `style-src`
 *     because Tailwind v4's CSS-in-JS layer + Sonner inject inline styles;
 *     the runtime cost of switching to nonces isn't worth the marginal
 *     gain today.
 *   - connect-src lists Supabase + posthog + plausible so the browser can
 *     actually reach them: the Supabase origin the Worker has at runtime and
 *     the one the browser client was built with (VITE_SUPABASE_URL), the
 *     QCompass API (VITE_API_URL), and PostHog's API and assets origins when
 *     PostHog is configured.
 *   - Production sends frame-ancestors 'none' and, for older user agents
 *     (e.g. corp proxies), X-Frame-Options DENY. Dev sends neither, so an
 *     editor preview iframe of `vite dev` keeps working.
 *   - setResponseHeaders() receives a Headers object. The locked
 *     @tanstack/start-server-core 1.167.19 iterated it with Object.entries(),
 *     which yields nothing for a Headers instance, so none of these headers
 *     was sent. 1.169.39 (the GHSA-qx66-fv34-fjm8 fix) iterates the Headers,
 *     so they are sent from then on, which is why the nonce exists (lane
 *     W0-npm).
 */

// First: zod's CSP setting must precede every schema (src/lib/zod-csp.ts).
import "@/lib/zod-csp";
import { createStart, createMiddleware } from "@tanstack/react-start";
import { setResponseHeaders } from "@tanstack/react-start/server";
import { attachSupabaseAuth } from "@/integrations/supabase/auth-attacher";
import { API_BASE_URL, FEATURES } from "@/config/features";
import { POSTHOG_CONFIG } from "@/lib/telemetry";
import {
  connectOriginsFor,
  createCspNonce,
  cspSources,
  rjsfFormReachable,
  securityHeaders,
} from "@/lib/csp";

// The Supabase project the Worker is configured with at runtime.
const SUPABASE_HOST =
  connectOriginsFor(process.env.SUPABASE_URL ?? process.env.VITE_SUPABASE_URL)[0] ?? "";

const PRODUCTION = process.env.NODE_ENV === "production";
// Build-time origins: the QCompass API (and its visualization socket), the
// Supabase project the browser client was built with, and PostHog when it is
// configured.
const { connectOrigins: CONNECT_ORIGINS, scriptOrigins: SCRIPT_ORIGINS } = cspSources({
  apiUrl: API_BASE_URL,
  supabaseBuildUrl: import.meta.env.VITE_SUPABASE_URL as string | undefined,
  posthogKey: POSTHOG_CONFIG.key,
  posthogApiHost: POSTHOG_CONFIG.apiHost,
  posthogHostSetting: import.meta.env.VITE_POSTHOG_HOST as string | undefined,
});
// ajv's `new Function` is needed only where the RJSF configurator form can render.
const RJSF_FORM = rjsfFormReachable(FEATURES);

const securityHeadersMiddleware = createMiddleware().server(async ({ next, request }) => {
  const cspNonce = createCspNonce();
  const result = await next({ context: { cspNonce } });

  setResponseHeaders(
    new Headers(
      securityHeaders({
        production: PRODUCTION,
        nonce: cspNonce,
        supabaseHost: SUPABASE_HOST,
        connectOrigins: CONNECT_ORIGINS,
        scriptOrigins: SCRIPT_ORIGINS,
        rjsfForm: RJSF_FORM,
        https: new URL(request.url).protocol === "https:",
      }),
    ),
  );

  return result;
});

export const startInstance = createStart(() => ({
  functionMiddleware: [attachSupabaseAuth],
  requestMiddleware: [securityHeadersMiddleware],
}));
