import { useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { loadFixture } from "@/lib/fixtures";
import { FormulaListShape } from "@/lib/fixtureSchemas";
import { Math as MathBlock } from "@/components/math";
import { EmptyPanel } from "@/components/visualizer/empty-panel";
import { DataErrorPanel } from "@/components/data-error-panel";
import { PanelContextMenu } from "@/components/visualizer/panel-context-menu";
import { useVisualizerStore } from "@/store/visualizer";
import { notifyServiceError, dismissServiceError, toUserError } from "@/lib/serviceErrors";
import { cn } from "@/lib/utils";
import { annotateLatex } from "@/lib/annotateLatex";
import type { BakedVisualizationTimeline, FormulaVariant } from "@/types/visualizer";

export interface FormulaOverlayProps {
  timelineA: BakedVisualizationTimeline | null;
  timelineB?: BakedVisualizationTimeline | null;
}

interface FormulaEntry {
  id: FormulaVariant;
  name: string;
  latex: string;
  notes?: string;
}

/**
 * Panel 6 — annotated formula.
 *
 * Renders the active F-variant's LaTeX with `\htmlId{<term>}` wrappers
 * around the terms listed in `meta.visualizationHints.formulaTermIds`.
 * Terms appearing in the current frame's `active_terms` glow indigo via
 * the `formula-glow` keyframe (defined in styles.css).
 *
 * KaTeX renders synchronously into the DOM; a post-render effect walks
 * the wrapper and toggles `data-active="true"` on the matching nodes.
 * That keeps the formula HTML stable across renders — only the data
 * attribute changes, so we don't pay the KaTeX re-layout cost on every
 * frame.
 */
export function FormulaOverlay({ timelineA, timelineB }: FormulaOverlayProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const frameIdx = useVisualizerStore((s) => s.currentFrameIndex);

  const {
    data: formulas,
    error: formulasError,
    refetch: refetchFormulas,
  } = useQuery<FormulaEntry[]>({
    queryKey: ["formulas-F1-F7"],
    queryFn: () =>
      loadFixture<FormulaEntry[]>("formulas/F1-F7.json", {
        validate: (raw) => FormulaListShape.parse(raw) as unknown as FormulaEntry[],
      }),
    staleTime: Infinity,
    retry: 1,
  });

  // Surface fixture-load failures as a sonner toast (deduped via stable
  // scope id) AND in-place via the DataErrorPanel below — so the user
  // is never left staring at an empty panel.
  useEffect(() => {
    if (!formulasError) return;
    notifyServiceError(formulasError, "formulas");
  }, [formulasError]);

  const variant = timelineA?.formulaVariant ?? null;
  const formula = useMemo(
    () => formulas?.find((f) => f.id === variant) ?? null,
    [formulas, variant],
  );

  const termIds = useMemo(
    () => timelineA?.meta.visualizationHints.formulaTermIds ?? [],
    [timelineA],
  );

  const annotatedTex = useMemo(() => {
    if (!formula) return "";
    return annotateLatex(formula.latex, termIds);
  }, [formula, termIds]);

  // Active-terms glow: read the active set from both timelines (so the
  // user sees an A↔B union when overlay is on).
  const activeTerms = useMemo(() => {
    const a = timelineA?.frames[frameIdx]?.active_terms ?? [];
    const b = timelineB?.frames[frameIdx]?.active_terms ?? [];
    return new Set([...a, ...b]);
  }, [timelineA, timelineB, frameIdx]);

  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;
    const nodes = el.querySelectorAll<HTMLElement>("[id^='vfx-']");
    for (const node of nodes) {
      const term = node.id.replace(/^vfx-/, "");
      if (activeTerms.has(term)) {
        node.setAttribute("data-active", "true");
      } else {
        node.removeAttribute("data-active");
      }
    }
  }, [activeTerms, annotatedTex]);

  if (formulasError) {
    const ue = toUserError(formulasError, "formulas");
    return (
      <PanelContextMenu panelId="formula" label="Formula" timelineA={timelineA}>
        <div className="h-full w-full">
          <DataErrorPanel
            title={ue.title}
            description={ue.description}
            onRetry={() => {
              dismissServiceError("formulas");
              void refetchFormulas();
            }}
            dense
          />
        </div>
      </PanelContextMenu>
    );
  }

  if (!timelineA || !formula) {
    return (
      <PanelContextMenu panelId="formula" label="Formula" timelineA={timelineA}>
        <div className="h-full w-full">
          <EmptyPanel
            title="Formula"
            reason={
              timelineA
                ? `No formula entry for variant ${variant ?? "?"}.`
                : "Pick a run to see the active F-formula."
            }
          />
        </div>
      </PanelContextMenu>
    );
  }

  return (
    <PanelContextMenu
      panelId="formula"
      label={`${formula.id} · ${formula.name}`}
      timelineA={timelineA}
      timelineB={timelineB}
    >
      <div
        ref={containerRef}
        className="flex h-full w-full flex-col gap-2 p-3"
        data-testid="visualizer-formula"
      >
        <header className="flex items-center justify-between text-[10px] font-mono text-muted-foreground">
          <span>
            {formula.id} · {formula.name}
          </span>
          <span>{activeTerms.size} active</span>
        </header>
        <div
          ref={wrapperRef}
          className={cn(
            "min-h-0 flex-1 overflow-auto rounded-md border border-border bg-card/60 p-3",
            "[&_[data-active='true']]:rounded-sm",
            "[&_[data-active='true']]:px-1",
            "[&_[data-active='true']]:[animation:formula-glow_0.6s_ease-out]",
            "[&_[data-active='true']]:bg-[color:var(--color-accent-indigo)]/10",
            "[&_[data-active='true']]:text-[color:var(--color-accent-indigo)]",
          )}
        >
          <MathBlock tex={annotatedTex} block />
        </div>
        {formula.notes ? (
          <p className="text-[11px] leading-snug text-muted-foreground">{formula.notes}</p>
        ) : null}
      </div>
    </PanelContextMenu>
  );
}

// `annotateLatex` lives in `src/lib/annotateLatex.ts` so it can be
// unit-tested without pulling in the React renderer.
