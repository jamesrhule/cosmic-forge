/**
 * QCompass — Auth/tenancy service stub.
 *
 * @example
 *   const tenants = await listTenants();
 */
import * as sdk from "@qcompass/frontend-sdk";
import { loadFixture } from "@/lib/fixtures";
import { api, usesApi } from "@/lib/sdk";

export interface Tenant {
  id: string;
  label: string;
  role: "admin" | "member" | "viewer";
}

/** @endpoint GET /api/qcompass/tenants */
export async function listTenants(): Promise<Tenant[]> {
  if (usesApi()) return api((c) => sdk.listTenants(c));
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
