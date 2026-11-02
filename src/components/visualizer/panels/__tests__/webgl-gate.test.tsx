import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

// R3F needs a real WebGL context; stand in for <Canvas> so the test checks
// only whether each panel *mounts* it (PLAN.md correction 7c).
vi.mock("@react-three/fiber", () => ({
  Canvas: (_props: { children?: ReactNode }) => <div data-testid="r3f-canvas" />,
}));
vi.mock("@react-three/drei", () => ({ OrbitControls: () => null }));

import { detectWebGL } from "@/lib/webgl";
import { normalizeDomainTimeline } from "@/lib/visualizer/domainFrames";
import { AtomArray3D } from "../amo/AtomArray3D";
import { LatticeWithBondColors } from "../condmat/LatticeWithBondColors";
import { OrbitalOccupation3D } from "../chemistry/OrbitalOccupation3D";

function firstFrame(id: string, domain: "amo" | "condmat" | "chemistry") {
  const raw = JSON.parse(
    readFileSync(
      resolve(__dirname, `../../../../../public/fixtures/visualizations/${id}.json`),
      "utf8",
    ),
  );
  return normalizeDomainTimeline(raw, { run_id: id, domain, synthetic: true }).frames[0];
}

const PANELS = [
  {
    name: "AtomArray3D",
    el: () => <AtomArray3D frame={firstFrame("rydberg-mis", "amo") as never} />,
  },
  {
    name: "LatticeWithBondColors",
    el: () => <LatticeWithBondColors frame={firstFrame("hubbard-4x4", "condmat") as never} />,
  },
  {
    name: "OrbitalOccupation3D",
    el: () => <OrbitalOccupation3D frame={firstFrame("h2-sto3g", "chemistry") as never} />,
  },
];

function stubWebGL(available: boolean) {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation((() =>
    available ? ({} as RenderingContext) : null) as never);
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("WebGLGate on the 3D domain panels", () => {
  for (const p of PANELS) {
    it(`${p.name} mounts an R3F Canvas when detectWebGL() is true`, async () => {
      stubWebGL(true);
      expect(detectWebGL()).toBe(true);
      render(p.el());
      expect(await screen.findByTestId("r3f-canvas")).toBeTruthy();
    });

    it(`${p.name} shows the no-WebGL fallback instead of a Canvas when detectWebGL() is false`, async () => {
      stubWebGL(false);
      expect(detectWebGL()).toBe(false);
      render(p.el());
      expect(await screen.findByText(/needs WebGL/)).toBeTruthy();
      expect(screen.queryByTestId("r3f-canvas")).toBeNull();
    });
  }
});
