// Gate 1 SEC-M2 (round 3B): the deploy job's allowlist for the build's
// wrangler config.
//
//   node scripts/check_wrangler_deploy_config.mjs dist/server/wrangler.json
//
// deploy.yml's `web` job runs this from its fresh checkout, after the build
// artifact is downloaded into dist/ and before the one step that holds
// CLOUDFLARE_API_TOKEN runs `wrangler deploy --config dist/server/wrangler.json`.
// dist/ comes from a job that ran third-party build code, so that config is
// untrusted: a key such as `rules`, `base_dir`, `site`, `text_blobs`,
// `data_blobs`, `wasm_modules` or `assets.directory` can make wrangler read
// files of the deploy runner (for example /proc/self/environ, which holds the
// token) into the Worker it uploads, and a binding can reach other resources
// of the account.
//
// So the config must be exactly the one the build is known to generate:
//
//   1. The expected config is derived here, from the checkout: wrangler's own
//      reader (`unstable_readConfig`, the call @cloudflare/vite-plugin makes)
//      over wrangler.jsonc, then the plugin's output step. That step, read
//      from node_modules/@cloudflare/vite-plugin/dist/index.mjs (1.32.2,
//      `readWorkerConfig`, `resolveWorkerConfig` and `outputConfigPlugin`):
//        - deletes alias, base_dir, find_additional_modules, minify,
//          no_bundle, preserve_file_names, site, tsconfig, build and define;
//        - sets main to the entry chunk's file name, no_bundle to true, rules
//          to [{ESModule, ["**/*.js", "**/*.mjs"]}] and assets.directory to
//          the client output relative to the server output ("../client");
//        - drops an empty `unsafe`.
//      It also sets upload_source_maps when the build makes source maps;
//      this build does not, and a source map can name any file, so that key
//      is refused.
//   2. The build's config is read twice, with JSON.parse and with wrangler's
//      own reader (the parser `wrangler deploy` uses), and both must equal
//      the expected config: every key, every value, at every depth. The only
//      free value is `main`, which must be a plain relative .js/.mjs path to
//      a regular file inside dist/server.
//   3. Nothing under dist/ may be a symbolic link or anything but a regular
//      file or a directory.
//
// Exit 0 when the config may be deployed; otherwise print each problem as a
// GitHub error annotation and exit 1. Nothing here runs code from dist/.

import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const DIST = "dist";
const SERVER = path.join(DIST, "server");
const CLIENT = path.join(DIST, "client");
const CONFIG = path.join(SERVER, "wrangler.json");
const USER_CONFIG = "wrangler.jsonc";

// @cloudflare/vite-plugin readWorkerConfig: removed from the worker config.
const NOT_KEPT_BY_THE_PLUGIN = [
  "alias",
  "base_dir",
  "find_additional_modules",
  "minify",
  "no_bundle",
  "preserve_file_names",
  "site",
  "tsconfig",
  "build",
  "define",
];
// @cloudflare/vite-plugin outputConfigPlugin: the rules it writes.
const PLUGIN_RULES = [{ type: "ESModule", globs: ["**/*.js", "**/*.mjs"] }];
const MAIN = /^[A-Za-z0-9_][A-Za-z0-9_.-]*(\/[A-Za-z0-9_][A-Za-z0-9_.-]*)*\.m?js$/;

const problems = [];

function isPlainObject(value) {
  return (
    value !== null &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.getPrototypeOf(value) === Object.prototype
  );
}

function compare(actual, expected, where) {
  if (isPlainObject(expected)) {
    if (!isPlainObject(actual)) {
      problems.push(`${where}: ${JSON.stringify(actual)} is not a plain object`);
      return;
    }
    for (const key of Object.keys(actual)) {
      if (!Object.hasOwn(expected, key)) {
        problems.push(`${where}.${key}: not in the config the build generates`);
      }
    }
    for (const key of Object.keys(expected)) {
      if (!Object.hasOwn(actual, key)) {
        problems.push(`${where}.${key}: missing`);
      } else {
        compare(actual[key], expected[key], `${where}.${key}`);
      }
    }
  } else if (Array.isArray(expected)) {
    if (!Array.isArray(actual) || actual.length !== expected.length) {
      problems.push(`${where}: ${JSON.stringify(actual)} is not ${JSON.stringify(expected)}`);
      return;
    }
    expected.forEach((item, i) => compare(actual[i], item, `${where}[${i}]`));
  } else if (actual !== expected) {
    problems.push(`${where}: ${JSON.stringify(actual)} is not ${JSON.stringify(expected)}`);
  }
}

