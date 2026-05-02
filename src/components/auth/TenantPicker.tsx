/**
 * QCompass — Tenant picker dropdown (scaffolding).
 * @example <TenantPicker />
 */
import { useEffect, useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/store/auth";
import { listTenants, type Tenant } from "@/services/qcompass/auth";

export function TenantPicker() {
  const tenantId = useAuth((s) => s.tenantId);
  const setTenant = useAuth((s) => s.setTenant);
  const [tenants, setTenants] = useState<Tenant[]>([]);

  useEffect(() => {
    listTenants().then(setTenants).catch(() => setTenants([]));
  }, []);

  return (
    <Select value={tenantId ?? undefined} onValueChange={(v) => setTenant(v)}>
      <SelectTrigger className="h-7 w-48 text-xs">
        <SelectValue placeholder="Select tenant" />
      </SelectTrigger>
      <SelectContent>
        {tenants.map((t) => (
          <SelectItem key={t.id} value={t.id} className="text-xs">
            {t.label} · <span className="text-muted-foreground">{t.role}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
