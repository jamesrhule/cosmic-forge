/**
 * Domain visualizer streaming service.
 *
 * Two transports, both speaking the P0-02 `cosmic_forge_viz` stream
 * protocol (docs/build/lanes/P0-02-viz.md, "Protocol notes"):
 *   - `sse`: named events `header` (run metadata), `frame` (bare frame
 *     JSON), `done`. Not available for gravity / statmech.
 *   - `ws`:  every message is a binary envelope `{type, seq, tau,
 *     payload}` (msgpack, or JSON bytes when the server lacks msgpack):
 *     `header` → `frame`×N → `end` (or `error`). Default when the
 *     `liveDomainStream` feature flag is on.
 *
 * Every domain is served on the M8 `/ws/qcompass/…` route, which has no
 * SSE counterpart, so `sse` falls back to the WebSocket (c5).
 * Every frame is lifted into the canonical panel types by the shared
 * normaliser; header payloads and frames of another domain are dropped.
 */

import { API_BASE_URL, FEATURES } from "@/config/features";
import { apiSse } from "@/lib/apiClient";
import { domainVisualizationPath, unwrapStreamEnvelope } from "@/lib/visualizer/domainFrames";
import type { DomainVisualizationFrame, VisualizationDomain } from "@/types/manifest";

export interface OpenStreamOptions {
  transport?: "sse" | "ws";
  totalFrames?: number;
  fps?: number;
  signal?: AbortSignal;
}

export interface DomainStream {
  frames: AsyncIterable<DomainVisualizationFrame>;
  close: () => void;
}

export function openDomainStream(
  domain: VisualizationDomain,
  runId: string,
  opts: OpenStreamOptions = {},
): DomainStream {
  let transport = opts.transport ?? (FEATURES.liveDomainStream ? "ws" : "sse");
  if (transport === "sse" && domainVisualizationPath("sse", domain, runId) === null)
    transport = "ws";
  return transport === "ws"
    ? openWebSocketStream(domain, runId, opts)
    : openSseStream(domain, runId, opts);
}

function queryOf(opts: OpenStreamOptions): string {
  const params = new URLSearchParams();
  if (opts.totalFrames !== undefined) params.set("total", String(opts.totalFrames));
  if (opts.fps !== undefined) params.set("fps", String(opts.fps));
  const q = params.toString();
  return q ? `?${q}` : "";
}

// ─── SSE transport ─────────────────────────────────────────────────────

function openSseStream(
  domain: VisualizationDomain,
  runId: string,
  opts: OpenStreamOptions,
): DomainStream {
  const ctrl = new AbortController();
  if (opts.signal) {
    opts.signal.addEventListener("abort", () => ctrl.abort(), { once: true });
  }
  const path = `${domainVisualizationPath("sse", domain, runId)}${queryOf(opts)}`;
  // apiSse yields each event's JSON data and stops on `done`; the
  // `header` event's data has no τ and is skipped by the unwrapper.
  const raw = apiSse<unknown>(path, { signal: ctrl.signal });
  async function* frames(): AsyncGenerator<DomainVisualizationFrame> {
    for await (const msg of raw) {
      const f = unwrapStreamEnvelope(msg, domain);
      if (f === "end") return;
      if (f) yield f;
    }
  }
  return { frames: frames(), close: () => ctrl.abort() };
}

// ─── WebSocket transport ───────────────────────────────────────────────

async function decodeMessage(data: ArrayBuffer): Promise<unknown> {
  const bytes = new Uint8Array(data);
  // JSON-bytes fallback when the server has no msgpack encoder.
  if (bytes[0] === 0x7b /* "{" */) {
    return JSON.parse(new TextDecoder("utf-8").decode(bytes));
  }
  // Dynamic import keeps @msgpack/msgpack (a direct dependency) out of
  // the critical bundle.
  const mod = await import("@msgpack/msgpack");
  return mod.decode(bytes);
}

function openWebSocketStream(
  domain: VisualizationDomain,
  runId: string,
  opts: OpenStreamOptions,
): DomainStream {
  const base = API_BASE_URL.replace(/^http/, "ws").replace(/\/+$/, "");
  const url = `${base}${domainVisualizationPath("ws", domain, runId)}${queryOf(opts)}`;

  const queue: DomainVisualizationFrame[] = [];
  const waiters: ((value: IteratorResult<DomainVisualizationFrame>) => void)[] = [];
  let closed = false;
  // Messages decode asynchronously; chain them so frame order is kept.
  let chain: Promise<void> = Promise.resolve();

  const ws = new WebSocket(url);
  ws.binaryType = "arraybuffer";

  const done = (): IteratorResult<DomainVisualizationFrame> => ({
    value: undefined as unknown as DomainVisualizationFrame,
    done: true,
  });

  function push(frame: DomainVisualizationFrame) {
    const w = waiters.shift();
    if (w) w({ value: frame, done: false });
    else queue.push(frame);
  }

  const cleanup = () => {
    if (closed) return;
    closed = true;
    // The server keeps the socket open after `end` until we close it.
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) ws.close();
    while (waiters.length) waiters.shift()!(done());
  };

  ws.addEventListener("message", (ev: MessageEvent) => {
    if (!(ev.data instanceof ArrayBuffer)) return; // protocol is binary-only
    const data = ev.data;
    chain = chain.then(async () => {
      if (closed) return;
      try {
        const f = unwrapStreamEnvelope(await decodeMessage(data), domain);
        if (f === "end") cleanup();
        else if (f) push(f);
      } catch {
        /* skip malformed message */
      }
    });
  });
  ws.addEventListener("close", () => {
    // Let already-received messages drain before signalling the end.
    chain = chain.then(cleanup);
  });
  ws.addEventListener("error", cleanup);
  if (opts.signal) opts.signal.addEventListener("abort", cleanup, { once: true });

  const iterator: AsyncIterator<DomainVisualizationFrame> = {
    next() {
      if (queue.length > 0) return Promise.resolve({ value: queue.shift()!, done: false });
      if (closed) return Promise.resolve(done());
      return new Promise((resolve) => waiters.push(resolve));
    },
    return() {
      cleanup();
      return Promise.resolve(done());
    },
  };

  return {
    frames: { [Symbol.asyncIterator]: () => iterator },
    close: cleanup,
  };
}
