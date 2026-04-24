/**
 * Tool-call audit logger — writes a row to `tool_call_audit` for every
 * assistant tool invocation we dispatch (or refuse to dispatch).
 *
 * Storage: Postgres `tool_call_audit` (RLS: users see their own rows;
 * admins see all; only the row owner can insert).
 *
 * Failure mode: best-effort. We never let an audit-write error crash the
 * assistant pipeline — the row is dropped, a console warning fires, and
 * `trackError` records the failure for telemetry. This matches the
 * "Postgres table only — export/CLI for review" decision: the table is the
 * archive, not a critical dependency.
 *
 * Argument redaction: tool args can contain free-form chat text and
 * occasionally PII / secrets. `redactArgs()` strips known sensitive keys
 * and truncates large strings before write. Extend `SENSITIVE_KEYS` as new
 * tools are added.
 */

import { supabase } from "@/integrations/supabase/client";
import { trackError } from "@/lib/telemetry";
import { getToolTier, type ToolTier } from "@/lib/toolRegistry";

export type AuditStatus = "ok" | "error" | "denied" | "pending_approval";

export interface AuditRow {
  toolName: string;
  conversationId?: string;
  args?: unknown;
  status: AuditStatus;
  resultSummary?: string;
  latencyMs?: number;
  approvalTokenId?: string;
}

const SENSITIVE_KEYS = new Set([
  "password",
  "secret",
  "token",
  "api_key",
  "apiKey",
  "authorization",
  "auth",
  "approval_token",
]);

const MAX_STRING_LENGTH = 2000;

export function redactArgs(input: unknown): unknown {
  if (input == null) return input;
  if (typeof input === "string") {
    return input.length > MAX_STRING_LENGTH
      ? `${input.slice(0, MAX_STRING_LENGTH)}…[truncated ${input.length - MAX_STRING_LENGTH}]`
      : input;
  }
  if (Array.isArray(input)) return input.map(redactArgs);
  if (typeof input === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(input as Record<string, unknown>)) {
      out[k] = SENSITIVE_KEYS.has(k.toLowerCase()) ? "[redacted]" : redactArgs(v);
    }
    return out;
  }
  return input;
}

/**
 * Write a single audit row. Resolves to `true` on success, `false` on
 * failure — never throws.
 */
export async function logToolCall(row: AuditRow): Promise<boolean> {
  try {
    const { data: auth } = await supabase.auth.getUser();
    const userId = auth.user?.id ?? null;
    const tier: ToolTier = getToolTier(row.toolName);

    const { error } = await supabase.from("tool_call_audit").insert({
      user_id: userId,
      conversation_id: row.conversationId ?? null,
      tool_name: row.toolName,
      tier,
      args_redacted: row.args === undefined ? null : (redactArgs(row.args) as never),
      status: row.status,
      result_summary: row.resultSummary?.slice(0, 1000) ?? null,
      latency_ms: row.latencyMs ?? null,
      approval_token_id: row.approvalTokenId ?? null,
    });

    if (error) {
      console.warn("[audit] insert failed", error.message);
      trackError("service_error", { scope: "audit_insert_failed", message: error.message, tool: row.toolName });
      return false;
    }
    return true;
  } catch (err) {
    console.warn("[audit] logger threw", err);
    trackError("service_error", { scope: "audit_logger_threw", message: err instanceof Error ? err.message : String(err), tool: row.toolName, });
    return false;
  }
}

/**
 * Convenience wrapper: time a tool invocation and audit the outcome.
 * Use only for tools that resolve to a single value (not async iterables).
 */
export async function withAudit<T>(
  meta: { toolName: string; conversationId?: string; args?: unknown },
  fn: () => Promise<T>,
): Promise<T> {
  const started = performance.now();
  try {
    const result = await fn();
    void logToolCall({
      ...meta,
      status: "ok",
      latencyMs: Math.round(performance.now() - started),
    });
    return result;
  } catch (err) {
    void logToolCall({
      ...meta,
      status: "error",
      resultSummary: err instanceof Error ? err.message : String(err),
      latencyMs: Math.round(performance.now() - started),
    });
    throw err;
  }
}
