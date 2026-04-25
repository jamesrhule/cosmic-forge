import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type {
  ProvenanceRecord,
  ResourceEstimate,
} from "@/types/qcompass";

interface ProvenancePanelProps {
  provenance: ProvenanceRecord;
  warning?: "no_classical_reference" | null;
}

export function ProvenancePanel({ provenance, warning }: ProvenancePanelProps) {
  const {
    classical_reference_hash,
    device_calibration_hash,
    error_mitigation_config,
    resource_estimate,
    recorded_at,
  } = provenance;

  const isUnavailable = classical_reference_hash === "unavailable";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Provenance</span>
          {isUnavailable && (
            <Badge variant="outline" className="text-[11px]">
              no classical reference
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {warning === "no_classical_reference" && (
          <Alert variant="default" className="border-yellow-500/40 bg-yellow-500/10">
            <AlertTitle className="text-sm">Qualitative result only</AlertTitle>
            <AlertDescription className="text-xs">
              No classical reference is feasible at this scale (e.g. Reiher-2017
              FeMoco active space). The audit accepts this as a documented
              exception; downstream analyses should treat the energy as
              qualitative.
            </AlertDescription>
          </Alert>
        )}

        <dl className="grid grid-cols-1 gap-3 text-xs md:grid-cols-2">
          <Field label="classical_reference_hash" value={classical_reference_hash} mono />
          <Field
            label="device_calibration_hash"
            value={device_calibration_hash ?? "—"}
            mono
          />
          <Field label="recorded_at" value={recorded_at} />
          <Field
            label="error_mitigation_config"
            value={
              error_mitigation_config && Object.keys(error_mitigation_config).length > 0
                ? JSON.stringify(error_mitigation_config)
                : "—"
            }
            mono
          />
        </dl>

        {resource_estimate && (
          <div className="rounded-md border bg-muted/20 p-3">
            <div className="mb-2 text-xs font-medium">Resource estimate</div>
            <ResourceEstimateView estimate={resource_estimate} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Field({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className={mono ? "truncate font-mono text-[11px]" : ""} title={value}>
        {value}
      </dd>
    </div>
  );
}

function ResourceEstimateView({ estimate }: { estimate: ResourceEstimate }) {
  return (
    <dl className="grid grid-cols-2 gap-2 text-[11px] md:grid-cols-3">
      <Field label="estimator" value={estimate.estimator} />
      <Field label="physical_qubits" value={String(estimate.physical_qubits)} mono />
      <Field label="logical_qubits" value={String(estimate.logical_qubits)} mono />
      <Field label="t_count" value={String(estimate.t_count)} mono />
      <Field label="depth" value={String(estimate.depth)} mono />
      <Field
        label="runtime_seconds"
        value={estimate.runtime_seconds.toFixed(2)}
        mono
      />
    </dl>
  );
}
