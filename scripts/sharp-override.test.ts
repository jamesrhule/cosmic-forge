// @vitest-environment node
/**
 * Guard for the `sharp` override in package.json (lane W0-npm, N4).
 *
 * `overrides.sharp` (0.35.5) lifts sharp out of the range miniflare declares
 * (`^0.34.5` in miniflare 4.20260410.0, pinned by @cloudflare/vite-plugin
 * 1.32.2) to get the GHSA-f88m-g3jw-g9cj / GHSA-rgj7-g3m4-5g8c /
 * GHSA-wq5f-xc86-pv6w fixes. miniflare `import()`s sharp only in its local
 * Images-binding fetcher, so the override is safe only while wrangler.jsonc
 * declares no Images binding (top level or any `env.*`).
 *
 * If this test fails: either drop the Images binding, or (better) remove the
 * sharp override. The override is meant to go at the next
 * @cloudflare/vite-plugin upgrade, to a release whose miniflare asks for a
 * patched sharp itself; see docs/build/lanes/W0-deps.md (W0-npm, N4).
 */
import { existsSync, readFileSync } from "node:fs";
import ts from "typescript";
import { describe, expect, it } from "vitest";

const ROOT = new URL("../", import.meta.url);
const read = (p: string) => readFileSync(new URL(p, ROOT), "utf8");

/** Parse JSON with comments and trailing commas (wrangler.jsonc). */
function parseJsonc(name: string, text: string): Record<string, unknown> {
  const { config, error } = ts.parseConfigFileTextToJson(name, text);
  if (error)
    throw new Error(`${name}: ${ts.flattenDiagnosticMessageText(error.messageText, "\n")}`);
  return config as Record<string, unknown>;
}

/** Every Images binding declared at the top level or in a named environment. */
export function imagesBindings(config: Record<string, unknown>): string[] {
  const found: string[] = [];
  if (config.images !== undefined) found.push("images");
  const envs = (config.env ?? {}) as Record<string, Record<string, unknown> | undefined>;
  for (const [name, env] of Object.entries(envs)) {
    if (env?.images !== undefined) found.push(`env.${name}.images`);
  }
  return found;
}

/**
 * Does `version` satisfy a caret `range` (`^MAJOR.MINOR.PATCH`)? Throws on any
 * other range form, so a miniflare that changes its range shape makes this
 * guard fail loudly instead of passing by accident.
 */
export function satisfiesCaret(version: string, range: string): boolean {
  const r = /^\^(\d+)\.(\d+)\.(\d+)$/.exec(range.trim());
  const v = /^(\d+)\.(\d+)\.(\d+)$/.exec(version.trim());
  if (!r || !v) throw new Error(`unsupported version/range: ${version} vs ${range}`);
  const [rM, rm, rp] = r.slice(1).map(Number);
  const [vM, vm, vp] = v.slice(1).map(Number);
  const cmp = vM - rM || vm - rm || vp - rp;
  if (cmp < 0) return false;
  // ^0.0.z pins the patch, ^0.y.z pins the minor, ^x.y.z pins the major.
  if (rM > 0) return vM === rM;
  if (rm > 0) return vM === 0 && vm === rm;
  return vM === 0 && vm === 0 && vp === rp;
}

/** The miniflare that @cloudflare/vite-plugin resolves (nested copy first). */
function miniflareManifest(): { version: string; dependencies?: Record<string, string> } {
  const nested = "node_modules/@cloudflare/vite-plugin/node_modules/miniflare/package.json";
  return JSON.parse(
    read(existsSync(new URL(nested, ROOT)) ? nested : "node_modules/miniflare/package.json"),
  );
}

describe("sharp override vs. Images binding", () => {
  it("wrangler.jsonc declares no Images binding while sharp is overridden outside miniflare's range", () => {
    const override = (JSON.parse(read("package.json")).overrides ?? {}).sharp as string | undefined;
    if (override === undefined) return; // no override, nothing to guard
    const miniflare = miniflareManifest();
    const range = miniflare.dependencies?.sharp;
    expect(range, `miniflare ${miniflare.version} no longer depends on sharp`).toBeDefined();
    if (satisfiesCaret(override, range!)) return; // the override is inside miniflare's own range
    const bindings = imagesBindings(parseJsonc("wrangler.jsonc", read("wrangler.jsonc")));
    expect(
      bindings,
      `wrangler.jsonc declares an Images binding (${bindings.join(", ")}) while package.json ` +
        `overrides sharp to ${override}, outside miniflare ${miniflare.version}'s ${range}. ` +
        "Remove the sharp override (meant to go at the next @cloudflare/vite-plugin upgrade; " +
        "docs/build/lanes/W0-deps.md, W0-npm N4) or drop the binding.",
    ).toEqual([]);
  });

  it("finds Images bindings in JSONC with comments, at the top level and per environment", () => {
    const text = `{
      // a comment
      "name": "x",
      "images": { "binding": "IMAGES" }, /* block */
      "env": { "staging": { "images": { "binding": "IMG" } }, "prod": {}, },
    }`;
    expect(imagesBindings(parseJsonc("t.jsonc", text))).toEqual(["images", "env.staging.images"]);
    expect(imagesBindings(parseJsonc("t.jsonc", `{ "name": "x" }`))).toEqual([]);
  });

  it("compares caret ranges the way npm does", () => {
    expect(satisfiesCaret("0.34.5", "^0.34.5")).toBe(true);
    expect(satisfiesCaret("0.34.9", "^0.34.5")).toBe(true);
    expect(satisfiesCaret("0.35.5", "^0.34.5")).toBe(false);
    expect(satisfiesCaret("0.34.4", "^0.34.5")).toBe(false);
    expect(satisfiesCaret("1.2.0", "^1.0.0")).toBe(true);
    expect(satisfiesCaret("2.0.0", "^1.0.0")).toBe(false);
    expect(() => satisfiesCaret("0.35.5", ">=0.34.5")).toThrow(/unsupported/);
  });

  it("today: the override is outside miniflare's range, so the guard is live", () => {
    const override = JSON.parse(read("package.json")).overrides?.sharp as string | undefined;
    const range = miniflareManifest().dependencies?.sharp;
    if (override === undefined || range === undefined) return;
    expect(satisfiesCaret(override, range)).toBe(false);
  });
});
