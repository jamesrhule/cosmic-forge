import type { RunConfig } from "@/types/domain";

export type ValidityLevel = "ok" | "warn" | "error";

export interface ValidityResult {
  level: ValidityLevel;
  message: string;
  details: Array<{ field: string; level: ValidityLevel; message: string }>;
}

/**
 * Stub validator for a RunConfig. Today this is a coarse range check on
 * the couplings; Claude Code will replace it with the real physics
 * constraint checker (CMB priors, reheating consistency, etc.).
 */
export function checkConfigValidity(config: RunConfig): ValidityResult {
  const details: ValidityResult["details"] = [];
  const c = config.couplings;

  if (c.xi <= 0) details.push(rule("xi", "error", "ξ must be positive"));
  else if (c.xi > 1) details.push(rule("xi", "warn", "ξ unusually large (>1)"));

  if (c.theta_grav < 0 || c.theta_grav > 2 * Math.PI)
    details.push(rule("theta_grav", "error", "θ_grav out of [0, 2π]"));

  if (c.M1 < 1e6 || c.M1 > 1e16)
    details.push(rule("M1", "warn", "M₁ outside natural seesaw window"));

  if (config.reheating.T_reh_GeV <= 0)
    details.push(rule("T_reh_GeV", "error", "T_reh must be positive"));

  const level: ValidityLevel = details.some((d) => d.level === "error")
    ? "error"
    : details.some((d) => d.level === "warn")
      ? "warn"
      : "ok";

  const message =
    level === "ok"
      ? "Configuration is physically admissible."
      : level === "warn"
        ? "Configuration is admissible but has unusual values."
        : "Configuration violates a hard constraint.";

  return { level, message, details };
}

function rule(
  field: string,
  level: ValidityLevel,
  message: string,
): ValidityResult["details"][number] {
  return { field, level, message };
}
