/**
 * Persistence helpers — read/write to the `runs`, `run_results`,
 * `audit_reports`, and `viz_timelines` tables, plus the `viz-timelines`
 * and `run-artifacts` storage buckets.
 *
 * These helpers are wired into `services/*.ts` but only fire when
 * `FEATURES.persistRuns === true`. While the flag is off, services keep
 * returning fixtures and these helpers act as no-ops.
 *
 * The "public catalog + author-attributed" tenancy model is enforced by
 * RLS; the helpers don't repeat the check. Signed-out users get reads
 * only; writes require auth.
 */

import { supabase } from "@/integrations/supabase/client";
import { FEATURES } from "@/config/features";
import { trackError, trackWarn } from "@/lib/telemetry";
import { enforceRateLimit, LIMITS } from "@/lib/rateLimit";
import { isEmailVerified } from "@/lib/emailVerification";
import type { RunConfig, RunResult, AuditReport, RunStatus } from "@/types/domain";
import type { VisualizationTimeline } from "@/types/visualizer";

export type RunVisibility = "public" | "unlisted" | "private";

export interface RunRow {
  id: string;
  author_user_id: string | null;
  visibility: RunVisibility;
  status: RunStatus;
  label: string | null;
  notes: string | null;
  config: RunConfig;
  potential_kind: string | null;
  precision: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

const VIZ_BUCKET = "viz-timelines";

function isOn(): boolean {
  return FEATURES.persistRuns === true;
}

/**
 * Insert or upsert a run row. Author is resolved from the current session
 * — signed-out callers get a `NOT_AUTHENTICATED` error. The row id must
 * be globally unique (we reuse the run-id convention from the fixtures).
 */
export async function persistRunRow(input: {
  id: string;
  config: RunConfig;
  visibility?: RunVisibility;
  status?: RunStatus;
  label?: string;
  notes?: string;
}): Promise<{ ok: boolean; reason?: string }> {
  if (!isOn()) return { ok: true, reason: "persistence disabled" };

  const { data: auth } = await supabase.auth.getUser();
  if (!auth.user) return { ok: false, reason: "NOT_AUTHENTICATED" };

  const { error } = await supabase.from("runs").upsert(
    {
      id: input.id,
      author_user_id: auth.user.id,
      visibility: input.visibility ?? "public",
      status: input.status ?? "queued",
      label: input.label ?? null,
      notes: input.notes ?? null,
      config: input.config as never,
      potential_kind: input.config.potential.kind,
      precision: input.config.precision,
    },
    { onConflict: "id" },
  );

  if (error) {
    trackError("service_error", { scope: "persist_run_failed", message: error.message, runId: input.id });
    return { ok: false, reason: error.message };
  }
  return { ok: true };
}

export async function setRunStatus(
  runId: string,
  status: RunStatus,
  patch?: { startedAt?: string; completedAt?: string },
): Promise<void> {
  if (!isOn()) return;
  const { error } = await supabase
    .from("runs")
    .update({
      status,
      started_at: patch?.startedAt ?? null,
      completed_at: patch?.completedAt ?? null,
    })
    .eq("id", runId);
  if (error) trackError("service_error", { scope: "persist_status_failed", message: error.message, runId });
}

export async function persistRunResult(runId: string, payload: RunResult): Promise<void> {
  if (!isOn()) return;
  const { error } = await supabase
    .from("run_results")
    .upsert({ run_id: runId, payload: payload as never }, { onConflict: "run_id" });
  if (error) trackError("service_error", { scope: "persist_result_failed", message: error.message, runId });
}

export async function persistAuditReport(runId: string, audit: AuditReport): Promise<void> {
  if (!isOn()) return;

  // Use a defensive accessor — the actual AuditReport shape may evolve.
  const verdicts = (audit as unknown as { checks?: Array<{ verdict?: string }> }).checks ?? [];
  const passCount = verdicts.filter((v) => String(v?.verdict ?? "").startsWith("PASS")).length;
  const failCount = verdicts.filter((v) => v?.verdict === "FAIL").length;

  const { error } = await supabase.from("audit_reports").upsert(
    {
      run_id: runId,
      verdicts: audit as never,
      pass_count: passCount,
      fail_count: failCount,
    },
    { onConflict: "run_id" },
  );
  if (error) trackError("service_error", { scope: "persist_audit_failed", message: error.message, runId });
}

/**
 * Hard server-side size cap for timeline uploads. The render path tolerates
 * up to 200 MB in the browser, but persisted blobs are deliberately tighter
 * (10 MB) so a single hostile upload can't exhaust the bucket budget.
 */
const MAX_PERSIST_TIMELINE_BYTES = 10 * 1024 * 1024;

/**
 * Upload a visualization timeline JSON blob to the `viz-timelines` bucket
 * and write a manifest row to `viz_timelines`. The path convention is
 * `<runId>/timeline.json` — RLS on storage uses the first path segment to
 * resolve run visibility.
 *
 * Tier-4 hardening:
 *   - rejects unauthenticated callers
 *   - blocks unverified-email accounts (soft client-side gate; RLS is the
 *     authoritative check on the row write)
 *   - enforces a per-user upload bucket (5 / 10 min)
 *   - rejects blobs over 10 MB before they ever leave the tab
 */
export async function persistVisualizationTimeline(input: {
  runId: string;
  timeline: VisualizationTimeline;
  expiresAt?: Date;
}): Promise<{ ok: boolean; reason?: string }> {
  if (!isOn()) return { ok: true, reason: "persistence disabled" };

  // 1. Email-verification gate (write-only, soft client-side check;
  //    the row write is also blocked by RLS for unverified emails).
  const { data: auth } = await supabase.auth.getUser();
  if (!auth.user) return { ok: false, reason: "not authenticated" };
  if (!isEmailVerified(auth.user)) {
    trackWarn("email_verify_block", "timeline write blocked: email unverified", {
      runId: input.runId,
    });
    return { ok: false, reason: "email not verified" };
  }

  // 2. Rate-limit timeline uploads per user.
  const allowed = await enforceRateLimit(LIMITS.timelineWrite);
  if (!allowed) return { ok: false, reason: "rate limit exceeded" };

  const path = `${input.runId}/timeline.json`;
  const body = JSON.stringify(input.timeline);

  // 3. Hard size cap (server-side).
  if (body.length > MAX_PERSIST_TIMELINE_BYTES) {
    trackWarn(
      "timeline_size_block",
      `timeline ${(body.length / 1024 / 1024).toFixed(1)} MB exceeds 10 MB cap`,
      { runId: input.runId, bytes: body.length },
    );
    return { ok: false, reason: "timeline too large" };
  }

  const bytes = new Blob([body], { type: "application/json" });

  const { error: upErr } = await supabase.storage
    .from(VIZ_BUCKET)
    .upload(path, bytes, { upsert: true, contentType: "application/json" });

  if (upErr) {
    trackError("service_error", { scope: "persist_timeline_upload_failed", message: upErr.message, runId: input.runId });
    return { ok: false, reason: upErr.message };
  }

  const frames = (input.timeline as unknown as { frames?: unknown[] }).frames;
  const duration = (input.timeline as unknown as { durationSeconds?: number }).durationSeconds;

  const { error: rowErr } = await supabase.from("viz_timelines").upsert(
    {
      run_id: input.runId,
      frame_count: Array.isArray(frames) ? frames.length : null,
      duration_seconds: typeof duration === "number" ? duration : null,
      bytes_size: body.length,
      storage_path: path,
      manifest: null,
      expires_at: input.expiresAt?.toISOString() ?? null,
    },
    { onConflict: "run_id" },
  );
  if (rowErr) {
    trackError("service_error", { scope: "persist_timeline_row_failed", message: rowErr.message, runId: input.runId });
    return { ok: false, reason: rowErr.message };
  }
  return { ok: true };
}

/**
 * Resolve a signed URL for a stored timeline. Public runs are still
 * served from the (private) bucket via signed URLs to keep the read path
 * uniform — RLS decides whether the signing succeeds.
 */
export async function getTimelineSignedUrl(
  runId: string,
  ttlSeconds = 60 * 5,
): Promise<string | null> {
  if (!isOn()) return null;
  const { data, error } = await supabase.storage
    .from(VIZ_BUCKET)
    .createSignedUrl(`${runId}/timeline.json`, ttlSeconds);
  if (error || !data) {
    if (error) {
      // "Object not found" / 404 / RLS rejections are expected when no
      // timeline has been backfilled yet — caller falls back to
      // bundled fixtures. Only surface unexpected failures.
      const benign = /not found|object not found|404|row-level security/i.test(error.message);
      if (!benign) {
        trackError("service_error", { scope: "timeline_sign_failed", message: error.message, runId });
      }
    }
    return null;
  }
  return data.signedUrl;
}

/**
 * Convenience wrapper: resolve the signed URL, fetch the JSON, return
 * the parsed timeline. Returns `null` on any miss (no row, RLS rejection,
 * fetch error). Callers fall back to bundled fixtures.
 */
export async function loadTimelineFromStorage(
  runId: string,
): Promise<VisualizationTimeline | null> {
  if (!isOn()) return null;
  const url = await getTimelineSignedUrl(runId);
  if (!url) return null;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      trackError("service_error", {
        scope: "timeline_fetch_failed",
        message: `${res.status} ${res.statusText}`,
        runId,
      });
      return null;
    }
    return (await res.json()) as VisualizationTimeline;
  } catch (err) {
    trackError("service_error", {
      scope: "timeline_fetch_threw",
      message: err instanceof Error ? err.message : String(err),
      runId,
    });
    return null;
  }
}

/** List public + own runs (RLS handles the filter). */
export async function listRunRows(limit = 50): Promise<RunRow[]> {
  if (!isOn()) return [];
  const { data, error } = await supabase
    .from("runs")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(limit);
  if (error) {
    trackError("service_error", { scope: "list_runs_failed", message: error.message });
    return [];
  }
  return (data ?? []) as unknown as RunRow[];
}
