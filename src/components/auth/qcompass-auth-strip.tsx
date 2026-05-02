/**
 * QCompass — Auth strip rendered in __root when qcompassAuth is on.
 *
 * @example
 *   {FEATURES.qcompassAuth && <QCompassAuthStrip />}
 */
import { useState } from "react";
import { useAuth } from "@/store/auth";
import { TokenInput } from "./TokenInput";
import { TenantPicker } from "./TenantPicker";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function QCompassAuthStrip() {
  const token = useAuth((s) => s.token);
  const tenantId = useAuth((s) => s.tenantId);
  const signOut = useAuth((s) => s.signOut);
  const [tokenOpen, setTokenOpen] = useState(false);

  return (
    <div className="flex items-center gap-2 border-b bg-muted/30 px-3 py-1 text-xs">
      <span className="font-mono text-muted-foreground">QCompass auth</span>
      <Badge variant={token ? "secondary" : "outline"} className="font-mono text-[10px]">
        token · {token ? "set" : "—"}
      </Badge>
      <TenantPicker />
      <Button size="sm" variant="ghost" onClick={() => setTokenOpen(true)}>
        {token ? "Change token" : "Set token"}
      </Button>
      {(token || tenantId) && (
        <Button size="sm" variant="ghost" onClick={signOut}>
          Sign out
        </Button>
      )}
      <TokenInput open={tokenOpen} onOpenChange={setTokenOpen} />
    </div>
  );
}
