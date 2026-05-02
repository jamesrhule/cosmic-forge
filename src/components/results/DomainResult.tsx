/**
 * QCompass — Per-domain Result dispatcher.
 *
 * Reads `plugin.resultRendererId` and dispatches to the appropriate
 * domain Result component. Carve-outs (HEP, nuclear, gravity) ship
 * full implementations; others render a coming-online card that
 * still consumes the fixture's payload end-to-end.
 *
 * @example
 *   <DomainResult domainId="hep.lattice" run={run} />
 */
import type { DomainId, DomainRunResult } from "@/lib/domains/types";
import { ProvenancePanel } from "@/components/ProvenancePanel";
import { ProvenanceWarningBanner } from "@/components/ProvenanceWarningBanner";
import { ParticleObservablesTable } from "@/components/results/hep/ParticleObservablesTable";
import { NuclearObservablesTable } from "@/components/results/nuclear/NuclearObservablesTable";
import { ComingOnlineCard } from "@/components/qcompass-coming-online-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { AlertTriangle } from "lucide-react";

export interface DomainResultProps {
  domainId: DomainId;
  run: DomainRunResult;
}

export function DomainResult({ domainId, run }: DomainResultProps) {
  const payload = run.payload ?? {};
  const summary = (payload.summary as string | undefined) ?? "";

  // ─── CARVE-OUT 2: gravity provenance guard ─────────────────
  if (domainId === "gravity.syk") {
    if (run.is_learned_hamiltonian) {
      const warning = run.provenance.provenance_warning?.trim();
      if (!warning) {
        return (
          <Alert variant="destructive" data-testid="gravity-guard-blocked">
            <AlertTriangle className="size-5" />
            <AlertTitle>Render blocked — missing provenance warning</AlertTitle>
            <AlertDescription>
              This run has <code>is_learned_hamiltonian: true</code> but no
              <code> provenance_warning</code> was supplied. The gravity
              renderer refuses to display learned-Hamiltonian results
              without the required warning.
            </AlertDescription>
          </Alert>
        );
      }
      return (
        <div className="space-y-4" data-testid="gravity-result-with-warning">
          <ProvenanceWarningBanner
            warning={warning}
            arxivId={run.provenance.arxiv_reference}
          />
          <ComingOnlineCard
            title="Gravity · learned-SYK surrogate"
            description={summary}
            fields={[
              { label: "Domain", value: run.domain },
              { label: "Status", value: run.status },
            ]}
          />
          <ProvenancePanel provenance={run.provenance} />
        </div>
      );
    }
    return (
      <div className="space-y-4" data-testid="gravity-result">
        <ComingOnlineCard
          title="Gravity · SYK / JT"
          description={summary}
          fields={[
            { label: "Domain", value: run.domain },
            { label: "Status", value: run.status },
          ]}
        />
        <ProvenancePanel provenance={run.provenance} />
      </div>
    );
  }

  // ─── CARVE-OUT 1a: HEP ─────────────────────────────────────
  if (domainId === "hep.lattice") {
    return (
      <div className="space-y-4">
        <ParticleObservablesTable obs={run.particle_obs} />
        <ProvenancePanel provenance={run.provenance} />
      </div>
    );
  }

  // ─── CARVE-OUT 1b: Nuclear ─────────────────────────────────
  if (domainId === "nuclear.structure") {
    return (
      <div className="space-y-4">
        <NuclearObservablesTable
          obs={run.particle_obs}
          modelDomain={run.model_domain}
        />
        <ProvenancePanel provenance={run.provenance} />
      </div>
    );
  }

  // ─── Other domains: coming-online card consuming fixture ───
  const fields = Object.entries(payload)
    .filter(([k, v]) => k !== "summary" && (typeof v === "number" || typeof v === "string"))
    .slice(0, 6)
    .map(([k, v]) => ({ label: k, value: v as number | string }));

  return (
    <div className="space-y-4">
      <ComingOnlineCard
        title={run.label}
        description={summary || `${domainId} run`}
        fields={fields.length > 0 ? fields : [{ label: "Status", value: run.status }]}
      />
      <ProvenancePanel provenance={run.provenance} />
    </div>
  );
}
