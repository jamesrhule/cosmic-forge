import { describe, expect, it, vi } from "vitest";
import { parseSse, QcompassClient, QcompassError, getRun, submitRun } from "@qcompass/frontend-sdk";

function streamOf(text: string): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({
    start(ctrl) {
      // Split mid-line so the parser has to buffer.
      ctrl.enqueue(bytes.slice(0, 7));
      ctrl.enqueue(bytes.slice(7));
      ctrl.close();
    },
  });
}

async function collect<T>(it: AsyncIterable<T>): Promise<T[]> {
  const out: T[] = [];
  for await (const v of it) out.push(v);
  return out;
}

describe("@qcompass/frontend-sdk (P4-02)", () => {
  it("parses named SSE events, multi-line data, comments and CRLF", async () => {
    const events = await collect(
      parseSse(
        streamOf(
          ': keep-alive\r\nevent: status\r\ndata: {"status":"running"}\r\n\r\n' +
            'data: {"a":\ndata: 1}\n\n' +
            "event: end\ndata: {}\n\n" +
            "data: not json\n\n",
        ),
      ),
    );
    expect(events).toEqual([
      { event: "status", data: { status: "running" } },
      { event: "message", data: { a: 1 } },
      { event: "end", data: {} },
      { event: "message", data: { _raw: "not json" } },
    ]);
  });

  it("sends per-request headers and the path the OpenAPI route names", async () => {
    const fetchImpl = vi.fn(
      async () => new Response(JSON.stringify({ id: "r1" }), { status: 200 }),
    );
    const client = new QcompassClient({
      baseUrl: "http://api.test/",
      headers: async () => ({ Authorization: "Bearer k", "X-QCompass-Tenant": "acme" }),
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    await getRun(client, "chemistry.molecular", "run 1");
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://api.test/api/qcompass/domains/chemistry.molecular/runs/run%201");
    expect(init.headers).toMatchObject({
      Accept: "application/json",
      Authorization: "Bearer k",
      "X-QCompass-Tenant": "acme",
    });
  });

  it("raises QcompassError with the parsed error envelope", async () => {
    const body = { detail: { code: "PLAN_CONCURRENT_JOBS_EXCEEDED", message: "limit 1" } };
    const fetchImpl = vi.fn(async () => new Response(JSON.stringify(body), { status: 429 }));
    const client = new QcompassClient({
      baseUrl: "http://api.test",
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    const err = await submitRun(client, "chemistry", { molecule: "H2" }).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(QcompassError);
    expect((err as QcompassError).status).toBe(429);
    expect((err as QcompassError).body).toEqual(body);
    const [, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ molecule: "H2" });
  });
});
