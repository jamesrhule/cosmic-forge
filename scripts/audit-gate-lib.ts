/**
 * Pure logic of the dependency audit gate (P0-05). `scripts/audit-gate.ts` is
 * the CLI around it; `scripts/audit-gate.test.ts` drives it with real
 * `bun audit --json` output captured under `scripts/fixtures/audit-gate/`.
 *
 * Input: the exit status, stdout and stderr of `bun audit --json` (bun 1.4.4,
 * the version CI pins). Its JSON is one object keyed by package name, each
 * value an array of advisories:
 *
 *   { "<package>": [{ "id": 1242281, "url": "https://github.com/advisories/GHSA-…",
 *                     "title": "…", "severity": "critical",
 *                     "vulnerable_versions": ">=1.143.12 <1.168.60", … }], … }
 *
 * bun exits 0 with `{}` when nothing is found and 1 when anything is found
 * (any severity). It also exits 1, with empty stdout, when it cannot audit at
 * all (no lockfile, registry unreachable). So the exit status alone never
 * means "clean", and anything this module does not recognise fails closed.
 *
 * Scope: every package `bun audit` checks, i.e. the whole installed tree from
 * bun.lock, production and dev alike, which is what the gate has always run
 * (no `--production`). The packages that build the web and server bundles
 * (vite, the TanStack and Cloudflare plugins, tailwind) are declared in
 * `dependencies`, so a production/dev split would not match "what ships"
 * anyway. See docs/build/lanes/W0-deps.md (2026-11-02, W0-npm).
 */

export const SEVERITY_RANK = {
  info: 0,
  low: 1,
  moderate: 2,
  high: 3,
  critical: 4,
} as const;

export type Severity = keyof typeof SEVERITY_RANK;

/** Advisories at or above this severity block the gate. */
export const FAIL_AT: Severity = "high";

export interface Finding {
  /** Package name as bun reports it (the key of the JSON object). */
  pkg: string;
  /** GHSA id when the advisory URL carries one, otherwise the numeric id. */
  id: string;
  /** Every id this advisory may be allowlisted by (GHSA and numeric). */
  ids: string[];
  severity: Severity;
  title: string;
  url: string;
  vulnerableVersions: string;
}

export interface AuditRun {
  /** Exit status; null when the process was killed or never started. */
  status: number | null;
  stdout: string;
  stderr: string;
  /** spawn error, signal name, etc. */
  error?: string;
}

export type Verdict =
  | { kind: "pass"; findings: Finding[]; allowlisted: Finding[] }
  | { kind: "fail"; findings: Finding[]; blocking: Finding[]; allowlisted: Finding[] }
  | { kind: "error"; reason: string };

export class AuditParseError extends Error {}

const GHSA_RE = /GHSA(?:-[0-9a-z]{4}){3}/;

function isSeverity(s: unknown): s is Severity {
  return typeof s === "string" && Object.prototype.hasOwnProperty.call(SEVERITY_RANK, s);
}

/**
 * Parse `bun audit --json` stdout into findings. Throws AuditParseError on
 * anything that is not exactly bun's shape, including npm's
 * (`{vulnerabilities: …}`, `{advisories: …}`) and empty output.
 */
export function parseBunAuditJson(stdout: string): Finding[] {
  const text = stdout.trim();
  if (text === "") throw new AuditParseError("empty stdout");
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch (err) {
    throw new AuditParseError(`stdout is not JSON: ${(err as Error).message}`);
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new AuditParseError("top level is not an object keyed by package name");
  }
  const findings: Finding[] = [];
  for (const [pkg, advisories] of Object.entries(parsed as Record<string, unknown>)) {
    if (!Array.isArray(advisories)) {
      throw new AuditParseError(`value for "${pkg}" is not an array of advisories`);
    }
    if (advisories.length === 0) {
      throw new AuditParseError(`"${pkg}" is listed with no advisories`);
    }
    for (const raw of advisories) {
      if (typeof raw !== "object" || raw === null) {
        throw new AuditParseError(`"${pkg}" has a non-object advisory`);
      }
      const a = raw as Record<string, unknown>;
      if (!isSeverity(a.severity)) {
        throw new AuditParseError(
          `"${pkg}" advisory has unknown severity ${JSON.stringify(a.severity)}`,
        );
      }
      const url = typeof a.url === "string" ? a.url : "";
      const ghsa = url.match(GHSA_RE)?.[0];
      const numeric =
        typeof a.id === "number" || (typeof a.id === "string" && a.id !== "")
          ? String(a.id)
          : undefined;
      if (!ghsa && !numeric) {
        throw new AuditParseError(`"${pkg}" advisory has neither a GHSA url nor an id`);
      }
      const ids = [ghsa, numeric].filter((x): x is string => !!x);
      findings.push({
        pkg,
        id: ids[0],
        ids,
        severity: a.severity,
        title: typeof a.title === "string" ? a.title : "",
        url,
        vulnerableVersions: typeof a.vulnerable_versions === "string" ? a.vulnerable_versions : "",
      });
    }
  }
  return findings;
}

/**
 * Parse `.audit-allowlist.json` (`{ "allowed": ["GHSA-…" | "<numeric id>", …] }`).
 * Throws on any other shape so a broken allowlist can't silently allow nothing
 * or everything.
 */
export function parseAllowlist(text: string): Set<string> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch (err) {
    throw new AuditParseError(`allowlist is not JSON: ${(err as Error).message}`);
  }
  const allowed = (parsed as { allowed?: unknown } | null)?.allowed;
  if (
    typeof parsed !== "object" ||
    parsed === null ||
    !Array.isArray(allowed) ||
    !allowed.every((x) => typeof x === "string" && x.trim() !== "")
  ) {
    throw new AuditParseError('allowlist must be { "allowed": ["GHSA-…", …] }');
  }
  return new Set(allowed as string[]);
}

/** Decide the gate from one `bun audit --json` run. Fails closed. */
export function evaluate(run: AuditRun, allowed: Set<string> = new Set()): Verdict {
  if (run.status === null) {
    return {
      kind: "error",
      reason: `bun audit did not exit normally (${run.error ?? "no status"})`,
    };
  }
  if (run.status !== 0 && run.status !== 1) {
    return {
      kind: "error",
      reason: `bun audit exited ${run.status}, which the gate does not understand`,
    };
  }
  let findings: Finding[];
  try {
    findings = parseBunAuditJson(run.stdout);
  } catch (err) {
    const stderr = run.stderr.trim();
    return {
      kind: "error",
      reason:
        `bun audit exited ${run.status} with output the gate cannot read (${(err as Error).message})` +
        (stderr ? `; stderr: ${stderr.slice(0, 500)}` : ""),
    };
  }
  if (run.status === 1 && findings.length === 0) {
    return { kind: "error", reason: "bun audit exited 1 but reported no advisories" };
  }
  const atOrAbove = findings.filter((f) => SEVERITY_RANK[f.severity] >= SEVERITY_RANK[FAIL_AT]);
  const allowlisted = atOrAbove.filter((f) => f.ids.some((id) => allowed.has(id)));
  const blocking = atOrAbove.filter((f) => !allowlisted.includes(f));
  if (blocking.length > 0) return { kind: "fail", findings, blocking, allowlisted };
  return { kind: "pass", findings, allowlisted };
}

/** Advisory counts by severity, for the summary line. */
export function countBySeverity(findings: Finding[]): Record<Severity, number> {
  const counts: Record<Severity, number> = { info: 0, low: 0, moderate: 0, high: 0, critical: 0 };
  for (const f of findings) counts[f.severity] += 1;
  return counts;
}
