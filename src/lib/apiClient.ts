/**
 * Untyped escape hatch onto the compute API, for routes outside its
 * OpenAPI document (e.g. the `cosmic_forge_viz` manifest routes).
 *
 * Typed routes go through `@/lib/sdk` (`api(...)` with the generated SDK,
 * P4-02). Both use the same SDK client, auth headers and error mapping, so
 * there is one HTTP path to the backend (R20).
 *
 * Behavior:
 *  - When `VITE_API_URL` is unset, every helper throws `BackendUnavailable`
 *    so callers can branch into their fixture mode.
 *  - Errors are the app's `ServiceError` (`errorFromResponse`).
 */

import { API_BASE_URL } from "@/config/features";
import { api, apiStream } from "@/lib/sdk";

export { errorFromResponse } from "@/lib/apiErrors";

export class BackendUnavailable extends Error {
  constructor() {
    super("API_BASE_URL not configured; falling back to fixtures");
    this.name = "BackendUnavailable";
  }
}

export function isBackendConfigured(): boolean {
  return Boolean(API_BASE_URL && API_BASE_URL.length > 0);
}

function pathOf(path: string): string {
  if (!isBackendConfigured()) throw new BackendUnavailable();
  return path.startsWith("/") ? path : `/${path}`;
}

export async function apiFetch<T>(
  path: string,
  init: { method?: "GET" | "POST" | "DELETE"; body?: object | null; signal?: AbortSignal } = {},
): Promise<T> {
  const p = pathOf(path);
  const method = init.method ?? "GET";
  return api<T>((c) => {
    if (method === "POST") return c.postJson<T>(p, init.body ?? {}, { signal: init.signal });
    if (method === "DELETE") return c.deleteJson<T>(p);
    return c.getJson<T>(p, { signal: init.signal });
  });
}

/**
 * Async generator over an SSE stream: one parsed JSON payload per event.
 * Stops on `event: done` / `event: end` or when the stream closes.
 */
export async function* apiSse<T>(
  path: string,
  opts: { signal?: AbortSignal; method?: "GET" | "POST"; body?: object } = {},
): AsyncIterable<T> {
  const p = pathOf(path);
  for await (const ev of apiStream((c) =>
    c.sse<T>(p, { method: opts.method, body: opts.body, signal: opts.signal }),
  )) {
    if (ev.event === "done" || ev.event === "end") return;
    yield ev.data;
  }
}
