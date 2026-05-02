/**
 * QCompass — HTTP wrapper that injects bearer + tenant headers when
 * `FEATURES.qcompassAuth` is true. Otherwise passes through to fetch.
 *
 * @example
 *   const data = await apiFetch<MyType>("/api/qcompass/...");
 */
import { FEATURES, API_BASE_URL } from "@/config/features";
import { getAuthSnapshot } from "@/store/auth";

export interface ApiFetchOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

export function isQcompassBackendConfigured(): boolean {
  return FEATURES.liveBackend && Boolean(API_BASE_URL);
}

export async function apiFetch<T>(path: string, opts: ApiFetchOptions = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers ?? {}),
  };

  if (FEATURES.qcompassAuth) {
    const { token, tenantId } = getAuthSnapshot();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (tenantId) headers["X-QCompass-Tenant"] = tenantId;
  }

  const res = await fetch(url, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  });
  if (!res.ok) {
    throw new Error(`apiFetch ${path} failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}
