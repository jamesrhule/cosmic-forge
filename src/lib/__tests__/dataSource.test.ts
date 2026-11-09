import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// P4-02: with VITE_API_URL set, services use the SDK and never read a
// fixture — not even after an API error.
vi.mock("@/config/features", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/config/features")>();
  return {
    ...real,
    API_BASE_URL: "http://api.test",
    DATA_SOURCE: "api",
    FEATURES: { ...real.FEATURES, liveBackend: true, persistRuns: false, qcompassAuth: false },
  };
});

// The real loader imports `cloudflare:workers` (SSR); record every call
// instead and apply the real guard, so a fixture read would be visible.
const { fixtureCalls } = vi.hoisted(() => ({ fixtureCalls: [] as string[] }));
vi.mock("@/lib/fixtures", async () => {
  const { assertFixtureReadAllowed } = await import("@/lib/fixtureGuard");
  const read = async (path: string) => {
    fixtureCalls.push(path);
    assertFixtureReadAllowed(path);
    throw new Error(`test double: would fetch /fixtures/${path}`);
  };
  return {
    loadFixture: read,
    loadJsonlFixture: async function* (path: string) {
      yield await read(path);
    },
    sleep: async () => {},
  };
});

import { assertFixtureReadAllowed } from "@/lib/fixtureGuard";
import { getRun, listRuns, startRun } from "@/services/qcompass/runs";
import { getBenchmarks } from "@/services/simulator";
import { getManifestSchema } from "@/services/qcompass/manifestSchema";
import { ServiceError } from "@/types/domain";

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  fixtureCalls.length = 0;
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function urls(): string[] {
  return fetchMock.mock.calls.map((c) => String(c[0]));
}

describe("DATA_SOURCE = api", () => {
  it("the fixture guard refuses data fixtures and allows reference content", () => {
    expect(() => assertFixtureReadAllowed("benchmarks.json")).toThrow(ServiceError);
    expect(() => assertFixtureReadAllowed("chemistry/runs/h2-sto3g.json")).toThrow(
      /not read when VITE_API_URL is set/,
    );
    expect(() => assertFixtureReadAllowed("formulas/F1-F7.json")).not.toThrow();
  });

  it("services call the API through the SDK", async () => {
    fetchMock.mockImplementation(async (url: string) => {
      if (url.endsWith("/runs") && fetchMock.mock.calls.at(-1)?.[1]?.method === "POST") {
        return new Response(JSON.stringify({ runId: "qc_1" }), { status: 202 });
      }
      return new Response(JSON.stringify(url.endsWith("/runs") ? [] : { benchmarks: [] }), {
        status: 200,
      });
    });
    expect(await listRuns("chemistry.molecular")).toEqual([]);
    expect(await startRun("chemistry.molecular", { molecule: "H2" })).toEqual({ runId: "qc_1" });
    await getBenchmarks();
    expect(urls()).toEqual([
      "http://api.test/api/qcompass/domains/chemistry.molecular/runs",
      "http://api.test/api/qcompass/domains/chemistry.molecular/runs",
      "http://api.test/api/benchmarks",
    ]);
    expect(fixtureCalls).toEqual([]);
  });

  it("an API error propagates as ServiceError with no fixture fallback", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: { code: "NOT_FOUND", message: "no run" } }), {
        status: 404,
      }),
    );
    const err = await getRun("hep.lattice", "schwinger-1plus1d").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ServiceError);
    expect((err as ServiceError).code).toBe("NOT_FOUND");
    await expect(getManifestSchema("hep.lattice")).rejects.toBeInstanceOf(ServiceError);
    expect(urls().some((u) => u.includes("/fixtures/"))).toBe(false);
    expect(fixtureCalls).toEqual([]);
  });

  it("an unreachable API is UPSTREAM_FAILURE, not a fixture", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(getBenchmarks()).rejects.toMatchObject({ code: "UPSTREAM_FAILURE" });
    expect(urls()).toEqual(["http://api.test/api/benchmarks"]);
    expect(fixtureCalls).toEqual([]);
  });
});
