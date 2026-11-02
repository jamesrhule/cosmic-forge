import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// SF5: the live cosmology path submits and reads through one route, the
// platform route for `cosmology.ucglef1`, and waits for the terminal status.
vi.mock("@/config/features", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/config/features")>();
  return {
    ...real,
    API_BASE_URL: "http://api.test",
    DATA_SOURCE: "api",
    FEATURES: { ...real.FEATURES, liveBackend: true, persistRuns: false, qcompassAuth: false },
  };
});
vi.mock("@/lib/fixtures", () => ({
  loadFixture: async (path: string) => {
    throw new Error(`fixture read in API mode: ${path}`);
  },
  loadJsonlFixture: async function* (path: string) {
    yield await Promise.reject(new Error(`fixture read in API mode: ${path}`));
  },
  sleep: async () => {},
}));

import { cosmologyUcglef1 } from "@/lib/domains/cosmology.ucglef1";
import { cosmologyRunResult, getRun } from "@/services/simulator";
import { downloadArtifact, listArtifacts } from "@/services/artifacts";
import type { Manifest, CosmologyProblem } from "@/lib/domains/types";

const BASE = "http://api.test/api/qcompass/domains/cosmology.ucglef1/runs";
const fetchMock = vi.fn();
let stored: Record<string, unknown> = { id: "qc_c1", status: "queued", payload: {} };

const RESULT = { id: "qcrun_internal", eta_B: { value: 6.1e-10 }, audit: { checks: [] } };

beforeEach(() => {
  fetchMock.mockReset();
  stored = { id: "qc_c1", status: "queued", payload: {} };
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async (url: string, init?: RequestInit) => {
    if (url === BASE && init?.method === "POST") {
      return new Response(JSON.stringify({ runId: "qc_c1" }), { status: 202 });
    }
    if (url === `${BASE}/qc_c1/stream`) {
      // The worker finishes while the client streams.
      stored = {
        id: "qc_c1",
        domain: "cosmology.ucglef1",
        label: "x",
        status: "completed",
        created_at: "2026-10-31T00:00:00Z",
        provenance: { classical_reference_hash: "" },
        payload: { status_detail: "completed", result: { run_result: RESULT } },
      };
      const body =
        'event: history\ndata: {"runId":"qc_c1"}\n\n' +
        'event: status\ndata: {"status":"running","at":"t"}\n\n' +
        'event: progress\ndata: {"stage":"run","fraction":1.0}\n\n' +
        'event: status\ndata: {"status":"completed","at":"t"}\n\n' +
        "event: end\ndata: {}\n\n";
      return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
    }
    if (url === `${BASE}/qc_c1`) return new Response(JSON.stringify(stored), { status: 200 });
    return new Response(JSON.stringify({ detail: { code: "NOT_FOUND", message: url } }), {
      status: 404,
    });
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("live cosmology runs (SF5)", () => {
  it("submits, waits for the terminal status and reads the result on one route", async () => {
    const sim = cosmologyUcglef1.simulation;
    const manifest = {
      domain: "cosmology.ucglef1",
      version: "1.0",
      problem: { potential: { kind: "starobinsky" }, precision: "fast" },
    } as unknown as Manifest<CosmologyProblem>;
    const instance = await sim.prepare(manifest);
    const result = await sim.run(instance);
    expect(result.id).toBe("qc_c1");
    expect(result.eta_B.value).toBe(6.1e-10);
    const urls = fetchMock.mock.calls.map((c) => String(c[0]));
    expect(urls).toEqual([BASE, `${BASE}/qc_c1/stream`, `${BASE}/qc_c1`]);
    expect(urls.some((u) => u.includes("/api/runs/"))).toBe(false);
  });

  it("an unfinished run is not passed off as a result", async () => {
    await expect(getRun("qc_c1")).rejects.toMatchObject({ code: "NOT_FOUND" });
  });

  it("reads agent (ucgle_f1.run) payloads, which are the RunResult itself, on the same route", async () => {
    // The backend serves an agent run on the platform route with the RunResult
    // as its payload, and also on the legacy /api/runs route.
    const agentRun = { id: "run_a", status: "completed", payload: { ...RESULT } };
    fetchMock.mockImplementation(async (url: string) => {
      if (url === `${BASE}/run_a`) return new Response(JSON.stringify(agentRun), { status: 200 });
      if (url.endsWith("/api/runs/run_a")) {
        return new Response(JSON.stringify({ ...RESULT, id: "run_a" }), { status: 200 });
      }
      return new Response(JSON.stringify({ detail: { code: "NOT_FOUND", message: url } }), {
        status: 404,
      });
    });
    const viaGetRun = await getRun("run_a");
    expect(viaGetRun.id).toBe("run_a");
    expect(viaGetRun.eta_B.value).toBe(6.1e-10);
    expect(fetchMock.mock.calls.map((c) => String(c[0]))).toEqual([`${BASE}/run_a`]);
    const r = cosmologyRunResult(agentRun);
    expect(r.id).toBe("run_a");
    expect(r.eta_B.value).toBe(6.1e-10);
  });
});

describe("artefacts in API mode (nit)", () => {
  it("report NOT_IMPLEMENTED instead of calling a route that does not exist", async () => {
    await expect(listArtifacts("qc_c1")).rejects.toMatchObject({ code: "NOT_IMPLEMENTED" });
    await expect(
      downloadArtifact({
        runId: "qc_c1",
        name: "a.csv",
        path: "a.csv",
        mimeType: "text/csv",
        sizeBytes: 1,
        description: "x",
      }),
    ).rejects.toMatchObject({ code: "NOT_IMPLEMENTED" });
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
