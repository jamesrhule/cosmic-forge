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

const persisted = vi.hoisted(() => ({ statuses: [] as string[] }));
vi.mock("@/lib/persistence", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/persistence")>();
  return {
    ...real,
    setRunStatus: async (_id: string, status: string) => {
      persisted.statuses.push(status);
      return { ok: true };
    },
    persistRunResult: async () => ({ ok: true }),
    persistAuditReport: async () => ({ ok: true }),
  };
});

import { parseSse } from "@qcompass/frontend-sdk";
import { streamRun as streamDomainRun } from "@/services/qcompass/runs";
import { awaitRun, streamRun as streamCosmologyRun } from "@/services/simulator";

/** An SSE body; an event given as `[name, data, id]` carries an `id:` line. */
const sse = (events: Array<[string, unknown] | [string, unknown, string]>) =>
  new Response(
    events
      .map(
        ([e, d, id]) =>
          `${id === undefined ? "" : `id: ${id}\n`}event: ${e}\ndata: ${JSON.stringify(d)}\n\n`,
      )
      .join(""),
    { status: 200, headers: { "Content-Type": "text/event-stream" } },
  );

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
  persisted.statuses.length = 0;
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

// WORKER verifier NIT: job_events ids come from a sequence, not commit order,
// so a replay may order events differently from the first delivery. Where the
// stream carries ids, replays are skipped by id, not by count.
describe("replayed events are recognised by id where the stream carries ids", () => {
  it("the SDK's SSE parser keeps each event's own id (not inherited)", async () => {
    const body = sse([
      ["status", { status: "running" }, "7"],
      ["progress", { fraction: 0.5 }],
    ]).body!;
    const got = [];
    for await (const ev of parseSse(body)) got.push(ev);
    expect(got).toEqual([
      { event: "status", data: { status: "running" }, id: "7" },
      { event: "progress", data: { fraction: 0.5 } },
    ]);
  });

  it("an event that committed late is delivered once, and nothing is repeated", async () => {
    const base = "http://api.test/api/qcompass/domains/chemistry.molecular/runs";
    // First delivery: event 2 had not committed yet when 3 was read.
    streams = [
      sse([
        ["history", { runId: "qc_ids" }],
        ["progress", { fraction: 0.1 }, "1"],
        ["progress", { fraction: 0.3 }, "3"],
        ABORTED,
        ["end", {}],
      ]),
      sse([
        ["history", { runId: "qc_ids" }],
        ["progress", { fraction: 0.1 }, "1"],
        ["progress", { fraction: 0.2 }, "2"],
        ["progress", { fraction: 0.3 }, "3"],
        ["status", { status: "completed" }, "4"],
        ["end", {}],
      ]),
    ];
    const done = {
      id: "qc_ids",
      domain: "chemistry.molecular",
      label: "x",
      status: "completed",
      created_at: "2026-11-02T00:00:00Z",
      payload: { status_detail: "completed" },
    };
    runs = [{ ...done, status: "running" }, done];
    route(base, "qc_ids");
    const progress: number[] = [];
    for await (const ev of streamDomainRun("chemistry.molecular", "qc_ids")) {
      if (ev.type === "running") progress.push(ev.progress);
    }
    // By count, the replay would skip 0.1 and 0.2 and repeat 0.3.
    expect(progress).toEqual([0.1, 0.3, 0.2]);
    expect(streamCalls()).toBe(2);
  });

  // W1 R4-API: the API sends each job_events row id as `id:`; events it makes
  // up (history, end, STREAM_ABORTED, the status of a run that ended without
  // one) carry none and fall back to their position among id-less events.
  it("the API's shape (row ids, an id-less status for a run that ended) is delivered once", async () => {
    const base = "http://api.test/api/qcompass/domains/chemistry.molecular/runs";
    streams = [
      sse([
        ["history", { runId: "qc_api" }],
        ["status", { status: "running" }, "41"],
        ["progress", { stage: "run", fraction: 0.4 }, "43"],
        ABORTED,
        ["end", {}],
      ]),
      sse([
        ["history", { runId: "qc_api" }],
        ["status", { status: "running" }, "41"],
        ["progress", { stage: "run", fraction: 0.4 }, "43"],
        ["progress", { stage: "run", fraction: 0.8 }, "44"],
        ["status", { status: "completed" }],
        ["end", {}],
      ]),
    ];
    const done = {
      id: "qc_api",
      domain: "chemistry.molecular",
      label: "x",
      status: "completed",
      created_at: "2026-11-02T00:00:00Z",
      payload: { status_detail: "completed" },
    };
    runs = [{ ...done, status: "running" }, done];
    route(base, "qc_api");
    const got = [];
    for await (const ev of streamDomainRun("chemistry.molecular", "qc_api")) got.push(ev);
    expect(got.map((e) => [e.type, "progress" in e ? e.progress : undefined])).toEqual([
      ["queued", undefined],
      ["running", 0],
      ["running", 0.4],
      ["running", 0.8],
      ["result", undefined],
    ]);
    expect(streamCalls()).toBe(2);
  });
});

// SF5 residual (c5): a cosmology stream that ends while its run is not over
// surfaces STREAM_ABORTED, never "no result yet", and the persisted row is
// not marked completed.
describe("a cosmology stream that ends before its run surfaces STREAM_ABORTED", () => {
  const base = "http://api.test/api/qcompass/domains/cosmology.ucglef1/runs";
  const running = {
    id: "qc_cut",
    domain: "cosmology.ucglef1",
    label: "x",
    status: "running",
    created_at: "2026-11-02T00:00:00Z",
    provenance: { classical_reference_hash: "" },
    payload: {},
  };
  const cut = () =>
    sse([
      ["history", { runId: "qc_cut" }],
      ["status", { status: "running", at: "t" }],
      ["end", {}],
    ]);

  it("awaitRun rejects with STREAM_ABORTED", async () => {
    streams = [cut()];
    runs = [running];
    route(base, "qc_cut");
    await expect(awaitRun("qc_cut")).rejects.toMatchObject({ code: "STREAM_ABORTED" });
  });

  it("streamRun rejects with STREAM_ABORTED and never marks the run completed", async () => {
    streams = [cut()];
    runs = [running];
    route(base, "qc_cut");
    const got: string[] = [];
    await expect(
      (async () => {
        for await (const ev of streamCosmologyRun("qc_cut")) got.push(ev.type);
      })(),
    ).rejects.toMatchObject({ code: "STREAM_ABORTED" });
    expect(got).toEqual(["status"]);
    expect(persisted.statuses).toEqual(["running"]);
  });
});
