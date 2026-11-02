import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";

// c5 (W1 FE3): the cosmology visualizer views in an API build (VITE_API_URL
// set, persistRuns on, as production builds them). They list the tenant's
// runs from the API, never the bundled demo catalogue; they read nothing
// from Postgres or Storage for a bundled demo id; the cosmology domain card
// renders the API's VisualizationResponse with its synthetic label; and there
// is no "Live" toggle that could only replay a fixture.
vi.mock("@/config/features", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/config/features")>();
  return {
    ...real,
    API_BASE_URL: "http://api.test",
    DATA_SOURCE: "api",
    FEATURES: {
      ...real.FEATURES,
      liveBackend: true,
      liveVisualization: true,
      persistRuns: true,
      qcompassAuth: false,
    },
  };
});

const h = vi.hoisted(() => ({
  fixtureReads: [] as string[],
  storageReads: [] as string[],
  dbTables: [] as string[],
  dbRunRows: [] as Array<Record<string, unknown>>,
  route: {
    loaderData: {} as Record<string, unknown>,
    params: {} as Record<string, string>,
    search: { mode: "single", phase: false, frame: 0 } as Record<string, unknown>,
  },
}));

vi.mock("@/lib/fixtures", () => ({
  loadFixture: async (path: string) => {
    h.fixtureReads.push(path);
    throw new Error(`fixture read in API mode: ${path}`);
  },
  loadJsonlFixture: async function* (path: string) {
    h.fixtureReads.push(path);
    yield await Promise.reject(new Error(`fixture read in API mode: ${path}`));
  },
  sleep: async () => {},
}));

vi.mock("@/lib/persistence", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/persistence")>();
  return {
    ...real,
    loadTimelineFromStorage: async (id: string) => {
      h.storageReads.push(id);
      return null;
    },
    setRunStatus: async () => ({ ok: true }),
    persistRunResult: async () => ({ ok: true }),
    persistAuditReport: async () => ({ ok: true }),
  };
});

vi.mock("@/integrations/supabase/client", () => {
  const chain = (table: string) => {
    const c: Record<string, unknown> = {};
    for (const m of ["select", "eq", "order"]) c[m] = () => c;
    c.maybeSingle = async () => ({ data: null, error: null });
    c.limit = async () => ({ data: table === "runs" ? h.dbRunRows : [], error: null });
    return c;
  };
  return {
    supabase: {
      from: (table: string) => {
        h.dbTables.push(table);
        return chain(table);
      },
      auth: {
        getUser: async () => ({ data: { user: null } }),
        getSession: async () => ({ data: { session: null } }),
      },
    },
  };
});

vi.mock("@tanstack/react-router", async (importOriginal) => {
  const real = await importOriginal<typeof import("@tanstack/react-router")>();
  const api = {
    useLoaderData: () => h.route.loaderData,
    useParams: () => h.route.params,
    useSearch: () => h.route.search,
  };
  return {
    ...real,
    Link: ({ children, ...rest }: { children?: ReactNode; "data-testid"?: string }) => (
      <a data-testid={rest["data-testid"]}>{children}</a>
    ),
    createFileRoute: () => (options: Record<string, unknown>) => ({ options, ...api }),
    getRouteApi: () => api,
  };
});

// The six-panel surface's heavy panels are not under test here.
vi.mock("@/components/visualizer/panel-phase-space", () => ({ PhaseSpaceCanvas: () => null }));
vi.mock("@/components/visualizer/panel-gb-window", () => ({ GBWindowTimeline: () => null }));
vi.mock("@/components/visualizer/panel-sgwb", () => ({ SGWBSnapshotPlot: () => null }));
vi.mock("@/components/visualizer/panel-anomaly", () => ({ AnomalyIntegrandPlot: () => null }));
vi.mock("@/components/visualizer/panel-lepton-flow", () => ({ LeptonFlowSankey: () => null }));
vi.mock("@/components/visualizer/panel-formula", () => ({ FormulaOverlay: () => null }));
vi.mock("@/components/visualizer/transport-bar", () => ({ TransportBar: () => null }));
vi.mock("@/components/visualizer/keymap-overlay", () => ({ KeymapOverlay: () => null }));
vi.mock("@/components/dev/fps-overlay", () => ({ FpsOverlay: () => null }));

