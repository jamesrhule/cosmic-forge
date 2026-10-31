/**
 * Minimal declaration for the Workers runtime module. Only the part used by
 * `src/lib/fixtures.ts` (the static-assets binding) is typed.
 */
declare module "cloudflare:workers" {
  export const env: {
    ASSETS?: { fetch: (input: Request | string, init?: RequestInit) => Promise<Response> };
  };
}
