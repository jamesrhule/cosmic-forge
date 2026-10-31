import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  domainVisualizationPath,
  normalizeDomainFrame,
  normalizeDomainTimeline,
  unwrapStreamEnvelope,
} from "@/lib/visualizer/domainFrames";

function fixture(id: string): unknown {
  return JSON.parse(
    readFileSync(
      resolve(__dirname, `../../../../public/fixtures/visualizations/${id}.json`),
      "utf8",
    ),
  );
}

describe("normalizeDomainTimeline (flat fixtures)", () => {
  it("chemistry: orbitals indexed, energies unknown, slater kept as flow", () => {
    const tl = normalizeDomainTimeline(fixture("h2-sto3g"), {
      run_id: "h2-sto3g",
      domain: "chemistry",
      synthetic: true,
    });
    expect(tl.manifest.metadata.synthetic).toBe(true);
    expect(tl.frames.length).toBe(32);
    const f = tl.frames[0];
    if (f.domain !== "chemistry") throw new Error("wrong domain");
    expect(f.orbitals[0]).toMatchObject({ index: 0, energy_hartree: null });
    expect(f.slater_flow.length).toBe(8);
    expect(f.slater_determinants).toEqual([]);
  });

  it("condmat: bonds without endpoints are not paired", () => {
    const tl = normalizeDomainTimeline(fixture("hubbard-4x4"), { run_id: "x", domain: "condmat" });
    const f = tl.frames[0];
    if (f.domain !== "condmat") throw new Error("wrong domain");
    expect(f.bond_strengths).toEqual([]);
    expect(f.unpaired_bond_strengths.length).toBeGreaterThan(0);
    expect(f.otoc_butterfly?.axes).toBe("index");
    expect(f.spectral_function_Akw?.axes).toBe("index");
  });

  it("amo: ⟨σzσz⟩ matrix is not relabelled as g²", () => {
    const tl = normalizeDomainTimeline(fixture("rydberg-mis"), { run_id: "x", domain: "amo" });
    const f = tl.frames[0];
    if (f.domain !== "amo") throw new Error("wrong domain");
    expect(f.correlations).toBeNull();
    expect(f.zz_correlations.length).toBe(5);
    expect(f.atom_positions[0].rydberg).toBeNull();
  });

  it("nuclear: scalar LNV becomes the indicator, tracker stays null", () => {
    const tl = normalizeDomainTimeline(fixture("0nbb-1plus1d-toy"), {
      run_id: "x",
      domain: "nuclear",
    });
    const f = tl.frames[0];
    if (f.domain !== "nuclear") throw new Error("wrong domain");
    expect(f.lnv_tracker).toBeNull();
    expect(typeof f.lnv_indicator).toBe("number");
    expect(f.shell_occupation[0].energy_MeV).toBeNull();
  });

  it("structured frames pass through", () => {
    const f = normalizeDomainFrame({
      domain: "hep",
      tau: 1,
      phase: "vacuum",
      active_terms: [],
      plaquettes: [{ cell: [1, 2, 0], flux: 0.5, energy: 0.1 }],
      chiral_condensate: -0.2,
      string_tension: 0.3,
    });
    expect(f).toMatchObject({
      domain: "hep",
      plaquettes: [{ cell: [1, 2, 0], flux: 0.5, energy: 0.1 }],
    });
  });

  it("honours a top-level synthetic flag from the server", () => {
    const tl = normalizeDomainTimeline(
      { run_id: "r", domain: "hep", synthetic: true, frames: [] },
      { run_id: "r", domain: "hep" },
    );
    expect(tl.manifest.metadata.synthetic).toBe(true);
  });
});

describe("stream envelope protocol", () => {
  const frame = { domain: "chemistry", tau: 0.5, phase: "scf", active_terms: [], orbitals: [1, 0] };
  it("skips header, unwraps frame, stops on end/error", () => {
    expect(
      unwrapStreamEnvelope({ type: "header", seq: 0, payload: { n_frames: 3 } }, "chemistry"),
    ).toBeNull();
    expect(
      unwrapStreamEnvelope({ type: "frame", seq: 1, tau: 0.5, payload: frame }, "chemistry"),
    ).toMatchObject({ domain: "chemistry", tau: 0.5 });
    expect(unwrapStreamEnvelope({ type: "end", seq: 2 }, "chemistry")).toBe("end");
    expect(unwrapStreamEnvelope({ type: "error", seq: 2 }, "chemistry")).toBe("end");
  });
  it("SSE: bare frame passes, header data (no τ) is skipped", () => {
    expect(unwrapStreamEnvelope(frame, "chemistry")).not.toBeNull();
    expect(
      unwrapStreamEnvelope(
        { run_id: "r", domain: "chemistry", n_frames: 3, manifest: {} },
        "chemistry",
      ),
    ).toBeNull();
  });
  it("routes gravity/statmech to the M8 qcompass paths", () => {
    expect(domainVisualizationPath("ws", "gravity", "a b")).toBe(
      "/ws/qcompass/domains/gravity.syk/runs/a%20b/visualization",
    );
    expect(domainVisualizationPath("sse", "statmech", "r")).toBeNull();
    expect(domainVisualizationPath("api", "chemistry", "r")).toBe(
      "/api/runs/chemistry/r/visualization",
    );
  });

  it("ignores prototype-polluting particle_obs keys (CodeQL js/remote-property-injection)", () => {
    const raw = JSON.parse(
      '{"domain":"hep","tau":0,"phase":"vacuum","active_terms":[],' +
        '"particle_obs":{"__proto__":{"value":1,"polluted":true},"m_pi":{"value":0.14,"unit":"GeV"}}}',
    );
    const f = normalizeDomainFrame(raw);
    if (!f || f.domain !== "hep") throw new Error("wrong domain");
    expect(Object.keys(f.particle_obs)).toEqual(["m_pi"]);
    expect(({} as Record<string, unknown>).polluted).toBeUndefined();
    expect(Object.getPrototypeOf(f.particle_obs)).toBe(Object.prototype);
  });
});

describe("normalizeDomainTimeline (API synthetic bake, B2 / R7)", () => {
  it("keeps the API's synthetic flag and source so the UI labels the frames", () => {
    const tl = normalizeDomainTimeline(
      { run_id: "qc_hep_1", domain: "hep", frames: [], synthetic: true, source: "synthetic-bake" },
      { run_id: "qc_hep_1", domain: "hep" },
    );
    expect(tl.manifest.metadata.synthetic).toBe(true);
    expect(tl.manifest.metadata.source).toBe("synthetic-bake");
  });

  it("does not label a response that is not synthetic", () => {
    const tl = normalizeDomainTimeline(
      { run_id: "r", domain: "hep", frames: [] },
      { run_id: "r", domain: "hep" },
    );
    expect(tl.manifest.metadata.synthetic).toBeUndefined();
  });
});
