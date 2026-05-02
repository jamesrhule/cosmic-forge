/**
 * QCompass — Parameter scan service.
 *
 * @example
 *   const scans = await listScans("hep.lattice");
 */
import { FEATURES } from "@/config/features";
import type { DomainId } from "@/lib/domains/types";
import { apiFetch, isQcompassBackendConfigured } from "./http";

export interface ScanSummary {
  id: string;
  domain: DomainId;
  label: string;
  axes: string[];
  shape: number[];
}

/** @endpoint GET /api/qcompass/scans?domain={domain} */
export async function listScans(domain: DomainId): Promise<ScanSummary[]> {
  if (FEATURES.liveBackend && isQcompassBackendConfigured()) {
    try {
      return await apiFetch<ScanSummary[]>(
        `/api/qcompass/scans?domain=${encodeURIComponent(domain)}`,
      );
    } catch {
      /* fall through */
    }
  }
  return [];
}

/** @endpoint GET /api/qcompass/scans/{id} */
export async function getScan(scanId: string): Promise<ScanSummary | null> {
  if (FEATURES.liveBackend && isQcompassBackendConfigured()) {
    try {
      return await apiFetch<ScanSummary>(`/api/qcompass/scans/${encodeURIComponent(scanId)}`);
    } catch {
      /* fall through */
    }
  }
  return null;
}

/** @endpoint POST /api/qcompass/scans */
export async function startScan(
  domain: DomainId,
  manifest: Record<string, unknown>,
): Promise<{ scanId: string }> {
  if (FEATURES.liveBackend && isQcompassBackendConfigured()) {
    try {
      return await apiFetch<{ scanId: string }>(`/api/qcompass/scans`, {
        method: "POST",
        body: { domain, manifest },
      });
    } catch {
      /* fall through */
    }
  }
  return { scanId: `scan-${domain}-${Date.now()}` };
}
