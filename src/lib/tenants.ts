/**
 * Tenant helpers — Tier 5 scaffold.
 *
 * Every authenticated user gets a "Personal" tenant on signup
 * (auth.users trigger -> ensure_personal_tenant). UI flows that don't
 * yet expose tenant switching should default to the user's personal
 * tenant via {@link getDefaultTenantId}.
 */

import { supabase } from "@/integrations/supabase/client";
import { trackError } from "@/lib/telemetry";

export interface TenantSummary {
  id: string;
  name: string;
  slug: string;
  role: "owner" | "admin" | "member" | "viewer";
  subscriptionTier: "free" | "pro" | "team" | "enterprise";
}

export async function listTenants(): Promise<TenantSummary[]> {
  const { data, error } = await supabase
    .from("tenant_members")
    .select("role, tenant:tenants(id, name, slug, subscription_tier)")
    .order("joined_at", { ascending: true });

  if (error) {
    trackError("service_error", { scope: "list_tenants", message: error.message });
    return [];
  }
  return (data ?? [])
    .map((row) => {
      const t = row.tenant as { id: string; name: string; slug: string; subscription_tier: TenantSummary["subscriptionTier"] } | null;
      if (!t) return null;
      return {
        id: t.id,
        name: t.name,
        slug: t.slug,
        role: row.role as TenantSummary["role"],
        subscriptionTier: t.subscription_tier,
      };
    })
    .filter(Boolean) as TenantSummary[];
}

/**
 * Returns the user's first tenant (their Personal one, in practice).
 * Used as the default scope for new runs / jobs until a tenant switcher
 * UI exists.
 */
export async function getDefaultTenantId(): Promise<string | null> {
  const tenants = await listTenants();
  return tenants[0]?.id ?? null;
}
