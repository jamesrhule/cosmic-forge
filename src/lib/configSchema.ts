import { z } from "zod";

const finitePos = z
  .number({ message: "Required" })
  .refine(Number.isFinite, "Must be a finite number")
  .refine((v) => v > 0, "Must be positive");

const finite = z.number({ message: "Required" }).refine(Number.isFinite, "Must be a finite number");

export const RunConfigSchema = z.object({
  potential: z.object({
    kind: z.enum(["starobinsky", "natural", "hilltop", "custom"]),
    params: z.record(z.string(), z.number()),
    customPython: z.string().optional(),
  }),
  couplings: z.object({
    xi: finite.refine((v) => v >= 0, "ξ must be ≥ 0"),
    theta_grav: finite.refine((v) => v >= 0 && v <= 2 * Math.PI, "θ_grav ∈ [0, 2π]"),
    f_a: finitePos,
    M_star: finitePos,
    M1: finitePos,
    S_E2: finitePos,
  }),
  reheating: z.object({
    Gamma_phi: finitePos,
    T_reh_GeV: finitePos,
  }),
  precision: z.enum(["fast", "standard", "high"]),
});

export type RunConfigInput = z.infer<typeof RunConfigSchema>;
