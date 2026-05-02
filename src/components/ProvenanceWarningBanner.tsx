/**
 * QCompass — Provenance warning banner.
 *
 * Big red banner used by the gravity domain (and any future domain
 * with `requiresProvenanceWarning: true`) for runs flagged
 * `is_learned_hamiltonian === true`. The Result renderer REFUSES to
 * render the rest of the view if required and warning is empty.
 *
 * @example
 *   <ProvenanceWarningBanner warning={p.provenance_warning} arxivId={p.arxiv_reference} />
 */
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ArxivLink } from "@/components/arxiv-link";
import { AlertTriangle } from "lucide-react";

export interface ProvenanceWarningBannerProps {
  warning: string;
  arxivId?: string | null;
}

export function ProvenanceWarningBanner({ warning, arxivId }: ProvenanceWarningBannerProps) {
  return (
    <Alert variant="destructive" className="border-2">
      <AlertTriangle className="size-5" />
      <AlertTitle className="text-base font-semibold">
        Provenance warning — not a first-principles simulation
      </AlertTitle>
      <AlertDescription className="space-y-2">
        <p>{warning}</p>
        {arxivId && (
          <div className="pt-1">
            <ArxivLink id={arxivId} />
          </div>
        )}
      </AlertDescription>
    </Alert>
  );
}
