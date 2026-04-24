import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { z } from "zod";
import { useAuth } from "@/lib/auth";

const searchSchema = z.object({
  redirect: z.string().optional().default("/"),
});

export const Route = createFileRoute("/auth/callback")({
  validateSearch: (s) => searchSchema.parse(s),
  component: AuthCallbackRoute,
});

function AuthCallbackRoute() {
  const { redirect } = Route.useSearch();
  const navigate = useNavigate();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (loading) return;
    // Whether or not auth resolved, send the user somewhere reasonable.
    // If the OAuth handshake is still in flight, the AuthProvider will
    // emit a state change shortly and the next render will navigate.
    if (user) {
      void navigate({ to: redirect, replace: true });
    }
  }, [user, loading, redirect, navigate]);

  return (
    <div className="grid min-h-screen place-items-center bg-background text-sm text-muted-foreground">
      <div className="flex items-center gap-3">
        <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
        Completing sign in…
      </div>
    </div>
  );
}
