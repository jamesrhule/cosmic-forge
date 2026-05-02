/**
 * QCompass — Auth/tenancy service stub.
 *
 * @example
 *   const tenants = await listTenants();
 */
import { FEATURES } from "@/config/features";
import { loadFixture } from "@/lib/fixtures";
import { apiFetch, isQcompassBackendConfigured } from "./http";

export interface Tenant {
  id: string;
  label: string;
  role: "admin" | "member" | "viewer";
}

/** @endpoint GET /api/qcompass/tenants */
export async function listTenants(): Promise<Tenant[]> {
  if (FEATURES.liveBackend && isQcompassBackendConfigured()) {
    try {
      return await apiFetch<Tenant[]>("/api/qcompass/tenants");
    } catch {
      /* fall through */
    }
  }
  return loadFixture<Tenant[]>("auth/tenants.json");
}

/**
 * No-op token validator. The backend wires real verification later.
 * Returns true when `token` is non-empty so the UI can stop showing
 * "Set your token" affordances.
 */
export function validateToken(token: string | null): boolean {
  return Boolean(token && token.length > 0);
}
