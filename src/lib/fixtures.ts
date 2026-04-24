import { createIsomorphicFn } from "@tanstack/react-start";
import { ServiceError } from "@/types/domain";

/**
 * Resolve a `/fixtures/...` path to something `fetch` can consume.
 *
 * - Client: relative URL is fine — the browser resolves it against the
 *   current origin.
 * - Server (SSR): Node / Worker `fetch` rejects relative URLs; we
 *   reconstruct an absolute one from the in-flight request via
 *   `getRequest()`. Wrapped in `createIsomorphicFn` so the
 *   server-only `@tanstack/react-start/server` import is dropped from
 *   the client bundle (the import-protection plugin enforces this).
 */
const resolveFixtureUrl = createIsomorphicFn()
  .client((path: string) => `/fixtures/${path}`)
  .server((path: string) => {
    const rel = `/fixtures/${path}`;
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { getRequest } = require("@tanstack/react-start/server") as {
        getRequest: () => Request | undefined;
      };
      const req = getRequest();
      if (req?.url) return new URL(rel, req.url).toString();
    } catch {
      /* fall through to localhost fallback */
    }
    return new URL(rel, "http://localhost:8080").toString();
  });

/** Shared loader for /public/fixtures JSON files. */
export async function loadFixture<T>(path: string): Promise<T> {
  const url = await resolveFixtureUrl(path);
  const res = await fetch(url);
  if (!res.ok) {
    throw new ServiceError("NOT_FOUND", `Fixture not found: ${path} (status ${res.status})`);
  }
  return (await res.json()) as T;
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
  const url = await resolveFixtureUrl(path);
  const res = await fetch(url, { signal });
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
