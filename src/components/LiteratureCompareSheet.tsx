/**
 * QCompass — Literature comparison sheet.
 *
 * Opened from a row in <ParticleObservablesTable> or
 * <NuclearObservablesTable>. Overlays measured value with literature
 * references and a sigma score (color-blind safe: color + stroke).
 *
 * @example
 *   <LiteratureCompareSheet observable="chiral_condensate" measured={...} corpus="lattice-qcd" />
 */
import { useEffect, useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { ArxivLink } from "@/components/arxiv-link";
import { Sci } from "@/components/sci";
import {
  getLatticeQCDReferences,
  getNuclearReferences,
  type LiteratureReference,
} from "@/services/qcompass/literature";

export interface LiteratureCompareSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  observable: string;
  observableLabel: string;
  measured: { value: number; uncertainty: number; units: string };
  corpus: "lattice-qcd" | "nuclear";
}

function sigma(measuredValue: number, ref: LiteratureReference, measuredUnc: number): number {
  const denom = Math.sqrt(measuredUnc ** 2 + ref.uncertainty ** 2);
  if (denom === 0) return 0;
  return Math.abs(measuredValue - ref.value) / denom;
}

function sigmaTone(s: number): { color: string; pattern: string; label: string } {
  // Color-blind safe: color + stroke pattern + text label.
  if (s < 1) return { color: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300", pattern: "border-l-4 border-emerald-500", label: "consistent" };
  if (s < 2) return { color: "bg-amber-500/15 text-amber-700 dark:text-amber-300", pattern: "border-l-4 border-dashed border-amber-500", label: "tension" };
  return { color: "bg-red-500/15 text-red-700 dark:text-red-300", pattern: "border-l-4 border-dotted border-red-500", label: "discrepant" };
}

export function LiteratureCompareSheet({
  open,
  onOpenChange,
  observable,
  observableLabel,
  measured,
  corpus,
}: LiteratureCompareSheetProps) {
  const [refs, setRefs] = useState<LiteratureReference[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    const promise = corpus === "lattice-qcd" ? getLatticeQCDReferences() : getNuclearReferences();
    promise
      .then((r) => setRefs(r.filter((x) => x.observable === observable)))
      .finally(() => setLoading(false));
  }, [open, observable, corpus]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Literature comparison</SheetTitle>
          <SheetDescription>
            <span className="font-mono text-xs">{observableLabel}</span>
          </SheetDescription>
        </SheetHeader>

        <div className="mt-4 space-y-2">
          <div className="rounded border bg-muted/40 p-3 text-sm">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Measured</div>
            <div className="font-mono">
              <Sci value={measured.value} /> ± <Sci value={measured.uncertainty} />{" "}
              <span className="text-xs text-muted-foreground">{measured.units}</span>
            </div>
          </div>

          {loading && <p className="text-xs text-muted-foreground">Loading references…</p>}
          {!loading && refs.length === 0 && (
            <p className="text-xs text-muted-foreground">No literature references for this observable.</p>
          )}

          {refs.map((r) => {
            const s = sigma(measured.value, r, measured.uncertainty);
            const tone = sigmaTone(s);
            const delta = measured.value - r.value;
            return (
              <div key={r.arxiv_id + r.source_label} className={`rounded p-3 text-sm ${tone.pattern} ${tone.color}`}>
                <div className="flex items-center justify-between">
                  <div className="font-medium">{r.source_label}</div>
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {tone.label} · {s.toFixed(2)}σ
                  </Badge>
                </div>
                <div className="mt-1 font-mono text-xs">
                  <Sci value={r.value} /> ± <Sci value={r.uncertainty} /> {r.units}
                  <span className="ml-2 text-muted-foreground">
                    (Δ = <Sci value={delta} />)
                  </span>
                </div>
                <div className="mt-2">
                  <ArxivLink id={r.arxiv_id} />
                </div>
                {r.notes && <p className="mt-1 text-[11px] italic">{r.notes}</p>}
              </div>
            );
          })}
        </div>
      </SheetContent>
    </Sheet>
  );
}
