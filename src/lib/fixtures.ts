import { ServiceError } from "@/types/domain";

/** Shared loader for /public/fixtures JSON files. */
export async function loadFixture<T>(path: string): Promise<T> {
  const url = `/fixtures/${path}`;
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
  const url = `/fixtures/${path}`;
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
