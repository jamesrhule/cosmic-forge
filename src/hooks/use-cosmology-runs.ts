import { useEffect, useState } from "react";
import { usesApi } from "@/lib/sdk";
import { listRuns } from "@/services/qcompass/runs";
import type { RunSummary } from "@/lib/domains/types";

export type CosmologyRuns =
  | { state: "fixtures" }
  | { state: "loading" }
  | { state: "ready"; runs: RunSummary[] }
  | { state: "error"; message: string };

/**
 * The signed-in tenant's cosmology runs, from the compute API
 * (`GET /api/qcompass/domains/cosmology.ucglef1/runs`), for the `/visualizer`
 * views in an API build (c5): they list real runs, never the bundled demo
 * catalogue. Fetched in the browser, where the session's token is, not in the
 * SSR loader. In a fixture build it is `{ state: "fixtures" }` and nothing is
 * fetched.
 */
export function useCosmologyRuns(): CosmologyRuns {
  const api = usesApi();
  const [runs, setRuns] = useState<CosmologyRuns>(
    api ? { state: "loading" } : { state: "fixtures" },
  );
  useEffect(() => {
    if (!api) return;
    let cancelled = false;
    listRuns("cosmology.ucglef1")
      .then((rows) => !cancelled && setRuns({ state: "ready", runs: rows }))
      .catch(
        (err: unknown) =>
          !cancelled &&
          setRuns({ state: "error", message: err instanceof Error ? err.message : String(err) }),
      );
    return () => {
      cancelled = true;
    };
  }, [api]);
  return runs;
}
