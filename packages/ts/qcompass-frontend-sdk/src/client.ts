/**
 * Tiny HTTP client + SSE/WS helpers (PROMPT 8 v2 §C).
 *
 * The SDK stays dependency-free so `pnpm install` in the broader
 * monorepo doesn't pull anything new. Native `fetch` + native
 * `EventSource` + native `WebSocket` are assumed (Node 22 / modern
 * browsers).
 */

export class QcompassError extends Error {
  readonly status: number;
  readonly body: unknown;
  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
    this.name = "QcompassError";
  }
}

export interface ClientConfig {
  /** Base URL of the FastAPI server (no trailing slash). */
  baseUrl: string;
  /** Optional bearer token (forwarded as `Authorization`). */
  token?: string;
  /** Optional fetch override (for tests / custom transports). */
  fetchImpl?: typeof fetch;
}

export class QcompassClient {
  readonly baseUrl: string;
  readonly token?: string;
  private readonly fetchImpl: typeof fetch;

  constructor(cfg: ClientConfig) {
    this.baseUrl = cfg.baseUrl.replace(/\/+$/, "");
    this.token = cfg.token;
    this.fetchImpl = cfg.fetchImpl ?? globalThis.fetch.bind(globalThis);
  }

  async getJson<T>(path: string): Promise<T> {
    const resp = await this.fetchImpl(`${this.baseUrl}${path}`, {
      headers: this.headers(),
    });
    return this.parseJson<T>(resp);
  }

  async postJson<T>(path: string, body: unknown): Promise<T> {
    const resp = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { ...this.headers(), "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return this.parseJson<T>(resp);
  }

  async deleteJson<T>(path: string): Promise<T> {
    const resp = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method: "DELETE",
      headers: this.headers(),
    });
    return this.parseJson<T>(resp);
  }

  /**
   * Open an SSE stream and yield typed event payloads. Use as:
   *   for await (const ev of client.sse<RunEvent>('/api/...')) ...
   * Server events are JSON-decoded; non-JSON `data:` lines are
   * yielded as the raw string under the `_raw` field.
   */
  async *sse<T>(path: string): AsyncIterable<T> {
    if (typeof globalThis.EventSource === "undefined") {
      yield* sseViaFetch<T>(this.baseUrl + path, this.fetchImpl, this.headers());
      return;
    }
    const url = `${this.baseUrl}${path}`;
    const es = new globalThis.EventSource(url);
    try {
      while (true) {
        const ev = await waitForMessage(es);
        if (ev === "close") return;
        try {
          yield JSON.parse(ev.data) as T;
        } catch {
          yield { _raw: ev.data } as unknown as T;
        }
      }
    } finally {
      es.close();
    }
  }

  /**
   * Open a WS connection and return the raw socket. The cosmic_forge_viz
   * WS endpoint sends ormsgpack-framed envelopes; the SDK ships
   * `decodeFrame` for the JSON fallback path.
   */
  openWebSocket(path: string, protocols?: string | string[]): WebSocket {
    const proto = this.baseUrl.startsWith("https") ? "wss" : "ws";
    const url = this.baseUrl.replace(/^https?/, proto) + path;
    return new globalThis.WebSocket(url, protocols);
  }

  private headers(): Record<string, string> {
    const h: Record<string, string> = { Accept: "application/json" };
    if (this.token) h.Authorization = `Bearer ${this.token}`;
    return h;
  }

  private async parseJson<T>(resp: Response): Promise<T> {
    if (!resp.ok) {
      const text = await resp.text();
      let body: unknown = text;
      try {
        body = JSON.parse(text);
      } catch {
        // keep text body
      }
      throw new QcompassError(
        resp.status,
        `${resp.status} ${resp.statusText} on ${resp.url}`,
        body,
      );
    }
    return resp.json() as Promise<T>;
  }
}

/** JSON-decode a single envelope frame (matches `protocol.encode`). */
export function decodeFrame<T = unknown>(blob: ArrayBuffer | string): T {
  if (typeof blob === "string") {
    return JSON.parse(blob) as T;
  }
  // Try JSON first; ormsgpack decoding requires the @msgpack/msgpack
  // dep which the SDK doesn't bundle. Callers that opt into the
  // binary path should decode externally.
  const text = new TextDecoder().decode(new Uint8Array(blob));
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new QcompassError(
      0, "frame is not JSON; install ormsgpack on the wire if needed",
    );
  }
}

// ── helpers ─────────────────────────────────────────────────────────

function waitForMessage(es: EventSource): Promise<MessageEvent | "close"> {
  return new Promise((resolve, reject) => {
    const onMsg = (ev: MessageEvent) => {
      cleanup();
      resolve(ev);
    };
    const onErr = () => {
      cleanup();
      // EventSource errors are spec-vague; treat as graceful close.
      resolve("close");
    };
    function cleanup() {
      es.removeEventListener("message", onMsg);
      es.removeEventListener("error", onErr);
    }
    es.addEventListener("message", onMsg);
    es.addEventListener("error", onErr);
  });
}

async function* sseViaFetch<T>(
  url: string,
  fetchImpl: typeof fetch,
  headers: Record<string, string>,
): AsyncIterable<T> {
  const resp = await fetchImpl(url, {
    headers: { ...headers, Accept: "text/event-stream" },
  });
  if (!resp.ok || !resp.body) {
    throw new QcompassError(resp.status, `SSE failed for ${url}`);
  }
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const lines = block.split("\n").filter((l) => l.startsWith("data:"));
      if (lines.length === 0) continue;
      const payload = lines.map((l) => l.slice(5).trimStart()).join("\n");
      try {
        yield JSON.parse(payload) as T;
      } catch {
        yield { _raw: payload } as unknown as T;
      }
    }
  }
}
