import { createFileRoute, notFound } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { FEATURES } from "@/config/features";
import { useAuth } from "@/store/auth";
import { getVerdictReport, type VerdictReport } from "@/services/qcompass/verdict";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const ADMIN_TENANT_ID = "tenant-admin";

export const Route = createFileRoute("/admin/verdict")({
  beforeLoad: () => {
    if (!FEATURES.qcompassMultiDomain || !FEATURES.qcompassAuth) {
      throw notFound();
    }
  },
  component: VerdictPage,
  head: () => ({ meta: [{ title: "Verdict · QCompass admin" }] }),
});

function VerdictPage() {
  const tenantId = useAuth((s) => s.tenantId);
  const [report, setReport] = useState<VerdictReport | null>(null);

  useEffect(() => {
    if (tenantId === ADMIN_TENANT_ID) {
      getVerdictReport().then(setReport).catch(() => setReport(null));
    }
  }, [tenantId]);

  if (tenantId !== ADMIN_TENANT_ID) {
    return (
      <div className="mx-auto max-w-2xl p-6" data-testid="verdict-blocked">
        <h1 className="text-xl font-semibold">Admin only</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Switch to the QCompass admin tenant to view the Phase-3 verdict
          report.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">QCompass · Phase-3 verdict</h1>
      {!report ? (
        <p className="text-xs text-muted-foreground">Loading…</p>
      ) : (
        <Card className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/40 text-xs uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left">Domain</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {report.rows.map((r) => (
                <tr key={r.domain} className="border-t">
                  <td className="px-3 py-2 font-mono text-xs">{r.domain}</td>
                  <td className="px-3 py-2">
                    <Badge
                      variant={
                        r.status === "DELIVERED"
                          ? "default"
                          : r.status === "FAILED"
                            ? "destructive"
                            : "secondary"
                      }
                    >
                      {r.status}
                    </Badge>
                  </td>
                  <td className="px-3 py-2 text-xs">
                    <ul className="list-disc pl-4">
                      {r.evidence.map((e, i) => (
                        <li key={i}>{e}</li>
                      ))}
                    </ul>
                    {r.audit_archive_url && (
                      <a
                        href={r.audit_archive_url}
                        className="text-primary hover:underline"
                        target="_blank"
                        rel="noreferrer"
                      >
                        audit archive ↗
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
