/**
 * Billing — Tier 5 stub.
 *
 * Real provider (Paddle / Stripe) is intentionally NOT wired yet.
 * This file exists so plan-gating logic and the /pricing UI have a
 * stable interface. When billing lands, only `getCurrentTier` and the
 * checkout helper need to change.
 */

import { supabase } from "@/integrations/supabase/client";
import type { TenantSummary } from "@/lib/tenants";

export type SubscriptionTier = "free" | "pro" | "team" | "enterprise";

export interface PlanLimits {
  maxRunsPerMonth: number;
  maxConcurrentJobs: number;
  maxTimelineBytes: number;
  gpuAccess: boolean;
  prioritySupport: boolean;
}

export const PLAN_LIMITS: Record<SubscriptionTier, PlanLimits> = {
  free: {
    maxRunsPerMonth: 25,
    maxConcurrentJobs: 1,
    maxTimelineBytes: 10 * 1024 * 1024,
    gpuAccess: false,
    prioritySupport: false,
  },
  pro: {
    maxRunsPerMonth: 500,
    maxConcurrentJobs: 4,
    maxTimelineBytes: 50 * 1024 * 1024,
    gpuAccess: true,
    prioritySupport: false,
  },
  team: {
    maxRunsPerMonth: 5_000,
    maxConcurrentJobs: 16,
    maxTimelineBytes: 250 * 1024 * 1024,
    gpuAccess: true,
    prioritySupport: true,
  },
  enterprise: {
    maxRunsPerMonth: Number.POSITIVE_INFINITY,
    maxConcurrentJobs: Number.POSITIVE_INFINITY,
    maxTimelineBytes: 1024 * 1024 * 1024,
    gpuAccess: true,
    prioritySupport: true,
  },
};

export async function getCurrentTier(tenantId: string): Promise<SubscriptionTier> {
  const { data, error } = await supabase
    .from("tenants")
    .select("subscription_tier")
    .eq("id", tenantId)
    .maybeSingle();
  if (error || !data) return "free";
  return data.subscription_tier as SubscriptionTier;
}

export function canUse(tier: SubscriptionTier, feature: keyof PlanLimits): boolean {
  const v = PLAN_LIMITS[tier][feature];
  return typeof v === "boolean" ? v : v > 0;
}

export function tierOf(tenant: TenantSummary | null | undefined): SubscriptionTier {
  return (tenant?.subscriptionTier as SubscriptionTier | undefined) ?? "free";
}

/** Stub — real checkout will redirect to provider. */
export async function startCheckout(_tenantId: string, _tier: SubscriptionTier): Promise<{ url: string | null }> {
  return { url: null };
}
