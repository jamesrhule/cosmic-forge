/**
 * Email-verification gate (soft, write-only).
 *
 * The auth row's `email_confirmed_at` is the source of truth. We expose
 * a single sync helper plus a thin React hook so any mutation path can
 * bail with a friendly toast before hitting the network.
 *
 * Server-side enforcement still runs in RLS (see the
 * `verified users insert own audit rows` policy and the
 * `claim_admin` function's `email_verified` check). The client-side
 * gate is purely a UX layer — never rely on it for security.
 */

import { useAuth } from "@/lib/auth";
import type { Session, User } from "@supabase/supabase-js";

export function isEmailVerified(user: User | null): boolean {
  if (!user) return false;
  // Supabase records confirmation in two places depending on flow; check
  // both so OAuth (Google) users are considered verified by default.
  if (user.email_confirmed_at) return true;
  // Google sign-in path doesn't set email_confirmed_at; trust providers.
  const identity = user.app_metadata?.provider;
  if (identity && identity !== "email") return true;
  return false;
}

export function isSessionVerified(session: Session | null): boolean {
  return isEmailVerified(session?.user ?? null);
}

export function useEmailVerified(): {
  user: User | null;
  verified: boolean;
  needsVerification: boolean;
} {
  const { user } = useAuth();
  const verified = isEmailVerified(user);
  return {
    user,
    verified,
    needsVerification: Boolean(user) && !verified,
  };
}

/** Standard message to show in a toast / error banner when blocked. */
export const VERIFY_EMAIL_MESSAGE =
  "Please verify your email before continuing. Check your inbox for the link we sent on signup.";
