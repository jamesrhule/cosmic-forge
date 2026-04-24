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

  useEffect(() => {
    let mounted = true;

    // 1. Subscribe FIRST so we never miss a state change.
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      if (!mounted) return;
      setSession(next);
      if (next?.user) {
        // Defer the role fetch out of the auth callback to avoid
        // re-entrant supabase calls.
        setTimeout(() => fetchRoles(next.user.id), 0);
      } else {
        setRoles([]);
      }
    });

    // 2. Then resolve the existing session.
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      setSession(data.session);
      if (data.session?.user) {
        fetchRoles(data.session.user.id);
      }
      setLoading(false);
    });

    return () => {
      mounted = false;
      sub.subscription.unsubscribe();
    };
  }, [fetchRoles]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: session?.user ?? null,
      session,
      roles,
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
        await supabase.auth.signOut();
      },
      claimAdmin: async (email) => {
        const { data, error } = await supabase.rpc("claim_admin", { _email: email });
        if (error) return false;
        if (data === true && session?.user) {
          await fetchRoles(session.user.id);
          return true;
        }
        return false;
      },
    }),
    [session, roles, loading, fetchRoles],
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
      loading: false,
      hasRole: () => false,
      signInWithPassword: async () => ({ error: new Error("AuthProvider missing") }),
      signUp: async () => ({ error: new Error("AuthProvider missing") }),
      signInWithGoogle: async () => ({ error: new Error("AuthProvider missing") }),
      signOut: async () => {},
      claimAdmin: async () => false,
    };
  }
  return ctx;
}
