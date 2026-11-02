import { describe, expect, it } from "vitest";
import {
  buildCsp,
  connectOriginsFor,
  createCspNonce,
  cspSources,
  posthogOrigins,
  rjsfFormReachable,
  securityHeaders,
  type RjsfFormFlags,
} from "./csp";

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

describe("framing: production refuses it, dev allows an editor preview", () => {
  const base = { nonce: "n", supabaseHost: "", https: false };

  it("production sends frame-ancestors 'none' and X-Frame-Options DENY", () => {
    const h = securityHeaders({ ...base, production: true });
    expect(h["X-Frame-Options"]).toBe("DENY");
    expect(directives(h["Content-Security-Policy"])).toContain("frame-ancestors 'none'");
  });

  it("dev sends neither, so `vite dev` can be framed", () => {
    const h = securityHeaders({ ...base, production: false });
    expect(h).not.toHaveProperty("X-Frame-Options");
    expect(h["Content-Security-Policy"]).not.toContain("frame-ancestors");
    expect(buildCsp({ ...base, production: false })).not.toContain("frame-ancestors");
  });

  it("both modes keep every other header", () => {
    for (const production of [true, false]) {
      const h = securityHeaders({ ...base, production });
      expect(h).toMatchObject({
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Cross-Origin-Opener-Policy": "same-origin",
        "X-DNS-Prefetch-Control": "off",
      });
      expect(h["Permissions-Policy"]).toContain("camera=()");
      expect(h["Content-Security-Policy"]).toBe(buildCsp({ ...base, production }));
    }
  });
});

describe("'unsafe-eval' only where the RJSF configurator form can render", () => {
  const scriptSrc = (csp: string) => directives(csp).find((d) => d.startsWith("script-src"));
  const OFF: RjsfFormFlags = {
    liveBackend: false,
    qcompassMultiDomain: false,
    qcompassChemistry: false,
    qcompassCondmat: false,
    qcompassAmo: false,
    qcompassHep: false,
    qcompassNuclear: false,
    qcompassGravity: false,
    qcompassStatmech: false,
  };
  const DOMAINS = [
    "qcompassChemistry",
    "qcompassCondmat",
    "qcompassAmo",
    "qcompassHep",
    "qcompassNuclear",
    "qcompassGravity",
    "qcompassStatmech",
  ] as const;

  it("production without the form: no 'unsafe-eval'", () => {
    const csp = buildCsp({
      production: true,
      nonce: "n",
      supabaseHost: "",
      https: true,
      rjsfForm: false,
    });
    expect(scriptSrc(csp)).toBe("script-src 'self' 'nonce-n' https://plausible.io");
  });

  it("production with the form: 'unsafe-eval'", () => {
    const csp = buildCsp({
      production: true,
      nonce: "n",
      supabaseHost: "",
      https: true,
      rjsfForm: true,
    });
    expect(scriptSrc(csp)).toBe("script-src 'self' 'nonce-n' 'unsafe-eval' https://plausible.io");
  });

  it("dev keeps 'unsafe-eval' for HMR either way", () => {
    for (const rjsfForm of [true, false]) {
      const csp = buildCsp({ production: false, supabaseHost: "", https: false, rjsfForm });
      expect(scriptSrc(csp)).toContain("'unsafe-eval'");
    }
  });

  it("the default build (no flags, no API) cannot render the form", () => {
    expect(rjsfFormReachable(OFF)).toBe(false);
  });

  it("the multi-domain flag alone, or a domain flag alone, does not make a domain reachable", () => {
    expect(rjsfFormReachable({ ...OFF, qcompassMultiDomain: true })).toBe(false);
    for (const d of DOMAINS) expect(rjsfFormReachable({ ...OFF, [d]: true })).toBe(false);
  });

  it("any QCompass domain with the multi-domain flag can render it", () => {
    for (const d of DOMAINS) {
      expect(rjsfFormReachable({ ...OFF, qcompassMultiDomain: true, [d]: true })).toBe(true);
    }
  });

  it("a live API can render it for cosmology too (the API serves its schema)", () => {
    expect(rjsfFormReachable({ ...OFF, liveBackend: true })).toBe(true);
  });
});

