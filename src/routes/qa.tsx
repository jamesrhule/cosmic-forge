import { createFileRoute, useLoaderData, useSearch } from "@tanstack/react-router";
import { z } from "zod";
import { fallback, zodValidator } from "@tanstack/zod-adapter";
import { getRun, getScan } from "@/services/simulator";
import { QaShell, type QaTab } from "@/components/qa/qa-shell";
import type { RunResult, ScanResult } from "@/types/domain";

const tabSchema = z.enum(["configurator", "control", "research", "checklist"]);

const qaSearchSchema = z.object({
  tab: fallback(tabSchema, "configurator").default("configurator"),
});

export const Route = createFileRoute("/qa")({
  head: () => ({
    meta: [
      { title: "Chart resize QA — UCGLE-F1 Workbench" },
      {
        name: "description",
        content:
          "All-in-one harness reproducing the Configurator, Control, and Research layouts with the resize checklist and live chart-size badges.",
      },
      { name: "robots", content: "noindex,nofollow" },
    ],
  }),
  validateSearch: zodValidator(qaSearchSchema),
  loader: async (): Promise<{ runs: RunResult[]; scan: ScanResult }> => {
    const [a, b, scan] = await Promise.all([
      getRun("kawai-kim-natural"),
      getRun("starobinsky-standard"),
      getScan("xi-theta-64x64"),
    ]);
    return { runs: [a, b], scan };
  },
  component: QaRoute,
  errorComponent: ({ error, reset }) => (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold text-foreground">QA harness failed to load</h1>
        <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
        <button
          type="button"
          onClick={() => reset()}
          className="mt-4 inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Retry
        </button>
      </div>
    </div>
  ),
  notFoundComponent: () => (
    <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
      Not found.
    </div>
  ),
});

function QaRoute() {
  // The QA harness is an internal developer tool — exposing it on the
  // production build leaks a parallel UI surface that confuses users
  // and inflates indexable URLs (already noindexed, but still
  // reachable). Render the same 404 the root route uses when the
  // current build is not a dev build.
  if (!import.meta.env.DEV) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-4">
        <div className="max-w-md text-center">
          <h1 className="text-7xl font-bold text-foreground">404</h1>
          <h2 className="mt-4 text-xl font-semibold text-foreground">
            Page not found
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            The page you're looking for doesn't exist or has been moved.
          </p>
          <a
            href="/"
            className="mt-6 inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </a>
        </div>
      </div>
    );
  }
  const { runs, scan } = useLoaderData({ from: "/qa" });
  const { tab } = useSearch({ from: "/qa" }) as { tab: QaTab };
  return <QaShell tab={tab} runs={runs} scan={scan} />;
}
