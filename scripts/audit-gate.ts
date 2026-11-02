#!/usr/bin/env bun
/**
 * Dependency audit gate (CI `frontend` job: `bun run audit:gate`).
 *
 * Runs `bun audit --json` over bun.lock and fails if any advisory of severity
 * high or critical is found in any package of the installed tree (production
 * and dev). It fails closed: output it cannot read, or an exit status it does
 * not understand, is a failure, never an OK. Decision logic and its tests:
 * scripts/audit-gate-lib.ts, scripts/audit-gate.test.ts.
 *
 * Allowlist by advisory id (GHSA or bun's numeric id) via .audit-allowlist.json,
 * only after a documented review with a ledger entry:
 *
 *   { "allowed": ["GHSA-xxxx-xxxx-xxxx"] }
 *
 * Before a pass is trusted, the same registry must report the advisory of a
 * committed canary lock (scripts/fixtures/audit-gate/canary/, one package with
 * a long-standing critical advisory); a registry with no advisory data answers
 * `{}` for everything, which looks clean. The canary is audited in a scratch
 * directory holding copies of its two files plus this project's registry
 * configuration (bunfig.toml, .npmrc), with the same environment, so it asks
 * the registry the main audit asked. It is never installed or built.
 *
 * Exit codes: 0 pass, 1 blocking advisories, 2 the gate could not decide
 * (including "no advisory data" from the canary).
 */
import { spawnSync } from "node:child_process";
import { copyFileSync, existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  AuditParseError,
  type AuditRun,
  CANARY,
  countBySeverity,
  evaluateWithCanary,
  FAIL_AT,
  parseAllowlist,
} from "./audit-gate-lib";

const ALLOWLIST_PATH = ".audit-allowlist.json";

let allowed = new Set<string>();
if (existsSync(ALLOWLIST_PATH)) {
  try {
    allowed = parseAllowlist(readFileSync(ALLOWLIST_PATH, "utf8"));
  } catch (err) {
    console.error(`[audit-gate] ERROR — ${ALLOWLIST_PATH}: ${(err as AuditParseError).message}`);
    process.exit(2);
  }
}

// Run the same bun that runs this script (CI pins it), not whatever is on PATH.
const bun = process.versions.bun ? process.execPath : "bun";

function audit(cwd?: string): AuditRun {
  const r = spawnSync(bun, ["audit", "--json"], {
    cwd,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  return {
    status: r.status,
    stdout: r.stdout ?? "",
    stderr: r.stderr ?? "",
    error: r.error ? String(r.error) : (r.signal ?? undefined),
  };
}

const CANARY_DIR = "scripts/fixtures/audit-gate/canary";
// Project files that choose the registry; the environment is inherited as is.
const REGISTRY_CONFIG = ["bunfig.toml", ".npmrc"];

function auditCanary(): AuditRun {
  const dir = mkdtempSync(join(tmpdir(), "audit-gate-canary-"));
  try {
    copyFileSync(join(CANARY_DIR, "package.json.fixture"), join(dir, "package.json"));
    copyFileSync(join(CANARY_DIR, "bun.lock.fixture"), join(dir, "bun.lock"));
    for (const f of REGISTRY_CONFIG) if (existsSync(f)) copyFileSync(f, join(dir, f));
    return audit(dir);
  } catch (err) {
    return { status: null, stdout: "", stderr: "", error: String(err) };
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

const verdict = evaluateWithCanary(audit(), auditCanary, allowed);

if (verdict.kind === "error") {
  console.error(`[audit-gate] ERROR — ${verdict.reason}`);
  console.error("[audit-gate] Failing closed: an audit that cannot be read is not a pass.");
  process.exit(2);
}

const c = countBySeverity(verdict.findings);
console.log(
  `[audit-gate] bun audit: ${verdict.findings.length} advisories ` +
    `(${c.critical} critical, ${c.high} high, ${c.moderate} moderate, ${c.low} low); ` +
    `gate fails at ${FAIL_AT} and above.`,
);

const used = new Set(verdict.allowlisted.flatMap((f) => f.ids.filter((id) => allowed.has(id))));
for (const f of verdict.allowlisted) {
  console.warn(`[audit-gate] allowlisted: [${f.severity}] ${f.pkg} ${f.id} — ${f.title}`);
}
for (const id of allowed) {
  if (!used.has(id)) console.warn(`[audit-gate] allowlist entry ${id} matches nothing; remove it.`);
}

if (verdict.kind === "pass") {
  console.log(
    `[audit-gate] canary: the registry reported ${verdict.canary?.length ?? 0} advisor${verdict.canary?.length === 1 ? "y" : "ies"} ` +
      `for ${CANARY.pkg} ${CANARY.version} (${verdict.canary?.map((f) => f.id).join(", ")}).`,
  );
  console.log(
    `[audit-gate] OK — no advisories ≥ ${FAIL_AT} (allowlisted: ${verdict.allowlisted.length}).`,
  );
  process.exit(0);
}

const n = verdict.blocking.length;
console.error(`[audit-gate] FAIL — ${n} blocking advisor${n === 1 ? "y" : "ies"}:`);
for (const f of verdict.blocking) {
  console.error(`  · [${f.severity}] ${f.pkg} ${f.vulnerableVersions} — ${f.title} (${f.id})`);
}
console.error(
  `Fix by upgrading. Allowlist by id in ${ALLOWLIST_PATH} only after a documented review.`,
);
process.exit(1);
