import { useState } from "react";
import { Download, MessageSquare, PlayCircle, RotateCcw, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { ArxivLink } from "@/components/arxiv-link";
import { Sci } from "@/components/sci";
import { configToYaml } from "@/lib/configYaml";
import { kawaiKimDefaults } from "@/lib/configDefaults";
import { startRun } from "@/services/simulator";
import { useChat } from "@/store/ui";
import type { BenchmarkEntry, RunConfig } from "@/types/domain";

export interface ActionsRailProps {
  config: RunConfig;
  benchmarks: BenchmarkEntry[];
  canRun: boolean;
  onLoadConfig: (next: RunConfig) => void;
}

export function ActionsRail({
  config,
  benchmarks,
  canRun,
  onLoadConfig,
}: ActionsRailProps) {
  const [submitting, setSubmitting] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const addContext = useChat((s) => s.addContext);
  const openChat = useChat((s) => s.setOpen);

  const onRun = async () => {
    setSubmitting(true);
    try {
      const { runId } = await startRun(config);
      toast.success("Run queued", {
        description: `Streaming events for ${runId}…`,
      });
    } catch (err) {
      toast.error("Failed to enqueue run", {
        description: err instanceof Error ? err.message : "Unknown error",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const onExport = () => {
    const yaml = configToYaml(config);
    const blob = new Blob([yaml], { type: "text/yaml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ucgle-config-${Date.now()}.yaml`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast.success("Config exported");
  };

  const onRestoreV2 = () => {
    onLoadConfig(kawaiKimDefaults());
    toast.success("Restored V2 (Kawai-Kim) defaults");
  };

  const onAskAssistant = () => {
    addContext({
      kind: "config",
      label: `${config.potential.kind} · ξ=${config.couplings.xi.toExponential(2)}`,
      config,
    });
    openChat(true);
    toast.message("Config attached to chat");
  };

  return (
    <div className="sticky top-4 space-y-2">
      <Button
        type="button"
        size="lg"
        className="w-full justify-start gap-2"
        disabled={!canRun || submitting}
        onClick={onRun}
      >
        <PlayCircle className="h-4 w-4" />
        {submitting ? "Queueing…" : "Run simulation"}
      </Button>

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetTrigger asChild>
          <Button type="button" variant="outline" className="w-full justify-start gap-2">
            <Sparkles className="h-4 w-4" />
            Load from benchmark
          </Button>
        </SheetTrigger>
        <SheetContent className="w-[480px] sm:max-w-[480px]">
          <SheetHeader>
            <SheetTitle>Benchmark catalog</SheetTitle>
            <SheetDescription>
              Click a benchmark to populate the form with its canonical
              configuration.
            </SheetDescription>
          </SheetHeader>
          <ul className="mt-4 space-y-2 overflow-y-auto pr-1">
            {benchmarks.map((b) => (
              <li key={b.id}>
                <button
                  type="button"
                  onClick={() => {
                    onLoadConfig(b.config);
                    setSheetOpen(false);
                    toast.success(`Loaded ${b.label}`);
                  }}
                  className="w-full rounded-md border bg-card p-3 text-left text-sm transition hover:border-primary hover:bg-accent/50"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="font-medium">{b.label}</div>
                      <div className="mt-0.5 text-xs text-muted-foreground">
                        {b.description}
                      </div>
                    </div>
                    <ArxivLink id={b.arxivId} />
                  </div>
                  <div className="mt-2 flex items-center gap-3 text-[11px] text-muted-foreground">
                    <span>
                      η_B target: <Sci value={b.expectedEta_B} sig={2} />
                    </span>
                    <span>·</span>
                    <span className="font-mono">{b.config.potential.kind}</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </SheetContent>
      </Sheet>

      <Button
        type="button"
        variant="outline"
        className="w-full justify-start gap-2"
        onClick={onExport}
      >
        <Download className="h-4 w-4" />
        Export config (YAML)
      </Button>

      <Button
        type="button"
        variant="outline"
        className="w-full justify-start gap-2"
        onClick={onAskAssistant}
      >
        <MessageSquare className="h-4 w-4" />
        Ask assistant
      </Button>

      <Separator />

      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="w-full justify-start gap-2 text-muted-foreground"
        onClick={onRestoreV2}
      >
        <RotateCcw className="h-3.5 w-3.5" />
        Restore V2 defaults
      </Button>
    </div>
  );
}
