/**
 * Builds without 'unsafe-eval' (src/lib/csp.ts, `rjsfFormReachable`) run zod
 * jitless, so its `new Function` probe never runs; builds that can render the
 * RJSF form keep zod's default.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

afterEach(() => {
  vi.doUnmock("@/config/features");
  vi.resetModules();
  delete z.config().jitless;
});

async function load(flags: Record<string, boolean>) {
  vi.resetModules();
  vi.doMock("@/config/features", async (importOriginal) => {
    const real = await importOriginal<typeof import("@/config/features")>();
    return { ...real, FEATURES: { ...real.FEATURES, ...flags } };
  });
  return import("@/lib/zod-csp");
}

describe("src/lib/zod-csp.ts", () => {
  it("default build (no 'unsafe-eval'): importing it makes zod jitless", async () => {
    delete z.config().jitless;
    const m = await load({ liveBackend: false, qcompassMultiDomain: false });
    expect(m.ZOD_JITLESS).toBe(true);
    expect(z.config().jitless).toBe(true);
  });

  it("a build that can render the RJSF form ('unsafe-eval'): zod keeps its default", async () => {
    delete z.config().jitless;
    const m = await load({ qcompassMultiDomain: true, qcompassChemistry: true });
    expect(m.ZOD_JITLESS).toBe(false);
    expect(z.config().jitless).toBeUndefined();
  });

  it("is a declared side effect and the first import of the client entry modules", () => {
    const read = (p: string) => readFileSync(resolve(process.cwd(), p), "utf8");
    expect(JSON.parse(read("package.json")).sideEffects).toContain("./src/lib/zod-csp.ts");
    for (const entry of ["src/start.ts", "src/router.tsx"]) {
      const firstImport = read(entry)
        .split("\n")
        .find((l) => l.startsWith("import "));
      expect(firstImport, entry).toBe('import "@/lib/zod-csp";');
    }
  });
});
