/**
 * Thin HTTP client for the FastAPI backend.
 *
 * Behavior:
 *  - When `API_BASE_URL` is unset, every helper throws `BackendUnavailable`
 *    so callers can branch into their fixture fallback.
 *  - When set, requests are prefixed and the current Supabase access
 *    token is attached as `Authorization: Bearer …`.
 *  - SSE helper yields parsed JSON events from `event: data` payloads.
 */

import { API_BASE_URL } from "@/config/features";
import { supabase } from "@/integrations/supabase/client";
import { PLAN_ERROR_CODES, ServiceError, type ServiceErrorCode } from "@/types/domain";

export class BackendUnavailable extends Error {
  constructor() {
    super("API_BASE_URL not configured; falling back to fixtures");
    this.name = "BackendUnavailable";
  }
}

export function isBackendConfigured(): boolean {
  return Boolean(API_BASE_URL && API_BASE_URL.length > 0);
}

async function authHeader(): Promise<HeadersInit> {
  try {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

function joinUrl(path: string): string {
  if (!isBackendConfigured()) throw new BackendUnavailable();
  const base = API_BASE_URL.replace(/\/+$/, "");
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${base}${suffix}`;
}

function statusToCode(
  status: number,
): "NOT_FOUND" | "INVALID_INPUT" | "UNAUTHORIZED" | "RATE_LIMITED" | "SERVER_ERROR" {
  if (status === 404) return "NOT_FOUND";
  if (status === 400 || status === 422) return "INVALID_INPUT";
  if (status === 401 || status === 403) return "UNAUTHORIZED";
  if (status === 429) return "RATE_LIMITED";
  return "SERVER_ERROR";
}

/**
 * Build the ServiceError for a failed response. The API's error envelope is
 * `{"detail": {"code", "message"}}` (P3-06); plan-limit and budget codes
 * (429/402, P3-05) are kept verbatim so the UI can say which limit was hit.
 */
export function errorFromResponse(status: number, bodyText: string): ServiceError {
  let message = bodyText || `${status}`;
  try {
    const detail = (JSON.parse(bodyText) as { detail?: { code?: string; message?: string } })
      .detail;
    if (detail && typeof detail === "object") {
      if (typeof detail.message === "string") message = detail.message;
      const code = detail.code as ServiceErrorCode | undefined;
      if (code && (PLAN_ERROR_CODES as readonly string[]).includes(code)) {
        return new ServiceError(code, message);
      }
    }
  } catch {
    /* not JSON: keep the raw text */
  }
  return new ServiceError(statusToCode(status) as never, message);
}

export async function apiFetch<T>(
  path: string,
  init: Omit<RequestInit, "body"> & { body?: BodyInit | object | null } = {},
): Promise<T> {
  const url = joinUrl(path);
  const headers: HeadersInit = {
    Accept: "application/json",
    ...(await authHeader()),
    ...(init.headers ?? {}),
  };

  let body = init.body as BodyInit | undefined;
  if (body && typeof body === "object" && !(body instanceof FormData) && !(body instanceof Blob)) {
    (headers as Record<string, string>)["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }

  const res = await fetch(url, { ...init, headers, body });
  if (!res.ok) {
    let text = `${res.status} ${res.statusText}`;
    try {
      text = (await res.text()) || text;
    } catch {
      /* ignore */
    }
    throw errorFromResponse(res.status, text);
  }

  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") ?? "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

/**
 * Async generator over an SSE stream. Yields one parsed JSON event per
 * `data:` line (concatenating multi-line payloads per spec). Stops on
 * `event: done` or stream close.
 */
export async function* apiSse<T>(
  path: string,
  opts: { signal?: AbortSignal; method?: string; body?: object } = {},
): AsyncIterable<T> {
  const url = joinUrl(path);
  const res = await fetch(url, {
    method: opts.method ?? "GET",
    headers: {
      Accept: "text/event-stream",
      ...(opts.body ? { "Content-Type": "application/json" } : {}),
      ...(await authHeader()),
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  });

  if (!res.ok || !res.body) {
    throw new ServiceError(statusToCode(res.status) as never, `SSE failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let dataLines: string[] = [];
  let eventName = "message";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let nl: number;
      while ((nl = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, nl).replace(/\r$/, "");
        buffer = buffer.slice(nl + 1);

        if (line === "") {
          // Dispatch event
          if (dataLines.length > 0) {
            const payload = dataLines.join("\n");
            dataLines = [];
            if (eventName === "done") return;
            try {
              yield JSON.parse(payload) as T;
            } catch {
              /* skip malformed event */
            }
          }
          eventName = "message";
          continue;
        }

        if (line.startsWith(":")) continue; // comment
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
          continue;
        }
        if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).replace(/^\s/, ""));
          continue;
        }
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      /* ignore */
    }
  }
}
