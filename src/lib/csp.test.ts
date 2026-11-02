import { describe, expect, it } from "vitest";
import { buildCsp, connectOriginsFor, createCspNonce } from "./csp";

const directives = (csp: string) => csp.split("; ");

describe("buildCsp", () => {
  it("production script-src: self, the nonce, eval for ajv, Plausible; no unsafe-inline", () => {
    const csp = buildCsp({ production: true, nonce: "abc123==", supabaseHost: "", https: true });
    const scriptSrc = directives(csp).find((d) => d.startsWith("script-src"));
    expect(scriptSrc).toBe("script-src 'self' 'nonce-abc123==' 'unsafe-eval' https://plausible.io");
    expect(scriptSrc).not.toContain("'unsafe-inline'");
  });

  it("dev keeps the HMR policy and no nonce", () => {
    const csp = buildCsp({ production: false, nonce: "abc123==", supabaseHost: "", https: false });
    expect(directives(csp)).toContain(
      "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://plausible.io",
    );
    expect(csp).not.toContain("nonce-");
  });

  it("keeps every other directive", () => {
    const csp = buildCsp({
      production: true,
      nonce: "n",
      supabaseHost: "https://x.supabase.co",
      https: true,
    });
    expect(directives(csp)).toEqual([
      "default-src 'self'",
      "base-uri 'self'",
      "form-action 'self'",
      "frame-ancestors 'none'",
      "object-src 'none'",
      "script-src 'self' 'nonce-n' 'unsafe-eval' https://plausible.io",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob: https:",
      "font-src 'self' data:",
      "connect-src 'self' https://x.supabase.co wss: https://plausible.io https://app.posthog.com",
      "media-src 'self' blob:",
      "worker-src 'self' blob:",
      "manifest-src 'self'",
      "upgrade-insecure-requests",
    ]);
  });

  it("adds the API and PostHog origins to connect-src", () => {
    const csp = buildCsp({
      production: true,
      supabaseHost: "",
      connectOrigins: ["https://api.example.org", "wss://api.example.org"],
      https: true,
    });
    expect(directives(csp)).toContain(
      "connect-src 'self'  https://api.example.org wss://api.example.org wss: https://plausible.io https://app.posthog.com",
    );
  });

  it("sends upgrade-insecure-requests only over https", () => {
    const base = { production: true, nonce: "n", supabaseHost: "" };
    expect(buildCsp({ ...base, https: true })).toContain("upgrade-insecure-requests");
    expect(buildCsp({ ...base, https: false })).not.toContain("upgrade-insecure-requests");
  });
});

describe("connectOriginsFor", () => {
  it("returns the origin and its socket twin", () => {
    expect(connectOriginsFor("https://api.example.org/v1/")).toEqual([
      "https://api.example.org",
      "wss://api.example.org",
    ]);
    expect(connectOriginsFor("http://localhost:8000")).toEqual([
      "http://localhost:8000",
      "ws://localhost:8000",
    ]);
  });

  it("returns nothing for unset, invalid or non-http URLs", () => {
    expect(connectOriginsFor(undefined)).toEqual([]);
    expect(connectOriginsFor("")).toEqual([]);
    expect(connectOriginsFor("not a url")).toEqual([]);
    expect(connectOriginsFor("javascript:alert(1)")).toEqual([]);
  });
});

describe("createCspNonce", () => {
  it("returns 128 random bits as base64, different each call", () => {
    const a = createCspNonce();
    const b = createCspNonce();
    expect(a).toMatch(/^[A-Za-z0-9+/]{22}==$/);
    expect(atob(a)).toHaveLength(16);
    expect(a).not.toBe(b);
  });
});
