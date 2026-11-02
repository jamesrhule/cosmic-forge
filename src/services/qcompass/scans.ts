/**
 * QCompass — Parameter scan service.
 *
 * With `VITE_API_URL` set, reads and writes the compute API's scan store
 * through the generated SDK (P4-02). Without it there are no scans (no scan
 * fixtures ship for the QCompass domains).
 *
 * @example
 *   const scans = await listScans("hep.lattice");
 */
import * as sdk from "@qcompass/frontend-sdk";
import type { DomainId } from "@/lib/domains/types";
import { api, usesApi } from "@/lib/sdk";

export interface ScanSummary {
  id: string;
  domain: DomainId;
  label: string;
  axes: string[];
  shape: number[];
}

/** The API's ScanEnvelope → the catalog row the UI lists. */
function toSummary(s: sdk.ScanEnvelope): ScanSummary {
  const axes = Object.keys(s.axes ?? {});
  const shape = axes.map((k) => {
    const v = s.axes[k];
    return Array.isArray(v) ? v.length : 1;
  });
  return { id: s.scanId, domain: s.domain as DomainId, label: s.kind, axes, shape };
}

/** @endpoint GET /api/qcompass/scans?domain={domain} */
export async function listScans(domain: DomainId): Promise<ScanSummary[]> {
  if (!usesApi()) return [];
  const res = await api((c) => sdk.listScans(c, { domain }));
  return res.scans.map(toSummary);
}

/** @endpoint GET /api/qcompass/scans/{id} */
export async function getScan(scanId: string): Promise<ScanSummary | null> {
  if (!usesApi()) return null;
  return toSummary(await api((c) => sdk.getScan(c, scanId)));
}

/** @endpoint POST /api/qcompass/scans */
export async function startScan(
  domain: DomainId,
  manifest: Record<string, unknown>,
): Promise<{ scanId: string }> {
  if (usesApi()) {
    const res = await api((c) =>
      sdk.createScan(c, { domain, kind: "manifest", payload: { manifest } }),
    );
    return { scanId: res.scanId };
  }
  return { scanId: `scan-${domain}-${Date.now()}` };
}
