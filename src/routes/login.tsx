import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, type FormEvent } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/lib/auth";

const searchSchema = z.object({
  redirect: z.string().optional().default("/"),
});

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in — UCGLE-F1 Workbench" },
      {
        name: "description",
        content: "Sign in to author runs, persist results, and manage the public catalog.",
      },
    ],
  }),
  validateSearch: (s) => searchSchema.parse(s),
  component: LoginRoute,
});

function LoginRoute() {
  const { redirect } = Route.useSearch();
  const navigate = useNavigate();
  const { user, signInWithPassword, signUp, signInWithGoogle, claimAdmin, requestPasswordReset } = useAuth();

  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [adminEmail, setAdminEmail] = useState("");
  const [resetting, setResetting] = useState(false);
  // Inline field-level errors. Cleared on next edit so the user gets
  // immediate feedback that their correction is being considered.
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // If already signed in, bounce immediately. Side-effect must run in
  // an effect — calling navigate() during render schedules an update on
  // the router and triggers a React warning + duplicate navigate on
  // fast refresh.
  useEffect(() => {
    if (user) {
      void navigate({ to: redirect, replace: true });
    }
  }, [user, redirect, navigate]);

  const validate = () => {
    let ok = true;
    setFormError(null);
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setEmailError("Enter a valid email address.");
      ok = false;
    } else {
      setEmailError(null);
    }
    if (password.length < 8) {
      setPasswordError("Password must be at least 8 characters.");
      ok = false;
    } else {
      setPasswordError(null);
    }
    return ok;
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setBusy(true);
    try {
      const fn = mode === "signin" ? signInWithPassword : signUp;
      const { error } = await fn(email, password);
      if (error) {
        setFormError(error.message);
        toast.error(mode === "signin" ? "Sign in failed" : "Sign up failed", {
          description: error.message,
        });
        return;
      }
      if (mode === "signup") {
        toast.success("Check your inbox", {
          description: "Confirm your email to finish creating the account.",
        });
      } else {
        toast.success("Signed in");
        void navigate({ to: redirect, replace: true });
      }
    } finally {
      setBusy(false);
    }
  };

  const onGoogle = async () => {
    setBusy(true);
    try {
      const { error } = await signInWithGoogle(redirect);
      if (error) {
        setFormError(error.message);
        toast.error("Google sign in failed", { description: error.message });
      }
    } finally {
      setBusy(false);
    }
  };

  const onClaimAdmin = async () => {
    if (!adminEmail.trim()) return;
    const ok = await claimAdmin(adminEmail.trim());
    if (ok) {
      toast.success("Admin role granted");
    } else {
      toast.error("Couldn't claim admin", {
        description: "You must be signed in with that exact email.",
      });
    }
  };

  const onForgotPassword = async () => {
    if (!email.trim()) {
      setEmailError("Enter your email first, then click \"Forgot password?\".");
      return;
    }
    setEmailError(null);
    setResetting(true);
    try {
      const { error } = await requestPasswordReset(email.trim());
      if (error) {
        setFormError(error.message);
        toast.error("Couldn't send reset email", { description: error.message });
      } else {
        toast.success("Reset link sent", {
          description: "Check your inbox for a password recovery email.",
        });
      }
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-12">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-1">
          <CardTitle className="text-xl">
            {mode === "signin" ? "Sign in" : "Create account"}
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            UCGLE-F1 Workbench · authoring access
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <Button
            type="button"
            variant="outline"
            className="w-full"
            disabled={busy}
            onClick={onGoogle}
          >
            <GoogleIcon className="mr-2 h-4 w-4" />
            Continue with Google
          </Button>

          <div className="relative">
            <Separator />
            <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-card px-2 text-[10px] uppercase tracking-wider text-muted-foreground">
              or
            </span>
          </div>

          <form onSubmit={onSubmit} className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-xs">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-xs">
                  Password
                </Label>
                {mode === "signin" ? (
                  <button
                    type="button"
                    onClick={onForgotPassword}
                    disabled={resetting}
                    className="text-[10px] text-muted-foreground underline-offset-2 hover:underline disabled:opacity-60"
                  >
                    {resetting ? "Sending…" : "Forgot password?"}
                  </button>
                ) : null}
              </div>
              <Input
                id="password"
                type="password"
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <Button type="submit" className="w-full" disabled={busy}>
              {busy ? "…" : mode === "signin" ? "Sign in" : "Create account"}
            </Button>
          </form>

          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <button
              type="button"
              className="underline-offset-2 hover:underline"
              onClick={() => setMode((m) => (m === "signin" ? "signup" : "signin"))}
            >
              {mode === "signin" ? "Need an account?" : "Have an account? Sign in"}
            </button>
            <Link to="/" className="underline-offset-2 hover:underline">
              ← Catalog
            </Link>
          </div>

          <details className="rounded-md border bg-muted/30 px-3 py-2 text-xs">
            <summary className="cursor-pointer text-muted-foreground">
              First-user admin claim
            </summary>
            <div className="mt-2 space-y-2">
              <p className="text-muted-foreground">
                After signing in, paste your exact email to grant yourself the
                admin role (one-shot, idempotent).
              </p>
              <div className="flex gap-2">
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={adminEmail}
                  onChange={(e) => setAdminEmail(e.target.value)}
                  className="h-8 text-xs"
                />
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={onClaimAdmin}
                  disabled={!user}
                >
                  Claim
                </Button>
              </div>
              {!user ? (
                <p className="text-[10px] text-muted-foreground">
                  (Sign in first.)
                </p>
              ) : null}
            </div>
          </details>
        </CardContent>
      </Card>
    </div>
  );
}

function GoogleIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" {...props}>
      <path
        fill="#EA4335"
        d="M12 11v2.8h7.8c-.3 1.7-2.2 5-7.8 5-4.7 0-8.5-3.9-8.5-8.7s3.8-8.7 8.5-8.7c2.7 0 4.5 1.1 5.5 2.1l3.7-3.6C18.8 1.5 15.7 0 12 0 5.4 0 0 5.4 0 12s5.4 12 12 12c6.9 0 11.5-4.8 11.5-11.7 0-.8-.1-1.4-.2-2H12z"
      />
    </svg>
  );
}
