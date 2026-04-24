import { createFileRoute, Link, useLoaderData } from "@tanstack/react-router";
import { useDeferredValue, useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Toaster } from "@/components/ui/sonner";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMediaQuery } from "@/hooks/use-media-query";
import { EquationBlock } from "@/components/equation-block";
import { ValidityLight } from "@/components/validity-light";
import { CostBadge } from "@/components/cost-badge";
import { ContextChip } from "@/components/context-chip";
import { PotentialCard } from "@/components/configurator/PotentialCard";
import { CouplingsCard } from "@/components/configurator/CouplingsCard";
import { SeesawCard } from "@/components/configurator/SeesawCard";
import { ReheatingCard } from "@/components/configurator/ReheatingCard";
import { ActionsRail } from "@/components/configurator/ActionsRail";
import { kawaiKimDefaults } from "@/lib/configDefaults";
import { RunConfigSchema } from "@/lib/configSchema";
import { renderF1WithValues } from "@/lib/equationFormatter";
import { checkConfigValidity } from "@/lib/validity";
import { getBenchmarks } from "@/services/simulator";
import type { BenchmarkIndex, RunConfig } from "@/types/domain";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Configurator — UCGLE-F1 Workbench" },
      {
        name: "description",
        content:
          "Configure a gravitational-leptogenesis run: potential, GB/CS couplings, seesaw sector, reheating.",
      },
    ],
  }),
  loader: async (): Promise<{ benchmarks: BenchmarkIndex }> => {
    const benchmarks = await getBenchmarks();
    return { benchmarks };
  },
  component: ConfiguratorRoute,
});

function ConfiguratorRoute() {
  const { benchmarks } = useLoaderData({ from: "/" });

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-20 flex h-14 items-center gap-4 border-b bg-background/80 px-6 backdrop-blur">
        <Link to="/" className="font-semibold tracking-tight hover:underline">
          UCGLE-F1 Workbench
        </Link>
        <span className="rounded-full border bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
          static-shell
        </span>
        <nav className="ml-6 hidden items-center gap-1 md:flex">
          <NavTab to="/" exact>
            Configurator
          </NavTab>
          <NavTab to="/qa" search={{ tab: "control" }}>
            Control
          </NavTab>
          <NavTab to="/qa" search={{ tab: "research" }}>
            Research
          </NavTab>
        </nav>
        <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
          <Link
            to="/visualizer"
            className="rounded-md border px-2 py-1 font-mono text-[11px] hover:bg-muted"
          >
            /visualizer
          </Link>
          <Link
            to="/qa"
            className="rounded-md border px-2 py-1 font-mono text-[11px] hover:bg-muted"
          >
            /qa
          </Link>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--color-status-canceled)]" />
            fixture mode
          </span>
        </div>
      </header>

      <NarrowScreenGate>
        <main className="flex-1">
          <Configurator benchmarks={benchmarks.benchmarks} />
        </main>
      </NarrowScreenGate>

      <footer className="border-t px-6 py-3 text-[11px] text-muted-foreground">
        build static-shell-2025.04 · fixture mode · see README for handoff contract
      </footer>

      <Toaster richColors closeButton position="bottom-right" />
    </div>
  );
}

function NavTab({
  children,
  active,
}: {
  children: React.ReactNode;
  active?: boolean;
}) {
  return (
    <span
      className={
        "rounded-md px-3 py-1.5 text-sm transition " +
        (active
          ? "bg-accent text-accent-foreground"
          : "text-muted-foreground hover:bg-muted")
      }
    >
      {children}
    </span>
  );
}

