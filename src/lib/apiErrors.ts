/**
 * The compute API's error envelope → the app's `ServiceError` (P3-05/P3-06).
 *
 * The envelope is `{"detail": {"code", "message"}}`; plan-limit and budget
 * codes (429/402) are kept verbatim so the UI can say which limit was hit.
 */
import { PLAN_ERROR_CODES, ServiceError, type ServiceErrorCode } from "@/types/domain";

function statusToCode(
  status: number,
): "NOT_FOUND" | "INVALID_INPUT" | "UNAUTHORIZED" | "RATE_LIMITED" | "SERVER_ERROR" {
  if (status === 404) return "NOT_FOUND";
  if (status === 400 || status === 422) return "INVALID_INPUT";
  if (status === 401 || status === 403) return "UNAUTHORIZED";
  if (status === 429) return "RATE_LIMITED";
  return "SERVER_ERROR";
}

/** Build the ServiceError for a failed response. */
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
