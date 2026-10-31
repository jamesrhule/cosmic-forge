/**
 * Domain visualizer streaming service.
 *
 * Two transports:
 *   - `sse`: JSON frames over `apiSse`. Always available when the
 *     backend is configured.
 *   - `ws`:  binary msgpack frames over a WebSocket. Behind the
 *     `liveDomainStream` feature flag because msgpack support is
 *     loaded dynamically.
 */

import { API_BASE_URL, FEATURES } from "@/config/features";
import { apiSse } from "@/lib/apiClient";
import type {
  DomainVisualizationFrame,
  VisualizationDomain,
} from "@/types/manifest";

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
  const transport = opts.transport
    ?? (FEATURES.liveDomainStream ? "ws" : "sse");
  if (transport === "ws") {
    return openWebSocketStream(domain, runId, opts);
  }
  return openSseStream(domain, runId, opts);
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
  const params = new URLSearchParams();
  if (opts.totalFrames !== undefined) params.set("total", String(opts.totalFrames));
  if (opts.fps !== undefined) params.set("fps", String(opts.fps));
  const query = params.toString();
  const path = `/sse/runs/${domain}/${encodeURIComponent(runId)}/visualization${
    query ? `?${query}` : ""
  }`;
  const iter = apiSse<DomainVisualizationFrame>(path, { signal: ctrl.signal });
  return {
    frames: iter,
    close: () => ctrl.abort(),
  };
}

// ─── WebSocket transport ───────────────────────────────────────────────

async function decodeMsgpack(data: ArrayBuffer): Promise<unknown> {
  // Dynamic import keeps @msgpack/msgpack out of the critical bundle
  // and lets the build succeed when the optional dep isn't installed.
  try {
    const mod = await import(/* @vite-ignore */ "@msgpack/msgpack");
    return mod.decode(new Uint8Array(data));
  } catch {
    // Fallback: assume the server fell back to JSON-encoded bytes.
    const text = new TextDecoder("utf-8").decode(new Uint8Array(data));
    return JSON.parse(text);
  }
}

function openWebSocketStream(
  domain: VisualizationDomain,
  runId: string,
  opts: OpenStreamOptions,
): DomainStream {
  const base = API_BASE_URL.replace(/^http/, "ws").replace(/\/+$/, "");
  const params = new URLSearchParams();
  if (opts.totalFrames !== undefined) params.set("total", String(opts.totalFrames));
  if (opts.fps !== undefined) params.set("fps", String(opts.fps));
  const query = params.toString();
  const url = `${base}/ws/runs/${domain}/${encodeURIComponent(runId)}/visualization${
    query ? `?${query}` : ""
  }`;

  const queue: DomainVisualizationFrame[] = [];
  const waiters: ((value: IteratorResult<DomainVisualizationFrame>) => void)[] = [];
  let closed = false;

  const ws = new WebSocket(url);
  ws.binaryType = "arraybuffer";

  function deliver(value: IteratorResult<DomainVisualizationFrame>) {
    const w = waiters.shift();
    if (w) w(value);
  }

  ws.addEventListener("message", async (ev) => {
    if (typeof ev.data === "string") {
      if (ev.data === "__done__") {
        closed = true;
        while (waiters.length) deliver({ value: undefined, done: true });
      }
      return;
    }
    if (ev.data instanceof ArrayBuffer) {
      try {
        const decoded = (await decodeMsgpack(ev.data)) as DomainVisualizationFrame;
        if (waiters.length) {
          deliver({ value: decoded, done: false });
        } else {
          queue.push(decoded);
        }
      } catch {
        /* skip malformed frame */
      }
    }
  });

  const cleanup = () => {
    closed = true;
    if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
      ws.close();
    }
    while (waiters.length) deliver({ value: undefined, done: true });
  };

  ws.addEventListener("close", cleanup);
  ws.addEventListener("error", cleanup);

  if (opts.signal) {
    opts.signal.addEventListener("abort", cleanup, { once: true });
  }

  const iterator: AsyncIterator<DomainVisualizationFrame> = {
    next() {
      if (queue.length > 0) {
        return Promise.resolve({ value: queue.shift()!, done: false });
      }
      if (closed) {
        return Promise.resolve({ value: undefined as unknown as DomainVisualizationFrame, done: true });
      }
      return new Promise((resolve) => {
        waiters.push(resolve);
      });
    },
    return() {
      cleanup();
      return Promise.resolve({ value: undefined as unknown as DomainVisualizationFrame, done: true });
    },
  };

  return {
    frames: { [Symbol.asyncIterator]: () => iterator },
    close: cleanup,
  };
}
