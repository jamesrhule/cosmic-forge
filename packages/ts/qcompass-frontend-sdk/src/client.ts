/**
 * HTTP client + SSE/WS helpers for the QCompass compute API.
 *
 * Dependency-free at runtime: native `fetch`, `ReadableStream` and
 * `WebSocket` (Node >= 18, modern browsers). Paths and bodies are typed
 * from the API's OpenAPI document (`./generated/openapi.ts`, P4-02); see
 * `./api.ts` for the helpers that read those types.
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

export type HeaderSource =
  | Record<string, string>
  | (() => Record<string, string> | Promise<Record<string, string>>);

export interface ClientConfig {
  /** Base URL of the FastAPI server (no trailing slash needed). */
  baseUrl: string;
  /** Optional bearer token (forwarded as `Authorization`). */
  token?: string;
  /**
   * Extra headers, or a function returning them per request (e.g. a fresh
   * session token plus `X-QCompass-Tenant`). They override `token`.
   */
  headers?: HeaderSource;
  /** Optional fetch override (for tests / custom transports). */
  fetchImpl?: typeof fetch;
}

/** One server-sent event: its `event:` name and JSON-decoded `data:`. */
export interface SseEvent<T = unknown> {
  event: string;
  data: T;
  /**
   * The `id:` field of this event's own block, when the server sent one.
   * (Unlike `EventSource.lastEventId`, an id is not inherited by later
   * events, so a consumer can tell events with an id from events without.)
   */
  id?: string;
}

export class QcompassClient {
  readonly baseUrl: string;
  readonly token?: string;
  private readonly extraHeaders?: HeaderSource;
  private readonly fetchImpl: typeof fetch;

  constructor(cfg: ClientConfig) {
    // Strip trailing slashes without a backtracking regex (CodeQL js/polynomial-redos).
    let base = cfg.baseUrl;
    while (base.endsWith("/")) base = base.slice(0, -1);
    this.baseUrl = base;
    this.token = cfg.token;
    this.extraHeaders = cfg.headers;
    this.fetchImpl = cfg.fetchImpl ?? globalThis.fetch.bind(globalThis);
  }

  async getJson<T>(path: string, init: { signal?: AbortSignal } = {}): Promise<T> {
    const resp = await this.fetchImpl(`${this.baseUrl}${path}`, {
      headers: await this.headers(),
      signal: init.signal,
    });
    return this.parseJson<T>(resp);
  }

  async postJson<T>(path: string, body: unknown, init: { signal?: AbortSignal } = {}): Promise<T> {
    const resp = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { ...(await this.headers()), "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: init.signal,
    });
    return this.parseJson<T>(resp);
  }

  async deleteJson<T>(path: string): Promise<T> {
    const resp = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method: "DELETE",
      headers: await this.headers(),
    });
    return this.parseJson<T>(resp);
  }

  /** GET a binary body (artefact downloads). */
  async getBlob(path: string): Promise<Blob> {
    const resp = await this.fetchImpl(`${this.baseUrl}${path}`, {
      headers: { ...(await this.headers()), Accept: "*/*" },
    });
    if (!resp.ok) throw await this.error(resp);
    return resp.blob();
  }

  /**
   * Stream server-sent events over `fetch` (so auth headers are sent, which
   * `EventSource` can't do) and yield each event with its name. `data:` is
   * JSON-decoded; a non-JSON payload is yielded as `{ _raw: string }`.
   * The generator ends when the server closes the stream.
   */
  async *sse<T = unknown>(
    path: string,
    init: { method?: "GET" | "POST"; body?: unknown; signal?: AbortSignal } = {},
  ): AsyncGenerator<SseEvent<T>> {
    const headers: Record<string, string> = {
      ...(await this.headers()),
      Accept: "text/event-stream",
    };
    if (init.body !== undefined) headers["Content-Type"] = "application/json";
    const resp = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method: init.method ?? "GET",
      headers,
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
      signal: init.signal,
    });
    if (!resp.ok || !resp.body) throw await this.error(resp);
    yield* parseSse<T>(resp.body);
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

  private async headers(): Promise<Record<string, string>> {
    const h: Record<string, string> = { Accept: "application/json" };
    if (this.token) h.Authorization = `Bearer ${this.token}`;
    const extra =
      typeof this.extraHeaders === "function" ? await this.extraHeaders() : this.extraHeaders;
    return { ...h, ...(extra ?? {}) };
  }

  private async error(resp: Response): Promise<QcompassError> {
    let text = "";
    try {
      text = await resp.text();
    } catch {
      // keep empty body
    }
    let body: unknown = text;
    try {
      body = JSON.parse(text);
    } catch {
      // keep text body
    }
    return new QcompassError(resp.status, `${resp.status} ${resp.statusText} on ${resp.url}`, body);
  }

  private async parseJson<T>(resp: Response): Promise<T> {
    if (!resp.ok) throw await this.error(resp);
    if (resp.status === 204) return undefined as T;
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
    throw new QcompassError(0, "frame is not JSON; install ormsgpack on the wire if needed");
  }
}

/**
 * Parse an SSE byte stream (WHATWG event-stream rules: `event:`, multi-line
 * `data:`, `:` comments, blank-line dispatch; CRLF tolerated).
 */
export async function* parseSse<T = unknown>(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<SseEvent<T>> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let dataLines: string[] = [];
  let eventName = "message";
  let eventId: string | undefined;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let nl: number;
      while ((nl = buffer.indexOf("\n")) >= 0) {
        let line = buffer.slice(0, nl);
        if (line.endsWith("\r")) line = line.slice(0, -1);
        buffer = buffer.slice(nl + 1);
        if (line === "") {
          if (dataLines.length > 0) {
            const payload = dataLines.join("\n");
            let data: unknown;
            try {
              data = JSON.parse(payload);
            } catch {
              data = { _raw: payload };
            }
            yield eventId === undefined
              ? { event: eventName, data: data as T }
              : { event: eventName, data: data as T, id: eventId };
          }
          dataLines = [];
          eventName = "message";
          eventId = undefined;
          continue;
        }
        if (line.startsWith(":")) continue;
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("id:")) {
          const rest = line.slice(3);
          const value = rest.startsWith(" ") ? rest.slice(1) : rest;
          // WHATWG: an id containing NULL is ignored.
          if (!value.includes("\0")) eventId = value;
        } else if (line.startsWith("data:")) {
          const rest = line.slice(5);
          dataLines.push(rest.startsWith(" ") ? rest.slice(1) : rest);
        }
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // already released
    }
  }
}
