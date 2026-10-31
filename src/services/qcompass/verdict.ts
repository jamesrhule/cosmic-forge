/**
 * QCompass — Phase-3 verdict report service.
 *
 * Verdict reports are admin-only (PLAN.md correction 9). They are served by
 * the compute API, which verifies the caller's Supabase session and `admin`
 * role. There is no static-file fallback: the old
 * `/fixtures/verdict/*` files are no longer part of the build.
 *
 * @example
 *   const v = await getVerdictReport();
 */
import { API_BASE_URL } from "@/config/features";
import { supabase } from "@/integrations/supabase/client";
import type { DomainId } from "@/lib/domains/types";
import { ServiceError } from "@/types/domain";

export interface VerdictRow {
  domain: DomainId;
  status: "DELIVERED" | "PENDING" | "FAILED";
  evidence: string[];
  audit_archive_url?: string;
  notes?: string;
}

export interface VerdictReport {
  generated_at: string;
  reviewer: string;
  rows: VerdictRow[];
}

/** @endpoint GET /api/verdict/{id} */
export async function getVerdictReport(id = "sample"): Promise<VerdictReport> {
  if (!API_BASE_URL) {
    throw new ServiceError(
      "UPSTREAM_FAILURE",
      "The compute API isn't configured (VITE_API_URL); verdict reports are served only by the API.",
    );
  }
  const { data } = await supabase.auth.getSession();
  const token = data?.session?.access_token;
  if (!token) {
    throw new ServiceError("UPSTREAM_FAILURE", "Sign in with an admin account to view verdicts.");
  }
  const res = await fetch(`${API_BASE_URL}/api/verdict/${encodeURIComponent(id)}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new ServiceError(
      res.status === 404 ? "NOT_FOUND" : "UPSTREAM_FAILURE",
      `Verdict request failed: ${res.status} ${res.statusText}`,
    );
  }
  return (await res.json()) as VerdictReport;
}
