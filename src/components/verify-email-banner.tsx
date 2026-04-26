/**
 * Soft email-verification banner. Renders only when the user is signed
 * in but `email_confirmed_at` is unset. Sticky to the top of the app
 * shell; non-blocking. Writes (runs, audits, claim_admin) are gated
 * separately via `enforceRateLimit` + RLS.
 */

import { useState } from "react";
import { useEmailVerified } from "@/lib/emailVerification";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "sonner";

export function VerifyEmailBanner() {
  const { needsVerification, user } = useEmailVerified();
  const { signOut } = useAuth();
  const [sending, setSending] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  if (!needsVerification || dismissed || !user?.email) return null;

  async function resend() {
    if (!user?.email) return;
    setSending(true);
    const { error } = await supabase.auth.resend({ type: "signup", email: user.email });
    setSending(false);
    if (error) {
      toast.error(`Couldn't resend: ${error.message}`);
    } else {
      toast.success("Verification email sent. Check your inbox.");
    }
  }

  return (
    <div
      role="status"
      className="border-b border-amber-600/40 bg-amber-500/10 px-4 py-2 text-sm text-amber-100"
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2">
        <span>
          Please verify <strong>{user.email}</strong> — runs, audits, and admin actions are blocked
          until confirmation.
        </span>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={resend} disabled={sending}>
            {sending ? "Sending…" : "Resend email"}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setDismissed(true)}>
            Dismiss
          </Button>
          <Button size="sm" variant="ghost" onClick={() => void signOut()}>
            Sign out
          </Button>
        </div>
      </div>
    </div>
  );
}
