/**
 * Two-layer rate limiter used by client-side mutations.
 *
 * 1. **In-memory burst guard** — a per-tab token bucket that throttles
 *    accidental tight loops (a `useEffect` retry storm, a misbehaving
 *    test) before they ever leave the browser. Resets on full page
 *    reload, which is fine: it's a politeness layer, not a security
 *    layer.
 *
 * 2. **Postgres durable counter** — calls the `check_rate_limit` RPC
 *    (SECURITY DEFINER, keyed on `auth.uid()`) so that abuse from
 *    multiple tabs / devices / IPs against the same account still gets
 *    caught. Returns `false` when the bucket is exhausted; the caller
 *    is expected to surface a friendly toast.
 *
 * The Postgres call is fire-and-forget for the *first* request in a
 * window so the UX cost is one round-trip per N actions, not per
 * action. Subsequent calls within a 250ms window reuse the cached
 * decision.
 *
 * The in-memory layer is authoritative when the network call is in
 * flight, so a flood within a single tab is throttled even before the
 * server replies.
 */

import { supabase } from "@/integrations/supabase/client";
import { trackWarn } from "@/lib/telemetry";

export interface RateLimitConfig {
  /** Stable identifier used as the Postgres bucket key, e.g. `"run_create"`. */
  scope: string;
  /** Bucket capacity (max burst). */
  capacity: number;
  /** Refill rate, in tokens per second. */
  refillPerSec: number;
}

interface MemBucket {
  tokens: number;
  refilledAt: number;
}

const memBuckets = new Map<string, MemBucket>();

function takeMemory(cfg: RateLimitConfig): boolean {
  const now = performance.now();
  const existing = memBuckets.get(cfg.scope);
  const elapsedSec = existing ? Math.max(0, (now - existing.refilledAt) / 1000) : 0;
  const tokens = Math.min(
    cfg.capacity,
    (existing?.tokens ?? cfg.capacity) + elapsedSec * cfg.refillPerSec,
  );
  if (tokens >= 1) {
    memBuckets.set(cfg.scope, { tokens: tokens - 1, refilledAt: now });
    return true;
  }
  memBuckets.set(cfg.scope, { tokens, refilledAt: now });
  return false;
}

interface ServerDecision {
  allowed: boolean;
  decidedAt: number;
}

const serverDecisionCache = new Map<string, ServerDecision>();
const SERVER_CACHE_MS = 250;

async function checkServer(cfg: RateLimitConfig): Promise<boolean> {
  const cached = serverDecisionCache.get(cfg.scope);
  const now = performance.now();
  if (cached && now - cached.decidedAt < SERVER_CACHE_MS) {
    return cached.allowed;
  }

  try {
    const { data, error } = await supabase.rpc("check_rate_limit", {
      _scope: cfg.scope,
      _capacity: cfg.capacity,
      _refill_per_sec: cfg.refillPerSec,
    });
    if (error) {
      // Soft-fail: allow on RPC error so a transient DB blip doesn't
      // brick the UI. We surface a warning so the dashboard can spot
      // pathological failure rates.
      trackWarn("rate_limit_rpc", error.message, { scope: cfg.scope });
      return true;
    }
    const allowed = data === true;
    serverDecisionCache.set(cfg.scope, { allowed, decidedAt: now });
    return allowed;
  } catch (err) {
    trackWarn("rate_limit_rpc", err instanceof Error ? err.message : String(err), {
      scope: cfg.scope,
    });
    return true;
  }
}

/**
 * Returns `true` when the action may proceed, `false` otherwise.
 *
 * Callers should toast or set a form error on `false`. The in-memory
 * decision is checked first and short-circuits the server round-trip
 * when a burst is already exhausted.
 */
export async function enforceRateLimit(cfg: RateLimitConfig): Promise<boolean> {
  if (!takeMemory(cfg)) {
    trackWarn("rate_limit_burst", `mem-bucket exhausted for ${cfg.scope}`, {
      scope: cfg.scope,
    });
    return false;
  }
  return checkServer(cfg);
}

/** Preset buckets used across the app — keep in lockstep with backend ops. */
export const LIMITS = {
  runCreate: { scope: "run_create", capacity: 10, refillPerSec: 10 / 600 } as RateLimitConfig,
  auditWrite: { scope: "audit_write", capacity: 60, refillPerSec: 1 } as RateLimitConfig,
  claimAdmin: { scope: "claim_admin", capacity: 3, refillPerSec: 3 / 3600 } as RateLimitConfig,
  passwordReset: { scope: "password_reset", capacity: 5, refillPerSec: 5 / 3600 } as RateLimitConfig,
  timelineWrite: { scope: "timeline_write", capacity: 5, refillPerSec: 5 / 600 } as RateLimitConfig,
} as const;
