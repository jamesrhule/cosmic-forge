/**
 * QCompass — Phase-3 verdict report service (fixture-only).
 *
 * @example
 *   const v = await getVerdictReport();
 */
import { loadFixture } from "@/lib/fixtures";
import type { DomainId } from "@/lib/domains/types";

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

/** @endpoint GET /api/qcompass/verdict  (fixture today) */
export async function getVerdictReport(): Promise<VerdictReport> {
  return loadFixture<VerdictReport>("verdict/sample-verdict.yaml.json");
}
