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

import { ActionsRail } from "@/components/configurator/ActionsRail";
import { QaControlFrame } from "@/components/qa/qa-control-frame";
import SgwbCompareChart from "@/components/visualizer/lazy/sgwb-compare-chart";
import { SGWBPlot } from "@/components/sgwb-plot";
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
    expect(status.textContent).toContain(`η_B not published — ${REASON}`);
    expect(status.textContent).not.toMatch(/η_B =|NaN/);
    expect(screen.getByTestId("workbench-run-eta-b").textContent).toBe(
      `η_B not published — ${REASON}`,
    );
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
  const spectrum = (flag?: boolean) => ({
    f_Hz: [1e-19, 1e-18],
    Omega_gw: [1e-12, 1e-11],
    chirality: [0.1, 0.2],
    ...(flag === undefined ? {} : { f_Hz_is_placeholder: flag, note: "M6 placeholder: …" }),
  });

  it("the run plot says its frequencies are placeholders when the API flags them", () => {
    const { container } = render(
      <SGWBPlot spectra={[{ id: "qc_1", label: "qc_1", data: spectrum(true) }]} />,
    );
    expect(container.textContent).toContain("placeholder frequencies");
    expect(container.textContent).toContain("M6 placeholder");
  });

  it("an unflagged spectrum (bundled fixtures) gets no placeholder note", () => {
    const { container } = render(
      <SGWBPlot
        spectra={[{ id: "kk", label: "kk", data: fixture("kawai-kim-natural").spectra.sgwb }]}
      />,
    );
    expect(container.textContent).not.toContain("placeholder");
  });

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
