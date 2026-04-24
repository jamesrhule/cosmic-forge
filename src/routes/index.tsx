import { createFileRoute, Link, useLoaderData } from "@tanstack/react-router";
import { useDeferredValue, useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ThemeToggle } from "@/components/theme-toggle";
import { UserMenu } from "@/components/user-menu";
import { DomainSelector } from "@/components/domain-selector";
import { FEATURES } from "@/config/features";

const IS_DEV = import.meta.env.DEV;
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "@/components/ui/resizable";
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
      { property: "og:title", content: "Configurator — UCGLE-F1 Workbench" },
      {
        property: "og:description",
        content:
          "Configure a gravitational-leptogenesis run: potential, GB/CS couplings, seesaw sector, reheating.",
      },
      { property: "og:url", content: "/" },
      { name: "twitter:title", content: "Configurator — UCGLE-F1 Workbench" },
      {
        name: "twitter:description",
        content:
          "Configure a gravitational-leptogenesis run: potential, GB/CS couplings, seesaw sector, reheating.",
      },
    ],
  }),
  loader: async (): Promise<{ benchmarks: BenchmarkIndex }> => {
    try {
      const benchmarks = await getBenchmarks();
      return { benchmarks };
    } catch (err) {
      // Toast is best-effort — on SSR sonner becomes a no-op, which is
      // fine; the route's errorComponent still renders.
      const { notifyServiceError } = await import("@/lib/serviceErrors");
      notifyServiceError(err, "benchmarks");
      throw err;
    }
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
        {IS_DEV && (
          <span className="rounded-full border bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
            dev build
          </span>
        )}
        {FEATURES.domainsRegistry && <DomainSelector />}
        <nav className="ml-6 hidden items-center gap-1 md:flex">
          <NavTab to="/" exact>
            Configurator
          </NavTab>
          {IS_DEV && (
            <>
              <NavTab to="/qa" search={{ tab: "control" }}>
                Control
              </NavTab>
              <NavTab to="/qa" search={{ tab: "research" }}>
                Research
              </NavTab>
            </>
          )}
        </nav>
        <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
          <Link
            to="/visualizer"
            className="rounded-md border px-2 py-1 font-mono text-[11px] hover:bg-muted"
          >
            /visualizer
          </Link>
          {IS_DEV && (
            <Link
              to="/qa"
              className="rounded-md border px-2 py-1 font-mono text-[11px] hover:bg-muted"
            >
              /qa
            </Link>
          )}
          <ThemeToggle />
          <UserMenu redirectPath="/" />
        </div>
      </header>

      <main className="flex-1">
        <Configurator benchmarks={benchmarks.benchmarks} />
      </main>

      <footer className="border-t px-6 py-3 text-[11px] text-muted-foreground">
        UCGLE-F1 Workbench · {IS_DEV ? "dev build" : "v1.0"} · see README for
        handoff contract
      </footer>
    </div>
  );
}

type NavTabProps =
  | {
      to: "/";
      exact?: boolean;
      search?: never;
      children: React.ReactNode;
    }
  | {
      to: "/qa";
      exact?: boolean;
      search?: { tab: "configurator" | "control" | "research" | "checklist" };
      children: React.ReactNode;
    };

function NavTab({ to, exact, search, children }: NavTabProps) {
  const base = "rounded-md px-3 py-1.5 text-sm transition text-muted-foreground hover:bg-muted";
  const active = "rounded-md px-3 py-1.5 text-sm bg-accent text-accent-foreground";
  if (to === "/qa") {
    return (
      <Link
        to="/qa"
        search={search}
        activeOptions={{ exact: exact ?? false, includeSearch: !!search }}
        className={base}
        activeProps={{ className: active }}
      >
        {children}
      </Link>
    );
  }
  return (
    <Link
      to="/"
      activeOptions={{ exact: exact ?? false }}
      className={base}
      activeProps={{ className: active }}
    >
      {children}
    </Link>
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
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>
            The Configurator uses a three-column layout that needs at least
            1024px. Open this app on a desktop browser or expand the window.
          </p>
          <p>
            In the meantime, the{" "}
            <Link to="/visualizer" className="text-primary hover:underline">
              Visualizer
            </Link>{" "}
            renders on smaller screens — pick a run and replay its
            six-panel timeline.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function Configurator({ benchmarks }: { benchmarks: BenchmarkIndex["benchmarks"] }) {
  const isWide = useMediaQuery("(min-width: 1024px)");
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

  const formCards = (
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
  );

  const previews = (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Configurator</h1>
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
          <CardTitle className="text-sm font-medium">F1 — primary mechanism</CardTitle>
        </CardHeader>
        <CardContent>
          <EquationBlock copyable latex={f1Latex} />
          <p className="mt-2 text-[11px] text-muted-foreground">
            Numeric placeholders update as you edit couplings.{" "}
            <span className="font-mono">⟨RR̃⟩_Ψ</span> is computed by the backend from the
            chosen V(Ψ) and the GB/CS sector.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Active context</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <ContextChip
            kind="config"
            label={`${deferred.potential.kind} · ${deferred.precision}`}
          />
          <ContextChip kind="benchmark" label={`${benchmarks.length} benchmarks available`} />
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
  );

  const actions = (
    <ActionsRail
      config={deferred}
      benchmarks={benchmarks}
      canRun={canRun}
      onLoadConfig={(next) => reset(next, { keepDirty: false, keepTouched: false })}
    />
  );

  // Narrow viewports stack the three columns vertically. The resizable
  // splitter UX requires real estate that simply doesn't exist below
  // 1024px, so we trade it for a scrollable single-column layout that
  // still surfaces every section in the same order.
  if (!isWide) {
    return (
      <div className="flex flex-col gap-4 px-4 py-4 sm:px-6">
        <div>{actions}</div>
        <div>{previews}</div>
        <div className="rounded-md bg-muted/30 p-3">{formCards}</div>
      </div>
    );
  }

  return (
    <ResizablePanelGroup orientation="horizontal" className="min-h-[calc(100vh-3.5rem-2.5rem)]">
      {/* LEFT: form cards */}
      <ResizablePanel defaultSize={28} minSize={22} maxSize={40}>
        <div className="h-full overflow-y-auto border-r bg-muted/30 p-4">{formCards}</div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      {/* CENTER: previews */}
      <ResizablePanel defaultSize={50} minSize={36}>
        <div className="h-full overflow-y-auto px-6 py-5">{previews}</div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      {/* RIGHT: actions */}
      <ResizablePanel defaultSize={22} minSize={18} maxSize={32}>
        <div className="h-full overflow-y-auto p-4">{actions}</div>
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
    <AccordionItem value={value} className="overflow-hidden rounded-md border bg-card">
      <AccordionTrigger className="px-3 py-2 text-sm font-medium hover:no-underline">
        {title}
      </AccordionTrigger>
      <AccordionContent className="border-t bg-background px-3 py-3">{children}</AccordionContent>
    </AccordionItem>
  );
}

function flattenErrors(errors: unknown, prefix = ""): { path: string; message: string }[] {
  const out: { path: string; message: string }[] = [];
  if (!errors || typeof errors !== "object") return out;
  for (const [key, val] of Object.entries(errors as Record<string, unknown>)) {
    if (
      val &&
      typeof val === "object" &&
      "message" in val &&
      typeof (val as { message?: unknown }).message === "string"
    ) {
      out.push({ path: `${prefix}${key}`, message: (val as { message: string }).message });
    } else if (val && typeof val === "object") {
      out.push(...flattenErrors(val, `${prefix}${key}.`));
    }
  }
  return out;
}
