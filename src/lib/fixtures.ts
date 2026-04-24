import { ServiceError } from "@/types/domain";

/**
 * Resolve a `/fixtures/...` path to something `fetch` can consume.
 *
 * On the client a relative URL is fine. During SSR (TanStack Start /
 * Cloudflare Worker) Node's `fetch` rejects relative URLs — we
 * reconstruct an absolute one from the in-flight request via
 * `@tanstack/react-start/server`'s `getRequest()` (the same helper
 * used by `src/integrations/supabase/auth-middleware.ts`).
 */
async function resolveFixtureUrl(path: string): Promise<string> {
  const rel = `/fixtures/${path}`;
  if (typeof window !== "undefined") return rel;
  try {
    const mod = await import("@tanstack/react-start/server");
    const req = mod.getRequest?.();
    if (req?.url) return new URL(rel, req.url).toString();
  } catch {
    /* fall through to localhost fallback */
  }
  // Last-resort fallback for standalone scripts / tests so the URL is
  // at least parseable instead of throwing.
  return new URL(rel, "http://localhost:8080").toString();
}

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
