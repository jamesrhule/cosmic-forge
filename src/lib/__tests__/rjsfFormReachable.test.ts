/**
 * `rjsfFormReachable` (src/lib/csp.ts) decides whether production script-src
 * carries 'unsafe-eval'. These tests tie it to what the app really registers:
 * for each flag set, the domain plugins are loaded with those flags and the
 * configurator form counts as reachable when a domain that the configurator
 * route resolves (`resolveDomain`: registered, visible, enabled) has a
 * manifest-schema fixture, or a live API serves the schema.
 */
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { FeatureFlags } from "@/config/features";
import { rjsfFormReachable } from "@/lib/csp";

const OFF = {
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
type Flags = typeof OFF;

const DOMAIN_FLAGS = [
  "qcompassChemistry",
  "qcompassCondmat",
  "qcompassAmo",
  "qcompassHep",
  "qcompassNuclear",
  "qcompassGravity",
  "qcompassStatmech",
] as const;

const FLAG_SETS: Flags[] = [
  OFF,
  { ...OFF, qcompassMultiDomain: true },
  ...DOMAIN_FLAGS.map((d) => ({ ...OFF, [d]: true })),
  ...DOMAIN_FLAGS.map((d) => ({ ...OFF, qcompassMultiDomain: true, [d]: true })),
  Object.fromEntries(Object.keys(OFF).map((k) => [k, k !== "liveBackend"])) as Flags,
  { ...OFF, liveBackend: true },
];

async function loadWith(flags: Flags) {
  vi.resetModules();
  // The plugins' services import the fixture loader, which imports the
  // Worker-only `cloudflare:workers`; nothing here loads a fixture.
  vi.doMock("@/lib/fixtures", () => ({}));
  vi.doMock("@/config/features", async (importOriginal) => {
    const real = await importOriginal<typeof import("@/config/features")>();
    return {
      ...real,
      FEATURES: { ...real.FEATURES, ...flags } satisfies FeatureFlags,
    };
  });
  await import("@/lib/domains/register-all");
  return import("@/lib/domains/registry");
}

afterEach(() => {
  vi.doUnmock("@/config/features");
  vi.doUnmock("@/lib/fixtures");
  vi.resetModules();
});

const fixture = (p: string) => resolve(process.cwd(), "public/fixtures", p);

describe("rjsfFormReachable matches the registered domains", () => {
  for (const flags of FLAG_SETS) {
    const on = Object.entries(flags)
      .filter(([, v]) => v)
      .map(([k]) => k);
    it(`flags: ${on.join(", ") || "none"}`, async () => {
      const { listDomains, getDomain } = await loadWith(flags);
      const withSchema = listDomains().filter(
        (p) =>
          getDomain(p.id) !== undefined &&
          p.enabled &&
          existsSync(fixture(p.manifestSchemaUrl ?? `${p.id}/manifest-schema.json`)),
      );
      expect(rjsfFormReachable(flags)).toBe(flags.liveBackend || withSchema.length > 0);
    });
  }

  it("cosmology, enabled in every build, has no manifest-schema fixture", async () => {
    const { getDomain } = await loadWith(OFF);
    const cosmology = getDomain("cosmology.ucglef1");
    expect(cosmology?.enabled).toBe(true);
    expect(cosmology?.manifestSchemaUrl).toBeUndefined();
    expect(existsSync(fixture("cosmology.ucglef1/manifest-schema.json"))).toBe(false);
  });

  it("every QCompass domain's manifest schema is a fixture", async () => {
    const all = Object.fromEntries(Object.keys(OFF).map((k) => [k, true])) as Flags;
    const { listDomains } = await loadWith(all);
    const qcompass = listDomains().filter((p) => p.id !== "cosmology.ucglef1");
    expect(qcompass).toHaveLength(DOMAIN_FLAGS.length);
    for (const p of qcompass) {
      expect(p.manifestSchemaUrl, p.id).toBeDefined();
      expect(existsSync(fixture(p.manifestSchemaUrl!)), p.id).toBe(true);
    }
  });
});
