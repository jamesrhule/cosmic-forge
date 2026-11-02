import { describe, expect, it, vi } from "vitest";
import { blockedMessage, unconfiguredClient } from "../unconfigured";

// Minimal slice of the supabase-js surface the app touches.
interface ClientLike {
  from: (t: string) => {
    select: (c: string) => {
      eq: (
        k: string,
        v: unknown,
      ) => PromiseLike<{ data: unknown; error: { message: string } | null }>;
    };
  };
  auth: {
    getSession: () => Promise<{ data: { session: unknown }; error: { message: string } | null }>;
    onAuthStateChange: (cb: () => void) => { data: { subscription: { unsubscribe: () => void } } };
    signOut: () => Promise<{ error: { message: string } | null }>;
  };
  channel: (n: string) => { on: (...a: unknown[]) => { subscribe: () => unknown } };
}

describe("unconfigured Supabase client (R9)", () => {
  it("names each missing variable as BLOCKED-ON-JAMES", () => {
    expect(blockedMessage(["VITE_SUPABASE_URL", "VITE_SUPABASE_PUBLISHABLE_KEY"])).toBe(
      "BLOCKED-ON-JAMES:VITE_SUPABASE_URL BLOCKED-ON-JAMES:VITE_SUPABASE_PUBLISHABLE_KEY",
    );
  });

  it("degrades instead of throwing, and warns once", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const c = unconfiguredClient<ClientLike>(["VITE_SUPABASE_URL"]);
    unconfiguredClient<ClientLike>(["VITE_SUPABASE_URL"]);
    expect(warn).toHaveBeenCalledTimes(1);
    expect(String(warn.mock.calls[0][0])).toContain("BLOCKED-ON-JAMES:VITE_SUPABASE_URL");

    const q = await c.from("user_roles").select("role").eq("user_id", "u1");
    expect(q.data).toBeNull();
    expect(q.error?.message).toBe("BLOCKED-ON-JAMES:VITE_SUPABASE_URL");

    const s = await c.auth.getSession();
    expect(s.data.session).toBeNull();
    expect(s.error?.message).toContain("BLOCKED-ON-JAMES");

    const sub = c.auth.onAuthStateChange(() => {});
    expect(() => sub.data.subscription.unsubscribe()).not.toThrow();
    expect(() =>
      c
        .channel("x")
        .on("postgres_changes", {}, () => {})
        .subscribe(),
    ).not.toThrow();
    expect((await c.auth.signOut()).error?.message).toContain("BLOCKED-ON-JAMES");
    warn.mockRestore();
  });
});
