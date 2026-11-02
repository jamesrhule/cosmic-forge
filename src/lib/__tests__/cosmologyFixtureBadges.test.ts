import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";

// Decisions 13a and 16 (R7), fixture build: every bundled cosmology run
// fixture's own `synthetic` flag drives the badge on the views that show it
// (no id list of its own), and the badge fails closed: a bundled fixture that
// cannot be loaded or parsed is badged, not silently unbadged (physics review).
const root = resolve(__dirname, "../../../public/fixtures");
const h = vi.hoisted(() => ({ broken: new Map<string, unknown>() }));

vi.mock("@/lib/fixtures", () => ({
  loadFixture: async (path: string, opts: { validate?: (raw: unknown) => unknown } = {}) => {
    const raw = h.broken.has(path)
      ? h.broken.get(path)
      : JSON.parse(readFileSync(resolve(root, path), "utf8"));
    if (raw instanceof Error) throw raw;
    return opts.validate ? opts.validate(raw) : raw;
  },
  loadJsonlFixture: async function* () {},
  sleep: async () => {},
}));

import { getRunFixtureSummary, listRunFixtureSummaries } from "@/services/simulator";
import { Route as VisualizerLayoutRoute } from "@/routes/visualizer";

const KK_COUPLINGS = JSON.parse(readFileSync(resolve(root, "runs/kawai-kim-natural.json"), "utf8"))
  .config.couplings;

beforeEach(() => h.broken.clear());

describe("cosmology run fixture badges (Decisions 13a, 16)", () => {
  it("every bundled cosmology run fixture is listed with its own flag", async () => {
    const all = await listRunFixtureSummaries();
    expect(all.map((s) => s.id).sort()).toEqual([
      "failing-run",
      "gb-off-control",
      "kawai-kim-natural",
      "starobinsky-standard",
    ]);
    expect(all.every((s) => s.synthetic)).toBe(true);
    expect(all.find((s) => s.id === "kawai-kim-natural")?.couplings).toEqual(KK_COUPLINGS);
  });

  it("the /visualizer loader badges every listed run whose fixture is flagged", async () => {
    const loader = (VisualizerLayoutRoute.options as unknown as { loader: () => Promise<unknown> })
      .loader;
    const data = (await loader()) as { runIds: string[]; syntheticRunIds: string[] };
    expect(data.syntheticRunIds.sort()).toEqual([
      "gb-off-control",
      "kawai-kim-natural",
      "starobinsky-standard",
    ]);
    // The demo timelines have no run fixture, so no flag of their own (routed).
    expect(data.runIds.filter((id) => !data.syntheticRunIds.includes(id)).sort()).toEqual([
      "f2-nieh-yan-demo",
      "f3-large-N-demo",
      "f5-resonance-demo",
      "f7-stacked-demo",
    ]);
  });

  it("fails closed: an unreadable or malformed bundled fixture is reported synthetic", async () => {
    h.broken.set("runs/gb-off-control.json", new Error("ASSETS miss"));
    expect(await getRunFixtureSummary("gb-off-control")).toEqual({
      id: "gb-off-control",
      synthetic: true,
      couplings: null,
    });
    const malformed = JSON.parse(
      readFileSync(resolve(root, "runs/kawai-kim-natural.json"), "utf8"),
    ) as Record<string, unknown>;
    malformed.synthetic = "yes"; // zod rejects a non-boolean flag
    h.broken.set("runs/kawai-kim-natural.json", malformed);
    expect(await getRunFixtureSummary("kawai-kim-natural")).toMatchObject({ synthetic: true });
    const loader = (VisualizerLayoutRoute.options as unknown as { loader: () => Promise<unknown> })
      .loader;
    const data = (await loader()) as { syntheticRunIds: string[] };
    expect(data.syntheticRunIds).toContain("gb-off-control");
    expect(data.syntheticRunIds).toContain("kawai-kim-natural");
  });

  it("an id with no bundled fixture is not a bundled run", async () => {
    expect(await getRunFixtureSummary("f2-nieh-yan-demo")).toBeNull();
    expect(await getRunFixtureSummary("qc_real_1")).toBeNull();
  });
});