function NarrowScreenGate({ children }: { children: React.ReactNode }) {
  const isWide = useMediaQuery("(min-width: 1024px)");

  if (isWide) return <>{children}</>;

  return (
    <div className="px-6 py-10">
      <Card>
        <CardHeader>
          <CardTitle>Designed for wide screens</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            The UCGLE-F1 Workbench Configurator uses a three-column layout
            that needs at least 1024px to render. Open this app on a desktop
            browser or expand the window.
          </p>
          <p>
            On a phone you can still browse runs (Control view) and the
            Research gallery, which both ship in later releases.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function Configurator({ benchmarks }: { benchmarks: BenchmarkIndex["benchmarks"] }) {
  const form = useForm<RunConfig>({
    resolver: zodResolver(RunConfigSchema),
    defaultValues: kawaiKimDefaults(),
    mode: "onChange",
  });

  const { control, watch, setValue, reset, formState } = form;
  const config = watch();
  const deferred = useDeferredValue(config);

  const validity = useMemo(() => checkConfigValidity(deferred), [deferred]);
  const f1Latex = useMemo(() => renderF1WithValues(deferred), [deferred]);

  const canRun = formState.isValid && validity.level !== "error";

  // Apply zod resolver once on mount so isValid reflects defaults.
  useEffect(() => {
    void form.trigger();
  }, [form]);

  return (
    <ResizablePanelGroup
      orientation="horizontal"
      className="min-h-[calc(100vh-3.5rem-2.5rem)]"
    >
      {/* LEFT: form cards */}
      <ResizablePanel defaultSize={28} minSize={22} maxSize={40}>
        <div className="h-full overflow-y-auto border-r bg-muted/30 p-4">
          <Accordion
            type="multiple"
            defaultValue={["potential", "couplings", "seesaw", "reheating"]}
            className="space-y-2"
          >
            <FormSection value="potential" title="Potential V(Ψ)">
              <PotentialCard
                control={control}
                watch={watch}
                setValue={setValue}
                errors={formState.errors}
              />
            </FormSection>
            <FormSection value="couplings" title="GB / CS couplings">
              <CouplingsCard control={control} watch={watch} setValue={setValue} />
            </FormSection>
            <FormSection value="seesaw" title="Seesaw sector">
              <SeesawCard control={control} />
            </FormSection>
            <FormSection value="reheating" title="Reheating & precision">
              <ReheatingCard control={control} />
            </FormSection>
          </Accordion>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      {/* CENTER: previews */}
      <ResizablePanel defaultSize={50} minSize={36}>
        <div className="h-full overflow-y-auto px-6 py-5">
          <div className="mx-auto max-w-3xl space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h1 className="text-lg font-semibold tracking-tight">
                  Configurator
                </h1>
                <p className="text-xs text-muted-foreground">
                  Build a `RunConfig` and submit it to the simulator.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <CostBadge config={deferred} />
                <ValidityLight result={validity} />
              </div>
            </div>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  F1 — primary mechanism
                </CardTitle>
              </CardHeader>
              <CardContent>
                <EquationBlock copyable latex={f1Latex} />
                <p className="mt-2 text-[11px] text-muted-foreground">
                  Numeric placeholders update as you edit couplings.{" "}
                  <span className="font-mono">⟨RR̃⟩_Ψ</span> is computed by the
                  backend from the chosen V(Ψ) and the GB/CS sector.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Active context
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                <ContextChip
                  kind="config"
                  label={`${deferred.potential.kind} · ${deferred.precision}`}
                />
                <ContextChip
                  kind="benchmark"
                  label={`${benchmarks.length} benchmarks available`}
                />
              </CardContent>
            </Card>

            {!formState.isValid && (
              <Card className="border-destructive/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-destructive">
                    Invalid configuration
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-xs">
                  {flattenErrors(formState.errors).map((e, i) => (
                    <div key={i}>
                      <span className="font-mono">{e.path}</span>
                      <span className="text-muted-foreground"> — {e.message}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      {/* RIGHT: actions */}
      <ResizablePanel defaultSize={22} minSize={18} maxSize={32}>
        <div className="h-full overflow-y-auto p-4">
          <ActionsRail
            config={deferred}
            benchmarks={benchmarks}
            canRun={canRun}
            onLoadConfig={(next) =>
              reset(next, { keepDirty: false, keepTouched: false })
            }
          />
        </div>
      </ResizablePanel>
    </ResizablePanelGroup>
  );
}

function FormSection({
  value,
  title,
  children,
}: {
  value: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <AccordionItem
      value={value}
      className="overflow-hidden rounded-md border bg-card"
    >
      <AccordionTrigger className="px-3 py-2 text-sm font-medium hover:no-underline">
        {title}
      </AccordionTrigger>
      <AccordionContent className="border-t bg-background px-3 py-3">
        {children}
      </AccordionContent>
    </AccordionItem>
  );
}

function flattenErrors(errors: unknown, prefix = ""): { path: string; message: string }[] {
  const out: { path: string; message: string }[] = [];
  if (!errors || typeof errors !== "object") return out;
  for (const [key, val] of Object.entries(errors as Record<string, unknown>)) {
    if (val && typeof val === "object" && "message" in val && typeof (val as { message?: unknown }).message === "string") {
      out.push({ path: `${prefix}${key}`, message: (val as { message: string }).message });
    } else if (val && typeof val === "object") {
      out.push(...flattenErrors(val, `${prefix}${key}.`));
    }
  }
  return out;
}
