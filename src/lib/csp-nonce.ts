import { createIsomorphicFn, getGlobalStartContext } from "@tanstack/react-start";

/**
 * The CSP nonce of the current request (see `src/lib/csp.ts`).
 *
 * Server: read from the request context that the security-headers middleware
 * in `src/start.ts` fills; undefined outside a request. Client: undefined;
 * after hydration the router reads `<meta property="csp-nonce">` itself.
 */
export const getCspNonce = createIsomorphicFn()
  .server((): string | undefined => {
    try {
      const nonce = (getGlobalStartContext() as { cspNonce?: unknown } | undefined)?.cspNonce;
      return typeof nonce === "string" ? nonce : undefined;
    } catch {
      return undefined;
    }
  })
  .client((): string | undefined => undefined);