describe("posthogOrigins (posthog-js 1.371.4 RequestRouter)", () => {
  it("routes the default app.posthog.com host to the US cloud", () => {
    expect(posthogOrigins("https://app.posthog.com")).toEqual({
      api: "https://us.i.posthog.com",
      assets: "https://us-assets.i.posthog.com",
    });
    expect(posthogOrigins("https://app.posthog.com/")).toEqual(
      posthogOrigins("https://app.posthog.com"),
    );
  });

  it("routes US and EU cloud hosts to their assets hosts", () => {
    expect(posthogOrigins("https://us.i.posthog.com")?.assets).toBe(
      "https://us-assets.i.posthog.com",
    );
    expect(posthogOrigins("https://eu.i.posthog.com")).toEqual({
      api: "https://eu.i.posthog.com",
      assets: "https://eu-assets.i.posthog.com",
    });
  });

  it("serves both from a custom host (reverse proxy, self-hosted)", () => {
    expect(posthogOrigins("https://ph.example.org/ingest")).toEqual({
      api: "https://ph.example.org",
      assets: "https://ph.example.org",
    });
  });

  it("is undefined for an unset or invalid host", () => {
    expect(posthogOrigins(undefined)).toBeUndefined();
    expect(posthogOrigins("")).toBeUndefined();
    expect(posthogOrigins("not a url")).toBeUndefined();
  });
});

describe("cspSources", () => {
  it("adds the build-time Supabase origin (and its socket) to connect-src", () => {
    const { connectOrigins } = cspSources({ supabaseBuildUrl: "https://proj.supabase.co" });
    expect(connectOrigins).toEqual(["https://proj.supabase.co", "wss://proj.supabase.co"]);
    // Without a runtime SUPABASE_URL on the Worker, the browser client's origin is still allowed.
    const csp = buildCsp({ production: true, supabaseHost: "", https: true, connectOrigins });
    expect(directives(csp).find((d) => d.startsWith("connect-src"))).toContain(
      "https://proj.supabase.co wss://proj.supabase.co",
    );
  });

  it("keeps the runtime Supabase origin next to a different build-time one", () => {
    const { connectOrigins } = cspSources({ supabaseBuildUrl: "https://build.supabase.co" });
    const csp = buildCsp({
      production: true,
      supabaseHost: "https://runtime.supabase.co",
      https: true,
      connectOrigins,
    });
    const connect = directives(csp).find((d) => d.startsWith("connect-src")) ?? "";
    expect(connect).toContain("https://runtime.supabase.co");
    expect(connect).toContain("https://build.supabase.co");
  });

  it("lists an origin once when runtime and build time agree", () => {
    const { connectOrigins } = cspSources({ supabaseBuildUrl: "https://proj.supabase.co/" });
    const csp = buildCsp({
      production: true,
      supabaseHost: "https://proj.supabase.co",
      https: true,
      connectOrigins,
    });
    expect(csp.split("https://proj.supabase.co ").length - 1).toBe(1);
  });

  it("PostHog not configured: nothing in script-src, no PostHog origins", () => {
    const s = cspSources({ posthogApiHost: "https://app.posthog.com" });
    expect(s).toEqual({ connectOrigins: [], scriptOrigins: [] });
    const csp = buildCsp({ production: true, supabaseHost: "", https: true, ...s });
    expect(csp).not.toContain("assets.i.posthog.com");
  });

  it("PostHog configured: its assets host in script-src, API and assets in connect-src", () => {
    const s = cspSources({ posthogKey: "phc_test", posthogApiHost: "https://app.posthog.com" });
    expect(s.scriptOrigins).toEqual(["https://us-assets.i.posthog.com"]);
    expect(s.connectOrigins).toEqual([
      "https://us.i.posthog.com",
      "https://us-assets.i.posthog.com",
    ]);
    const csp = buildCsp({ production: true, nonce: "n", supabaseHost: "", https: true, ...s });
    expect(directives(csp).find((d) => d.startsWith("script-src"))).toBe(
      "script-src 'self' 'nonce-n' 'unsafe-eval' https://plausible.io https://us-assets.i.posthog.com",
    );
    expect(directives(csp).find((d) => d.startsWith("connect-src"))).toContain(
      "https://us.i.posthog.com https://us-assets.i.posthog.com",
    );
  });

  it("keeps the API origin and its socket, and a custom PostHog host setting", () => {
    const s = cspSources({
      apiUrl: "https://api.example.org/v1",
      posthogHostSetting: "https://eu.i.posthog.com",
    });
    expect(s.connectOrigins).toEqual([
      "https://api.example.org",
      "wss://api.example.org",
      "https://eu.i.posthog.com",
    ]);
  });
});