function checkTree(dir) {
  const stat = fs.lstatSync(dir, { throwIfNoEntry: false });
  if (!stat || stat.isSymbolicLink() || !stat.isDirectory()) {
    problems.push(`${dir}: not a directory`);
    return;
  }
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const entryPath = path.join(dir, entry.name);
    if (entry.isSymbolicLink()) {
      problems.push(`${entryPath}: symbolic link`);
    } else if (entry.isDirectory()) {
      checkTree(entryPath);
    } else if (!entry.isFile()) {
      problems.push(`${entryPath}: not a regular file`);
    }
  }
}

function checkMain(main) {
  if (typeof main !== "string" || !MAIN.test(main)) {
    problems.push(`main: ${JSON.stringify(main)} is not a relative .js/.mjs path inside ${SERVER}`);
    return;
  }
  const file = path.join(SERVER, main);
  const stat = fs.lstatSync(file, { throwIfNoEntry: false });
  if (!stat || !stat.isFile()) {
    problems.push(`main: ${file} is not a regular file`);
  } else if (fs.realpathSync(file) !== path.join(fs.realpathSync(SERVER), main)) {
    problems.push(`main: ${file} resolves outside ${SERVER}`);
  }
}

function expectedConfig(wrangler, main) {
  const config = wrangler.unstable_readConfig(
    { config: path.resolve(USER_CONFIG) },
    { preserveOriginalMain: true, hideWarnings: true },
  );
  for (const key of NOT_KEPT_BY_THE_PLUGIN) delete config[key];
  const output = {
    ...config,
    main,
    no_bundle: true,
    rules: PLUGIN_RULES,
    assets: { ...config.assets, directory: path.relative(SERVER, CLIENT) },
  };
  if (output.unsafe && Object.keys(output.unsafe).length === 0) output.unsafe = undefined;
  // The plugin writes JSON.stringify(output): undefined values disappear.
  return JSON.parse(JSON.stringify(output));
}

function main() {
  const requested = process.argv[2] ?? CONFIG;
  if (path.normalize(requested) !== CONFIG) {
    problems.push(`${requested}: the deploy reads ${CONFIG} only`);
    return;
  }
  checkTree(DIST);
  for (const dir of [SERVER, CLIENT]) {
    const stat = fs.lstatSync(dir, { throwIfNoEntry: false });
    if (!stat || !stat.isDirectory()) problems.push(`${dir}: missing from the build`);
  }
  const stat = fs.lstatSync(CONFIG, { throwIfNoEntry: false });
  if (!stat || !stat.isFile()) {
    problems.push(`${CONFIG}: missing from the build`);
    return;
  }
  if (problems.length > 0) return;

  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(CONFIG, "utf8"));
  } catch (error) {
    problems.push(`${CONFIG}: not strict JSON (${error.message})`);
    return;
  }
  // The locked wrangler of this checkout (installed with --ignore-scripts),
  // the same one the deploy step runs.
  const wrangler = createRequire(import.meta.url)("wrangler");
  const { rawConfig } = wrangler.experimental_readRawConfig({ config: CONFIG });
  checkMain(parsed?.main);
  const expected = expectedConfig(wrangler, parsed?.main);
  compare(parsed, expected, "config");
  compare(rawConfig, expected, "config (as wrangler reads it)");
}

try {
  main();
} catch (error) {
  problems.push(`check failed: ${error?.message ?? error}`);
}
if (problems.length > 0) {
  for (const problem of [...new Set(problems)]) {
    console.log(`::error::refusing ${CONFIG}: ${problem}`);
  }
  process.exit(1);
}
console.log(`${CONFIG} is the config the build generates from ${USER_CONFIG}; nothing else.`);
