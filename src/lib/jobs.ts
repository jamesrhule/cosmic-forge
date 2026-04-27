/**
 * Job queue helpers — thin Tier 5 scaffold.
 *
 * The `jobs` table + `claim_next_job` / `complete_job` RPCs live in
 * Postgres. Workers (out-of-process) call the RPCs with the service-role
 * key. App code only ever ENQUEUES jobs through these helpers.
 *
 * We deliberately keep the surface tiny so that the eventual worker
 * runtime (Cloud Run, modal, separate FastAPI worker, etc.) can be
 * swapped in without touching app code.
 */

import { supabase } from "@/integrations/supabase/client";
import { trackError } from "@/lib/telemetry";

export type ComputeClass = "cpu" | "gpu_small" | "gpu_large";
export type JobKind = "run.simulate" | "run.audit" | "viz.bake";

export interface EnqueueJobInput {
  tenantId: string;
  kind: JobKind;
  payload: Record<string, unknown>;
  runId?: string;
  computeClass?: ComputeClass;
  /** 0 = lowest, 100 = default, 1000 = urgent. */
  priority?: number;
  /** ISO timestamp; defaults to "now". */
  scheduledAt?: string;
}

export interface EnqueueJobResult {
  ok: boolean;
  jobId?: string;
  reason?: string;
}

export async function enqueueJob(input: EnqueueJobInput): Promise<EnqueueJobResult> {
  const { data: auth } = await supabase.auth.getUser();
  if (!auth.user) return { ok: false, reason: "NOT_AUTHENTICATED" };

  const { data, error } = await supabase
    .from("jobs")
    .insert({
      tenant_id: input.tenantId,
      kind: input.kind,
      payload: input.payload as never,
      run_id: input.runId ?? null,
      compute_class: input.computeClass ?? "cpu",
      priority: input.priority ?? 100,
      scheduled_at: input.scheduledAt ?? new Date().toISOString(),
      created_by: auth.user.id,
      status: "queued",
    })
    .select("id")
    .single();

  if (error) {
    trackError("service_error", { scope: "enqueue_job", message: error.message, kind: input.kind });
    return { ok: false, reason: error.message };
  }
  return { ok: true, jobId: data.id };
}
