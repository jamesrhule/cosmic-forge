import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/reset-password")({
  head: () => ({
    meta: [
      { title: "Reset password — UCGLE-F1 Workbench" },
      { name: "description", content: "Set a new password for your workbench account." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: ResetPasswordRoute,
});

function ResetPasswordRoute() {
  const navigate = useNavigate();
  const { user, loading, updatePassword } = useAuth();

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  // Wait one tick for AuthProvider to hydrate the recovery session from
  // the URL hash before deciding whether the link is valid.
  const [settled, setSettled] = useState(false);

  useEffect(() => {
    if (loading) return;
    const t = setTimeout(() => setSettled(true), 250);
    return () => clearTimeout(t);
  }, [loading]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      toast.error("Password too short", { description: "Use at least 8 characters." });
      return;
    }
    if (password !== confirm) {
      toast.error("Passwords don't match");
      return;
    }
    setBusy(true);
    try {
      const { error } = await updatePassword(password);
      if (error) {
        toast.error("Couldn't update password", { description: error.message });
        return;
      }
      toast.success("Password updated");
      void navigate({ to: "/", replace: true });
    } finally {
      setBusy(false);
    }
  };

  const linkExpired = settled && !user;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-1">
          <CardTitle className="text-xl">Reset password</CardTitle>
          <p className="text-xs text-muted-foreground">Choose a new password for your account.</p>
        </CardHeader>
        <CardContent className="space-y-4">
          {linkExpired ? (
            <div className="space-y-3 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-xs">
              <p className="text-destructive">
                This recovery link has expired or is invalid.
              </p>
              <Link to="/login" search={{ redirect: "/" }} className="inline-block underline-offset-2 hover:underline">
                ← Request a new one
              </Link>
            </div>
          ) : (
            <form onSubmit={onSubmit} className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="new-password" className="text-xs">
                  New password
                </Label>
                <Input
                  id="new-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="confirm-password" className="text-xs">
                  Confirm
                </Label>
                <Input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={busy || !settled}>
                {busy ? "…" : "Update password"}
              </Button>
            </form>
          )}

          <div className="text-xs text-muted-foreground">
            <Link to="/" className="underline-offset-2 hover:underline">
              ← Catalog
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
