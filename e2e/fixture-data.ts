import { readFileSync } from "node:fs";
import { join } from "node:path";

/** Read a JSON file the app ships under public/fixtures (test oracle data). */
export function fixture<T = unknown>(rel: string): T {
  return JSON.parse(readFileSync(join(process.cwd(), "public", "fixtures", rel), "utf8")) as T;
}

export interface ObsEntry {
  label: string;
  value: number;
  uncertainty: number;
  units: string;
  provider: string;
  backend: string;
  calibration_at: string;
}

export interface RunFixture {
  id: string;
  domain: string;
  label: string;
  payload: Record<string, unknown>;
  provenance: Record<string, unknown>;
  particle_obs?: Record<string, ObsEntry>;
  model_domain?: string;
  is_learned_hamiltonian?: boolean;
}

const SUP: Record<string, string> = {
  "0": "⁰",
  "1": "¹",
  "2": "²",
  "3": "³",
  "4": "⁴",
  "5": "⁵",
  "6": "⁶",
  "7": "⁷",
  "8": "⁸",
  "9": "⁹",
  "-": "⁻",
};

/** Independent oracle for the app's 3-significant-figure scientific format. */
export function sci3(value: number): string {
  if (value === 0) return "0";
  const exp = Math.floor(Math.log10(Math.abs(value)));
  const mantissa = value / 10 ** exp;
  const sup = String(exp)
    .split("")
    .map((c) => SUP[c] ?? c)
    .join("");
  return `${mantissa.toFixed(2)}×10${sup}`;
}
