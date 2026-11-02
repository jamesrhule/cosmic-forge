/**
 * The app's one connection to the compute API (P4-02).
 *
 * Services call the generated-type SDK (`@qcompass/frontend-sdk`) through
 * `api()` when `VITE_API_URL` is set (`DATA_SOURCE === "api"`) and read
 * bundled fixtures otherwise; never both, and never a fixture fallback after
 * an API error. Every failure reaches callers as the app's `ServiceError`
 * (P3-05/P3-06 envelope via `errorFromResponse`).
 *
 * Auth: the Supabase session's access token, or, behind
 * `FEATURES.qcompassAuth`, the API key and tenant held in `@/store/auth`
 * (sent as `Authorization` and `X-QCompass-Tenant`).
 */
import { QcompassClient, QcompassError, streamRun, type SseEvent } from "@qcompass/frontend-sdk";
import { API_BASE_URL, DATA_SOURCE, FEATURES } from "@/config/features";
import { supabase } from "@/integrations/supabase/client";
import { getAuthSnapshot } from "@/store/auth";
import { ServiceError } from "@/types/domain";
import { errorFromResponse } from "@/lib/apiErrors";

export { DATA_SOURCE };

/** True when services must use the API (and must not read fixtures). */
export function usesApi(): boolean {
  return DATA_SOURCE === "api";
}

export async function authHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  try {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) headers.Authorization = `Bearer ${token}`;
  } catch {
    /* Supabase not configured (BLOCKED-ON-JAMES:VITE_SUPABASE_URL): anonymous */
  }
  if (FEATURES.qcompassAuth) {
    const { token, tenantId } = getAuthSnapshot();
    if (token) headers.Authorization = `Bearer ${token}`;
    if (tenantId) headers["X-QCompass-Tenant"] = tenantId;
  }
  return headers;
}

let client: QcompassClient | null = null;

/** The shared SDK client. Throws when the app is built without `VITE_API_URL`. */
export function sdkClient(): QcompassClient {
  if (!usesApi()) {
    throw new ServiceError(
      "NOT_IMPLEMENTED",
      "VITE_API_URL is not set; this build reads bundled fixtures",
    );
  }
  client ??= new QcompassClient({ baseUrl: API_BASE_URL, headers: authHeaders });
  return client;
}

/** Map any SDK/network failure to the app's ServiceError shape. */
export function toServiceError(err: unknown): ServiceError {
  if (err instanceof ServiceError) return err;
  if (err instanceof QcompassError) {
    const body = typeof err.body === "string" ? err.body : JSON.stringify(err.body ?? "");
    return errorFromResponse(err.status, body || err.message);
  }
  if (err instanceof Error && err.name === "AbortError") {
    return new ServiceError("STREAM_ABORTED", err.message);
  }
  return new ServiceError(
    "UPSTREAM_FAILURE",
    `Compute API unreachable: ${err instanceof Error ? err.message : String(err)}`,
  );
}

/** Run one SDK call with the shared client; errors become ServiceError. */
export async function api<T>(call: (c: QcompassClient) => Promise<T>): Promise<T> {
  try {
    return await call(sdkClient());
  } catch (err) {
    throw toServiceError(err);
  }
}

/** Iterate one SDK event stream; errors become ServiceError. */
export async function* apiStream<E = SseEvent>(
  open: (c: QcompassClient) => AsyncIterable<E>,
): AsyncGenerator<E> {
  try {
    yield* open(sdkClient());
  } catch (err) {
    throw toServiceError(err);
  }
}

/** How many times one run stream reconnects after `STREAM_ABORTED`. */
export const MAX_STREAM_RECONNECTS = 20;

/**
 * A run's event stream (`GET /api/qcompass/domains/{domain}/runs/{id}/stream`)
 * that outlives the API's stream bounds (SF1). The API ends a stream with
 * `error {code: "STREAM_ABORTED"}` then `end` after its idle or overall
 * limit; while `isOver()` says the run has not ended, this reconnects and
 * skips the events it already delivered (every connection replays the run's
 * events from the start). `history` is yielded once; `end` and the
 * `STREAM_ABORTED` error are consumed here. Errors become ServiceError.
 *
 * Replays are recognised by event id where the stream carries one (SSE
 * `id:`): job_events ids come from a sequence, not commit order, so a replay
 * can order events differently from the first delivery. Events without an id
 * fall back to their position among the id-less events.
 */
export async function* runEventStream(
  domain: string,
  runId: string,
  isOver: () => Promise<boolean>,
  signal?: AbortSignal,
): AsyncGenerator<SseEvent> {
  let delivered = 0;
  const seen = new Set<string>();
  for (let attempt = 0; ; attempt++) {
    let aborted = false;
    let index = 0;
    for await (const ev of apiStream((c) => streamRun(c, domain, runId, signal))) {
      if (ev.event === "end") break;
      const code = (ev.data as { code?: unknown } | null | undefined)?.code;
      if (ev.event === "error" && code === "STREAM_ABORTED") {
        aborted = true;
        continue;
      }
      if (ev.event === "history") {
        if (attempt === 0) yield ev;
        continue;
      }
      if (ev.id !== undefined && ev.id !== "") {
        if (seen.has(ev.id)) continue; // replayed by the new connection
        seen.add(ev.id);
        yield ev;
        continue;
      }
      if (index++ < delivered) continue; // replayed by the new connection
      delivered++;
      yield ev;
    }
    if (!aborted || signal?.aborted || attempt >= MAX_STREAM_RECONNECTS) return;
    if (await isOver()) return;
  }
}
