// @vitest-environment node
/**
 * Fixture-based tests of the audit gate's decision (P0-05; lane W0-npm).
 * Every fixture under scripts/fixtures/audit-gate/ is real bun 1.4.4 output,
 * captured byte for byte (see the README there for the commands).
 */
import { existsSync, readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import {
  AuditParseError,
  CANARY,
  countBySeverity,
  evaluate,
  evaluateCanary,
  evaluateWithCanary,
  parseAllowlist,
  parseBunAuditJson,
  type AuditRun,
} from "./audit-gate-lib";

const fixture = (name: string) =>
  readFileSync(new URL(`./fixtures/audit-gate/${name}`, import.meta.url), "utf8");

// `bun audit --json` on bun.lock at 4de96fa (exit 1).
const BEFORE: AuditRun = { status: 1, stdout: fixture("bun-1.4.4-4de96fa.stdout"), stderr: "" };
// `bun audit --json` on bun.lock after this lane's upgrades (exit 1: moderate/low remain).
const AFTER: AuditRun = { status: 1, stdout: fixture("bun-1.4.4-after.stdout"), stderr: "" };
// A project whose only dependency is @protobufjs/utf8 1.1.0 (one moderate advisory; exit 1).
const MODERATE: AuditRun = {
  status: 1,
  stdout: fixture("bun-1.4.4-moderate-only.stdout"),
  stderr: "",
};
// A project whose only dependency is is-number 7.0.0 (no advisories; exit 0).
const CLEAN: AuditRun = { status: 0, stdout: fixture("bun-1.4.4-clean.stdout"), stderr: "" };

const HIGH_OR_CRITICAL_4DE96FA = [
  "@tanstack/react-start",
  "@tanstack/start-server-core",
  "brace-expansion",
  "browserslist",
  "dompurify",
  "fast-uri",
  "js-yaml",
  "nanoid",
  "postcss",
  "protobufjs",
  "seroval",
  "sharp",
  "source-map-js",
  "undici",
  "vite",
  "ws",
  "zod",
];

describe("parseBunAuditJson on real bun 1.4.4 output", () => {
  it("reads every advisory of the 4de96fa lock", () => {
    const findings = parseBunAuditJson(BEFORE.stdout);
    expect(findings).toHaveLength(130);
    expect(new Set(findings.map((f) => f.pkg)).size).toBe(29);
    expect(countBySeverity(findings)).toEqual({
      info: 0,
      low: 18,
      moderate: 53,
      high: 55,
      critical: 4,
    });
    const xss = findings.filter((f) => f.id === "GHSA-qx66-fv34-fjm8");
    expect(xss.map((f) => f.pkg).sort()).toEqual([
      "@tanstack/react-start",
      "@tanstack/start-server-core",
    ]);
    expect(xss.every((f) => f.severity === "critical")).toBe(true);
    expect(xss.find((f) => f.pkg === "@tanstack/react-start")).toMatchObject({
      ids: ["GHSA-qx66-fv34-fjm8", "1242281"],
      vulnerableVersions: ">=1.143.12 <1.168.60",
      url: "https://github.com/advisories/GHSA-qx66-fv34-fjm8",
    });
  });

  it("reads the clean and moderate-only outputs", () => {
    expect(parseBunAuditJson(CLEAN.stdout)).toEqual([]);
    expect(parseBunAuditJson(MODERATE.stdout)).toEqual([
      expect.objectContaining({
        pkg: "@protobufjs/utf8",
        id: "GHSA-q6x5-8v7m-xcrf",
        severity: "moderate",
      }),
    ]);
  });

  it("rejects npm's audit shapes instead of reading them as empty", () => {
    const npmV2 = JSON.stringify({
      auditReportVersion: 2,
      vulnerabilities: { seroval: { severity: "critical", via: [] } },
    });
    const npmV1 = JSON.stringify({ advisories: { 1: { severity: "high" } } });
    expect(() => parseBunAuditJson(npmV2)).toThrow(AuditParseError);
    expect(() => parseBunAuditJson(npmV1)).toThrow(AuditParseError);
  });
});

describe("evaluate", () => {
  it("fails on the 4de96fa lock, blocking every high and critical advisory", () => {
    const v = evaluate(BEFORE);
    expect(v.kind).toBe("fail");
    if (v.kind !== "fail") return;
    expect(v.blocking).toHaveLength(59);
    expect(v.blocking.every((f) => f.severity === "high" || f.severity === "critical")).toBe(true);
    expect([...new Set(v.blocking.map((f) => f.pkg))].sort()).toEqual(HIGH_OR_CRITICAL_4DE96FA);
    expect(v.blocking.map((f) => f.id)).toEqual(
      expect.arrayContaining(["GHSA-qx66-fv34-fjm8", "GHSA-mv8w-475r-vwqw", "GHSA-p6vx-979v-rg4c"]),
    );
  });

  it("fails on a single high advisory even when bun exits 0", () => {
    const one = JSON.parse(BEFORE.stdout).vite;
    const v = evaluate({ status: 0, stdout: JSON.stringify({ vite: one }), stderr: "" });
    expect(v.kind).toBe("fail");
  });

  it("fails on a single critical advisory", () => {
    const one = JSON.parse(BEFORE.stdout)["@tanstack/react-start"];
    const v = evaluate({
      status: 1,
      stdout: JSON.stringify({ "@tanstack/react-start": one }),
      stderr: "",
    });
    expect(v).toMatchObject({ kind: "fail", blocking: [{ id: "GHSA-qx66-fv34-fjm8" }] });
  });

  it("passes on moderate-only output (bun exits 1)", () => {
    expect(evaluate(MODERATE)).toMatchObject({ kind: "pass", allowlisted: [] });
  });

  it("passes on clean output (bun exits 0)", () => {
    expect(evaluate(CLEAN)).toEqual({ kind: "pass", findings: [], allowlisted: [] });
  });

  it("passes on the upgraded lock: only moderate and low remain", () => {
    const v = evaluate(AFTER);
    expect(v.kind).toBe("pass");
    const c = countBySeverity(parseBunAuditJson(AFTER.stdout));
    expect(c.high + c.critical).toBe(0);
  });

  it("allowlists by GHSA or numeric id, and only the listed advisory", () => {
    const byGhsa = evaluate(BEFORE, new Set(["GHSA-qx66-fv34-fjm8"]));
    expect(byGhsa.kind).toBe("fail");
    if (byGhsa.kind !== "fail") return;
    expect(byGhsa.allowlisted).toHaveLength(2);
    expect(byGhsa.blocking).toHaveLength(57);

    // vite at 4de96fa: one high (GHSA-587h-7wmj-h5pm, id 1242659) plus moderates and a low.
    const vite = JSON.parse(BEFORE.stdout).vite;
    const run = { status: 1, stdout: JSON.stringify({ vite }), stderr: "" };
    expect(evaluate(run).kind).toBe("fail");
    expect(evaluate(run, new Set(["1242659"])).kind).toBe("pass");
    expect(evaluate(run, new Set(["GHSA-587h-7wmj-h5pm"])).kind).toBe("pass");
    expect(evaluate(run, new Set(["GHSA-v6wh-96g9-6wx3"])).kind).toBe("fail");
  });
});

describe("evaluate fails closed", () => {
  const errorOf = (run: AuditRun) => {
    const v = evaluate(run);
    expect(v.kind).toBe("error");
    return v.kind === "error" ? v.reason : "";
  };

  it("on a registry that cannot be reached (real: exit 1, empty stdout)", () => {
    const stderr = fixture("bun-1.4.4-registry-unreachable.stderr");
    expect(errorOf({ status: 1, stdout: "", stderr })).toMatch(/ConnectionRefused/);
  });

  it("on a missing lockfile (real: exit 1, empty stdout)", () => {
    const stderr = fixture("bun-1.4.4-missing-lockfile.stderr");
    expect(errorOf({ status: 1, stdout: "", stderr })).toMatch(/missing lockfile/);
  });

  it("on unparseable or truncated output", () => {
    errorOf({ status: 1, stdout: "not json", stderr: "" });
    errorOf({ status: 1, stdout: BEFORE.stdout.slice(0, 1000), stderr: "" });
    errorOf({ status: 0, stdout: "", stderr: "" });
    errorOf({ status: 0, stdout: "[]", stderr: "" });
    errorOf({ status: 0, stdout: "null", stderr: "" });
  });

  it("on npm-shaped output", () => {
    errorOf({
      status: 1,
      stdout: JSON.stringify({ vulnerabilities: { x: { severity: "high", via: [] } } }),
      stderr: "",
    });
  });

  it("on an advisory with an unknown severity or no id", () => {
    errorOf({
      status: 1,
      stdout: JSON.stringify({ x: [{ id: 1, url: "", title: "t", severity: "severe" }] }),
      stderr: "",
    });
    errorOf({
      status: 1,
      stdout: JSON.stringify({ x: [{ title: "t", severity: "high" }] }),
      stderr: "",
    });
  });

  it("when bun exits 1 but reports nothing", () => {
    expect(errorOf({ status: 1, stdout: "{}\n", stderr: "" })).toMatch(/reported no advisories/);
  });

  it("on an exit status it does not understand", () => {
    expect(errorOf({ status: 2, stdout: CLEAN.stdout, stderr: "" })).toMatch(/exited 2/);
    expect(errorOf({ status: 127, stdout: "", stderr: "bun: not found" })).toMatch(/exited 127/);
    expect(errorOf({ status: null, stdout: "", stderr: "", error: "SIGKILL" })).toMatch(/SIGKILL/);
  });
});

describe("parseAllowlist", () => {
  it("reads the documented shape", () => {
    expect(parseAllowlist('{ "allowed": ["GHSA-xxxx-xxxx-xxxx"] }')).toEqual(
      new Set(["GHSA-xxxx-xxxx-xxxx"]),
    );
    expect(parseAllowlist('{ "allowed": [] }')).toEqual(new Set());
  });

  it("throws on anything else", () => {
    for (const bad of [
      "",
      "[]",
      "{}",
      '{ "allowed": "GHSA" }',
      '{ "allowed": [1] }',
      '{ "allowed": [""] }',
    ]) {
      expect(() => parseAllowlist(bad)).toThrow(AuditParseError);
    }
  });
});

// The canary lock (scripts/fixtures/audit-gate/canary/) audited against the
// real registry (exit 1) and against a registry that answers the bulk advisory
// endpoint with HTTP 200 `{}` (exit 0). The main lock against that registry
// also gives exactly `{}` (exit 0), byte-identical to a clean tree.
const CANARY_REAL: AuditRun = { status: 1, stdout: fixture("bun-1.4.4-canary.stdout"), stderr: "" };
const CANARY_EMPTY: AuditRun = {
  status: 0,
  stdout: fixture("bun-1.4.4-canary-empty-registry.stdout"),
  stderr: "",
};
const MAIN_EMPTY: AuditRun = {
  status: 0,
  stdout: fixture("bun-1.4.4-empty-registry.stdout"),
  stderr: "",
};

describe("canary: a pass needs advisory data from the same registry", () => {
  it("the committed canary lock pins exactly one package, the known-vulnerable one", () => {
    const dir = "./fixtures/audit-gate/canary/";
    const pkg = JSON.parse(fixture("canary/package.json.fixture"));
    expect(pkg.dependencies).toEqual({ [CANARY.pkg]: CANARY.version });
    expect(pkg.devDependencies ?? {}).toEqual({});
    const lock = fixture("canary/bun.lock.fixture");
    expect(lock).toContain(`"${CANARY.pkg}": ["${CANARY.pkg}@${CANARY.version}"`);
    expect(lock.match(/@\d+\.\d+\.\d+", ""/g)).toHaveLength(1);
    // Stored under names GitHub's dependency graph does not read as a manifest.
    for (const f of ["package.json", "bun.lock", "node_modules"]) {
      expect(existsSync(new URL(dir + f, import.meta.url)), f).toBe(false);
    }
  });

  it("the real registry reports the canary's advisory", () => {
    const c = evaluateCanary(CANARY_REAL);
    expect(c.ok).toBe(true);
    if (!c.ok) return;
    expect(c.findings.map((f) => f.id)).toContain(CANARY.advisory);
  });

  it("a registry with no advisory data looks clean on the main lock", () => {
    expect(MAIN_EMPTY.stdout).toBe(CLEAN.stdout);
    expect(evaluate(MAIN_EMPTY).kind).toBe("pass");
  });

  it("…and fails closed once the canary comes back empty", () => {
    const c = evaluateCanary(CANARY_EMPTY);
    expect(c).toMatchObject({ ok: false, reason: expect.stringMatching(/^no advisory data/) });
    const v = evaluateWithCanary(MAIN_EMPTY, () => CANARY_EMPTY);
    expect(v).toMatchObject({ kind: "error", reason: expect.stringMatching(/^no advisory data/) });
  });

  it("passes a clean or moderate-only tree only with the canary's advisory", () => {
    for (const main of [CLEAN, MODERATE, AFTER]) {
      const ok = evaluateWithCanary(main, () => CANARY_REAL);
      expect(ok.kind).toBe("pass");
      if (ok.kind === "pass") expect(ok.canary?.map((f) => f.id)).toContain(CANARY.advisory);
      expect(evaluateWithCanary(main, () => CANARY_EMPTY).kind).toBe("error");
    }
  });

  it("fails closed when the canary cannot be audited or answers for another package", () => {
    const unreachable = fixture("bun-1.4.4-registry-unreachable.stderr");
    for (const canary of [
      { status: 1, stdout: "", stderr: unreachable },
      { status: null, stdout: "", stderr: "", error: "SIGKILL" },
      { status: 2, stdout: CANARY_REAL.stdout, stderr: "" },
      { status: 1, stdout: "not json", stderr: "" },
      { status: 1, stdout: MODERATE.stdout, stderr: "" },
    ] satisfies AuditRun[]) {
      expect(evaluateCanary(canary).ok).toBe(false);
      expect(evaluateWithCanary(CLEAN, () => canary)).toMatchObject({
        kind: "error",
        reason: expect.stringMatching(/^no advisory data/),
      });
    }
  });

  it("a fail or an error stands without running the canary", () => {
    const canary = vi.fn(() => CANARY_EMPTY);
    expect(evaluateWithCanary(BEFORE, canary).kind).toBe("fail");
    expect(evaluateWithCanary({ status: 1, stdout: "", stderr: "" }, canary).kind).toBe("error");
    expect(canary).not.toHaveBeenCalled();
  });

  it("the allowlist still applies before the canary", () => {
    const vite = JSON.parse(BEFORE.stdout).vite;
    const run = { status: 1, stdout: JSON.stringify({ vite }), stderr: "" };
    expect(evaluateWithCanary(run, () => CANARY_REAL, new Set(["GHSA-587h-7wmj-h5pm"])).kind).toBe(
      "pass",
    );
    expect(evaluateWithCanary(run, () => CANARY_REAL).kind).toBe("fail");
  });
});
