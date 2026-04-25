#!/usr/bin/env bun
/**
 * Dependency audit gate.
 *
 * Runs `bun audit --json` (or falls back to `npm audit --json` against
 * the lockfile when bun's audit isn't yet available in the runner) and
 * fails the process if any vulnerability of severity ≥ HIGH_SEVERITY
 * is found. Allowlist by advisory id via .audit-allowlist.json:
 *
 *   { "allowed": ["GHSA-xxxx-xxxx-xxxx"] }
 */
import { spawnSync } from "node:child_process";
import { readFileSync, existsSync } from "node:fs";

const SEVERITY_RANK: Record<string, number> = {
  info: 0,
  low: 1,
  moderate: 2,
  high: 3,
  critical: 4,
};
const FAIL_AT = SEVERITY_RANK.high;

const allowlistPath = ".audit-allowlist.json";
const allowed: Set<string> = existsSync(allowlistPath)
  ? new Set<string>(JSON.parse(readFileSync(allowlistPath, "utf8")).allowed ?? [])
  : new Set();

interface Advisory {
  id: string;
  severity: string;
  title?: string;
  module_name?: string;
}

function tryRun(cmd: string, args: string[]): { stdout: string; status: number | null } {
  const r = spawnSync(cmd, args, { encoding: "utf8" });
  return { stdout: r.stdout ?? "", status: r.status };
}

// Prefer `bun audit` if available; fall back to npm audit (works against
// bun.lock via package-lock generation isn't needed — npm audits the
// installed node_modules directory).
let raw = tryRun("bun", ["audit", "--json"]);
if (raw.status !== 0 && raw.status !== 1) {
  console.warn("[audit-gate] `bun audit` unavailable, falling back to `npm audit --json`");
  raw = tryRun("npm", ["audit", "--json"]);
}

let advisories: Advisory[] = [];
try {
  const parsed = JSON.parse(raw.stdout || "{}");
  // npm audit v2 shape:
  if (parsed.vulnerabilities) {
    for (const [name, v] of Object.entries(parsed.vulnerabilities as Record<string, { severity: string; via: unknown[] }>)) {
      for (const via of v.via) {
        if (typeof via === "object" && via !== null && "source" in via) {
          const adv = via as { source: number | string; severity: string; title?: string };
          advisories.push({
            id: String(adv.source),
            severity: adv.severity ?? v.severity,
            title: adv.title,
            module_name: name,
          });
        }
      }
    }
  } else if (Array.isArray(parsed.advisories)) {
    advisories = parsed.advisories;
  }
} catch (err) {
  console.error("[audit-gate] failed to parse audit output:", err);
  console.error(raw.stdout.slice(0, 500));
  process.exit(2);
}

const blocking = advisories.filter(
  (a) => (SEVERITY_RANK[a.severity] ?? 0) >= FAIL_AT && !allowed.has(a.id),
);

if (blocking.length === 0) {
  console.log(`[audit-gate] OK — no advisories ≥ high (allowlisted: ${allowed.size}).`);
  process.exit(0);
}

console.error(`[audit-gate] FAIL — ${blocking.length} blocking advisor${blocking.length === 1 ? "y" : "ies"}:`);
for (const a of blocking) {
  console.error(`  · [${a.severity}] ${a.module_name ?? "?"} — ${a.title ?? "no title"} (id: ${a.id})`);
}
console.error(`Allowlist any of these by id in ${allowlistPath} after a documented review.`);
process.exit(1);
