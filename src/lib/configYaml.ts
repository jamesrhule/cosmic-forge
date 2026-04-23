import type { RunConfig } from "@/types/domain";

/**
 * Minimal, deterministic YAML serializer for `RunConfig`. We hand-roll
 * this rather than pulling in a yaml dep — the surface is tiny and the
 * backend uses PyYAML which round-trips this format cleanly.
 */
export function configToYaml(config: RunConfig): string {
  const lines: string[] = [];
  lines.push("# UCGLE-F1 run configuration");
  lines.push(`# generated ${new Date().toISOString()}`);
  lines.push("");

  lines.push("potential:");
  lines.push(`  kind: ${config.potential.kind}`);
  lines.push("  params:");
  const paramKeys = Object.keys(config.potential.params).sort();
  for (const k of paramKeys) {
    lines.push(`    ${k}: ${num(config.potential.params[k])}`);
  }
  if (config.potential.customPython) {
    lines.push("  customPython: |");
    for (const ln of config.potential.customPython.split("\n")) {
      lines.push(`    ${ln}`);
    }
  }

  lines.push("couplings:");
  for (const [k, v] of Object.entries(config.couplings)) {
    lines.push(`  ${k}: ${num(v as number)}`);
  }

  lines.push("reheating:");
  for (const [k, v] of Object.entries(config.reheating)) {
    lines.push(`  ${k}: ${num(v as number)}`);
  }

  lines.push(`precision: ${config.precision}`);
  lines.push("");
  return lines.join("\n");
}

function num(v: number): string {
  if (!Number.isFinite(v)) return String(v);
  if (v === 0) return "0";
  const abs = Math.abs(v);
  if (abs >= 1e-3 && abs < 1e6) return String(v);
  return v.toExponential(6);
}
