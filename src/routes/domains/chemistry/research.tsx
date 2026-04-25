import { createFileRoute } from "@tanstack/react-router";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export const Route = createFileRoute("/domains/chemistry/research")({
  component: ChemistryResearch,
});

function ChemistryResearch() {
  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          Chemistry research
        </h1>
        <p className="max-w-3xl text-sm text-muted-foreground">
          The chemistry research view is the chemistry-domain peer of the
          cosmology Research panel: methodology notes, audit (S-chem-1…5)
          summaries, and follow-up parameter scans. The agent integration
          for chemistry lands once the qcompass-router exposes a chemistry
          MCP-tool surface; for now this page documents the audit contract.
        </p>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>S-chem-* audit invariants</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <AuditRow
            id="S-chem-1"
            description="H₂ / STO-3G FCI within 1×10⁻⁸ Ha (classical path)."
            references={["doi:10.1007/978-3-319-16729-9"]}
          />
          <AuditRow
            id="S-chem-2"
            description="LiH / 6-31G DMRG within 1 mHa of CCSD(T)."
            references={["block2 v0.5.x"]}
          />
          <AuditRow
            id="S-chem-3"
            description="N₂ / cc-pVDZ CCSD(T) at re=1.0975 Å within chemical accuracy (1.6 mHa)."
            references={["NIST CCCBDB"]}
          />
          <AuditRow
            id="S-chem-4"
            description="H₂ SQD on noise-free Aer recovers FCI within 1×10⁻⁶ Ha."
            references={["qiskit-addon-sqd"]}
          />
          <AuditRow
            id="S-chem-5"
            description="ProvenanceRecord present + classical_reference_hash recorded for every dispatch path. FeMoco-toy uses the documented sentinel."
            references={[]}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Reference instances</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm">
            <li>
              <code className="font-mono">h2.yaml</code> — H₂ / STO-3G,
              backend_preference=auto, FCI reference.
            </li>
            <li>
              <code className="font-mono">lih.yaml</code> — LiH / 6-31G,
              backend_preference=classical, DMRG reference.
            </li>
            <li>
              <code className="font-mono">n2.yaml</code> — N₂ / cc-pVDZ,
              backend_preference=classical, CCSD(T) reference.
            </li>
            <li>
              <code className="font-mono">femoco_toy.yaml</code> —
              Reiher-2017 (54e/54o) toy, backend_preference=dice,
              <em> qualitative only</em> (no classical reference).
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function AuditRow({
  id,
  description,
  references,
}: {
  id: string;
  description: string;
  references: string[];
}) {
  return (
    <div className="flex items-start gap-3 border-b py-2 last:border-b-0">
      <code className="shrink-0 rounded bg-muted px-1.5 py-0.5 font-mono text-[11px]">
        {id}
      </code>
      <div className="flex-1">
        <div>{description}</div>
        {references.length > 0 && (
          <div className="mt-1 text-[11px] text-muted-foreground">
            {references.join(" · ")}
          </div>
        )}
      </div>
    </div>
  );
}
