/**
 * Centralised service-error → user-message mapping.
 *
 * Every fixture-backed (and live-backed) service call should funnel its
 * failures through `notifyServiceError(err, scope)` so the user sees a
 * consistent toast and the telemetry pipeline gets a single, structured
 * error event. Scopes also dedupe sonner toasts: a flapping fixture or a
 * router invalidation will replace the existing toast instead of stacking
 * a fresh one.
 */
import { toast } from "sonner";
import { ZodError } from "zod";
import { ServiceError, type ServiceErrorCode } from "@/types/domain";
import { trackError } from "@/lib/telemetry";

/**
 * Logical surfaces. Add a new entry when wiring a new service consumer
 * so the copy stays curated rather than degrading to a generic
 * "Something went wrong".
 */
export type ServiceScope =
  | "benchmarks"
  | "run"
  | "runs"
  | "visualization"
  | "audit"
  | "scan"
  | "models"
  | "model-status"
  | "model-install"
  | "artifacts"
  | "artifact-download"
  | "formulas"
  | "assistant";

export interface UserError {
  /** Toast title — short, action-led. */
  title: string;
  /** One-line plain-English explanation. */
  description: string;
  /** Stable code for telemetry / DataErrorPanel styling. */
  code: ServiceErrorCode | "FIXTURE_INVALID" | "UNKNOWN";
}

const SCOPE_TITLES: Record<ServiceScope, string> = {
  benchmarks: "Couldn't load the benchmark catalog",
  run: "Couldn't load this run",
  runs: "Couldn't load the run list",
  visualization: "Couldn't load this visualization",
  audit: "Couldn't load the audit report",
  scan: "Couldn't load the parameter scan",
  models: "Couldn't load the model list",
  "model-status": "Couldn't read the model status",
  "model-install": "Model install failed",
  artifacts: "Couldn't list run artifacts",
  "artifact-download": "Artifact download failed",
  formulas: "Couldn't load the formula reference",
  assistant: "Assistant failed",
};

/**
 * Translate any thrown value into a friendly user-facing message.
 * Falls back to a generic "Something went wrong" only when the input
 * is unrecognisable — never leaks raw stack frames.
 */
export function toUserError(err: unknown, scope: ServiceScope): UserError {
  const title = SCOPE_TITLES[scope];

  if (err instanceof ZodError) {
    const first = err.issues[0];
    const where = first?.path?.length ? ` at ${first.path.join(".")}` : "";
    return {
      title,
      description: `The data we received didn't match the expected shape${where}: ${first?.message ?? "validation failed"}.`,
      code: "FIXTURE_INVALID",
    };
  }

  if (err instanceof ServiceError) {
    switch (err.code) {
      case "NOT_FOUND":
        return {
          title,
          description:
            "The bundled fixture for this surface is missing. The build may be incomplete — try a hard refresh.",
          code: err.code,
        };
      case "INVALID_INPUT":
        return {
          title,
          description: err.message || "The data on disk is malformed.",
          code: "FIXTURE_INVALID",
        };
      case "UPSTREAM_FAILURE":
        return {
          title,
          description: "The backend is unreachable or returned an error. You're seeing sample data instead.",
          code: err.code,
        };
      case "STREAM_ABORTED":
        return {
          title,
          description: "The connection dropped before the response finished.",
          code: err.code,
        };
      case "NOT_IMPLEMENTED":
        return {
          title,
          description: "This action isn't wired up in the current build.",
          code: err.code,
        };
    }
  }

  if (err instanceof Error) {
    // AbortError is intentional cancellation — caller should filter
    // before getting here, but guard just in case.
    if (err.name === "AbortError") {
      return {
        title,
        description: "Request was cancelled.",
        code: "STREAM_ABORTED",
      };
    }
    return {
      title,
      description: err.message || "Something went wrong.",
      code: "UNKNOWN",
    };
  }

  return {
    title,
    description: "Something went wrong.",
    code: "UNKNOWN",
  };
}

/**
 * Render a sonner toast and emit one telemetry event. Uses a stable
 * id keyed by scope so retries replace the existing toast.
 */
export function notifyServiceError(
  err: unknown,
  scope: ServiceScope,
  opts: { silent?: boolean; extra?: Record<string, unknown> } = {},
): UserError {
  const ue = toUserError(err, scope);

  trackError("service_error", {
    scope,
    code: ue.code,
    message: err instanceof Error ? err.message : String(err),
    ...(opts.extra ?? {}),
  });

  if (!opts.silent) {
    try {
      toast.error(ue.title, {
        id: `svc:${scope}`,
        description: ue.description,
      });
    } catch {
      /* SSR or no-op sonner */
    }
  }

  return ue;
}

/** Clear the toast for a scope (e.g. on Retry). */
export function dismissServiceError(scope: ServiceScope): void {
  try {
    toast.dismiss(`svc:${scope}`);
  } catch {
    /* noop */
  }
}

/**
 * Dev-only: surface that the live backend failed and we silently fell
 * back to bundled fixtures. Production demo visitors don't need to see
 * this — they didn't ask for live data.
 */
export function notifyLiveFallback(scope: ServiceScope, err: unknown): void {
  if (!import.meta.env.DEV) return;
  const message = err instanceof Error ? err.message : String(err);
  try {
    toast.warning("Live backend unavailable — showing sample data", {
      id: `svc:live-fallback:${scope}`,
      description: `${SCOPE_TITLES[scope]} via fixtures. (${message.slice(0, 120)})`,
    });
  } catch {
    /* noop */
  }
}
