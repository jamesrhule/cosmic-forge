/**
 * Auth context for the workbench.
 *
 * Wraps Lovable Cloud (Supabase) auth. Public catalog browsing works
 * without a session — `user` is simply null. Once signed in, `roles`
 * is fetched from `public.user_roles` and exposed via `hasRole()`.
 *
 * Per Lovable Cloud rules: we install `onAuthStateChange` BEFORE the
 * initial `getSession()` call so the listener never misses the
 * hydration event.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";
import { lovable } from "@/integrations/lovable";
import { clearProfileCache, getProfile, type Profile } from "@/lib/profiles";
import { enforceRateLimit, LIMITS } from "@/lib/rateLimit";

export type AppRole = "viewer" | "researcher" | "admin";

interface AuthContextValue {
  user: User | null;
  session: Session | null;
  roles: AppRole[];
  profile: Profile | null;
  loading: boolean;
  hasRole: (role: AppRole) => boolean;
  signInWithPassword: (email: string, password: string) => Promise<{ error: Error | null }>;
  signUp: (email: string, password: string) => Promise<{ error: Error | null }>;
  signInWithGoogle: (redirectPath?: string) => Promise<{ error: Error | null }>;
  signOut: () => Promise<void>;
  /** First-user admin bootstrap: caller must be signed in with this email. */
  claimAdmin: (email: string) => Promise<boolean>;
  /** Send a password-recovery email; redirects to /reset-password. */
  requestPasswordReset: (email: string) => Promise<{ error: Error | null }>;
  /** Update the signed-in user's password (used in /reset-password flow). */
  updatePassword: (newPassword: string) => Promise<{ error: Error | null }>;
  /** Refresh the cached profile after an update. */
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [roles, setRoles] = useState<AppRole[]>([]);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchRoles = useCallback(async (userId: string) => {
    const { data, error } = await supabase
      .from("user_roles")
      .select("role")
      .eq("user_id", userId);
    if (error) {
      setRoles([]);
      return;
    }
    setRoles((data ?? []).map((r) => r.role as AppRole));
  }, []);

  const fetchProfile = useCallback(async (userId: string) => {
    const p = await getProfile(userId);
    setProfile(p);
  }, []);

  useEffect(() => {
    let mounted = true;

    // 1. Subscribe FIRST so we never miss a state change.
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      if (!mounted) return;
      setSession(next);
      if (next?.user) {
        // Defer reads out of the auth callback to avoid re-entrant
        // supabase calls.
        setTimeout(() => {
          void fetchRoles(next.user.id);
          void fetchProfile(next.user.id);
        }, 0);
      } else {
        setRoles([]);
        setProfile(null);
        clearProfileCache();
      }
    });

    // 2. Then resolve the existing session.
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      if (data.session?.user) {
        void fetchRoles(data.session.user.id);
        void fetchProfile(data.session.user.id);
      }
      setLoading(false);
    });

    return () => {
      mounted = false;
      sub.subscription.unsubscribe();
    };
  }, [fetchRoles, fetchProfile]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      session,
      roles,
      profile,
      loading,
      hasRole: (role) => roles.includes(role),
      signInWithPassword: async (email, password) => {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        return { error: error ? new Error(error.message) : null };
      },
      signUp: async (email, password) => {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo:
              typeof window !== "undefined"
                ? `${window.location.origin}/auth/callback`
                : undefined,
          },
        });
        return { error: error ? new Error(error.message) : null };
      },
      signInWithGoogle: async (redirectPath = "/") => {
        if (typeof window === "undefined") {
          return { error: new Error("OAuth requires a browser") };
        }
        const redirect_uri = `${window.location.origin}/auth/callback?redirect=${encodeURIComponent(
          redirectPath,
        )}`;
        const result = await lovable.auth.signInWithOAuth("google", { redirect_uri });
        if (result.error) {
          return { error: result.error instanceof Error ? result.error : new Error(String(result.error)) };
        }
        return { error: null };
      },
      signOut: async () => {
        clearProfileCache();
        await supabase.auth.signOut();
      },
      claimAdmin: async (email) => {
        // Hard rate-limit: 3 attempts/hour per identity, plus the
        // bootstrap-only check on the server side.
        const allowed = await enforceRateLimit(LIMITS.claimAdmin);
        if (!allowed) return false;
        const { data, error } = await supabase.rpc("claim_admin", { _email: email });
        if (error) return false;
        if (data === true && session?.user) {
          await fetchRoles(session.user.id);
          return true;
        }
        return false;
      },
      requestPasswordReset: async (email) => {
        if (typeof window === "undefined") {
          return { error: new Error("Reset requires a browser") };
        }
        const allowed = await enforceRateLimit(LIMITS.passwordReset);
        if (!allowed) {
          return {
            error: new Error("Too many reset requests. Please wait a few minutes and try again."),
          };
        }
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${window.location.origin}/reset-password`,
        });
        return { error: error ? new Error(error.message) : null };
      },
      updatePassword: async (newPassword) => {
        const { error } = await supabase.auth.updateUser({ password: newPassword });
        return { error: error ? new Error(error.message) : null };
      },
      refreshProfile: async () => {
        if (!session?.user) return;
        clearProfileCache();
        await fetchProfile(session.user.id);
      },
    }),
    [session, roles, profile, loading, fetchRoles, fetchProfile],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    // SSR-safe fallback: behave as signed-out, no-op writers.
    return {
      user: null,
      session: null,
      roles: [],
      profile: null,
      loading: false,
      hasRole: () => false,
      signInWithPassword: async () => ({ error: new Error("AuthProvider missing") }),
      signUp: async () => ({ error: new Error("AuthProvider missing") }),
      signInWithGoogle: async () => ({ error: new Error("AuthProvider missing") }),
      signOut: async () => {},
      claimAdmin: async () => false,
      requestPasswordReset: async () => ({ error: new Error("AuthProvider missing") }),
      updatePassword: async () => ({ error: new Error("AuthProvider missing") }),
      refreshProfile: async () => {},
    };
  }
  return ctx;
}
