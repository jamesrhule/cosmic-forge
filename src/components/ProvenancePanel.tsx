/**
 * QCompass — Provenance panel.
 *
 * Always visible on every run-detail page across all 8 domains.
 * Renders fields from `RunResult.provenance` and degrades gracefully
 * when fields are missing (cosmology runs lack most).
 *
 * @example
 *   <ProvenancePanel provenance={run.provenance} />
 */
import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronRight, AlertTriangle } from "lucide-react";
import type { ProvenanceRecordExt } from "@/lib/domains/types";

export interface ProvenancePanelProps {
  provenance: ProvenanceRecordExt | null | undefined;
}

function isStale(iso: string | null | undefined): boolean {
  if (!iso) return false;
  const t = new Date(iso).getTime();
  return Number.isFinite(t) && Date.now() - t > 24 * 3600 * 1000;
}

function shortHash(h: string | null | undefined): string {
  if (!h) return "—";
  return h.length > 12 ? `${h.slice(0, 8)}…${h.slice(-4)}` : h;
}

export function ProvenancePanel({ provenance }: ProvenancePanelProps) {
  const [emOpen, setEmOpen] = useState(false);
  const p = provenance ?? {};
  const hasAnything =
    p.classical_reference_hash ||
    p.device_calibration_hash ||
    p.error_mitigation_config ||
    p.resource_estimate ||
    (p.transforms_applied && p.transforms_applied.length) ||
    p.model_domain ||
    p.provenance_warning;

  if (!hasAnything) {
    return (
      <Card className="p-3 text-xs text-muted-foreground">
        No provenance metadata recorded for this run (typical for
        classical-CPU cosmology runs).
      </Card>
    );
  }

  return (
    <Card className="space-y-3 p-4 text-sm">
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
          Provenance
        </h3>
        {p.model_domain && (
          <Badge variant="secondary" className="font-mono text-[11px]">
            model_domain · {p.model_domain}
          </Badge>
        )}
      </div>

      {p.provenance_warning && (
        <Alert variant="destructive">
          <AlertTriangle className="size-4" />
          <AlertTitle>Provenance warning</AlertTitle>
          <AlertDescription>{p.provenance_warning}</AlertDescription>
        </Alert>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Classical reference">
          <code className="font-mono text-xs">{shortHash(p.classical_reference_hash)}</code>
        </Field>
        <Field label="Device calibration">
          <code className="font-mono text-xs">{shortHash(p.device_calibration_hash)}</code>
          {isStale(p.device_calibration_at) && (
            <Badge variant="destructive" className="ml-2 text-[10px]">
              stale &gt; 24h
            </Badge>
          )}
        </Field>
        {p.resource_estimate && (
          <Field label="Resource estimate">
            <span className="font-mono text-xs">
              {p.resource_estimate.logical_qubits ?? "—"}L /{" "}
              {p.resource_estimate.physical_qubits ?? "—"}P /{" "}
              {p.resource_estimate.wallclock_s ?? "—"}s
            </span>
          </Field>
        )}
        {p.transforms_applied && p.transforms_applied.length > 0 && (
          <Field label="Transforms">
            <div className="flex flex-wrap gap-1">
              {p.transforms_applied.map((t) => (
                <Badge key={t} variant="outline" className="font-mono text-[10px]">
                  {t}
                </Badge>
              ))}
            </div>
          </Field>
        )}
      </div>

      {p.error_mitigation_config && (
        <Collapsible open={emOpen} onOpenChange={setEmOpen}>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
            <ChevronRight
              className={`size-3 transition-transform ${emOpen ? "rotate-90" : ""}`}
            />
            Error mitigation config
          </CollapsibleTrigger>
          <CollapsibleContent>
            <pre className="mt-2 overflow-auto rounded border bg-muted p-2 font-mono text-[11px]">
              {JSON.stringify(p.error_mitigation_config, null, 2)}
            </pre>
          </CollapsibleContent>
        </Collapsible>
      )}
    </Card>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <div className="flex items-center">{children}</div>
    </div>
  );
}
