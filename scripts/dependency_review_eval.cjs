// Offline re-run of the CI `dependency review` decision (PLAN P0-05, R11) on a
// dependency-graph compare, for checking a branch before or without a PR.
//
// It re-implements actions/dependency-review-action@v4 (SHA 2031cfc0, v4.9.0) with the
// SPDX libraries at the action's locked versions, plus this repository's stricter R11
// scan (a denied identifier anywhere in an expression). Configuration mirrors
// .github/workflows/ci.yml: fail-on-severity high, the deny-licenses list, the default
// fail-on-scopes [runtime], no allow-ghsas, no allow-dependencies-licenses.
//
// Usage:
//   gh api "repos/jamesrhule/cosmic-forge/dependency-graph/compare/$(git rev-parse origin/main)...$(git rev-parse HEAD)" > /tmp/compare.json
//   npm install --prefix /tmp/dre spdx-expression-parse@4.0.0 \
//     @onebeyond/spdx-license-satisfies@1.0.1 spdx-license-ids@3.0.20 spdx-exceptions@2.3.0
//   NODE_PATH=/tmp/dre/node_modules node scripts/dependency_review_eval.cjs /tmp/compare.json
//
// Changes with a null licence and a GitHub source URL are listed, not judged: the action
// replaces their licence with the repository's GitHub licence at run time.
"use strict";
const fs = require("fs");
const parse = require("spdx-expression-parse"); // 4.0.0 (action's isValid)
const spdxlib = require("@onebeyond/spdx-license-satisfies"); // 1.0.1 (action's satisfiesAny)

const DENY =
  "GPL-1.0-or-later, GPL-2.0-only, GPL-2.0-or-later, GPL-3.0-only, GPL-3.0-or-later, AGPL-1.0-or-later, AGPL-3.0-only, AGPL-3.0-or-later, SSPL-1.0, BUSL-1.1, CC-BY-NC-4.0, EUPL-1.2".split(
    ", ",
  );
const SEVERITIES = ["critical", "high", "moderate", "low"];
const MIN = "high";

const cleanInvalidSPDX = (e) =>
  e.replace(/(?<![\w-])OTHER(?![\w-])/g, "LicenseRef-clearlydefined-OTHER");
const isValid = (e) => {
  try {
    parse(cleanInvalidSPDX(e));
    return true;
  } catch (_) {
    return false;
  }
};
const satisfiesAny = (e, l) => {
  try {
    return spdxlib.satisfiesAny(cleanInvalidSPDX(e), l);
  } catch (_) {
    return false;
  }
};

const changes = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
// filterChangesByScopes: fail-on-scopes defaults to [runtime], and a change without a
// scope (Enterprise Server) counts as runtime (filter.ts: `change.scope || 'runtime'`).
const FAIL_ON_SCOPES = ["runtime"];
const scoped = changes.filter((c) => FAIL_ON_SCOPES.includes(c.scope || "runtime"));

// Vulnerabilities (filterChangesBySeverity): added only, severity >= high
const idx = SEVERITIES.indexOf(MIN);
const vulnerable = scoped
  .map((c) => ({
    ...c,
    vulnerabilities: (c.vulnerabilities || []).filter((v) => SEVERITIES.indexOf(v.severity) <= idx),
  }))
  .filter((c) => c.change_type === "added" && c.vulnerabilities.length > 0);

// Licences (getInvalidLicenseChanges with deny list)
const forbidden = [],
  unresolved = [],
  unlicensed = [],
  needsGhLookup = [];
const cache = new Map();
for (const c of scoped) {
  if (c.change_type === "removed") continue;
  if (c.license === null) {
    if (c.source_repository_url !== null) needsGhLookup.push(c);
    else unlicensed.push(c);
    continue;
  }
  const lic = c.license;
  if (lic === "NOASSERTION") {
    unlicensed.push(c);
    continue;
  }
  if (cache.get(lic) === undefined) {
    if (isValid(lic)) cache.set(lic, !satisfiesAny(lic, DENY));
    else {
      unresolved.push(c);
    }
  }
  if (cache.get(lic) === false) forbidden.push(c);
}

// Stricter lane check (task acceptance): any denied identifier anywhere in the expression.
const tok = (s) => (s || "").match(/[A-Za-z0-9.+-]+/g) || [];
const anyDenied = scoped.filter(
  (c) => c.change_type === "added" && tok(c.license).some((t) => DENY.includes(t)),
);

const fmt = (c) => `${c.manifest} » ${c.name}@${c.version}`;
const out = {
  added: scoped.filter((c) => c.change_type === "added").length,
  removed: scoped.filter((c) => c.change_type === "removed").length,
  vulnerable: vulnerable.map(
    (c) =>
      `${fmt(c)} :: ` +
      c.vulnerabilities.map((v) => `${v.severity} ${v.advisory_ghsa_id}`).join(", "),
  ),
  forbidden: forbidden.map((c) => `${fmt(c)} :: ${c.license}`),
  unresolved: unresolved.map((c) => `${fmt(c)} :: ${c.license}`),
  unlicensed_null_no_repo: unlicensed.map(fmt),
  null_licence_with_repo_action_fetches_github_licence: needsGhLookup.map(
    (c) => `${fmt(c)} :: ${c.source_repository_url}`,
  ),
  any_denied_identifier_in_expression: anyDenied.map((c) => `${fmt(c)} :: ${c.license}`),
};
console.log(JSON.stringify(out, null, 2));
const fail = vulnerable.length + forbidden.length + unresolved.length;
console.log(
  `ACTION VERDICT: ${fail === 0 ? "PASS" : "FAIL"} (vulnerable=${vulnerable.length}, forbidden=${forbidden.length}, unresolved=${unresolved.length}; GitHub-licence lookups pending=${needsGhLookup.length})`,
);
