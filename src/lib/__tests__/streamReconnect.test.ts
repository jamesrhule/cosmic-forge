import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// c3-stream-bounds (SF1): the API ends a run stream with STREAM_ABORTED after
// its idle or overall bound. While the run is not over, the client
// reconnects and resumes where it was, without repeating events.
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

import { streamRun as streamDomainRun } from "@/services/qcompass/runs";
import { streamRun as streamCosmologyRun } from "@/services/simulator";

const sse = (events: [string, unknown][]) =>
  new Response(events.map(([e, d]) => `event: ${e}\ndata: ${JSON.stringify(d)}\n\n`).join(""), {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });

const ABORTED: [string, unknown] = [
  "error",
  { code: "STREAM_ABORTED", message: "no run event for 900s; reconnect to resume" },
];
const fetchMock = vi.fn();
let streams: Response[] = [];
let runs: Record<string, unknown>[] = [];

function route(base: string, runId: string) {
  fetchMock.mockImplementation(async (url: string) => {
    if (url === `${base}/${runId}/stream`) {
      const next = streams.shift();
      if (!next) throw new Error("unexpected extra stream");
      return next;
    }
    if (url === `${base}/${runId}`) {
      const run = runs.length > 1 ? runs.shift() : runs[0];
      return new Response(JSON.stringify(run), { status: 200 });
    }
    return new Response(JSON.stringify({ detail: { code: "NOT_FOUND", message: url } }), {
      status: 404,
    });
  });
}

const streamCalls = () =>
  fetchMock.mock.calls.map((c) => String(c[0])).filter((u) => u.endsWith("/stream")).length;

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("run streams reconnect after STREAM_ABORTED while the run is not over", () => {
  it("domain runs resume without repeating events and end with the result", async () => {
    const base = "http://api.test/api/qcompass/domains/chemistry.molecular/runs";
    streams = [
      sse([
        ["history", { runId: "qc_long" }],
        ["status", { status: "running" }],
        ["progress", { stage: "prepare", fraction: 0.5 }],
        ABORTED,
        ["end", {}],
      ]),
      sse([
        ["history", { runId: "qc_long" }],
        ["status", { status: "running" }],
        ["progress", { stage: "prepare", fraction: 0.5 }],
        ["progress", { stage: "run", fraction: 1.0 }],
        ["status", { status: "completed" }],
        ["end", {}],
      ]),
    ];
    const done = {
      id: "qc_long",
      domain: "chemistry.molecular",
      label: "x",
      status: "completed",
      created_at: "2026-11-02T00:00:00Z",
      payload: { status_detail: "completed" },
    };
    runs = [{ ...done, status: "running" }, done];
    route(base, "qc_long");
    const got = [];
    for await (const ev of streamDomainRun("chemistry.molecular", "qc_long")) got.push(ev);
    expect(got.map((e) => [e.type, "progress" in e ? e.progress : undefined])).toEqual([
      ["queued", undefined],
      ["running", 0],
      ["running", 0.5],
      ["running", 1.0],
      ["result", undefined],
    ]);
    expect(streamCalls()).toBe(2);
  });

  it("a domain run that ended while the stream was down is not streamed again", async () => {
    const base = "http://api.test/api/qcompass/domains/chemistry.molecular/runs";
    streams = [sse([["history", { runId: "qc_gone" }], ABORTED, ["end", {}]])];
    runs = [
      {
        id: "qc_gone",
        domain: "chemistry.molecular",
        label: "x",
        status: "failed",
        created_at: "2026-11-02T00:00:00Z",
        payload: { error: "JOB_TIMEOUT" },
      },
    ];
    route(base, "qc_gone");
    const got = [];
    for await (const ev of streamDomainRun("chemistry.molecular", "qc_gone")) got.push(ev);
    expect(got.at(-1)).toMatchObject({ type: "error", message: "Run qc_gone failed: JOB_TIMEOUT" });
    expect(streamCalls()).toBe(1);
  });

  it("cosmology runs resume and end with the result instead of stopping silently", async () => {
    const base = "http://api.test/api/qcompass/domains/cosmology.ucglef1/runs";
    streams = [
      sse([
        ["history", { runId: "qc_cosmo" }],
        ["status", { status: "running", at: "t" }],
        ["progress", { module: "M1", fraction: 1 / 6, detail: "M1 finished" }],
        ABORTED,
        ["end", {}],
      ]),
      sse([
        ["history", { runId: "qc_cosmo" }],
        ["status", { status: "running", at: "t" }],
        ["progress", { module: "M1", fraction: 1 / 6, detail: "M1 finished" }],
        ["progress", { module: "M2", fraction: 2 / 6, detail: "M2 finished" }],
        ["status", { status: "completed", at: "t" }],
        ["end", {}],
      ]),
    ];
    const result = { id: "qcrun_x", eta_B: { value: 6.1e-10 }, audit: { checks: [] } };
    const done = {
      id: "qc_cosmo",
      domain: "cosmology.ucglef1",
      label: "x",
      status: "completed",
      created_at: "2026-11-02T00:00:00Z",
      provenance: { classical_reference_hash: "" },
      payload: { status_detail: "completed", result: { run_result: result } },
    };
    runs = [{ ...done, status: "running", payload: {} }, done];
    route(base, "qc_cosmo");
    const got = [];
    for await (const ev of streamCosmologyRun("qc_cosmo")) got.push(ev);
    expect(got.map((e) => e.type)).toEqual(["status", "progress", "progress", "status", "result"]);
    expect(got.filter((e) => e.type === "progress").map((e) => e.module)).toEqual(["M1", "M2"]);
    expect(got.at(-1)).toMatchObject({ type: "result", payload: { eta_B: { value: 6.1e-10 } } });
    expect(streamCalls()).toBe(2);
  });
});
