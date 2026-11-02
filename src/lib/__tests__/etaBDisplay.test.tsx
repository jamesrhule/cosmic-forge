import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

// W1 FE3: a refused η_B (pipeline.eta_B_refusal) reads
// "η_B not published — <reason>" wherever a run's η_B is shown, and M6's
// placeholder frequencies are labelled on the SGWB plot. Bundled fixtures
// (finite η_B, no flags) read exactly as before.
const REASON =
  "ΔN_L depends on the scale-factor normalisation (residual 9); M4 does not yet match a to reheating (P1-04)";

vi.mock("@/lib/sdk", async (importOriginal) => {
  const real = await importOriginal<typeof import("@/lib/sdk")>();
  return { ...real, usesApi: () => true };
});
vi.mock("@/services/simulator", () => ({ startRun: async () => ({ runId: "qc_refused" }) }));
vi.mock("@/services/qcompass/runs", () => ({
  // The platform route's stored result: value is the stored marker "NaN".
  streamRun: async function* () {
    yield { type: "queued", runId: "qc_refused" };
    yield {
      type: "result",
      runId: "qc_refused",
      payload: {
        payload: {
          result: {
            eta_B: "NaN",
            run_result: { eta_B: { value: "NaN", uncertainty: "NaN", refusal: REASON } },
          },
        },
      },
    };
  },
}));

import { ETA_B_NO_REASON, etaBNotPublished, readEtaB } from "@/lib/etaB";
import { ActionsRail } from "@/components/configurator/ActionsRail";
import { QaControlFrame } from "@/components/qa/qa-control-frame";
import SgwbCompareChart from "@/components/visualizer/lazy/sgwb-compare-chart";
import { kawaiKimDefaults } from "@/lib/configDefaults";
import type { RunResult } from "@/types/domain";

const fixture = (id: string) =>
  JSON.parse(
    readFileSync(resolve(__dirname, `../../../public/fixtures/runs/${id}.json`), "utf8"),
  ) as RunResult;

(globalThis as { ResizeObserver?: unknown }).ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

afterEach(() => cleanup());

describe("readEtaB", () => {
  it("a fixture's finite η_B is published as is", () => {
    expect(readEtaB(fixture("kawai-kim-natural").eta_B)).toEqual({
      kind: "published",
      value: 6.1e-10,
    });
  });

  it("a refused η_B is never a number, with or without its reason", () => {
    for (const value of [null, "NaN", undefined, Number.NaN]) {
      expect(readEtaB({ value, refusal: REASON })).toEqual({ kind: "refused", reason: REASON });
      expect(readEtaB({ value })).toEqual({ kind: "refused", reason: ETA_B_NO_REASON });
    }
    expect(readEtaB({ value: 6.1e-10, refusal: REASON })).toEqual({
      kind: "refused",
      reason: REASON,
    });
    expect(readEtaB(undefined)).toBeNull();
    expect(etaBNotPublished(REASON)).toBe(`η_B not published — ${REASON}`);
  });
});

describe("η_B wherever a run's η_B is shown", () => {
  it("the Configurator's live run status says why η_B is not published", async () => {
    render(
      <ActionsRail
        config={kawaiKimDefaults()}
        benchmarks={[]}
        canRun={true}
        onLoadConfig={() => {}}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /Run simulation/ }));
    const status = await screen.findByTestId("workbench-run-status");
    await waitFor(() => expect(status.getAttribute("data-status")).toBe("completed"));
    expect(screen.getByTestId("workbench-run-eta-b").textContent).toBe(
      `η_B not published — ${REASON}`,
    );
    expect(status.textContent).not.toMatch(/η_B =|NaN/);
  });

  it("the run list reads a fixture as before and a refused run with its reason", () => {
    const refused = {
      ...fixture("kawai-kim-natural"),
      id: "qc_refused",
      synthetic: undefined,
      eta_B: { value: null, uncertainty: null, budget: {}, refusal: REASON },
    } as unknown as RunResult;
    render(<QaControlFrame runs={[fixture("kawai-kim-natural"), refused]} />);
    expect(screen.getByText("η_B = 6.10e-10 · completed")).toBeTruthy();
    expect(screen.getByText(`η_B not published — ${REASON} · completed`)).toBeTruthy();
  });
});

describe("SGWB frequency axis (M6 placeholder)", () => {
  const data = [
    { f: 1e-19, a: 1e-12 },
    { f: 1e-18, a: 1e-11 },
  ];
  const chart = (placeholderFrequencies?: boolean) =>
    render(
      <SgwbCompareChart
        width={480}
        height={280}
        data={data}
        spectra={[{ id: "a", label: "a" }]}
        bands={[]}
        colors={["#000"]}
        placeholderFrequencies={placeholderFrequencies}
      />,
    );

  it("is labelled 'placeholder frequencies' when the API flags them", () => {
    const { container } = chart(true);
    expect(container.textContent).toContain("placeholder frequencies");
    expect(container.textContent).not.toContain("f [Hz]");
  });

  it("keeps 'f [Hz]' for unflagged data (bundled fixtures)", () => {
    const { container } = chart();
    expect(container.textContent).toContain("f [Hz]");
    expect(container.textContent).not.toContain("placeholder");
  });
});
