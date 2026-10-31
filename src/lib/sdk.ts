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
import { QcompassClient, QcompassError, type SseEvent } from "@qcompass/frontend-sdk";
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