import "@/lib/domains/cosmology.ucglef1";
import {
  getVisualization,
  hasVisualization,
  listVisualizationRunIds,
  listVisualizationSummaries,
  streamVisualization,
} from "@/services/visualizer";
import { getRun, getRunFixtureSummary, listRuns } from "@/services/simulator";
import { Route as VisualizerLayoutRoute } from "@/routes/visualizer";
import { Route as VisualizerIndexRoute } from "@/routes/visualizer.index";
import { Route as DomainVisualizerRoute } from "@/routes/domains/$domain/visualizer.$id";

const BUNDLED = [
  "kawai-kim-natural",
  "starobinsky-standard",
  "gb-off-control",
  "f2-nieh-yan-demo",
  "f3-large-N-demo",
  "f5-resonance-demo",
  "f7-stacked-demo",
];
const RUNS_URL = "http://api.test/api/qcompass/domains/cosmology.ucglef1/runs";
let apiRuns: Array<Record<string, unknown>> = [];
const fetchMock = vi.fn();

beforeEach(() => {
  h.fixtureReads.length = 0;
  h.storageReads.length = 0;
  h.dbTables.length = 0;
  h.dbRunRows = [];
  apiRuns = [];
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async (url: string) => {
    if (url === RUNS_URL) return new Response(JSON.stringify(apiRuns), { status: 200 });
    const viz = /\/api\/qcompass\/domains\/([^/]+)\/runs\/([^/?]+)\/visualization/.exec(url);
    if (viz) {
      return new Response(
        JSON.stringify({
          run_id: viz[2],
          domain: viz[1].split(".")[0],
          schema_version: 1,
          n_frames: 3,
          frames: [
            { tau: 0, phase: "inflation", active_terms: ["xi"] },
            { tau: 30, phase: "gb_window", active_terms: ["xi", "theta"] },
            { tau: 60, phase: "reheating", active_terms: [] },
          ],
          synthetic: true,
          source: "synthetic-bake",
        }),
        { status: 200 },
      );
    }
    return new Response(JSON.stringify({ detail: { code: "NOT_FOUND", message: url } }), {
      status: 404,
    });
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("/visualizer in an API build lists real runs, never the bundled catalogue (c5)", () => {
  it("the loader and catalogue helpers return no bundled id and read no fixture", async () => {
    expect(listVisualizationSummaries()).toEqual([]);
    expect(listVisualizationRunIds()).toEqual([]);
    expect(BUNDLED.some((id) => hasVisualization(id))).toBe(false);
    const loader = (VisualizerLayoutRoute.options as unknown as { loader: () => Promise<unknown> })
      .loader;
    expect(await loader()).toEqual({ summaries: [], runIds: [], syntheticRunIds: [] });
    expect(await getRunFixtureSummary("kawai-kim-natural")).toBeNull();
    expect(h.fixtureReads).toEqual([]);
  });

  it("the index lists the tenant's cosmology runs from the API, without frame counts", async () => {
    apiRuns = [
      {
        id: "qc_real_1",
        label: "cosmology · qc_real_1",
        status: "completed",
        domain: "cosmology.ucglef1",
        created_at: "2026-11-02T10:00:00Z",
      },
    ];
    h.route.loaderData = { summaries: [], runIds: [], syntheticRunIds: [] };
    const Index = (VisualizerIndexRoute.options as unknown as { component: () => ReactNode })
      .component;
    render(<Index />);
    expect(screen.getByTestId("visualizer-api-index")).toBeTruthy();
    const card = await screen.findByTestId("visualizer-api-run");
    expect(card.textContent).toContain("qc_real_1");
    expect(card.textContent).toContain("No six-panel timeline yet (P4-04)");
    const html = document.body.textContent ?? "";
    expect(html).not.toMatch(/240 frames|k-modes|baked GPU buffers/);
    for (const id of BUNDLED) expect(html).not.toContain(id);
    expect(fetchMock.mock.calls.map((c) => String(c[0]))).toEqual([RUNS_URL]);
    expect(h.fixtureReads).toEqual([]);
  });

  it("with no runs the index says so honestly", async () => {
    h.route.loaderData = { summaries: [], runIds: [], syntheticRunIds: [] };
    const Index = (VisualizerIndexRoute.options as unknown as { component: () => ReactNode })
      .component;
    render(<Index />);
    expect(await screen.findByText("No cosmology runs yet")).toBeTruthy();
    expect(screen.queryByTestId("visualizer-api-run")).toBeNull();
    expect(h.fixtureReads).toEqual([]);
  });
});

describe("no Postgres or Storage reads for bundled demo ids in an API build (c5)", () => {
  it("getVisualization skips Storage for a bundled id and still consults it for a real one", async () => {
    await expect(getVisualization("kawai-kim-natural")).rejects.toMatchObject({
      code: "NOT_FOUND",
    });
    expect(h.storageReads).toEqual([]);
    await expect(getVisualization("qc_real_1")).rejects.toMatchObject({ code: "NOT_FOUND" });
    expect(h.storageReads).toEqual(["qc_real_1"]);
    expect(h.fixtureReads).toEqual([]);
  });

  it("getRun skips Postgres for a bundled id and asks the API, which does not have it", async () => {
    await expect(getRun("kawai-kim-natural")).rejects.toMatchObject({ code: "NOT_FOUND" });
    expect(h.dbTables).toEqual([]);
    expect(fetchMock.mock.calls.map((c) => String(c[0]))).toEqual([
      `${RUNS_URL}/kawai-kim-natural`,
    ]);
    await expect(getRun("qc_real_1")).rejects.toMatchObject({ code: "NOT_FOUND" });
    expect(h.dbTables).toEqual(["run_results"]);
  });

  it("listRuns drops rows backfilled from bundled fixtures", async () => {
    h.dbRunRows = [
      { id: "kawai-kim-natural", run_results: { payload: { id: "kawai-kim-natural" } } },
      { id: "qc_real_1", run_results: { payload: { id: "qc_real_1" } } },
    ];
    expect((await listRuns()).map((r) => r.id)).toEqual(["qc_real_1"]);
  });
});

describe("the cosmology domain visualizer card in an API build (c5)", () => {
  it("maps the API's VisualizationResponse, renders, and carries the synthetic label", async () => {
    h.route.loaderData = { domainId: "cosmology.ucglef1", label: "Cosmology · UCGLE-F1" };
    h.route.params = { domain: "cosmology.ucglef1", id: "qc_cosmo_1" };
    const Card = (DomainVisualizerRoute.options as unknown as { component: () => ReactNode })
      .component;
    render(<Card />);
    const card = await screen.findByTestId("visualizer-coming-online");
    expect(card.textContent).toContain("[0, 60]"); // τ range read off the frames
    expect(card.textContent).toContain("theta");
    expect(screen.getByTestId("synthetic-fixture-label").textContent).toBe(
      "Synthetic frames — not a computed result. Real-run timelines arrive with P4-04.",
    );
    expect(h.fixtureReads).toEqual([]);
  });
});

describe("no Live toggle in an API build (c5)", () => {
  it("streamVisualization is NOT_IMPLEMENTED and reads no fixture", async () => {
    const it = streamVisualization("qc_real_1")[Symbol.asyncIterator]();
    await expect(it.next()).rejects.toMatchObject({ code: "NOT_IMPLEMENTED" });
    expect(h.fixtureReads).toEqual([]);
  });

  it("the six-panel surface shows no stream toggle", async () => {
    const { VisualizerLayout } = await import("@/components/visualizer/visualizer-layout");
    const timeline = { runId: "qc_real_1", frames: [] } as never;
    render(<VisualizerLayout timelineA={timeline} timelineB={null} toolbarLead={null} />);
    expect(screen.getByTestId("visualizer-layout")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /stream/i })).toBeNull();
    expect(screen.queryByText("Live")).toBeNull();
  });
});
