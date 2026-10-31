import { createIsomorphicFn } from "@tanstack/react-start";
import { ServiceError } from "@/types/domain";

/**
 * Fetch a `/fixtures/...` file.
 *
 * - Client: relative URL — the browser resolves it against the origin.
 * - Server on Cloudflare Workers: read through the static-assets binding
 *   (`env.ASSETS`, declared in `wrangler.jsonc`). A Worker can't reliably
 *   fetch its own public URL.
 * - Server elsewhere (`vite dev` on Node): absolute URL rebuilt from the
 *   in-flight request via `getRequest()`.
 *
 * `createIsomorphicFn` strips the server branch (and its dynamic imports)
 * from the client bundle. The previous implementation used `require()`,
 * which doesn't exist in ESM SSR, so it always fell back to
 * `http://localhost:8080` and SSR fixture loads failed (P0-05).
 */
const fetchFixture = createIsomorphicFn()
  .client((path: string, init?: RequestInit) => fetch(`/fixtures/${path}`, init))
  .server(async (path: string, init?: RequestInit) => {
    const rel = `/fixtures/${path}`;
    try {
      const mod = await import(/* @vite-ignore */ "cloudflare:workers");
      if (mod.env?.ASSETS) return mod.env.ASSETS.fetch(new URL(rel, "https://assets.invalid").toString(), init);
    } catch {
      /* not running on Workers */
    }
    const { getRequest } = await import("@tanstack/react-start/server");
    const req = getRequest();
    if (!req?.url) {
      throw new ServiceError("NOT_FOUND", `Fixture ${path}: no request context on the server`);
    }
    return fetch(new URL(rel, req.url).toString(), init);
  });

export interface LoadFixtureOptions<T> {
  /**
   * Optional runtime shape check. Receives the parsed JSON and must
   * either return a typed `T` or throw (e.g. a `ZodError`). Failures
   * are re-thrown as `ServiceError("INVALID_INPUT", …)` so consumers
   * can route them through `notifyServiceError` consistently.
   */
  validate?: (raw: unknown) => T;
}

/** Shared loader for /public/fixtures JSON files. */
export async function loadFixture<T>(path: string, opts: LoadFixtureOptions<T> = {}): Promise<T> {
  const res = await fetchFixture(path);
  if (!res.ok) {
    throw new ServiceError("NOT_FOUND", `Fixture not found: ${path} (status ${res.status})`);
  }
  let raw: unknown;
  try {
    raw = await res.json();
  } catch (err) {
    throw new ServiceError(
      "INVALID_INPUT",
      `Fixture ${path} is not valid JSON: ${err instanceof Error ? err.message : String(err)}`,
    );
  }
  if (!opts.validate) return raw as T;
  try {
    return opts.validate(raw);
  } catch (err) {
    const detail =
      err instanceof Error
        ? // ZodError pretty-prints to a long stack; trim to the first issue
          err.message.split("\n").slice(0, 4).join(" · ")
        : String(err);
    throw new ServiceError("INVALID_INPUT", `Fixture ${path} failed validation: ${detail}`);
  }
}

/**
 * Stream a JSONL fixture line by line as parsed events. Honours an
 * optional `AbortSignal` so callers can cancel mid-stream (e.g. the
 * chat drawer abandoning a generation when it closes).
 */
export async function* loadJsonlFixture<T>(
  path: string,
  delayMs = 200,
  signal?: AbortSignal,
): AsyncIterable<T> {
  const res = await fetchFixture(path, { signal });
  if (!res.ok) {
    throw new ServiceError("NOT_FOUND", `Stream fixture not found: ${path} (status ${res.status})`);
  }
  const text = await res.text();
  const lines = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  for (const line of lines) {
    if (signal?.aborted) {
      const err = new Error("Aborted");
      err.name = "AbortError";
      throw err;
    }
    await sleep(delayMs);
    yield JSON.parse(line) as T;
  }
}

export const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
