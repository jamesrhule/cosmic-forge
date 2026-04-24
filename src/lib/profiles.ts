/**
 * Profile helpers — read/write `public.profiles`. RLS makes profiles
 * world-readable; only the owner can write.
 */

import { supabase } from "@/integrations/supabase/client";
import { trackError } from "@/lib/telemetry";

export interface Profile {
  id: string;
  display_name: string | null;
  handle: string | null;
  avatar_url: string | null;
  bio: string | null;
  affiliation: string | null;
  created_at: string;
  updated_at: string;
}

export type ProfilePatch = Partial<
  Pick<Profile, "display_name" | "handle" | "avatar_url" | "bio" | "affiliation">
>;

// Module-local cache. Cleared on sign-out by AuthProvider.
const cache = new Map<string, Profile | null>();

export function clearProfileCache(): void {
  cache.clear();
}

export async function getProfile(userId: string): Promise<Profile | null> {
  if (cache.has(userId)) return cache.get(userId) ?? null;
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", userId)
    .maybeSingle();
  if (error) {
    trackError("service_error", { scope: "get_profile_failed", message: error.message, userId });
    cache.set(userId, null);
    return null;
  }
  cache.set(userId, (data as Profile | null) ?? null);
  return (data as Profile | null) ?? null;
}

export async function getProfilesByIds(ids: string[]): Promise<Map<string, Profile>> {
  const out = new Map<string, Profile>();
  if (ids.length === 0) return out;

  const need: string[] = [];
  for (const id of ids) {
    const cached = cache.get(id);
    if (cached) out.set(id, cached);
    else if (!cache.has(id)) need.push(id);
  }

  if (need.length === 0) return out;

  const { data, error } = await supabase.from("profiles").select("*").in("id", need);
  if (error) {
    trackError("service_error", { scope: "get_profiles_failed", message: error.message });
    return out;
  }
  for (const row of (data ?? []) as Profile[]) {
    cache.set(row.id, row);
    out.set(row.id, row);
  }
  // Mark misses so we don't re-fetch
  for (const id of need) {
    if (!out.has(id)) cache.set(id, null);
  }
  return out;
}

export async function updateProfile(
  userId: string,
  patch: ProfilePatch,
): Promise<{ ok: boolean; profile?: Profile; reason?: string }> {
  // Upsert because the row may not exist yet for OAuth users created
  // before the trigger landed.
  const { data, error } = await supabase
    .from("profiles")
    .upsert({ id: userId, ...patch }, { onConflict: "id" })
    .select("*")
    .single();
  if (error) {
    trackError("service_error", { scope: "update_profile_failed", message: error.message, userId });
    return { ok: false, reason: error.message };
  }
  cache.set(userId, data as Profile);
  return { ok: true, profile: data as Profile };
}
