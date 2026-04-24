import { createFileRoute, Link, Outlet, useRouter } from "@tanstack/react-router";
import { zodValidator } from "@tanstack/zod-adapter";
import { listVisualizationRunIds } from "@/services/visualizer";
import { visualizerSearchSchema } from "@/lib/visualizerSearch";
import { ErrorPage } from "@/components/error-page";
import { Button } from "@/components/ui/button";
import { UserMenu } from "@/components/user-menu";

/**
 * `/visualizer` parent route.
 *
 * Owns the shared search-param schema (inherited by `$runId`) and a
 * lightweight loader that returns the list of runs for which a baked
 * visualization fixture exists. The R3F / Recharts / KaTeX bundle is
 * NOT pulled in here — only the index card grid is rendered.
 */
export const Route = createFileRoute("/visualizer")({
  head: () => ({
    meta: [
      { title: "Visualizer — UCGLE-F1 Workbench" },
      {
        name: "description",
        content:
          "Particle, GB window, SGWB, anomaly, lepton flow, and formula panels for completed UCGLE-F1 runs.",
      },
      { property: "og:title", content: "Visualizer — UCGLE-F1 Workbench" },
      {
        property: "og:description",
        content:
          "Replay and compare completed gravitational-leptogenesis runs across six synchronized panels.",
      },
      { property: "og:url", content: "/visualizer" },
      { name: "twitter:title", content: "Visualizer — UCGLE-F1 Workbench" },
      {
        name: "twitter:description",
        content:
          "Replay and compare completed gravitational-leptogenesis runs across six synchronized panels.",
      },
    ],
  }),
  validateSearch: zodValidator(visualizerSearchSchema),
  loader: async (): Promise<{ runIds: string[] }> => ({
    runIds: listVisualizationRunIds(),
  }),
  component: VisualizerLayoutRoute,
  errorComponent: VisualizerErrorComponent,
  notFoundComponent: VisualizerNotFoundComponent,
});

function VisualizerLayoutRoute() {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-20 flex h-14 items-center gap-4 border-b bg-background/80 px-6 backdrop-blur">
        <Link to="/" className="font-semibold tracking-tight">
          UCGLE-F1 Workbench
        </Link>
        <span className="rounded-full border bg-muted px-2 py-0.5 font-mono text-[11px] text-muted-foreground">
          visualizer
        </span>
        <nav className="ml-6 hidden items-center gap-1 md:flex">
          <Link
            to="/"
            activeOptions={{ exact: true }}
            className="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted"
            activeProps={{
              className: "rounded-md px-3 py-1.5 text-sm bg-accent text-accent-foreground",
            }}
          >
            Configurator
          </Link>
          <Link
            to="/visualizer"
            activeOptions={{ exact: true }}
            className="rounded-md px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted"
            activeProps={{
              className: "rounded-md px-3 py-1.5 text-sm bg-accent text-accent-foreground",
            }}
          >
            Visualizer
          </Link>
        </nav>
        <div className="ml-auto flex items-center gap-3 text-xs text-muted-foreground">
          {import.meta.env.DEV && (
            <Link
              to="/qa"
              className="rounded-md border px-2 py-1 font-mono text-[11px] hover:bg-muted"
            >
              /qa
            </Link>
          )}
          <UserMenu redirectPath="/visualizer" />
        </div>
      </header>
      <main className="flex-1 min-h-0">
        <Outlet />
      </main>
    </div>
  );
}

function VisualizerErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  const router = useRouter();
  return (
    <ErrorPage
      eyebrow="Visualizer"
      title="Visualizer failed to load"
      description="The selected run couldn't be opened. Try again, or pick a different run from the index."
      errorMessage={error.message}
      primaryAction={
        <>
          <Button
            onClick={() => {
              router.invalidate();
              reset();
            }}
          >
            Retry
          </Button>
          <Button asChild variant="outline">
            <Link to="/visualizer">Back to runs</Link>
          </Button>
        </>
      }
    />
  );
}

function VisualizerNotFoundComponent() {
  return (
    <ErrorPage
      eyebrow="Visualizer"
      title="Run not found"
      description="The visualizer surface you requested doesn't exist. Pick a different run from the index."
      primaryAction={
        <Button asChild>
          <Link to="/visualizer">Back to runs</Link>
        </Button>
      }
    />
  );
}
